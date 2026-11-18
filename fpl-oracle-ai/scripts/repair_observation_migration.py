"""One-time repair of our interrupted local SQLite migration; never drop application tables."""
from pathlib import Path
import sqlite3
import shutil
from datetime import datetime,timezone

def main():
    path=Path('data/oracle.db').resolve()
    if path.parent!=Path('data').resolve():raise RuntimeError('Unexpected database path')
    folder=Path('data/backups');folder.mkdir(parents=True,exist_ok=True)
    target=folder/('before-observation-repair-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'.db')
    with sqlite3.connect(path) as source,sqlite3.connect(target) as backup:
        source.backup(backup)
        tables={r[0] for r in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if '_alembic_tmp_manager_tenures' in tables:
            original=source.execute('SELECT COUNT(*) FROM manager_tenures').fetchone()[0]
            staged=source.execute('SELECT COUNT(*) FROM _alembic_tmp_manager_tenures').fetchone()[0]
            if staged not in (0,original):raise RuntimeError('Nonempty staging/original counts differ; manual review required')
            original_ids=source.execute('SELECT id FROM manager_tenures ORDER BY id').fetchall()
            staged_ids=source.execute('SELECT id FROM _alembic_tmp_manager_tenures ORDER BY id').fetchall()
            if staged and original_ids!=staged_ids:raise RuntimeError('Staging identities differ; manual review required')
            source.execute('DROP TABLE _alembic_tmp_manager_tenures')
            source.commit()
        assert not source.execute('PRAGMA foreign_key_check').fetchall()
    print({'backup':str(target),'status':'original application tables preserved'})

if __name__=='__main__':main()
