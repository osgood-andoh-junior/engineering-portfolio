"""Resolve public, season-scoped FPL picks without guessing private transfer state."""
from typing import Literal
from pydantic import BaseModel,Field,model_validator
from sqlalchemy import select
from apps.api.db import utcnow
from apps.api.models import Club,Gameweek,Identity,Player


class PublicPick(BaseModel):
    element:int=Field(gt=0)
    position:int=Field(ge=1,le=15)
    multiplier:int=Field(ge=0,le=3)
    is_captain:bool
    is_vice_captain:bool
    element_type:int|None=Field(None,ge=1,le=4)


class PublicPicks(BaseModel):
    picks:list[PublicPick]=Field(min_length=15,max_length=15)

    @model_validator(mode='after')
    def coherent(self):
        if len({p.element for p in self.picks})!=15 or {p.position for p in self.picks}!=set(range(1,16)):
            raise ValueError('Expected 15 distinct player IDs and squad slots 1–15')
        if sum(p.is_captain for p in self.picks)!=1 or sum(p.is_vice_captain for p in self.picks)!=1:
            raise ValueError('Expected one selected captain and one vice-captain')
        if any(p.is_captain and p.is_vice_captain for p in self.picks):
            raise ValueError('Captain and vice-captain must be distinct')
        return self


class ImportedOptimizeInput(BaseModel):
    manager_id:int=Field(gt=0,le=999999999)
    gameweek:int=Field(ge=1,le=38)
    current:list[int]=Field(min_length=15,max_length=15)
    horizon:Literal[1,3,5]=1
    strategy:Literal['CONSERVATIVE','BALANCED','AGGRESSIVE']='BALANCED'


def resolve_public_squad(session,payload,manager_id,gameweek,forecasts):
    picks=PublicPicks.model_validate(payload['picks']).picks
    if payload['entry'].get('id')!=manager_id or payload['picks'].get('entry_history',{}).get('event')!=gameweek:
        raise ValueError('Public response does not match the requested manager and gameweek')
    upcoming=session.scalar(select(Gameweek).where(Gameweek.deadline>utcnow()).order_by(Gameweek.deadline))
    season=upcoming.season_id if upcoming else session.scalar(select(Gameweek.season_id).order_by(Gameweek.deadline.desc()))
    if not season or not session.scalar(select(Gameweek).where(Gameweek.season_id==season,Gameweek.event==gameweek)):
        raise ValueError('Requested gameweek is not present in the current season database')
    identities={i.fpl_id:i for i in session.scalars(select(Identity).where(Identity.season_id==season,Identity.fpl_id.in_([p.element for p in picks])))}
    players={p.id:p for p in session.scalars(select(Player).where(Player.id.in_([i.player_id for i in identities.values() if i.player_id is not None])))}
    clubs={c.id:c for c in session.scalars(select(Club))}
    forecast_maps={str(h):{p['id']:p for p in rows} for h,rows in forecasts.items()}
    resolved=[]
    for pick in sorted(picks,key=lambda p:p.position):
        identity=identities.get(pick.element)
        player=players.get(identity.player_id) if identity else None
        club=clubs.get(player.club_id) if player else None
        predictions={}
        for horizon,rows in forecast_maps.items():
            row=rows.get(player.id) if player else None
            predictions[horizon]={k:row.get(k) for k in ('expected_points','lower','upper','p60','p_zero_minutes','model_id','generated_at','stale','unavailable_reason')} if row else None
        resolved.append({'fpl_id':pick.element,'slot':pick.position,'multiplier':pick.multiplier,'is_captain':pick.is_captain,'is_vice_captain':pick.is_vice_captain,'position':pick.element_type or (player.position if player else None),'id':player.id if player else None,'name':player.name if player else None,'club_id':player.club_id if player else None,'club':club.name if club else None,'club_short':club.short_name if club else None,'price':player.price if player else None,'status':player.status if player else None,'registration_state':player.registration_state if player else None,'predictions':predictions})
    return {'manager_id':manager_id,'gameweek':gameweek,'season':season,'imported_at':utcnow().isoformat(),'forecast_event':upcoming.event if upcoming else None,'players':resolved,'unresolved_fpl_ids':[p['fpl_id'] for p in resolved if p['id'] is None],'limitations':['Public gameweek snapshot, including any applied automatic substitutions','Current-season club, position and buy prices may differ from the historical gameweek','Current ownership, selling prices, free transfers and unused chip state cannot be verified from public picks','Forecasts refer to upcoming gameweeks, not a retrospective forecast of the imported gameweek']}


def optimize_imported_squad(session,view,data,rows,rules_verified):
    if not rules_verified:
        raise ValueError('Current season composition rules are not verified')
    expected={p['id'] for p in view['players']}
    if None in expected or len(expected)!=15 or len(set(data.current))!=15 or set(data.current)!=expected:
        raise ValueError('Imported players must match all 15 season-resolved public picks')
    display={p['id']:p for p in view['players']}
    candidates=[{**p,'club':display[p['id']]['club'],'club_short':display[p['id']]['club_short']} for p in rows if p['id'] in expected]
    if len(candidates)!=15 or any(p['expected_points'] is None or p['stale'] for p in candidates):
        raise ValueError('Fresh model predictions are required for every imported player; refresh data and forecasts')
    if any(p.get('registration_state')!='verified' or p.get('status')=='u' for p in candidates):
        raise ValueError('Every imported player needs verified current FPL registration')
    from ml.optimization.squad import optimize
    # No purchases or sales: current replacement cost is only a composition bound.
    result=optimize(candidates,budget=sum(p['price'] for p in candidates),strategy=data.strategy,locked=data.current)
    result.update(scope='lineup_only',horizon=data.horizon,forecast_event=view['forecast_event'],source_gameweek=data.gameweek,manager_id=data.manager_id,transfers=[],transfer_status='unavailable_private_state',ownership_verified_for_current_deadline=False,limitations=result['limitations']+['All 15 imported players retained; no transfer spending or hits assumed','Historical public snapshot cannot verify current ownership, selling prices, free transfers or chip availability','One fixed starting XI and captain across the selected horizon; automatic substitutions are not simulated'])
    return result
