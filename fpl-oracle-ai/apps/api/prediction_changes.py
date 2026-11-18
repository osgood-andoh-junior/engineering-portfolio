from apps.api.models import Prediction,Player,Audit
from sqlalchemy import select,func

def snapshot(session,clubs):
    players=session.scalars(select(Player.id).where(Player.club_id.in_(clubs))).all()
    sub=select(Prediction.player_id,Prediction.horizon,func.max(Prediction.id).label('id')).where(Prediction.player_id.in_(players)).group_by(Prediction.player_id,Prediction.horizon).subquery()
    rows=session.scalars(select(Prediction).join(sub,Prediction.id==sub.c.id)).all()
    return {(r.player_id,r.horizon):{'prediction_id':r.id,'values':r.values,'model_id':r.model_id,'event':r.event} for r in rows}

def record_changes(session,before,after,event_id):
    changes=[]
    for key,new in after.items():
        old=before.get(key)
        if not old or old['prediction_id']==new['prediction_id']: continue
        changes.append({'player_id':key[0],'horizon':key[1],'before_id':old['prediction_id'],'after_id':new['prediction_id'],'model_before':old['model_id'],'model_after':new['model_id'],'feature_snapshot_before':old['values'].get('feature_snapshot_id'),'feature_snapshot_after':new['values'].get('feature_snapshot_id'),'expected_points_before':old['values']['expected_points'],'expected_points_after':new['values']['expected_points'],'delta':new['values']['expected_points']-old['values']['expected_points'],'interval_before':[old['values']['lower'],old['values']['upper']],'interval_after':[new['values']['lower'],new['values']['upper']]})
    session.add(Audit(action='prediction.changes',payload={'event_id':event_id,'changes':changes,'interpretation':'Input-associated forecast changes, not proven causal effects'}))
    return changes
