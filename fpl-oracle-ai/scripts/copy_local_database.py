"""Copy an existing verified SQLite warehouse to an empty migrated PostgreSQL DB."""
import json
from pathlib import Path
from sqlalchemy import create_engine,select,func,text,Integer
from apps.api.db import Base,engine
import apps.api.models  # Register all tables before copying.


def main():
    source_path=Path('data/oracle.db').resolve()
    if not source_path.is_file():
        raise SystemExit('Existing local SQLite warehouse not found')
    if engine.dialect.name!='postgresql':
        raise SystemExit('Set DATABASE_URL to the empty migrated PostgreSQL target')
    source=create_engine('sqlite:///'+source_path.as_posix())
    counts={}
    with source.connect() as incoming,engine.begin() as outgoing:
        incoming.execute(text('PRAGMA query_only=ON'))
        source_revision=incoming.scalar(text('SELECT version_num FROM alembic_version'))
        target_revision=outgoing.scalar(text('SELECT version_num FROM alembic_version'))
        if source_revision!=target_revision:
            raise SystemExit('Source and target migration revisions must match')
        tables=list(Base.metadata.sorted_tables)
        if any(outgoing.scalar(select(func.count()).select_from(t)) for t in tables):
            raise SystemExit('Target must be empty; existing records are never overwritten')
        for table in tables:
            count=0
            result=incoming.execute(select(table))
            for batch in result.mappings().partitions(500):
                rows=[dict(row) for row in batch]
                outgoing.execute(table.insert(),rows)
                count+=len(rows)
            counts[table.name]=count
            if outgoing.scalar(select(func.count()).select_from(table))!=count:
                raise RuntimeError('Count mismatch: '+table.name)
            if 'id' in table.c and isinstance(table.c.id.type,Integer):
                sequence=outgoing.scalar(text("SELECT pg_get_serial_sequence(:table_name,'id')"),{'table_name':table.name})
                if sequence:
                    maximum=outgoing.scalar(select(func.max(table.c.id))) or 0
                    outgoing.execute(text('SELECT setval(CAST(:sequence AS regclass),:value,:called)'),{'sequence':sequence,'value':max(1,maximum),'called':maximum>0})
    source.dispose()
    Path('data/postgres-copy-report.json').write_text(json.dumps(counts,indent=2))
    print(json.dumps({'copied_existing_real_records':counts,'source_preserved':True},indent=2))


if __name__=='__main__':
    main()
