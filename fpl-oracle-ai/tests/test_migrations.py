import os
import subprocess
import sys
from datetime import datetime,timezone
from sqlalchemy import create_engine,inspect,text
from sqlalchemy.orm import Session
from apps.api.db import Base
from infrastructure.migrations import schema_v1 as frozen

def test_additive_migration_preserves_referenced_tenures_and_matches_runtime_schema(tmp_path):
    url='sqlite:///'+(tmp_path/'migration.db').as_posix()
    env={**os.environ,'DATABASE_URL':url}
    def migrate(target):
        result=subprocess.run([sys.executable,'-m','alembic','upgrade' if target=='head' or target=='0004_initial' else 'downgrade','0004' if target=='0004_initial' else target],env=env,capture_output=True,text=True,timeout=60)
        assert result.returncode==0,result.stderr
    migrate('0004_initial')
    engine=create_engine(url)
    with Session(engine) as s:
        s.add_all([frozen.Source(id='test',url='https://official.example',official=True,permitted=True,license='test only'),frozen.Club(id=1,code=1,name='Test Club',short_name='TC'),frozen.Manager(id=1,name='Test Manager')]);s.flush()
        s.add(frozen.Evidence(id=1,source_id='test',digest='0'*64,uri='https://official.example/a',payload={}));s.flush()
        start=datetime(2024,1,1,tzinfo=timezone.utc)
        s.add(frozen.Tenure(id=1,manager_id=1,club_id=1,starts_at=start,evidence_id=1));s.flush()
        s.add(frozen.TacticalRegime(id=1,club_id=1,tenure_id=1,effective_at=start,reason='test only'));s.commit()
    migrate('head')
    inspector=inspect(engine)
    for table in Base.metadata.sorted_tables:
        assert {c.name for c in table.columns}=={c['name'] for c in inspector.get_columns(table.name)},table.name
    with engine.connect() as c:
        assert c.execute(text('SELECT COUNT(*) FROM manager_tenures')).scalar()==1
        assert not c.execute(text('PRAGMA foreign_key_check')).all()
    engine.dispose()
    migrate('0004')
    migrate('head')
