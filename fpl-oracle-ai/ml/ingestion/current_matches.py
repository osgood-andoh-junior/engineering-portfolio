from sqlalchemy import select
from apps.api.models import Identity,Gameweek,HistoricalStat,Player,Club,Fixture,Audit
from apps.api.db import utcnow
from ml.ingestion.fpl import FPLClient,evidence,parse_date

async def sync_player_matches(session,limit=50,offset=0,client=None):
    if client is None:
        async with FPLClient() as pooled:
            return await sync_player_matches(session,limit,offset,client=pooled)
    gw=session.scalar(select(Gameweek).order_by(Gameweek.deadline.desc()))
    if not gw: raise ValueError('Bootstrap must be ingested first')
    identities=session.scalars(select(Identity).where(Identity.season_id==gw.season_id,Identity.player_id.is_not(None)).order_by(Identity.fpl_id).offset(offset).limit(limit)).all()
    count=0;corrections=0
    for identity in identities:
        raw=await client.get(f'/element-summary/{identity.fpl_id}/')
        if not isinstance(raw.get('history'),list): raise ValueError('Unexpected player match schema')
        ev=evidence(session,'fpl',f'https://fantasy.premierleague.com/api/element-summary/{identity.fpl_id}/',raw)
        player=session.get(Player,identity.player_id)
        for match in raw['history']:
            if match.get('element') is not None and int(match['element'])!=identity.fpl_id:raise ValueError('Conflicting player identity in match response')
            kickoff=parse_date(match.get('kickoff_time'))
            if not kickoff or kickoff>=utcnow(): continue
            existing=session.scalar(select(HistoricalStat).where(HistoricalStat.season==gw.season_id,HistoricalStat.fpl_id==identity.fpl_id,HistoricalStat.fixture==match['fixture']))
            fixture=session.scalar(select(Fixture).where(Fixture.season_id==gw.season_id,Fixture.provider_id==match['fixture']))
            was_home=match.get('was_home')
            if not isinstance(was_home,bool):raise ValueError('Observed home/away flag required')
            team_id=(fixture.home_id if was_home else fixture.away_id) if fixture else None
            club=session.get(Club,team_id) if team_id else None
            values=dict(points=match['total_points'],minutes=match['minutes'],team=club.name if club else None,opponent=match.get('opponent_team'),home=was_home,price=match.get('value'),xg=float(match['expected_goals']) if match.get('expected_goals') is not None else None,xa=float(match['expected_assists']) if match.get('expected_assists') is not None else None)
            if existing:
                old={k:getattr(existing,k) for k in values}
                if old!=values:
                    session.add(Audit(action='match_stats.corrected',payload={'stat_id':existing.id,'previous_evidence_id':existing.evidence_id,'evidence_id':ev.id,'before':old,'after':values}))
                    for key,value in values.items():setattr(existing,key,value)
                    existing.observed_at=ev.observed_at;existing.evidence_id=ev.id;corrections+=1
                continue
            session.add(HistoricalStat(season=gw.season_id,fpl_id=identity.fpl_id,fixture=match['fixture'],kickoff=kickoff,observed_at=ev.observed_at,position=player.position,evidence_id=ev.id,**values))
            count+=1
        session.commit()
    session.add(Audit(action='matches.synced',payload={'season':gw.season_id,'players':len(identities),'new_rows':count,'offset':offset}))
    session.commit()
    return {'season':gw.season_id,'players':len(identities),'new_rows':count,'corrected_rows':corrections,'offset':offset}
