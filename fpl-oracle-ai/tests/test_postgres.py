import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone,timedelta
import pytest
from sqlalchemy import create_engine,text,select,func
from sqlalchemy.orm import sessionmaker
from apps.api.db import Base
from apps.api.models import Club,Manager,Source,FootballEvent,Job
from apps.api.events import EventInput,ingest_event

@pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'),reason='A dedicated PostgreSQL test service is required')
def test_concurrent_confirmed_appointments_are_idempotent(tmp_path,monkeypatch):
    from apps.api.config import settings
    monkeypatch.setattr(settings,'data_dir',tmp_path)
    engine=create_engine(os.environ['TEST_DATABASE_URL'])
    schema='oracle_test_'+uuid.uuid4().hex
    with engine.begin() as c:c.execute(text(f'CREATE SCHEMA {schema}'))
    scoped=engine.execution_options(schema_translate_map={None:schema})
    try:
        Base.metadata.create_all(scoped)
        factory=sessionmaker(scoped)
        with factory() as s:
            s.add_all([Club(id=1,code=1,name='Test Club',short_name='TC'),Manager(id=1,name='Test Manager'),Source(id='test',url='https://official.example',official=True,permitted=True,license='test only')]);s.commit()
        now=datetime.now(timezone.utc)-timedelta(days=1)
        data=EventInput(kind='APPOINTMENT',status='CONFIRMED',source_id='test',source_url='https://official.example/appointment',manager_id=1,to_club_id=1,effective_at=now,announced_at=now,observed_at=now)
        def insert(_):
            with factory() as s:
                row=ingest_event(s,data);s.commit();return row.id
        with ThreadPoolExecutor(max_workers=2) as pool:ids=list(pool.map(insert,range(2)))
        assert ids[0]==ids[1]
        with factory() as s:
            assert s.scalar(select(func.count()).select_from(FootballEvent))==1
            assert s.scalar(select(func.count()).select_from(Job))==1
    finally:
        with engine.begin() as c:c.execute(text(f'DROP SCHEMA {schema} CASCADE'))
        engine.dispose()
