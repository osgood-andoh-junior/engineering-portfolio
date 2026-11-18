from datetime import timedelta
from sqlalchemy import select,func
from apps.api.db import utcnow
from apps.api.models import ModelVersion,HistoricalStat,Evidence

def retraining_policy(session,now=None,min_new_rows=1000):
    now=now or utcnow()
    model=session.scalar(select(ModelVersion).where(ModelVersion.promoted.is_(True)))
    if not model:
        count=session.scalar(select(func.count()).select_from(HistoricalStat)) or 0
        return {'due':count>=500,'reason':'Initial real-data training threshold','new_rows':count}
    created=model.created_at.replace(tzinfo=now.tzinfo)
    if now-created<timedelta(days=7):return {'due':False,'reason':'Minimum seven-day retraining interval','model_id':model.id}
    count=session.scalar(select(func.count()).select_from(HistoricalStat).join(Evidence,HistoricalStat.evidence_id==Evidence.id).where(Evidence.observed_at>created,HistoricalStat.kickoff<now-timedelta(hours=3))) or 0
    return {'due':count>=min_new_rows,'reason':'At least 1000 new completed player-fixture observations after a seven-day interval','new_rows':count,'model_id':model.id}
