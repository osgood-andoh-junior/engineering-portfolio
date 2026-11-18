"""Isolated presentation-contract regressions; no data enters the live warehouse."""
from datetime import datetime,timezone,timedelta
import pytest
from fastapi.testclient import TestClient
from apps.api.main import app
from apps.api.db import session_dependency
from apps.api.models import Source,Season,Club,Player,Identity,Evidence,HistoricalStat,Fixture,ModelVersion,Prediction,Audit,Gameweek,Manager,Tenure,FootballEvent,TacticalObservation

@pytest.fixture
def ui_client(session):
    now=datetime.now(timezone.utc)
    session.add_all([Source(id='fpl',url='https://fantasy.premierleague.com',permitted=True,official=True),Season(id='2025-26'),Season(id='2026-27')]);session.flush()
    session.add_all([Club(id=1,code=1,name='Test Home',short_name='TH'),Club(id=2,code=2,name='Test Away',short_name='TA')]);session.flush()
    session.add_all([Player(id=1,code=1,name='Test Player',position=3,price=60,club_id=1,status='a'),Player(id=2,code=2,name='Other Player',position=4,price=70,club_id=2,status='a')]);session.flush()
    session.add_all([Identity(season_id='2026-27',fpl_id=11,player_id=1,name='Test Player'),Identity(season_id='2025-26',fpl_id=11,player_id=2,name='Other Player'),Gameweek(season_id='2026-27',event=10,deadline=now+timedelta(days=10)),Evidence(id=1,source_id='fpl',digest='a'*64,uri='https://fantasy.premierleague.com/api/fixtures/',payload={'fixtures':[{'id':99,'team_h_difficulty':2}]}),ModelVersion(id='old',kind='baseline',artifact='test-only',trained_until=now,metrics={}),ModelVersion(id='new',kind='lightgbm',artifact='test-only',trained_until=now,metrics={})]);session.flush()
    session.add(Fixture(id=1,season_id='2026-27',provider_id=99,event=10,home_id=1,away_id=2,kickoff=now,finished=False));session.flush()
    session.add_all([HistoricalStat(season='2026-27',fpl_id=11,fixture=99,kickoff=now,points=-1,minutes=30,home=True,team=None,xg=None,xa=None,evidence_id=1),HistoricalStat(season='2025-26',fpl_id=11,fixture=88,kickoff=now-timedelta(days=365),points=9,minutes=90,home=False,team='Historical Away',evidence_id=1)]);session.commit()
    app.dependency_overrides[session_dependency]=lambda:session
    try:
        with TestClient(app) as client:yield client
    finally:app.dependency_overrides.clear()

def test_fixture_read_model_preserves_missing_official_difficulty(ui_client):
    response=ui_client.get('/api/v1/presentation/fixtures');assert response.status_code==200
    data=response.json();assert data['items'][0]['home_difficulty']==2
    assert data['items'][0]['away_difficulty'] is None
    assert data['clubs'][0]['name']=='Test Home'

def test_transfer_api_requires_explicit_private_state(ui_client):
    assert ui_client.post('/api/v1/planning/transfers',json={'current':list(range(1,16))}).status_code==422
    supplied={'current':list(range(1,16)),'selling_prices':{},'bank':10,'free_transfers':2,'gameweek':10,'confirmed':False}
    assert ui_client.post('/api/v1/planning/transfers',json=supplied).status_code==422
    supplied.update(confirmed=True,chip='free_hit',chip_available=True,horizon=5)
    assert ui_client.post('/api/v1/planning/transfers',json=supplied).status_code==409

def test_history_is_identity_and_season_scoped_without_fabricated_goals(ui_client):
    data=ui_client.get('/api/v1/presentation/history/1').json()
    assert len(data['items'])==1 and data['items'][0]['points']==-1
    assert data['items'][0]['goals'] is None and data['items'][0]['xg'] is None
    assert data['items'][0]['club'] is None
    assert ui_client.get('/api/v1/presentation/history/999').status_code==404
    assert ui_client.get('/api/v1/presentation/history/1?limit=1000').status_code==422

def test_changes_keep_negative_ranges_versions_null_event_and_target_mismatch(ui_client,session):
    before=Prediction(player_id=1,model_id='old',batch='before',event=9,horizon=1,values={'expected_points':0,'lower':-4,'upper':8})
    after=Prediction(player_id=1,model_id='new',batch='after',event=10,horizon=1,values={'expected_points':2,'lower':-3,'upper':9})
    session.add_all([before,after]);session.flush()
    session.add(Audit(action='prediction.changes',payload={'event_id':None,'changes':[{'player_id':1,'horizon':1,'before_id':before.id,'after_id':after.id,'model_before':'old','model_after':'new','feature_snapshot_before':None,'feature_snapshot_after':2,'expected_points_before':0,'expected_points_after':2,'interval_before':[-4,8],'interval_after':[-3,9]}]}));session.commit()
    data=ui_client.get('/api/v1/presentation/changes?limit=1').json();c=data['items'][0]
    assert c['player']['club']=='Test Home' and c['player']['name']=='Test Player'
    assert c['before']['interval']==[-4,8] and c['delta']==2 and c['percent_change'] is None
    assert c['model_changed'] and c['feature_changed'] and not c['same_target'] and c['event'] is None
    assert ui_client.get('/api/v1/presentation/changes?search=unknown').json()['items']==[]

def test_prediction_filters_are_bounded_and_have_recent_actual_form(ui_client,session):
    session.add_all([Prediction(player_id=1,model_id='new',batch='current',event=10,horizon=1,values={'expected_points':5,'lower':-2,'upper':10}),Prediction(player_id=2,model_id='new',batch='current',event=10,horizon=1,values={'expected_points':2,'lower':-1,'upper':7})]);session.commit()
    data=ui_client.get('/api/v1/presentation/predictions?limit=1').json();assert data['total']==2 and len(data['items'])==1
    assert data['items'][0]['recent_points']==[-1] and data['items'][0]['club']=='Test Home'
    assert ui_client.get('/api/v1/presentation/predictions?position=4').json()['items'][0]['name']=='Other Player'
    assert ui_client.get('/api/v1/presentation/predictions?max_price=50').json()['total']==0
    assert ui_client.get('/api/v1/presentation/predictions?horizon=2').status_code==422

def test_club_history_excludes_unknown_clubs_without_current_membership_backfill(ui_client):
    data=ui_client.get('/api/v1/presentation/club-history?season=2026-27').json();assert data['items']==[] and data['missing_club_rows']==1

def test_model_charts_require_verified_export_and_registered_model(ui_client):
    data=ui_client.get('/api/v1/presentation/models/new/evaluation').json();assert data['available'] is False
    assert ui_client.get('/api/v1/presentation/models/unknown/evaluation').status_code==404

def test_event_and_tactical_read_models_preserve_attribution_and_observation_basis(ui_client,session):
    assert ui_client.get('/api/v1/presentation/events').json()['total']==0
    assert ui_client.get('/api/v1/presentation/tactics').json()['total']==0
    now=datetime.now(timezone.utc)
    session.add(FootballEvent(key='c'*64,kind='TRANSFER',status='REPORTED',player_id=1,from_club_id=1,to_club_id=2,effective_at=now,announced_at=now,observed_at=now,evidence_id=1))
    session.add(TacticalObservation(club_id=1,match_at=now,observed_at=now,formation='3-5-2',possession=0,pressing=None,inferred=True,evidence_id=1));session.commit()
    event=ui_client.get('/api/v1/presentation/events').json()['items'][0]
    assert event['person']=='Test Player' and event['status']=='REPORTED'
    assert event['from_club']=='Test Home' and event['to_club']=='Test Away'
    observation=ui_client.get('/api/v1/presentation/tactics').json()['items'][0]
    assert observation['inferred'] and observation['possession']==0 and observation['pressing'] is None
    assert observation['source_url'].startswith('https://')

def test_manager_usage_does_not_merge_reused_seasonal_player_ids(ui_client,session):
    now=datetime.now(timezone.utc);session.add(Manager(id=1,name='Test Coach'));session.flush()
    session.add(Tenure(manager_id=1,club_id=1,starts_at=now-timedelta(days=500),evidence_id=1));session.flush()
    session.add(Fixture(id=2,season_id='2025-26',provider_id=88,event=1,home_id=2,away_id=1,kickoff=now-timedelta(days=365),finished=True));session.commit()
    data=ui_client.get('/api/v1/presentation/managers/1').json()
    assert {p['id'] for p in data['usage']}=={1,2}
    assert next(p for p in data['usage'] if p['id']==2)['minutes']==90
    assert next(p for p in data['usage'] if p['id']==1)['minutes']==30
