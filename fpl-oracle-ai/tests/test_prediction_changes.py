from datetime import datetime,timezone
from apps.api.models import Club,Player,ModelVersion,Prediction,Audit
from apps.api.prediction_changes import snapshot,record_changes
from sqlalchemy import select

def test_before_after_preserves_original_prediction(session):
    session.add(Club(id=1,code=1,name='Test Club',short_name='TC'));session.flush()
    session.add_all([Player(id=1,code=1,name='Test Player',club_id=1,position=3,price=70,status='a'),ModelVersion(id='test',kind='baseline',trained_until=datetime(2024,1,1,tzinfo=timezone.utc),metrics={},artifact='test-only')]);session.flush()
    session.add(Prediction(player_id=1,model_id='test',batch='before',event=1,horizon=1,values={'expected_points':4,'lower':0,'upper':8}));session.commit()
    before=snapshot(session,[1])
    session.add(Prediction(player_id=1,model_id='test',batch='after',event=1,horizon=1,values={'expected_points':5,'lower':0,'upper':10}));session.flush()
    changes=record_changes(session,before,snapshot(session,[1]),1);session.commit()
    assert changes[0]['delta']==1
    assert len(session.scalars(select(Prediction)).all())==2
    assert session.scalar(select(Audit)).action=='prediction.changes'
