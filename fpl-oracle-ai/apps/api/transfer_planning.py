from typing import Literal
from pydantic import BaseModel,Field
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from apps.api.db import session_dependency,utcnow
from apps.api.models import Gameweek,Season
from ml.optimization.transfers import plan
router=APIRouter(prefix='/api/v1/planning')
class TransferState(BaseModel):
    manager_id:int|None=Field(None,gt=0,le=999999999)
    current:list[int]=Field(min_length=15,max_length=15)
    selling_prices:dict[int,int]
    bank:int=Field(ge=0,le=10000)
    free_transfers:int=Field(ge=0,le=5)
    gameweek:int=Field(ge=1,le=38)
    confirmed:Literal[True]
    horizon:Literal[1,3,5]=1
    max_transfers:int=Field(2,ge=0,le=15)
    strategy:Literal['CONSERVATIVE','BALANCED','AGGRESSIVE']='BALANCED'
    locked:list[int]=Field(default_factory=list,max_length=15)
    excluded:list[int]=Field(default_factory=list,max_length=500)
    chip:Literal['wildcard','free_hit']|None=None
    chip_available:bool=False
@router.post('/transfers')
def transfer_plan(data:TransferState,session=Depends(session_dependency)):
    from apps.api.main import latest_predictions
    gw=session.scalar(select(Gameweek).where(Gameweek.deadline>utcnow()).order_by(Gameweek.deadline))
    season=session.get(Season,gw.season_id) if gw else None
    if not gw or not season or not season.rules_verified or data.gameweek!=gw.event:raise HTTPException(409,'Refresh season rules and confirm the upcoming gameweek')
    if data.chip and (not data.chip_available or gw.event==1):raise HTTPException(409,'Confirm unused chip eligibility for this half-season in FPL')
    if data.chip and data.manager_id:
        import asyncio
        from ml.ingestion.fpl import FPLClient
        try:history=asyncio.run(FPLClient().get(f'/entry/{data.manager_id}/history/'))
        except Exception:raise HTTPException(502,'Chip history could not be verified; retry when FPL is available')
        name='freehit' if data.chip=='free_hit' else 'wildcard'
        half=1 if gw.event<=19 else 2
        if any(c.get('name')==name and (1 if c.get('event',0)<=19 else 2)==half for c in history.get('chips',[])):raise HTTPException(409,'This chip has already been used in the current half-season')
    if data.chip=='free_hit' and (data.horizon!=1 or gw.event==20):raise HTTPException(409,'Free Hit requires 1 GW; GW20 eligibility following GW19 usage is not verified')
    rows=latest_predictions(session,data.horizon)
    if not rows or any(p['stale'] for p in rows if p.get('expected_points') is not None):raise HTTPException(409,'Fresh official source and model forecasts required')
    rows=[p for p in rows if p.get('expected_points') is not None and p['club_id'] is not None]
    kwargs=dict(players=rows,current=data.current,selling=data.selling_prices,bank=data.bank,free_transfers=data.free_transfers,strategy=data.strategy)
    try:
        baseline=plan(**kwargs,max_transfers=0)
        result=plan(**kwargs,max_transfers=data.max_transfers,locked=data.locked,excluded=data.excluded,chip=data.chip)
        alternatives=[]
        for n in sorted({0,1,2,data.max_transfers}):
            if n>data.max_transfers:continue
            try:alternatives.append(plan(**kwargs,max_transfers=n,locked=data.locked,excluded=data.excluded,chip=data.chip))
            except ValueError:pass
    except ValueError as exc:raise HTTPException(422,str(exc))
    result['net_gain_vs_keep']=result['net_points']-baseline['net_points']
    five_impact=None
    if data.chip!='free_hit':
        from ml.optimization.squad import optimize
        five={p['id']:p for p in latest_predictions(session,5) if p.get('expected_points') is not None and not p['stale']}
        before=[five[i] for i in data.current if i in five]
        after=[five[p['id']] for p in result['squad'] if p['id'] in five]
        if len(before)==len(after)==15:
            old=optimize(before,budget=sum(p['price'] for p in before),strategy=data.strategy)
            new=optimize(after,budget=sum(p['price'] for p in after),strategy=data.strategy)
            five_impact={'before':old['expected_net_points'],'after':new['expected_net_points']-result['hit_cost'],'net_gain':new['expected_net_points']-result['hit_cost']-old['expected_net_points'],'scope':'Fixed post-transfer ownership, reoptimized aggregate XI; no future transfers or future prices'}
    return {'baseline':baseline,'recommended':result,'alternatives':alternatives,'five_gameweek_impact':five_impact,'horizon':data.horizon,'gameweek':gw.event,'state_provenance':'User-confirmed current ownership, bank, selling prices, free transfers and chip availability; not publicly verified','limitations':['Single deadline of transfers over aggregate forecast horizon','Future price changes, future transfer scheduling and automatic substitutions are not simulated']}
@router.get('/latest-squad/{manager_id}')
async def latest_squad(manager_id:int,session=Depends(session_dependency)):
    if not 1<=manager_id<=999999999:raise HTTPException(422,'Invalid manager ID')
    from ml.ingestion.fpl import FPLClient
    from apps.api.public_squad import resolve_public_squad
    from apps.api.main import latest_predictions
    import httpx
    async with FPLClient() as client:
        entry=await client.get(f'/entry/{manager_id}/');latest=entry.get('current_event')
        if not isinstance(latest,int):raise HTTPException(409,'No public squad gameweek available')
        for event in range(min(38,latest),max(0,latest-3),-1):
            try:picks=await client.get(f'/entry/{manager_id}/event/{event}/picks/')
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code==404:continue
                raise HTTPException(502,'Public FPL source unavailable')
            payload={'entry':entry,'picks':picks}
            payload['resolved']=resolve_public_squad(session,payload,manager_id,event,{h:latest_predictions(session,h) for h in (1,3,5)})
            transfers=await client.get(f'/entry/{manager_id}/transfers/')
            history=await client.get(f'/entry/{manager_id}/history/')
            temporary={c['event'] for c in history.get('chips',[]) if c.get('name')=='freehit'}
            from ml.optimization.transfers import selling_price
            evidence=[]
            for player in payload['resolved']['players']:
                buys=sorted((t for t in transfers if t.get('element_in')==player['fpl_id'] and t.get('event',99)<=event and t.get('event') not in temporary),key=lambda t:t.get('time',''),reverse=True)
                if buys and player['price'] is not None:
                    purchase=buys[0]['element_in_cost']
                    evidence.append({'player_id':player['id'],'purchase_price':purchase,'calculated_selling_price':selling_price(purchase,player['price']),'purchase_event':buys[0]['event'],'basis':'Public permanent transfer purchase cost and stored current official buy price; confirm against FPL'})
            payload['purchase_evidence']=evidence
            payload['chip_history']=history.get('chips',[])
            payload['ownership_status']='Latest public deadline snapshot; manually confirm current ownership'
            return payload
    raise HTTPException(409,'No recent public picks; choose a historical gameweek')
