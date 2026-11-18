import hashlib
import pickle
from datetime import timedelta
import numpy as np
import pandas as pd
from sqlalchemy import select,func
from apps.api.db import utcnow
from apps.api.models import ModelVersion, Player, Identity, HistoricalStat, Fixture, Prediction, Gameweek, Audit,Source,FeatureSnapshot,AvailabilitySnapshot,Tenure,Job
from ml.features.point_in_time import FEATURES
from ml.features.intelligence import context_at
from ml.calibration.distribution import distribution

def _refresh_predictions(session, clubs=None):
    model = session.scalar(select(ModelVersion).where(ModelVersion.promoted.is_(True)))
    if not model:
        return {'status':'unavailable','reason':'No promoted trained model'}
    # Pickle artifacts are trusted local training outputs; never accept user uploads.
    bundle = pickle.loads(__import__('pathlib').Path(model.artifact).read_bytes())
    minutes_version=session.scalar(select(ModelVersion).where(ModelVersion.kind=='minutes').order_by(ModelVersion.created_at.desc()))
    minutes_bundle=pickle.loads(__import__('pathlib').Path(minutes_version.artifact).read_bytes()) if minutes_version else None
    now = utcnow()
    refresh_job_highwater=session.scalar(select(func.max(Job.id)).where(Job.kind=='refresh')) or 0
    source=session.get(Source,'fpl')
    source_at=source.last_success.replace(tzinfo=now.tzinfo) if source and source.last_success else None
    source_stale=not source_at or (now-source_at).total_seconds()>1800
    gw = session.scalar(select(Gameweek).where(Gameweek.deadline > now).order_by(Gameweek.deadline))
    if not gw:
        return {'status':'unavailable','reason':'No upcoming gameweek in verified upstream data'}
    if model.trained_until.replace(tzinfo=now.tzinfo) >= gw.deadline.replace(tzinfo=now.tzinfo):
        raise ValueError('Artifact training cutoff would leak into forecast')
    deadline=pd.Timestamp(gw.deadline)
    if deadline.tzinfo is None:deadline=deadline.tz_localize('UTC')
    if pd.Timestamp(bundle['calibration_until'])>=deadline:
        raise ValueError('Calibration cutoff would leak into forecast')
    if minutes_bundle and pd.Timestamp(minutes_bundle['calibration_until'])>=deadline:
        raise ValueError('Minutes calibration cutoff would leak into forecast')
    players = session.scalars(select(Player).where(Player.club_id.in_(clubs)) if clubs else select(Player)).all()
    batch = hashlib.sha256(f'{model.id}:{now.isoformat()}'.encode()).hexdigest()[:24]
    count = 0
    for player in players:
        if player.registration_state!='verified':continue
        availability=session.scalar(select(AvailabilitySnapshot).where(AvailabilitySnapshot.player_id==player.id,AvailabilitySnapshot.observed_at<=now).order_by(AvailabilitySnapshot.observed_at.desc()))
        inputs={}
        feature_record=FeatureSnapshot(player_id=player.id,cutoff=now,values={},digest='pending')
        session.add(feature_record);session.flush()
        identities = session.execute(select(Identity.season_id,Identity.fpl_id).where(Identity.player_id == player.id)).all()
        history = []
        for season,pid in identities:
            history.extend(session.scalars(select(HistoricalStat).where(HistoricalStat.season == season,HistoricalStat.fpl_id == pid,HistoricalStat.kickoff < now-timedelta(hours=3))).all())
        history.sort(key=lambda h:h.kickoff)
        cold = len(history)<3
        tenure=session.scalar(select(Tenure).where(Tenure.club_id==player.club_id,Tenure.ends_at.is_(None)))
        player_context=context_at(session,player,now)
        context_uncertain=bool(tenure and player_context.get('manager_matches',0)<5)
        for horizon in (1,3,5):
            fixtures = session.scalars(select(Fixture).where(Fixture.season_id == gw.season_id, Fixture.event >= gw.event, Fixture.event < gw.event+horizon, Fixture.finished.is_(False), (Fixture.home_id == player.club_id)|(Fixture.away_id == player.club_id))).all()
            means=[];minute_distributions=[];uncertain_fixtures=0;availability_overrides=0
            for fixture in fixtures:
                values={f:np.nan for f in FEATURES}
                for n in (3,5,10):
                    values[f'points_{n}']=np.mean([h.points for h in history[-n:]]) if history else np.nan
                values.update(minutes_5=np.mean([h.minutes for h in history[-5:]]) if history else np.nan,sixty_minute_rate_5=np.mean([h.minutes>=60 for h in history[-5:]]) if history else np.nan,price=player.price,position=player.position,home=float(fixture.home_id==player.club_id),opponent=fixture.away_id if fixture.home_id==player.club_id else fixture.home_id,cold_start=int(cold))
                values['start_rate_5']=values['sixty_minute_rate_5']  # Legacy artifact schema: this was a 60-minute proxy, never actual starts.
                # Historical opponent provider IDs are not interchangeable with canonical club IDs.
                values['opponent']=np.nan
                values.update(player_context)
                inputs[str(fixture.id)]={k:float(v) if v is not None and np.isfinite(v) else None for k,v in values.items()}
                forced_unavailable=bool(availability and availability.chance==0 and fixture.event==gw.event)
                if minutes_bundle:
                    from ml.training.minutes import temperature_scale
                    probability=temperature_scale(minutes_bundle['model'].predict_proba(pd.DataFrame([values]).reindex(columns=minutes_bundle['features'])),minutes_bundle['temperature'])[0]
                    minute_distributions.append(np.asarray([1.0,0.0,0.0]) if forced_unavailable else probability)
                if cold and bundle['kind']=='baseline':
                    estimate=bundle['positions'].get(player.position,bundle['overall'])
                elif bundle['kind']=='baseline':
                    estimate=values['points_5']
                else:
                    estimate=float(bundle['model'].predict(pd.DataFrame([values]).reindex(columns=bundle['features']))[0])
                if forced_unavailable:
                    estimate=0.0
                    availability_overrides+=1
                else:uncertain_fixtures+=1
                means.append(estimate)
            residuals=np.asarray(bundle['residuals'])
            aggregated=residuals.mean()*uncertain_fixtures+(residuals-residuals.mean())*np.sqrt(uncertain_fixtures)
            result=distribution(float(sum(means)),aggregated,cold,context_uncertain=context_uncertain) if uncertain_fixtures else {'expected_points':0.0,'median':0.0,'lower':0.0,'upper':0.0,'p6':0.0,'p10':0.0,'p15':0.0,'cold_start':cold}
            result.update(fixtures=len(fixtures),p_start=None,p60=None,p_zero_minutes=None,manager_stability=None,rotation_risk=None,tactical_fit=None,transfer_impact=None,limitations=['Minutes probabilities unavailable: no separately calibrated minutes model','Multi-fixture intervals use independent residual approximation; correlated simulation pending','Archive calibration is retrospective, not timestamp-audited'])
            result.update(source_as_of=source_at.isoformat() if source_at else None,source_stale=bool(source_stale),refresh_job_highwater=refresh_job_highwater,history_observations=len(history),history_last_match=history[-1].kickoff.isoformat() if history else None)
            if minute_distributions:
                probabilities=np.asarray(minute_distributions)
                result['limitations']=[v for v in result['limitations'] if not v.startswith('Minutes probabilities unavailable')]
                result.update(p60=float(1-np.prod(1-probabilities[:,2])),p_zero_minutes=float(np.prod(probabilities[:,0])),expected_minutes=float(np.sum(probabilities@np.asarray(minutes_bundle['bucket_minutes']))),minutes_model_id=minutes_version.id,minutes_probability_scope='At least one fixture with 60+ minutes; multiple fixtures use an independence approximation')
            result['feature_snapshot_id']=feature_record.id
            result['availability_overrides']=availability_overrides
            result['availability_assumption']='Official next-round 0% availability forces a zero next-round scenario; later availability is not assumed unchanged'
            session.add(Prediction(player_id=player.id,model_id=model.id,batch=batch,event=gw.event,horizon=horizon,values=result))
            count+=1
        import json
        feature_record.values={'fixtures':inputs,'model':model.id,'source_as_of':source_at.isoformat() if source_at else None}
        feature_record.digest=hashlib.sha256(json.dumps(feature_record.values,sort_keys=True).encode()).hexdigest()
    session.add(Audit(action='predictions.refreshed',payload={'batch':batch,'count':count,'clubs':clubs,'model':model.id}))
    session.flush()
    return {'status':'generated','count':count,'batch':batch}

def refresh_predictions(session,clubs=None):
    from sklearn.ensemble import HistGradientBoostingClassifier  # Load the OpenMP runtime before limiting its threads.
    from threadpoolctl import threadpool_limits
    with threadpool_limits(limits=2):
        return _refresh_predictions(session,clubs)
