from datetime import datetime,timezone,timedelta
import pytest
from apps.api.intelligence import TacticalInput,ingest_tactical
from apps.api.models import Club,Source,TacticalObservation,Job
from sqlalchemy import select

def test_tactical_observations_provenance_and_idempotency(session):
    session.add_all([Club(id=1,code=1,name='Test Club',short_name='TC'),Source(id='licensed',url='https://stats.example',official=False,permitted=True,license='test only')]);session.commit()
    now=datetime.now(timezone.utc)-timedelta(days=1)
    data=TacticalInput(club_id=1,match_at=now-timedelta(hours=3),observed_at=now,source_id='licensed',source_url='https://stats.example/observations/1',formation='4-3-3',possession=60)
    first=ingest_tactical(session,data);session.commit()
    second=ingest_tactical(session,data);session.commit()
    assert first.id==second.id
    assert len(session.scalars(select(Job)).all())==1
    assert session.get(TacticalObservation,first.id).pressing is None

def test_invalid_formation_rejected():
    now=datetime.now(timezone.utc)-timedelta(days=1)
    with pytest.raises(ValueError):TacticalInput(club_id=1,match_at=now,observed_at=now,source_id='x',source_url='https://stats.example',formation='4-4-4')
