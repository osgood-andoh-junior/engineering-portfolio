import asyncio
import json
import time
from datetime import timedelta
from sqlalchemy import select, update
from apps.api.db import Session, utcnow
from apps.api.models import Job, Audit
from apps.api.cache import cache
from ml.ingestion.fpl import sync_fpl
from ml.inference.predict import refresh_predictions

def schedule(session):
    bucket=int(time.time()//900)
    key=f'sync:{bucket}'
    if not session.scalar(select(Job).where(Job.key==key)):
        session.add(Job(key=key,kind='sync',payload={}))
    from apps.api.models import Player
    from sqlalchemy import func
    count=session.scalar(select(func.count()).select_from(Player)) or 0
    if count:
        match_key=f'matches:{bucket}'
        if not session.scalar(select(Job).where(Job.key==match_key)):
            offset=(bucket%max(1,(count+49)//50))*50
            session.add(Job(key=match_key,kind='matches',payload={'offset':offset,'limit':50}))
    from workers.policy import retraining_policy
    decision=retraining_policy(session)
    if decision['due']:
        training_key=f"train:{decision.get('model_id','initial')}:{int(time.time()//604800)}"
        if not session.scalar(select(Job).where(Job.key==training_key)):
            session.add(Job(key=training_key,kind='train',payload=decision))
    session.commit()

async def run_once():
    with Session() as session:
        now=utcnow()
        session.execute(update(Job).where(Job.status=='running',Job.locked_at<now-timedelta(minutes=10)).values(status='pending',available_at=now))
        session.commit()
        job=session.scalar(select(Job).where(Job.status=='pending',Job.available_at<=now).order_by(Job.id).with_for_update(skip_locked=True).limit(1))
        if not job: return False
        job.status='running'; job.locked_at=now; job.attempts+=1
        session.commit()
        try:
            with cache.lock('inference-and-sync',ttl=600) as acquired:
                if not acquired:
                    job.status='pending'; job.available_at=utcnow()+timedelta(seconds=10); session.commit(); return True
                if job.kind=='sync':
                    result=await sync_fpl(session)
                    from ml.ingestion.managers import refresh_manager_match_facts
                    result['manager_match_facts']=refresh_manager_match_facts(session)
                    result['predictions']=refresh_predictions(session)
                elif job.kind=='refresh':
                    from apps.api.prediction_changes import snapshot,record_changes
                    before=snapshot(session,job.payload.get('clubs',[]))
                    result=refresh_predictions(session,job.payload.get('clubs'))
                    if result['status']=='unavailable':
                        raise ValueError(result['reason'])
                    record_changes(session,before,snapshot(session,job.payload.get('clubs',[])),job.payload['event_id'])
                elif job.kind=='matches':
                    from ml.ingestion.current_matches import sync_player_matches
                    result=await sync_player_matches(session,**job.payload)
                    result['predictions']=refresh_predictions(session)
                elif job.kind=='train':
                    from ml.training.train import train
                    from ml.training.minutes import train_minutes
                    result={'models':train(session),'minutes':train_minutes(session),'forecasts':refresh_predictions(session)}
                elif job.kind=='cache_predictions':
                    from apps.api.main import latest_predictions
                    args=job.payload;rows=latest_predictions(session,args['horizon'])
                    value={'items':rows[args['offset']:args['offset']+args['limit']],'total':len(rows),'offset':args['offset'],'limit':args['limit'],'reason':None if rows else 'No published trained-model predictions'}
                    cache.set(args['key'],value,60,stale_ttl=300)
                    result={'status':'cache refreshed'}
                else:
                    raise ValueError(f'Unknown durable job kind {job.kind}')
                session.commit()
                if job.kind!='cache_predictions':cache.invalidate()
                job.status='done'; job.error=None
                session.add(Audit(action='job.done',payload={'id':job.id,'result':result}))
                session.commit()
        except Exception as exc:
            session.rollback()
            job=session.get(Job,job.id)
            job.status='dead' if job.attempts>=5 else 'pending'
            job.error=str(exc)[:1000]
            if job.kind=='sync':
                from apps.api.models import Source
                source=session.get(Source,'fpl')
                if source: source.last_error=str(exc)[:1000]
            job.available_at=utcnow()+timedelta(seconds=min(3600,2**job.attempts*15))
            session.add(Audit(action='job.failed',payload={'id':job.id,'error':type(exc).__name__,'status':job.status}))
            session.commit()
            print(json.dumps({'level':'error','job':job.id,'error':str(exc)}),flush=True)
    return True

async def main():
    while True:
        with Session() as session: schedule(session)
        worked=await run_once()
        if not worked: await asyncio.sleep(5)

if __name__=='__main__': asyncio.run(main())
