import secrets
import time
import uuid
import logging
from collections import defaultdict, deque
from datetime import datetime,timezone
from typing import Literal
from fastapi import FastAPI, Depends, HTTPException, Header, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select, func, text
from sqlalchemy.orm import Session as DBSession
from apps.api.config import settings
from apps.api.db import session_dependency, utcnow
from apps.api.models import Player, Club, Fixture, Gameweek, Manager, Tenure, FootballEvent, TacticalObservation, HistoricalStat, Identity, ModelVersion, Prediction, Source, Job, Audit, Season
from apps.api.cache import cache
from apps.api.events import EventInput, ingest_event

app=FastAPI(title='FPL Oracle AI',version='0.1.0')
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origins.split(','),allow_credentials=False,allow_methods=['GET','POST'],allow_headers=['Content-Type','Authorization'])
limits=defaultdict(deque)
log=logging.getLogger('oracle')

@app.middleware('http')
async def trace_and_limit(request: Request, call_next):
    request_id=uuid.uuid4().hex
    key=request.client.host if request.client else 'unknown'
    now=time.monotonic()
    if len(limits)>10000: limits.clear()
    bucket=limits[key]
    while bucket and bucket[0]<now-60: bucket.popleft()
    if len(bucket)>=120:
        return JSONResponse({'error':{'code':'rate_limited','message':'Please retry shortly','request_id':request_id}},status_code=429,headers={'Retry-After':'60'})
    bucket.append(now)
    request.state.request_id=request_id
    response=await call_next(request)
    response.headers['X-Request-ID']=request_id
    response.headers['X-Content-Type-Options']='nosniff'
    if '/managers/fpl/' in request.url.path or '/planning/' in request.url.path or request.method!='GET': response.headers['Cache-Control']='no-store'
    log.info('request',extra={'request_id':request_id,'path':request.url.path,'status':response.status_code})
    return response

@app.exception_handler(HTTPException)
async def http_error(request,exc):
    return JSONResponse({'error':{'code':str(exc.status_code),'message':exc.detail,'request_id':getattr(request.state,'request_id',None)}},status_code=exc.status_code)

@app.exception_handler(RequestValidationError)
async def validation_error(request,exc):
    return JSONResponse({'error':{'code':'validation_error','message':'Invalid request parameters','details':jsonable_encoder(exc.errors(),custom_encoder={ValueError:str}),'request_id':getattr(request.state,'request_id',None)}},status_code=422)

@app.exception_handler(Exception)
async def server_error(request,exc):
    log.exception('request_failed',extra={'request_id':getattr(request.state,'request_id',None)})
    return JSONResponse({'error':{'code':'service_error','message':'Service unavailable; inspect server logs with the request ID','request_id':getattr(request.state,'request_id',None)}},status_code=503)

def admin(authorization: str=Header(default='')):
    if not settings.admin_token or not secrets.compare_digest(authorization,'Bearer '+settings.admin_token):
        raise HTTPException(401,'Internal operator token required')

def encode(row):
    values={c.name:getattr(row,c.name) for c in row.__table__.columns}
    return jsonable_encoder({k:(v.replace(tzinfo=timezone.utc) if isinstance(v,datetime) and v.tzinfo is None else v) for k,v in values.items()})

def page(session,model,offset=0,limit=50,query=None):
    query=query if query is not None else select(model)
    rows=session.scalars(query.offset(offset).limit(limit)).all()
    return {'items':[encode(r) for r in rows],'offset':offset,'limit':limit,'total':session.scalar(select(func.count()).select_from(query.subquery()))}

@app.get('/api/v1/health')
def health(session:DBSession=Depends(session_dependency)):
    try:
        session.execute(text('SELECT 1'))
        session.execute(select(Source).limit(1))
        session.execute(text('SELECT ingested_at FROM source_evidence LIMIT 0'))
    except Exception:
        raise HTTPException(503,'Database unavailable or migrations required')
    return {'status':'ok','database':'ready','service':'FPL Oracle AI'}

@app.get('/api/v1/players')
def players(offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=500),position:int|None=Query(None,ge=1,le=4),club_id:int|None=Query(None,gt=0),search:str=Query('',max_length=100),session:DBSession=Depends(session_dependency)):
    query=select(Player).order_by(Player.name)
    if position: query=query.where(Player.position==position)
    if club_id: query=query.where(Player.club_id==club_id)
    if search: query=query.where(Player.name.ilike('%'+search+'%'))
    return page(session,Player,offset,limit,query)

@app.get('/api/v1/players/{player_id}')
def player(player_id:int,session:DBSession=Depends(session_dependency)):
    row=session.get(Player,player_id)
    if not row: raise HTTPException(404,'Player not found')
    from ml.features.intelligence import context_at
    tenure=session.scalar(select(Tenure).where(Tenure.club_id==row.club_id,Tenure.ends_at.is_(None)))
    current_manager=session.get(Manager,tenure.manager_id) if tenure else None
    return {**encode(row),'current_manager':{'id':current_manager.id,'name':current_manager.name,'tenure_started':tenure.starts_at.isoformat(),'date_precision':'day for reviewed directory records'} if current_manager else None,'context':context_at(session,row,utcnow()),'coverage':{'tactical_fit':'unavailable until validated','manager_history':'only ingested verified tenures'}}

@app.get('/api/v1/clubs')
def clubs(session:DBSession=Depends(session_dependency)):
    return page(session,Club,limit=100)

@app.get('/api/v1/fixtures')
def fixtures(offset:int=Query(0,ge=0),limit:int=Query(100,ge=1,le=500),session:DBSession=Depends(session_dependency)):
    return page(session,Fixture,offset,limit,select(Fixture).order_by(Fixture.kickoff))

@app.get('/api/v1/gameweeks/current')
def current(session:DBSession=Depends(session_dependency)):
    row=session.scalar(select(Gameweek).where(Gameweek.deadline>utcnow()).order_by(Gameweek.deadline))
    if not row: row=session.scalar(select(Gameweek).where(Gameweek.current.is_(True)).order_by(Gameweek.deadline.desc()))
    return {'item':encode(row) if row else None,'reason':None if row else 'No ingested gameweek'}

def latest_predictions(session,horizon=1):
    # Refreshes may affect only one club. Select the latest row per player, rather than one global batch.
    gw=session.scalar(select(Gameweek).where(Gameweek.deadline>utcnow()).order_by(Gameweek.deadline))
    if not gw: return []
    sub=select(Prediction.player_id,func.max(Prediction.id).label('id')).where(Prediction.horizon==horizon,Prediction.event==gw.event).group_by(Prediction.player_id).subquery()
    rows=session.scalars(select(Prediction).join(sub,Prediction.id==sub.c.id)).all()
    output=[]
    now=utcnow()
    player_map={p.id:p for p in session.scalars(select(Player).where(Player.id.in_([r.player_id for r in rows])))}
    pending=session.scalars(select(Job).where(Job.kind=='refresh',Job.status.in_(['pending','running','dead']))).all()
    for row in rows:
        p=player_map.get(row.player_id)
        if p:
            invalidated=any(j.id>row.values.get('refresh_job_highwater',0) and (p.club_id in j.payload.get('clubs',[]) or p.id==j.payload.get('player_id')) for j in pending)
            values=dict(row.values)
            if p.registration_state!='verified' or p.status=='u':
                values.update(expected_points=None,median=None,lower=None,upper=None,p6=None,p10=None,p15=None,p60=None,p_zero_minutes=None,unavailable_reason='Awaiting verified FPL registration after a confirmed club change')
            output.append({**encode(p),**values,'prediction_id':row.id,'model_id':row.model_id,'batch':row.batch,'event':row.event,'horizon':row.horizon,'generated_at':row.generated_at.replace(tzinfo=timezone.utc).isoformat(),'stale':p.registration_state!='verified' or bool(row.values.get('source_stale',False)) or invalidated or (now-row.generated_at.replace(tzinfo=timezone.utc)).total_seconds()>3600,'pending_refresh':invalidated})
    return sorted(output,key=lambda p:p['expected_points'] if p['expected_points'] is not None else float('-inf'),reverse=True)

@app.get('/api/v1/predictions')
def predictions(horizon:int=Query(1,ge=1,le=5),offset:int=Query(0,ge=0),limit:int=Query(100,ge=1,le=500),session:DBSession=Depends(session_dependency)):
    if horizon not in (1,3,5): raise HTTPException(422,'Supported horizons: 1, 3, 5')
    key=f'predictions:{horizon}:{offset}:{limit}'
    value,state=cache.read(key)
    if state=='fresh':return {**value,'cache_state':state}
    if state=='stale' and cache.redis:
        job_key=f'cache:{cache.version()}:{key}:{int(time.time()//60)}'
        if not session.scalar(select(Job).where(Job.key==job_key)):
            from sqlalchemy.exc import IntegrityError
            try:
                session.add(Job(key=job_key,kind='cache_predictions',payload={'key':key,'horizon':horizon,'offset':offset,'limit':limit}));session.commit()
            except IntegrityError:session.rollback()
        return {**value,'cache_state':'stale; refresh queued'}
    with cache.lock('public:'+key,ttl=15) as acquired:
        if not acquired:raise HTTPException(503,'Forecast cache is warming; retry shortly')
        rows=latest_predictions(session,horizon)
        value={'items':rows[offset:offset+limit],'total':len(rows),'offset':offset,'limit':limit,'reason':None if rows else 'No published trained-model predictions'}
        cache.set(key,value,60,stale_ttl=300)
        return {**value,'cache_state':'fresh'}

@app.get('/api/v1/predictions/{player_id}')
def player_predictions(player_id:int,session:DBSession=Depends(session_dependency)):
    rows=session.scalars(select(Prediction).where(Prediction.player_id==player_id).order_by(Prediction.id.desc()).limit(30)).all()
    return {'items':[encode(r) for r in rows],'total':len(rows)}

@app.get('/api/v1/managers')
def managers(session:DBSession=Depends(session_dependency)):
    result=page(session,Manager,limit=100)
    for item in result['items']:
        tenure=session.scalar(select(Tenure).where(Tenure.manager_id==item['id'],Tenure.ends_at.is_(None)))
        club=session.get(Club,tenure.club_id) if tenure else None
        item['current_club']=club.name if club else None
        item['tenure_started']=tenure.starts_at.date().isoformat() if tenure else None
    return result

@app.get('/api/v1/managers/{manager_id}')
def manager(manager_id:int,session:DBSession=Depends(session_dependency)):
    row=session.get(Manager,manager_id)
    if not row: raise HTTPException(404,'Manager not found')
    tenures=session.scalars(select(Tenure).where(Tenure.manager_id==manager_id).order_by(Tenure.starts_at)).all()
    from apps.api.intelligence import manager_summary
    return {**encode(row),'tenures':[encode(t) for t in tenures],'club_statistics':jsonable_encoder(manager_summary(session,manager_id)),'coverage':'Verified ingested records only'}

@app.get('/api/v1/managers/fpl/{manager_id}/squad')
async def import_squad(manager_id:int,gameweek:int=Query(...,ge=1,le=38),session:DBSession=Depends(session_dependency)):
    if not 1<=manager_id<=999999999: raise HTTPException(422,'Invalid public manager ID')
    from ml.ingestion.fpl import FPLClient
    try:
        payload=await FPLClient().manager_squad(manager_id,gameweek)
    except Exception: raise HTTPException(502,'Public FPL import unavailable')
    from apps.api.public_squad import resolve_public_squad
    try:
        payload['resolved']=resolve_public_squad(session,payload,manager_id,gameweek,{h:latest_predictions(session,h) for h in (1,3,5)})
    except (ValueError,KeyError):raise HTTPException(502,'Public squad response could not be resolved safely; check current-season data')
    return payload

@app.get('/api/v1/tactics/teams')
def tactics(session:DBSession=Depends(session_dependency)):
    return page(session,TacticalObservation,limit=100,query=select(TacticalObservation).order_by(TacticalObservation.match_at.desc()))

@app.get('/api/v1/transfers/events')
def events(session:DBSession=Depends(session_dependency)):
    result=page(session,FootballEvent,limit=100,query=select(FootballEvent).order_by(FootballEvent.observed_at.desc()))
    from apps.api.models import Evidence
    for item in result['items']:
        ev=session.get(Evidence,item['evidence_id'])
        item['source_url']=ev.uri; item['source_id']=ev.source_id
    return result

@app.get('/api/v1/prediction-changes')
def prediction_changes(session:DBSession=Depends(session_dependency)):
    return page(session,Audit,limit=50,query=select(Audit).where(Audit.action=='prediction.changes').order_by(Audit.id.desc()))

@app.get('/api/v1/historical/players/{player_id}')
def historical_player(player_id:int,session:DBSession=Depends(session_dependency)):
    identities=session.scalars(select(Identity).where(Identity.player_id==player_id)).all()
    rows=[]
    for identity in identities:
        rows.extend(session.scalars(select(HistoricalStat).where(HistoricalStat.season==identity.season_id,HistoricalStat.fpl_id==identity.fpl_id).order_by(HistoricalStat.kickoff.desc()).limit(100)).all())
    return {'items':[encode(r) for r in sorted(rows,key=lambda r:r.kickoff,reverse=True)[:300]],'identity_policy':'Stable provider code only; unresolved IDs excluded'}

@app.get('/api/v1/models/metrics')
def model_metrics(session:DBSession=Depends(session_dependency)):
    result=page(session,ModelVersion,limit=100,query=select(ModelVersion).order_by(ModelVersion.created_at.desc()))
    for item in result['items']:item.pop('artifact',None)
    return result

@app.get('/api/v1/backtesting')
def backtesting():
    path=settings.artifact_dir/'backtest.json'
    if not path.exists():return {'items':[],'reason':'No completed rolling backtest'}
    import json
    return {'items':json.loads(path.read_text()),'limitations':['Retrospective archive simulation','Unavailable context groups cannot demonstrate manager/tactical lift','Squad-decision backtesting is not yet implemented']}

@app.get('/api/v1/data-health')
def data_health(session:DBSession=Depends(session_dependency)):
    coverage=session.execute(select(HistoricalStat.season,func.count()).group_by(HistoricalStat.season)).all()
    sources=[encode(s) for s in session.scalars(select(Source))]
    latest_model=session.scalar(select(ModelVersion).where(ModelVersion.promoted.is_(True)))
    upcoming=session.scalar(select(Gameweek).where(Gameweek.deadline>utcnow()).order_by(Gameweek.deadline))
    published=session.scalar(select(func.count()).select_from(select(Prediction.player_id,Prediction.horizon).where(Prediction.event==upcoming.event).group_by(Prediction.player_id,Prediction.horizon).subquery())) if upcoming else 0
    player_count=session.scalar(select(func.count()).select_from(Player))
    latest_history=session.scalar(select(Audit).where(Audit.action=='matches.synced').order_by(Audit.id.desc()))
    history_batch=latest_history.payload if latest_history else {}
    history_complete=bool(upcoming and history_batch.get('season')==upcoming.season_id and history_batch.get('offset')==0 and history_batch.get('players',0)>=player_count)
    history_warning='Current-season history requests completed for all registered players; empty upstream histories remain empty' if history_complete else 'Current-season player match history is only partially synchronized'
    return {'sources':sources,'coverage':[{'season':s,'rows':n} for s,n in coverage],'research_mode':not latest_model or latest_model.metrics.get('exact_deadline_fraction',0)<1,'counts':{'published_forecasts':published,'players':session.scalar(select(func.count()).select_from(Player)),'fixtures':session.scalar(select(func.count()).select_from(Fixture)),'predictions':session.scalar(select(func.count()).select_from(Prediction)),'managers':session.scalar(select(func.count()).select_from(Manager))},'jobs':[encode(j) for j in session.scalars(select(Job).order_by(Job.id.desc()).limit(20))],'cache':{'mode':'redis' if cache.redis else 'local development fallback','hits':cache.hits,'stale_hits':cache.stale_hits,'misses':cache.misses,'version':cache.version()},'warnings':['Historical gameweek deadline snapshots remain unavailable; archive model results are retrospective research','Current manager dates are verified; previous-club histories and licensed tactical observations remain incomplete',history_warning,'2026/27 availability follows upstream responses','No paid provider configured; no fabricated fallback data']}

class OptimizeInput(BaseModel):
    budget:int=Field(1000,ge=1,le=2000)
    horizon:Literal[1,3,5]=1
    strategy:Literal['CONSERVATIVE','BALANCED','AGGRESSIVE']='BALANCED'
    locked:list[int]=Field(default_factory=list,max_length=15)
    excluded:list[int]=Field(default_factory=list,max_length=500)
    current:list[int]=Field(default_factory=list,max_length=15)
    free_transfers:int=Field(1,ge=0,le=5)
    chip:Literal['wildcard','free_hit','bench_boost','triple_captain']|None=None

def optimize_request(data,session):
    gw=session.scalar(select(Gameweek).where(Gameweek.deadline>utcnow()).order_by(Gameweek.deadline))
    season=session.get(Season,gw.season_id) if gw else None
    if not season or not season.rules_verified:
        raise HTTPException(409,'Current season rules have not been verified; optimization is disabled')
    if data.current or data.chip:
        raise HTTPException(409,'Selling values, transfer rollover and chip availability are not yet verified for this season')
    rows=[p for p in latest_predictions(session,data.horizon) if p['expected_points'] is not None and p['club_id'] is not None and p['status']!='u']
    if not rows or any(r['stale'] for r in rows): raise HTTPException(409,'Fresh trained-model prediction batch required')
    from ml.optimization.squad import optimize
    try:
        result=optimize(rows,data.budget,data.strategy,data.locked,data.excluded,data.current,data.free_transfers,season.rules.get('hit_cost',4),data.chip)
    except ValueError as exc: raise HTTPException(422,str(exc))
    session.add(Audit(action='optimization.complete',payload={'input':data.model_dump(),'result':result}))
    session.commit()
    return result

@app.post('/api/v1/optimizer/squad')
def squad_opt(data:OptimizeInput,session:DBSession=Depends(session_dependency)): return optimize_request(data,session)

from apps.api.public_squad import ImportedOptimizeInput

@app.post('/api/v1/optimizer/imported')
async def imported_squad_opt(data:ImportedOptimizeInput,session:DBSession=Depends(session_dependency)):
    payload=await import_squad(data.manager_id,data.gameweek,session)
    from apps.api.public_squad import optimize_imported_squad
    season=session.get(Season,payload['resolved']['season'])
    try:
        return optimize_imported_squad(session,payload['resolved'],data,latest_predictions(session,data.horizon),bool(season and season.rules_verified))
    except ValueError as exc:raise HTTPException(409,str(exc))
@app.post('/api/v1/optimizer/transfers')
def transfers_opt(data:OptimizeInput,session:DBSession=Depends(session_dependency)):
    if len(set(data.current))!=15: raise HTTPException(422,'15 current player IDs required')
    raise HTTPException(409,'Selling-value and season-specific rollover planning not yet validated')
@app.post('/api/v1/optimizer/wildcard')
def wildcard(data:OptimizeInput,session:DBSession=Depends(session_dependency)):
    data.chip='wildcard'
    return optimize_request(data,session)
@app.post('/api/v1/optimizer/captain')
def captain(data:OptimizeInput,session:DBSession=Depends(session_dependency)):
    rows=[r for r in latest_predictions(session,data.horizon) if r['expected_points'] is not None]
    if data.current: rows=[r for r in rows if r['id'] in data.current]
    if not rows: raise HTTPException(409,'No available predictions')
    return {'items':rows[:10],'assumption':'Captain doubles points when playing; fallback and automatic substitutions not simulated'}

class AnalystInput(BaseModel):
    question:str=Field(min_length=3,max_length=2000)
    player_ids:list[int]=Field(default_factory=list,max_length=10)

class SquadValidationInput(BaseModel):
    player_ids:list[int]=Field(min_length=15,max_length=15)
    starters:list[int]=Field(min_length=11,max_length=11)
    captain:int=Field(gt=0)
    vice_captain:int=Field(gt=0)
    budget:int=Field(1000,ge=1,le=2000)

@app.post('/api/v1/squad/validate')
def validate_manual_squad(data:SquadValidationInput,session:DBSession=Depends(session_dependency)):
    from ml.optimization.squad import validate_squad
    rows=session.scalars(select(Player).where(Player.id.in_(data.player_ids))).all()
    values=[encode(p) for p in rows]
    errors=validate_squad(values,data.budget,data.starters)
    if any(p.registration_state!='verified' or p.status=='u' for p in rows):errors.append('All selected players need verified, available FPL registration')
    if data.captain not in data.starters or data.vice_captain not in data.starters or data.captain==data.vice_captain:
        errors.append('Distinct captain and vice-captain must belong to the starting XI')
    return {'valid':not errors,'errors':errors,'cost':sum(p.price for p in rows),'budget':data.budget,'scope':'Squad composition and starting XI only; ownership and chip eligibility not checked'}

class ComparisonInput(BaseModel):
    outgoing:int=Field(gt=0)
    incoming:int=Field(gt=0)
    horizon:Literal[1,3,5]=1
    user_point_cost:float=Field(0,ge=0,le=100)

@app.post('/api/v1/transfers/compare')
def compare_transfer(data:ComparisonInput,session:DBSession=Depends(session_dependency)):
    selected={p['id']:p for p in latest_predictions(session,data.horizon) if p['id'] in {data.outgoing,data.incoming} and p['expected_points'] is not None}
    if len(selected)!=2: raise HTTPException(409,'Two distinct players with stored forecasts are required')
    outgoing,incoming=selected[data.outgoing],selected[data.incoming]
    return {'outgoing':outgoing,'incoming':incoming,'expected_points_gain':incoming['expected_points']-outgoing['expected_points'],'user_supplied_point_cost':data.user_point_cost,'expected_net_gain':incoming['expected_points']-outgoing['expected_points']-data.user_point_cost,'current_buy_price_difference':incoming['price']-outgoing['price'],'limitations':['Research comparison; selling values and ownership not checked','User-supplied point cost is not a verified season-specific transfer-hit calculation','Uncertainty in the difference is not calibrated jointly']}

@app.post('/api/v1/analyst/query')
def analyst(data:AnalystInput,session:DBSession=Depends(session_dependency)):
    rows=[r for r in latest_predictions(session) if r['expected_points'] is not None]
    if data.player_ids: rows=[r for r in rows if r['id'] in data.player_ids]
    elif rows: return {'recommendation':'Select players to compare; no identities inferred from ambiguous names.','evidence':[],'confidence':'unavailable','mode':'structured retrieval without LLM'}
    if not rows: return {'recommendation':'No stored predictions available. Ingest data and train a model first.','evidence':[],'confidence':'unavailable','mode':'structured retrieval without LLM'}
    best=max(rows,key=lambda r:r['expected_points'])
    return {'recommendation':f"{best['name']} has the highest stored expected points among the selected players.",'evidence':[{'player_id':r['id'],'name':r['name'],'expected_points':r['expected_points'],'interval':[r['lower'],r['upper']],'model':r['model_id'],'source_timestamp':r['generated_at'],'cold_start':r['cold_start']} for r in rows],'risk':'Association from historical data, not a causal manager or transfer effect. Forecasts can be stale.','confidence':'See empirical intervals; no calibrated recommendation-confidence score','assumptions':['Selected players only','No invented injury, manager or transfer reports'],'mode':'structured retrieval without LLM'}

@app.post('/api/v1/internal/events',dependencies=[Depends(admin)])
def ingest(data:EventInput,session:DBSession=Depends(session_dependency)):
    try:
        row=ingest_event(session,data); session.commit(); cache.invalidate(); return encode(row)
    except ValueError as exc:
        session.rollback(); raise HTTPException(409,str(exc))

class SourceInput(BaseModel):
    id:str=Field(pattern=r'^[a-z0-9_-]{1,80}$')
    url:str=Field(pattern=r'^https://',max_length=600)
    official:bool=False
    permitted:bool=False
    license:str=Field(max_length=2000)

@app.post('/api/v1/internal/sources',dependencies=[Depends(admin)])
def register_source(data:SourceInput,session:DBSession=Depends(session_dependency)):
    if session.get(Source,data.id): raise HTTPException(409,'Source exists; review changes offline')
    row=Source(**data.model_dump()); session.add(row); session.commit(); return encode(row)

class ManagerInput(BaseModel):
    name:str=Field(min_length=2,max_length=160)

@app.post('/api/v1/internal/managers',dependencies=[Depends(admin)])
def create_manager(data:ManagerInput,session:DBSession=Depends(session_dependency)):
    row=Manager(name=data.name); session.add(row); session.commit(); return encode(row)

from apps.api.intelligence import TacticalInput,ingest_tactical
@app.post('/api/v1/internal/tactics',dependencies=[Depends(admin)])
def post_tactics(data:TacticalInput,session:DBSession=Depends(session_dependency)):
    try:
        row=ingest_tactical(session,data);session.commit();cache.invalidate();return encode(row)
    except ValueError as exc:
        session.rollback();raise HTTPException(409,str(exc))

# Additive read models for visual presentation; existing routes remain unchanged.
from apps.api.presentation import router as presentation_router
app.include_router(presentation_router)
from apps.api.transfer_planning import router as transfer_planning_router
app.include_router(transfer_planning_router)
