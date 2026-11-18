from fastapi.testclient import TestClient
from apps.api.main import app
from apps.api.db import session_dependency
from apps.api.models import Club,Player
from ml.optimization.squad import optimize

def test_manual_squad_validation_uses_independent_rules(session):
    for i in range(1,11):session.add(Club(id=i,code=i,name=f'Test Club {i}',short_name=str(i)))
    session.flush()
    pool=[]
    for i,pos in enumerate([1]*5+[2]*12+[3]*12+[4]*8):
        p=dict(id=i+1,name=f'Test Player {i}',code=i+1,position=pos,club_id=i%10+1,price=45,status='a',registration_state='verified')
        session.add(Player(**p));pool.append({**p,'expected_points':float(i%5+1)})
    session.commit();result=optimize(pool)
    data={'player_ids':[p['id'] for p in result['squad']],'starters':result['starters'],'captain':result['captain'],'vice_captain':result['vice_captain'],'budget':1000}
    app.dependency_overrides[session_dependency]=lambda:session
    try:
        with TestClient(app) as client:
            response=client.post('/api/v1/squad/validate',json=data)
            assert response.status_code==200 and response.json()['valid']
            data['captain']=data['vice_captain']
            assert not client.post('/api/v1/squad/validate',json=data).json()['valid']
    finally:app.dependency_overrides.clear()
