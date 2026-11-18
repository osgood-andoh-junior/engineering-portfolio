from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.config import settings


@lru_cache
def database_engine() -> Engine:
    return create_engine(
        settings().database_url,
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={"connect_timeout": 5},
    )


@lru_cache
def sessions() -> sessionmaker[Session]:
    return sessionmaker(database_engine(), expire_on_commit=False)
