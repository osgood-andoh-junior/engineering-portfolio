import importlib.util
from io import StringIO
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_frozen_migration_renders_postgresql_ddl_without_connecting():
    source = Path(__file__).parents[2] / "alembic" / "versions" / "0001_initial.py"
    spec = importlib.util.spec_from_file_location("initial_migration", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output = StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output}
    )
    with Operations.context(context):
        module.upgrade()
    sql = output.getvalue()
    assert sql.count("CREATE TABLE ") == 22
    assert "CREATE TABLE inventory" in sql
    assert "UNIQUE (provider, event_id)" in sql
    assert "reserved <= quantity" in sql
