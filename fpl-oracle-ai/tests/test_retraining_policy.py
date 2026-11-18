from datetime import datetime,timezone
from apps.api.models import ModelVersion
from workers.policy import retraining_policy

def test_no_training_without_real_data(session):
    assert not retraining_policy(session)['due']

def test_appointment_does_not_trigger_full_retraining(session):
    now=datetime.now(timezone.utc)
    session.add(ModelVersion(id='test',kind='baseline',trained_until=now,created_at=now,metrics={},artifact='test-only',promoted=True));session.commit()
    decision=retraining_policy(session,now=now)
    assert not decision['due'] and 'seven-day' in decision['reason']
