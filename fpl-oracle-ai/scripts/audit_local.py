"""Write measured local coverage and artifact availability without exposing secrets."""
import json
from pathlib import Path
from sqlalchemy import select,func,text
from apps.api.db import Session,engine,utcnow
from apps.api.config import settings
from apps.api.models import Player,Fixture,HistoricalStat,Identity,ModelVersion,Prediction,Manager,Tenure,TacticalObservation,FootballEvent,Source


def main():
    with Session() as session:
        counts={model.__tablename__:session.scalar(select(func.count()).select_from(model)) for model in (Player,Fixture,HistoricalStat,Identity,ModelVersion,Prediction,Manager,Tenure,TacticalObservation,FootballEvent)}
        coverage=[{'season':season,'rows':count,'players_with_rows':players} for season,count,players in session.execute(select(HistoricalStat.season,func.count(),func.count(func.distinct(HistoricalStat.fpl_id))).group_by(HistoricalStat.season).order_by(HistoricalStat.season))]
        models=[{'id':m.id,'kind':m.kind,'promoted':m.promoted,'artifact_exists':Path(m.artifact).is_file(),'trained_until':m.trained_until.isoformat(),'metrics':m.metrics} for m in session.scalars(select(ModelVersion).order_by(ModelVersion.created_at.desc()))]
        implemented={'baseline','catboost','lightgbm','lstm','gru','minutes'}
        registered={m['kind'] for m in models if m['artifact_exists']}
        redis_state='not configured'
        if settings.redis_url:
            try:
                from redis import Redis
                redis_state='PONG' if Redis.from_url(settings.redis_url,socket_connect_timeout=5,socket_timeout=5).ping() else 'no response'
            except Exception as exc:
                redis_state=type(exc).__name__
        report={'verified_at':utcnow().isoformat(),'database':engine.dialect.name,'migration':session.scalar(text('SELECT version_num FROM alembic_version')),'redis':redis_state,'counts':counts,'coverage':coverage,'models':models,'implemented_model_families_missing_artifacts':sorted(implemented-registered),'missing_or_unvalidated_model_capabilities':['Learned ensemble','Starting-XI classifier','Validated manager/tactical/transfer lift','Joint scoring-event and automatic-substitution simulation'],'source_status':[{'id':s.id,'last_success':s.last_success.isoformat() if s.last_success else None,'last_error':s.last_error} for s in session.scalars(select(Source))]}
    settings.data_dir.mkdir(exist_ok=True)
    (settings.data_dir/'local-audit.json').write_text(json.dumps(report,indent=2,default=str))
    print(json.dumps({k:v for k,v in report.items() if k!='models'},indent=2,default=str))


if __name__=='__main__':
    main()
