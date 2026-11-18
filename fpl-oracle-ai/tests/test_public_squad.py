"""Synthetic isolated API regressions; real manager verification lives in Playwright."""
from copy import deepcopy
from datetime import timedelta
from fastapi.testclient import TestClient
from sqlalchemy import select,delete
import pytest
from apps.api.db import session_dependency,utcnow
from apps.api.main import app
from apps.api.models import Club,Player,Season,Gameweek,Identity,ModelVersion,Prediction
from ml.ingestion.fpl import FPLClient


@pytest.fixture
def imported_client(session,monkeypatch):
    now=utcnow()
    session.add_all([Season(id='2026-27',rules_verified=True,rules={}),Season(id='2025-26',rules={})])
    session.add_all([Club(id=i,code=i,name=f'Test club {i}',short_name=f'T{i}') for i in range(1,7)])
    session.flush()
    positions=[1,2,2,2,2,3,3,3,3,4,4,1,4,3,2]
    for i,pos in enumerate(positions,1):
        session.add(Player(id=1000+i,code=10000+i,name=f'Test player {i}',club_id=(i-1)%6+1,position=pos,price=45,status='a',registration_state='verified'))
    session.add(Player(id=1999,code=19999,name='Different past-season identity',club_id=1,position=1,price=45,status='a',registration_state='verified'))
    session.flush()
    session.add_all([Identity(season_id='2026-27',fpl_id=i,player_id=1000+i,code=10000+i,name=f'Test player {i}') for i in range(1,16)])
    session.add(Identity(season_id='2025-26',fpl_id=1,player_id=1999,code=19999,name='Different past-season identity'))
    session.add_all([Gameweek(season_id='2026-27',event=8,deadline=now-timedelta(days=1)),Gameweek(season_id='2026-27',event=9,deadline=now+timedelta(days=2)),ModelVersion(id='test-only',kind='baseline',trained_until=now-timedelta(days=10),metrics={},artifact='test-only')]);session.flush()
    for i in range(1,16):
        for h in (1,3,5):
            session.add(Prediction(player_id=1000+i,model_id='test-only',batch='test-only',event=9,horizon=h,values={'expected_points':float(i%8+1)*h,'lower':0.,'upper':float(i%8+5)*h,'source_stale':False,'p60':.8,'p_zero_minutes':.1}))
    session.commit()
    payload={'entry':{'id':12345,'name':'Test-only public squad','current_event':8},'picks':{'active_chip':'wildcard','automatic_subs':[{'element_in':5,'element_out':13,'event':8}],'entry_history':{'event':8,'bank':0,'value':1000,'points':43},'picks':[{'element':i,'position':i,'element_type':pos,'multiplier':2 if i==10 else 1 if i<=11 else 0,'is_captain':i==13,'is_vice_captain':i==10} for i,pos in enumerate(positions,1)]}}
    async def public_response(self,manager_id,gameweek):return deepcopy(payload)
    monkeypatch.setattr(FPLClient,'manager_squad',public_response)
    app.dependency_overrides[session_dependency]=lambda:session
    with TestClient(app) as client:
        yield client,payload
    app.dependency_overrides.clear()


def test_public_import_preserves_raw_contract_resolves_season_ids_and_auto_sub_captain(imported_client):
    client,payload=imported_client
    response=client.get('/api/v1/managers/fpl/12345/squad?gameweek=8')
    assert response.status_code==200 and response.headers['cache-control']=='no-store'
    data=response.json();assert data['entry']==payload['entry'] and data['picks']==payload['picks']
    rows=data['resolved']['players'];assert len(rows)==15
    assert rows[0]['fpl_id']==1 and rows[0]['id']==1001 and rows[0]['id']!=1999
    assert rows[12]['is_captain'] and rows[12]['slot']==13
    assert rows[9]['is_vice_captain'] and rows[9]['multiplier']==2
    assert rows[0]['predictions']['3']['expected_points']==6
    assert data['resolved']['forecast_event']==9 and data['resolved']['unresolved_fpl_ids']==[]


@pytest.mark.parametrize('strategy,horizon',[('CONSERVATIVE',1),('BALANCED',3),('AGGRESSIVE',5)])
def test_imported_optimizer_keeps_all_fifteen_and_returns_legal_lineup(imported_client,strategy,horizon):
    client,_=imported_client
    response=client.post('/api/v1/optimizer/imported',json={'manager_id':12345,'gameweek':8,'current':list(range(1001,1016)),'strategy':strategy,'horizon':horizon})
    assert response.status_code==200,response.text
    data=response.json();assert data['scope']=='lineup_only' and data['horizon']==horizon
    assert {p['id'] for p in data['squad']}==set(range(1001,1016))
    assert all(p['club_short'] and p['club'] for p in data['squad'])
    assert len(set(data['starters']))==11 and len(set(data['bench']))==4
    assert not set(data['starters'])&set(data['bench'])
    assert data['captain'] in data['starters'] and data['vice_captain'] in data['starters']
    assert data['captain']!=data['vice_captain']
    assert data['transfers']==[] and data['transfer_status']=='unavailable_private_state'
    assert not data['ownership_verified_for_current_deadline']


def test_missing_identity_remains_unresolved_and_cannot_be_optimized(imported_client,session):
    client,_=imported_client
    session.execute(delete(Identity).where(Identity.season_id=='2026-27',Identity.fpl_id==1));session.commit()
    data=client.get('/api/v1/managers/fpl/12345/squad?gameweek=8').json()
    assert data['resolved']['unresolved_fpl_ids']==[1] and data['resolved']['players'][0]['id'] is None
    assert client.post('/api/v1/optimizer/imported',json={'manager_id':12345,'gameweek':8,'current':list(range(1001,1016))}).status_code==409


def test_public_import_rejects_duplicate_picks_and_wrong_snapshot(imported_client):
    client,payload=imported_client
    assert client.get('/api/v1/managers/fpl/12345/squad?gameweek=7').status_code==502
    payload['picks']['picks'][1]['element']=1
    assert client.get('/api/v1/managers/fpl/12345/squad?gameweek=8').status_code==502


def test_optimizer_rejects_tampered_ids_missing_predictions_and_stale_forecasts(imported_client,session):
    client,_=imported_client
    body={'manager_id':12345,'gameweek':8,'current':list(range(1001,1016)),'horizon':3}
    assert client.post('/api/v1/optimizer/imported',json={**body,'current':list(range(1001,1015))+[1999]}).status_code==409
    row=session.scalar(select(Prediction).where(Prediction.player_id==1001,Prediction.horizon==3))
    row.generated_at=utcnow()-timedelta(hours=2);session.commit()
    assert client.post('/api/v1/optimizer/imported',json=body).status_code==409
    session.delete(row);session.commit()
    assert client.post('/api/v1/optimizer/imported',json=body).status_code==409
