from apps.api.models import Club,Manager,Tenure,ManagerMatchStat,Job,ExternalMapping
from ml.ingestion.managers import import_reviewed_directory
from sqlalchemy import select
import json
from pathlib import Path

def test_reviewed_directory_is_idempotent_and_uses_external_ids(session):
    data=json.loads(Path('docs/verified_managers_2026-10-28.json').read_text())
    for record in data['records']:
        session.add(Club(code=record['club_code'],name=f"Fixture club {record['club_code']}",short_name=str(record['club_code'])))
    session.commit()
    first=import_reviewed_directory(session);second=import_reviewed_directory(session)
    assert first['clubs_changed']==20 and second['clubs_changed']==0
    assert len(session.scalars(select(Manager)).all())==20
    assert len(session.scalars(select(Tenure)).all())==20
    assert len(session.scalars(select(ExternalMapping)).all())==20
    assert len(session.scalars(select(Job)).all())==1
