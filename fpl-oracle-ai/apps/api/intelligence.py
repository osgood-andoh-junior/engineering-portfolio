from datetime import datetime,timezone
from collections import Counter
from urllib.parse import urlparse
from pydantic import BaseModel,Field,model_validator
from sqlalchemy import select
from apps.api.models import Source,Tenure,Fixture,ManagerMatchStat,TacticalObservation,PlayerRole,Player,Job,Audit
from ml.ingestion.fpl import evidence

class TacticalInput(BaseModel):
    club_id:int=Field(gt=0)
    match_at:datetime
    observed_at:datetime
    source_id:str=Field(max_length=80)
    source_url:str=Field(max_length=600)
    formation:str|None=Field(None,pattern=r'^\d(?:-\d){1,4}$')
    possession:float|None=Field(None,ge=0,le=100)
    pressing:float|None=Field(None,ge=0)
    inferred:bool=False
    @model_validator(mode='after')
    def timestamps(self):
        if self.match_at.tzinfo is None or self.observed_at.tzinfo is None:
            raise ValueError('Timezone-aware dates required')
        self.match_at=self.match_at.astimezone(timezone.utc)
        self.observed_at=self.observed_at.astimezone(timezone.utc)
        if self.observed_at<self.match_at or self.observed_at>datetime.now(timezone.utc):
            raise ValueError('Invalid observation timestamp')
        if self.formation and sum(map(int,self.formation.split('-')))!=10:
            raise ValueError('Outfield formation must total ten')
        return self

def ingest_tactical(session,data):
    source=session.get(Source,data.source_id)
    if not source or not source.permitted or urlparse(data.source_url).scheme!='https' or urlparse(data.source_url).hostname!=urlparse(source.url).hostname:
        raise ValueError('Permitted matching source required')
    ev=evidence(session,data.source_id,data.source_url,data.model_dump(mode='json'))
    existing=session.scalar(select(TacticalObservation).where(TacticalObservation.club_id==data.club_id,TacticalObservation.match_at==data.match_at,TacticalObservation.evidence_id==ev.id))
    if existing: return existing
    row=TacticalObservation(club_id=data.club_id,match_at=data.match_at,observed_at=data.observed_at,formation=data.formation,possession=data.possession,pressing=data.pressing,inferred=data.inferred,evidence_id=ev.id)
    session.add(row);session.flush()
    session.add(Job(key=f'tactical:{row.id}',kind='refresh',payload={'clubs':[data.club_id],'event_id':None}))
    session.add(Audit(action='tactical.observed',payload={'id':row.id,'source':data.source_url,'inferred':data.inferred}))
    return row

def manager_summary(session,manager_id,cutoff=None):
    cutoff=cutoff or datetime.now(timezone.utc)
    tenures=session.scalars(select(Tenure).where(Tenure.manager_id==manager_id)).all()
    result=[]
    for tenure in tenures:
        stats=session.scalars(select(ManagerMatchStat).where(ManagerMatchStat.tenure_id==tenure.id,ManagerMatchStat.observed_at<cutoff,ManagerMatchStat.played_at<cutoff)).all()
        result.append({'tenure_id':tenure.id,'club_id':tenure.club_id,'starts_at':tenure.starts_at,'ends_at':tenure.ends_at,'matches':len(stats),'wins':sum(s.goals_for>s.goals_against for s in stats),'draws':sum(s.goals_for==s.goals_against for s in stats),'losses':sum(s.goals_for<s.goals_against for s in stats),'goals_for':sum(s.goals_for for s in stats),'goals_against':sum(s.goals_against for s in stats),'formation_counts':dict(Counter(s.formation for s in stats if s.formation)),'average_possession':sum(s.possession for s in stats if s.possession is not None)/len([s for s in stats if s.possession is not None]) if any(s.possession is not None for s in stats) else None,'coverage':'No match statistics ingested' if not stats else 'Stored observations only'})
    return result
