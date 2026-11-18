import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from apps.api.db import Base
import apps.api.models

@pytest.fixture(autouse=True)
def isolated_unit_cache(monkeypatch):
    # Loading local .env must never let ordinary unit tests populate app Redis.
    # The real integration test passes an explicit database-15 client instead.
    from apps.api.config import settings
    from apps.api.cache import cache
    monkeypatch.setattr(settings,'redis_url',None)
    monkeypatch.setattr(cache,'redis',None)
    monkeypatch.setattr(cache,'local',{})
    monkeypatch.setattr(cache,'local_locks',{})

@pytest.fixture
def session(tmp_path,monkeypatch):
    from apps.api.config import settings
    monkeypatch.setattr(settings,'data_dir',tmp_path)
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    from sqlalchemy import event
    @event.listens_for(engine,'connect')
    def foreign_keys(connection,_): connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    with sessionmaker(engine,expire_on_commit=False)() as db:
        yield db
    engine.dispose()
