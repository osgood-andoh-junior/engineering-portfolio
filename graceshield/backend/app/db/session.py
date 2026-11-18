from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings


@lru_cache
def get_engine():
    settings = get_settings()
    url = settings.isolated_test_url() if settings.app_env == "test" else settings.connection_url()
    return create_engine(
        url,
        pool_size=3,
        max_overflow=2,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args={"connect_timeout": 10, "prepare_threshold": None},
        hide_parameters=True,
    )


def get_db():
    with Session(get_engine(), expire_on_commit=False) as session:
        try:
            yield session
            session.commit()
        except BaseException:
            session.rollback()
            raise
