import asyncio
from datetime import datetime,timezone,timedelta
from sqlalchemy import select
from apps.api.models import Source,Season,Club,Player,Identity,Gameweek,Fixture,HistoricalStat,Audit
from ml.ingestion.current_matches import sync_player_matches

def test_match_club_comes_from_fixture_and_official_corrections_are_audited(session):
    now=datetime.now(timezone.utc);played=now-timedelta(days=7)
    session.add_all([Source(id='fpl',url='https://fantasy.premierleague.com/api/',official=True,permitted=True,license='test only'),Season(id='2026-27'),Club(id=1,code=1,name='Previous club',short_name='PR'),Club(id=2,code=2,name='Current club',short_name='CU')]);session.flush()
    session.add(Player(id=1,code=1,name='Test player',club_id=2,position=3,price=60,status='a'));session.flush()
    session.add_all([Identity(season_id='2026-27',fpl_id=1,player_id=1,code=1,name='Test player'),Gameweek(season_id='2026-27',event=1,deadline=now+timedelta(days=10)),Fixture(season_id='2026-27',provider_id=5,event=1,home_id=1,away_id=2,kickoff=played,finished=True)]);session.commit()
    class TestOnlyClient:
        points=2
        async def get(self,_):return {'history':[{'element':1,'fixture':5,'kickoff_time':played.isoformat(),'total_points':self.points,'minutes':30,'was_home':True,'value':50}]}
    client=TestOnlyClient();asyncio.run(sync_player_matches(session,client=client))
    row=session.scalar(select(HistoricalStat));assert row.team=='Previous club' and row.points==2
    client.points=8
    result=asyncio.run(sync_player_matches(session,client=client))
    assert result['corrected_rows']==1 and row.points==8
    assert session.scalar(select(Audit).where(Audit.action=='match_stats.corrected')) is not None
