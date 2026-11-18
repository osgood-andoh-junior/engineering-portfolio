from sqlalchemy import create_engine, pool

from alembic import context
from app.core.config import get_settings, validate_database
from app.db.base import Base
from app.models import entities  # noqa: F401

settings = get_settings()
if settings.app_env == "production":
    raise RuntimeError(
        "Production migrations require separate explicit approval and a reviewed procedure."
    )
url = (
    settings.isolated_test_url()
    if settings.app_env == "test"
    else validate_database(
        settings.migration_database_url.get_secret_value() or settings.connection_url()
    )
)
if context.is_offline_mode():
    context.configure(
        url=url,
        target_metadata=Base.metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(
        url,
        poolclass=pool.NullPool,
        connect_args={"prepare_threshold": None, "connect_timeout": 10},
        hide_parameters=True,
    )
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
