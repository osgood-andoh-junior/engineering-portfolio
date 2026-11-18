from datetime import datetime,timezone,timedelta
from apps.api.models import Source,Evidence,Club,Manager,Player,Tenure,Season,Identity,Fixture,HistoricalStat
from ml.features.intelligence import context_at

def test_previous_club_matches_are_not_attributed_to_current_manager(session):
    now=datetime.now(timezone.utc)
    session.add_all([Source(id='test',url='https://official.example',official=True,permitted=True,license='test only'),Club(id=1,code=1,name='Current',short_name='CU'),Club(id=2,code=2,name='Previous',short_name='PR'),Manager(id=1,name='Test Manager'),Season(id='test')]);session.flush()
    session.add(Evidence(id=1,source_id='test',digest='2'*64,uri='https://official.example/a',payload={},observed_at=now-timedelta(days=30)));session.flush()
    session.add(Player(id=1,code=1,name='Test Player',club_id=1,position=3,price=60,status='a'));session.flush()
    session.add_all([Tenure(manager_id=1,club_id=1,starts_at=now-timedelta(days=30),evidence_id=1),Identity(season_id='test',fpl_id=1,player_id=1,code=1,name='Test Player'),Fixture(id=1,season_id='test',provider_id=1,event=1,home_id=2,away_id=1,kickoff=now-timedelta(days=5),finished=True)]);session.flush()
    session.add(HistoricalStat(season='test',fpl_id=1,fixture=1,kickoff=now-timedelta(days=5),observed_at=now-timedelta(days=4),points=3,minutes=90,position=3,home=True,evidence_id=1));session.commit()
    assert context_at(session,session.get(Player,1),now)['manager_matches']==0
