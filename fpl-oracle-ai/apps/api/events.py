import hashlib
import json
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import urlparse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from apps.api.models import Source, Player, Manager, Club, FootballEvent, Membership, Tenure, TacticalRegime, Job, Audit
from ml.ingestion.fpl import evidence

class EventInput(BaseModel):
    kind: Literal['SIGNING','TRANSFER','LOAN','LOAN_RETURN','DEPARTURE','APPOINTMENT','INTERIM','DISMISSAL']
    status: Literal['CONFIRMED','REPORTED','RUMORED']
    source_id: str = Field(max_length=80)
    source_url: str = Field(max_length=600)
    player_id: int | None = Field(default=None, gt=0)
    manager_id: int | None = Field(default=None, gt=0)
    from_club_id: int | None = Field(default=None, gt=0)
    to_club_id: int | None = Field(default=None, gt=0)
    effective_at: datetime
    announced_at: datetime
    observed_at: datetime

    @model_validator(mode='after')
    def valid(self):
        for dt in (self.effective_at, self.announced_at, self.observed_at):
            if dt.tzinfo is None:
                raise ValueError('Timezone-aware timestamps required')
        self.effective_at=self.effective_at.astimezone(timezone.utc)
        self.announced_at=self.announced_at.astimezone(timezone.utc)
        self.observed_at=self.observed_at.astimezone(timezone.utc)
        if self.announced_at > self.observed_at or self.observed_at > datetime.now(timezone.utc):
            raise ValueError('Invalid announcement/observation ordering')
        manager_event = self.kind in {'APPOINTMENT','INTERIM','DISMISSAL'}
        if manager_event != (self.manager_id is not None) or manager_event == (self.player_id is not None):
            raise ValueError('Exactly one appropriate entity required')
        if self.kind not in {'DEPARTURE','DISMISSAL'} and not self.to_club_id:
            raise ValueError('Destination club required')
        if self.kind in {'DEPARTURE','DISMISSAL'} and not self.from_club_id:
            raise ValueError('Origin club required')
        return self

def ingest_event(session, data: EventInput):
    source = session.get(Source, data.source_id)
    if not source or not source.permitted:
        raise ValueError('Source is not registered and permitted')
    url, registered = urlparse(data.source_url), urlparse(source.url)
    if url.scheme != 'https' or url.hostname != registered.hostname:
        raise ValueError('Evidence URL must match registered HTTPS source')
    if data.status == 'CONFIRMED' and not source.official:
        raise ValueError('Only registered official sources can confirm events')
    if data.effective_at > datetime.now(timezone.utc):
        raise ValueError('Future effective events must be deferred; no early authoritative changes')
    entity = session.get(Manager if data.manager_id else Player, data.manager_id or data.player_id)
    if not entity:
        raise ValueError('Unresolved entity')
    if data.status=='CONFIRMED' and data.kind in {'APPOINTMENT','INTERIM'}:
        elsewhere=session.scalar(select(Tenure).where(Tenure.manager_id==data.manager_id,Tenure.ends_at.is_(None),Tenure.club_id!=data.to_club_id))
        if elsewhere:
            raise ValueError('Confirm the previous club departure date before assigning another active club')
    for cid in (data.from_club_id, data.to_club_id):
        if cid and not session.get(Club, cid):
            raise ValueError('Unresolved club')
    canonical = {k: v for k,v in data.model_dump(mode='json').items() if k not in {'source_id','source_url','observed_at','announced_at','status'}}
    key = hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()
    existing = session.scalar(select(FootballEvent).where(FootballEvent.key == key))
    if existing and (existing.status == 'CONFIRMED' or data.status != 'CONFIRMED'):
        return existing
    # Serialize competing club/player changes before altering temporal records.
    if data.manager_id:
        session.execute(select(Club).where(Club.id == (data.to_club_id or data.from_club_id)).with_for_update()).first()
    else:
        session.execute(select(Player).where(Player.id == data.player_id).with_for_update()).first()
    existing=session.scalar(select(FootballEvent).where(FootballEvent.key==key).execution_options(populate_existing=True))
    if existing and (existing.status=='CONFIRMED' or data.status!='CONFIRMED'):
        return existing
    ev = evidence(session, data.source_id, data.source_url, data.model_dump(mode='json'),observed_at=data.observed_at)
    row = existing or FootballEvent(key=key, **data.model_dump(exclude={'source_id','source_url'}), evidence_id=ev.id)
    if existing:
        row.status, row.evidence_id = data.status, ev.id
    else:
        session.add(row)
    session.flush()
    if data.status == 'CONFIRMED':
        if data.manager_id:
            club_id = data.to_club_id or data.from_club_id
            current = session.scalar(select(Tenure).where(Tenure.club_id == club_id, Tenure.ends_at.is_(None)))
            if current:
                if current.starts_at.replace(tzinfo=timezone.utc) >= data.effective_at:
                    raise ValueError('Out-of-order or conflicting appointment requires review')
                if data.kind == 'DISMISSAL' and current.manager_id != data.manager_id:
                    raise ValueError('Dismissal does not match active manager')
                current.ends_at = data.effective_at
                current.ends_observed_at=data.observed_at;current.end_evidence_id=ev.id
                session.flush()
            if data.kind != 'DISMISSAL':
                tenure = Tenure(manager_id=data.manager_id, club_id=club_id, starts_at=data.effective_at, interim=data.kind == 'INTERIM', evidence_id=ev.id)
                session.add(tenure)
                session.flush()
                session.add(TacticalRegime(club_id=club_id, tenure_id=tenure.id, effective_at=data.effective_at, reason='Confirmed appointment'))
        else:
            if data.from_club_id and entity.club_id not in {None, data.from_club_id, data.to_club_id}:
                raise ValueError('Conflicting origin club requires review')
            current = session.scalar(select(Membership).where(Membership.player_id == data.player_id, Membership.ends_at.is_(None)))
            if current:
                if current.starts_at.replace(tzinfo=timezone.utc) >= data.effective_at:
                    raise ValueError('Out-of-order membership requires review')
                current.ends_at = data.effective_at
                current.ends_observed_at=data.observed_at;current.end_evidence_id=ev.id
                session.flush()
            if entity.club_id!=data.to_club_id:entity.registration_state='awaiting_fpl_verification'
            entity.club_id = data.to_club_id
            session.add(Membership(player_id=data.player_id, club_id=data.to_club_id, starts_at=data.effective_at, evidence_id=ev.id))
        session.add(Job(key=f'event:{key}', kind='refresh', payload={'event_id': row.id, 'clubs': [c for c in (data.from_club_id, data.to_club_id) if c], 'player_id': data.player_id}))
    session.add(Audit(action='event.ingested', payload={'event_id': row.id, 'status': data.status, 'source': data.source_url}))
    session.flush()
    return row
