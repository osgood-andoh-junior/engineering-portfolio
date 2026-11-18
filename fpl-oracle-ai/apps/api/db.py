from datetime import datetime, timezone
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from apps.api.config import settings

def utcnow():
    return datetime.now(timezone.utc)

class Base(DeclarativeBase):
    pass

settings.data_dir.mkdir(parents=True, exist_ok=True)
engine = create_engine(settings.database_url, pool_pre_ping=True, **({'connect_args': {'check_same_thread': False}} if settings.database_url.startswith('sqlite') else {}))
if settings.database_url.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def sqlite_fk(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA journal_mode=WAL')
        connection.execute('PRAGMA busy_timeout=5000')
Session = sessionmaker(engine, expire_on_commit=False)

def session_dependency():
    with Session() as session:
        yield session
