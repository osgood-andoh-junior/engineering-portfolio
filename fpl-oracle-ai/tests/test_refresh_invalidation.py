from datetime import timedelta
from apps.api.db import utcnow
from apps.api.models import Club,Player,Season,Gameweek,ModelVersion,Prediction,Job
from apps.api.main import latest_predictions

def test_published_batch_supersedes_old_jobs_but_new_jobs_invalidate(session):
    now=utcnow()
    session.add_all([Club(id=1,code=1,name='Test',short_name='T'),Season(id='test',rules={})])
    session.flush()
    session.add_all([Player(id=1,code=1,name='Test',club_id=1,position=3,price=50,status='a',registration_state='verified'),Gameweek(season_id='test',event=1,deadline=now+timedelta(days=1)),ModelVersion(id='test',kind='baseline',trained_until=now-timedelta(days=1),metrics={},artifact='test-only'),Job(id=1,key='old',kind='refresh',payload={'clubs':[1]})])
    session.flush()
    session.add(Prediction(player_id=1,model_id='test',batch='test',event=1,horizon=1,values={'expected_points':4,'refresh_job_highwater':1}))
    session.flush()
    assert not latest_predictions(session)[0]['stale']
    session.add(Job(id=2,key='new',kind='refresh',payload={'clubs':[1]}));session.flush()
    assert latest_predictions(session)[0]['stale']
