"""Bounded, additive read models for visual UI. No fabricated chart observations."""
import hashlib
import json
from pathlib import Path
from fastapi import APIRouter,Depends,Query,HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select,func,or_
from sqlalchemy.orm import Session
from apps.api.db import session_dependency
from apps.api.config import settings
from apps.api.models import Player,Club,Identity,HistoricalStat,Prediction,Audit,FootballEvent,Evidence,Fixture,Gameweek,Tenure,Manager,ManagerMatchStat,TacticalObservation,AvailabilitySnapshot

router=APIRouter(prefix='/api/v1/presentation')

def encoded(value):
    return jsonable_encoder(value)

def player_label(p,clubs):
    c=clubs.get(p.club_id) if p else None
    return {'id':p.id if p else None,'name':p.name if p else 'Unresolved player','position':p.position if p else None,'price':p.price if p else None,'club_id':p.club_id if p else None,'club':c.name if c else None,'club_short':c.short_name if c else None}

@router.get('/changes')
def changes(horizon:int=Query(1,ge=1,le=5),search:str=Query('',max_length=100),offset:int=Query(0,ge=0),limit:int=Query(12,ge=1,le=50),session:Session=Depends(session_dependency)):
    audits=session.scalars(select(Audit).where(Audit.action=='prediction.changes').order_by(Audit.id.desc()).limit(50)).all()
    flat=[(a,c) for a in audits for c in a.payload.get('changes',[]) if c.get('horizon')==horizon]
    players={p.id:p for p in session.scalars(select(Player).where(Player.id.in_({c.get('player_id') for _,c in flat})))}
    clubs={c.id:c for c in session.scalars(select(Club))}
    flat=[(a,c) for a,c in flat if not search or search.casefold() in (players[c['player_id']].name.casefold() if c.get('player_id') in players else '')]
    chosen=flat[offset:offset+limit]
    ids={c.get(key) for _,c in chosen for key in ('before_id','after_id') if c.get(key)}
    preds={p.id:p for p in session.scalars(select(Prediction).where(Prediction.id.in_(ids)))}
    output=[]
    for audit,c in chosen:
        before,after=preds.get(c.get('before_id')),preds.get(c.get('after_id'))
        event=session.get(FootballEvent,audit.payload.get('event_id')) if isinstance(audit.payload.get('event_id'),int) else None
        old=c.get('expected_points_before');new=c.get('expected_points_after')
        output.append({'id':f"{audit.id}:{c.get('player_id')}:{horizon}",'player':player_label(players.get(c.get('player_id')),clubs),'horizon':horizon,'before':{'mean':old,'interval':c.get('interval_before'),'timestamp':before.generated_at if before else None,'event':before.event if before else None,'model':c.get('model_before'),'feature_snapshot':c.get('feature_snapshot_before')},'after':{'mean':new,'interval':c.get('interval_after'),'timestamp':after.generated_at if after else None,'event':after.event if after else None,'model':c.get('model_after'),'feature_snapshot':c.get('feature_snapshot_after')},'delta':new-old if isinstance(old,(int,float)) and isinstance(new,(int,float)) else None,'percent_change':100*(new-old)/old if isinstance(old,(int,float)) and old>0 and isinstance(new,(int,float)) else None,'model_changed':c.get('model_before')!=c.get('model_after'),'feature_changed':c.get('feature_snapshot_before')!=c.get('feature_snapshot_after'),'same_target':bool(before and after and before.event==after.event and before.horizon==after.horizon),'event':{'kind':event.kind,'status':event.status,'announced_at':event.announced_at} if event else None,'recorded_at':audit.created_at})
    return encoded({'items':output,'total':len(flat),'offset':offset,'limit':limit})

@router.get('/fixtures')
def fixtures(session:Session=Depends(session_dependency)):
    clubs={c.id:c for c in session.scalars(select(Club))}
    evidence=session.scalar(select(Evidence).where(Evidence.source_id=='fpl',Evidence.uri.like('%/fixtures/')).order_by(Evidence.id.desc()))
    payload=evidence.payload if evidence else {}
    raw=payload if isinstance(payload,list) else payload.get('fixtures',[])
    difficulty={f['id']:f for f in raw}
    rows=[]
    for f in session.scalars(select(Fixture).order_by(Fixture.kickoff)):
        source=difficulty.get(f.provider_id,{})
        rows.append({'id':f.id,'event':f.event,'home_id':f.home_id,'away_id':f.away_id,'kickoff':f.kickoff,'finished':f.finished,'home_score':f.home_score,'away_score':f.away_score,'home_difficulty':source.get('team_h_difficulty'),'away_difficulty':source.get('team_a_difficulty')})
    return encoded({'items':rows,'clubs':[{'id':c.id,'name':c.name,'short_name':c.short_name} for c in clubs.values()],'difficulty_source':evidence.uri if evidence else None,'source_as_of':evidence.observed_at if evidence else None})

@router.get('/predictions')
def prediction_explorer(horizon:int=Query(1),search:str=Query('',max_length=100),position:int|None=Query(None,ge=1,le=4),max_price:int|None=Query(None,ge=0),club_id:int|None=None,sort:str=Query('expected_points',pattern='^(expected_points|price|p6|p10|p15|p60|name)$'),direction:str=Query('desc',pattern='^(asc|desc)$'),offset:int=Query(0,ge=0),limit:int=Query(25,ge=1,le=100),session:Session=Depends(session_dependency)):
    if horizon not in (1,3,5):raise HTTPException(422,'Supported horizons: 1, 3, 5')
    from apps.api.main import latest_predictions
    rows=latest_predictions(session,horizon)
    rows=[p for p in rows if (not search or search.casefold() in p['name'].casefold()) and (position is None or p['position']==position) and (max_price is None or p['price']<=max_price) and (club_id is None or p['club_id']==club_id)]
    known=[p for p in rows if p.get(sort) is not None];missing=[p for p in rows if p.get(sort) is None]
    known.sort(key=lambda p:p[sort],reverse=direction=='desc');rows=known+missing
    clubs={c.id:c for c in session.scalars(select(Club))}
    output=[]
    for p in rows[offset:offset+limit]:
        identities=session.execute(select(Identity.season_id,Identity.fpl_id).where(Identity.player_id==p['id'])).all()
        history=session.execute(select(HistoricalStat.points,HistoricalStat.minutes,HistoricalStat.kickoff).where(or_(*[(HistoricalStat.season==season)&(HistoricalStat.fpl_id==pid) for season,pid in identities])).order_by(HistoricalStat.kickoff.desc()).limit(5)).all() if identities else []
        availability=session.scalar(select(AvailabilitySnapshot).where(AvailabilitySnapshot.player_id==p['id']).order_by(AvailabilitySnapshot.observed_at.desc()).limit(1))
        club=clubs.get(p['club_id'])
        output.append({**p,'club':club.name if club else None,'club_short':club.short_name if club else None,'recent_points':[r.points for r in reversed(history)],'recent_minutes':[r.minutes for r in reversed(history)],'form':sum(r.points for r in history)/len(history) if history else None,'availability_news':availability.news if availability else None,'availability_chance':availability.chance if availability else None})
    return encoded({'items':output,'total':len(rows),'offset':offset,'limit':limit})

@router.get('/history/{player_id}')
def history(player_id:int,season:str|None=None,limit:int=Query(300,ge=1,le=500),session:Session=Depends(session_dependency)):
    player=session.get(Player,player_id)
    if not player:raise HTTPException(404,'Player not found')
    identities=session.execute(select(Identity.season_id,Identity.fpl_id).where(Identity.player_id==player_id)).all()
    query=select(HistoricalStat).where(or_(*[(HistoricalStat.season==s)&(HistoricalStat.fpl_id==p) for s,p in identities])) if identities else select(HistoricalStat).where(HistoricalStat.id==-1)
    seasons=session.execute(select(HistoricalStat.season,func.count(),func.sum(HistoricalStat.points),func.sum(HistoricalStat.minutes)).where(HistoricalStat.id.in_(query.with_only_columns(HistoricalStat.id))).group_by(HistoricalStat.season).order_by(HistoricalStat.season)).all()
    if season:query=query.where(HistoricalStat.season==season)
    rows=session.scalars(query.order_by(HistoricalStat.kickoff.desc()).limit(limit)).all()
    extra={}
    # Read only each requested player's columns from real retained archives.
    for s,pid in identities:
        if season and s!=season:continue
        path=settings.data_dir/'warehouse'/f'{s}.parquet'
        if path.exists():
            import pyarrow.parquet as pq
            available=set(pq.read_schema(path).names)
            columns=[c for c in ('element','fixture','goals_scored','assists') if c in available]
            if {'element','fixture'}.issubset(columns):
                frame=pq.read_table(path,columns=columns,filters=[('element','=',pid)]).to_pandas()
                for r in frame.to_dict('records'):extra[(s,int(r['fixture']))]=r
        else:
            ev=session.scalar(select(Evidence).where(Evidence.source_id=='fpl',Evidence.uri==f'https://fantasy.premierleague.com/api/element-summary/{pid}/').order_by(Evidence.id.desc()))
            for r in (ev.payload.get('history',[]) if ev and isinstance(ev.payload,dict) else []):extra[(s,r['fixture'])]=r
    def stat(value):
        import math
        return float(value) if isinstance(value,(int,float)) and math.isfinite(value) else None
    items=[{'season':r.season,'fixture':r.fixture,'kickoff':r.kickoff,'points':r.points,'minutes':r.minutes,'club':r.team,'home':r.home,'xg':r.xg,'xa':r.xa,'goals':stat(extra.get((r.season,r.fixture),{}).get('goals_scored')),'assists':stat(extra.get((r.season,r.fixture),{}).get('assists'))} for r in reversed(rows)]
    clubs={c.id:c for c in session.scalars(select(Club))}
    return encoded({'player':player_label(player,clubs),'items':items,'seasons':[{'season':s,'matches':n,'points':points,'minutes':minutes} for s,n,points,minutes in seasons],'limit':limit,'truncated':len(rows)==limit,'missing':['Unknown historical observation times remain unknown','Club labels are historical source labels; current clubs are not broadcast backwards']})

@router.get('/club-history')
def club_history(season:str=Query('2026-27'),session:Session=Depends(session_dependency)):
    rows=session.execute(select(HistoricalStat.team,func.count(),func.count(func.distinct(HistoricalStat.fixture)),func.sum(HistoricalStat.points),func.sum(HistoricalStat.minutes)).where(HistoricalStat.season==season,HistoricalStat.team.is_not(None)).group_by(HistoricalStat.team)).all()
    missing=session.scalar(select(func.count()).select_from(HistoricalStat).where(HistoricalStat.season==season,HistoricalStat.team.is_(None)))
    return {'items':[{'club':club,'player_fixtures':n,'matches':matches,'points':points,'minutes':minutes} for club,n,matches,points,minutes in rows],'missing_club_rows':missing,'scope':'Recorded player FPL contributions by historical source club, not league standings'}

@router.get('/managers/{manager_id}')
def manager_view(manager_id:int,session:Session=Depends(session_dependency)):
    manager=session.get(Manager,manager_id)
    if not manager:raise HTTPException(404,'Manager not found')
    clubs={c.id:c for c in session.scalars(select(Club))}
    tenures=session.scalars(select(Tenure).where(Tenure.manager_id==manager_id).order_by(Tenure.starts_at)).all()
    stats=session.scalars(select(ManagerMatchStat).where(ManagerMatchStat.tenure_id.in_([t.id for t in tenures])).order_by(ManagerMatchStat.played_at)).all()
    fixtures={f.id:f for f in session.scalars(select(Fixture).where(Fixture.id.in_([s.fixture_id for s in stats])))}
    usage=[]
    for t in tenures:
        q=select(HistoricalStat.season,HistoricalStat.fpl_id,func.count(),func.sum(HistoricalStat.minutes),func.sum(HistoricalStat.points),func.sum(__import__('sqlalchemy').case((HistoricalStat.minutes>=60,1),else_=0))).join(Fixture,(HistoricalStat.fixture==Fixture.provider_id)&(HistoricalStat.season==Fixture.season_id)).where(HistoricalStat.kickoff>=t.starts_at,or_((HistoricalStat.home.is_(True))&(Fixture.home_id==t.club_id),(HistoricalStat.home.is_(False))&(Fixture.away_id==t.club_id)))
        if t.ends_at:q=q.where(HistoricalStat.kickoff<t.ends_at)
        for season,pid,n,minutes,points,sixty in session.execute(q.group_by(HistoricalStat.season,HistoricalStat.fpl_id)):
            # Match facts currently cover this season; never merge seasonal IDs by name.
            matching=session.scalar(select(Identity).where(Identity.fpl_id==pid,Identity.season_id==season))
            p=session.get(Player,matching.player_id) if matching and matching.player_id else None
            usage.append({**player_label(p,clubs),'observations':n,'minutes':minutes,'points':points,'sixty_rate':sixty/n if n else None})
    formations={}
    for s in stats:
        if s.formation:formations[s.formation]=formations.get(s.formation,0)+1
    return encoded({'id':manager.id,'name':manager.name,'tenures':[{'club':clubs[t.club_id].name if t.club_id in clubs else None,'club_short':clubs[t.club_id].short_name if t.club_id in clubs else None,'starts_at':t.starts_at,'ends_at':t.ends_at,'interim':t.interim} for t in tenures],'matches':[{'date':s.played_at,'goals_for':s.goals_for,'goals_against':s.goals_against,'home':s.home,'opponent':clubs.get(fixtures[s.fixture_id].away_id if s.home else fixtures[s.fixture_id].home_id).short_name if s.fixture_id in fixtures else None,'result':'W' if s.goals_for>s.goals_against else 'D' if s.goals_for==s.goals_against else 'L','formation':s.formation} for s in stats],'formations':[{'name':k,'count':v} for k,v in formations.items()],'usage':sorted(usage,key=lambda r:r['minutes'] or 0,reverse=True)[:25],'coverage':'Only ingested match/tenure observations; 60-minute rate is not starting-XI probability'})

@router.get('/models/{model_id}/evaluation')
def model_evaluation(model_id:str,session:Session=Depends(session_dependency)):
    from apps.api.models import ModelVersion
    model=session.get(ModelVersion,model_id)
    if not model:raise HTTPException(404,'Model not found')
    path=settings.artifact_dir/'ui-evaluations'/(hashlib.sha256(model_id.encode()).hexdigest()+'.json')
    if not path.is_file():return {'available':False,'reason':'No verified evaluation chart export for this fitted run. Aggregate metrics remain available.'}
    return json.loads(path.read_text())

@router.get('/events')
def event_view(offset:int=Query(0,ge=0),limit:int=Query(25,ge=1,le=50),session:Session=Depends(session_dependency)):
    clubs={c.id:c for c in session.scalars(select(Club))}
    rows=session.scalars(select(FootballEvent).order_by(FootballEvent.announced_at.desc()).offset(offset).limit(limit)).all()
    output=[]
    for r in rows:
        player=session.get(Player,r.player_id) if r.player_id else None
        manager=session.get(Manager,r.manager_id) if r.manager_id else None
        evidence=session.get(Evidence,r.evidence_id)
        output.append({'id':r.id,'kind':r.kind,'status':r.status,'person':player.name if player else manager.name if manager else None,'player_id':player.id if player else None,'manager_id':manager.id if manager else None,'from_club':clubs[r.from_club_id].name if r.from_club_id in clubs else None,'to_club':clubs[r.to_club_id].name if r.to_club_id in clubs else None,'announced_at':r.announced_at,'effective_at':r.effective_at,'observed_at':r.observed_at,'source_url':evidence.uri if evidence else None})
    return encoded({'items':output,'total':session.scalar(select(func.count()).select_from(FootballEvent)),'offset':offset,'limit':limit})

@router.get('/tactics')
def tactical_view(offset:int=Query(0,ge=0),limit:int=Query(25,ge=1,le=50),session:Session=Depends(session_dependency)):
    clubs={c.id:c for c in session.scalars(select(Club))}
    rows=session.scalars(select(TacticalObservation).order_by(TacticalObservation.match_at.desc()).offset(offset).limit(limit)).all()
    return encoded({'items':[{'id':r.id,'club':clubs[r.club_id].name if r.club_id in clubs else None,'match_at':r.match_at,'observed_at':r.observed_at,'formation':r.formation,'possession':r.possession,'pressing':r.pressing,'inferred':r.inferred,'source_url':session.get(Evidence,r.evidence_id).uri if session.get(Evidence,r.evidence_id) else None} for r in rows],'total':session.scalar(select(func.count()).select_from(TacticalObservation)),'offset':offset,'limit':limit})
