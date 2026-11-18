"""One-time offline initial migration generator. Does not connect to any database."""

from pathlib import Path

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from app.db.base import Base
from app.models import entities  # noqa: F401

destination = Path(__file__).parent.parent / "alembic" / "versions" / "0001_initial.py"
if destination.exists():
    raise SystemExit("Initial migration already frozen. Create a new reviewed revision instead.")
statements = []
for table in Base.metadata.sorted_tables:
    statements.append(str(CreateTable(table).compile(dialect=postgresql.dialect())))
    for index in sorted(table.indexes, key=lambda i: i.name):
        statements.append(str(CreateIndex(index).compile(dialect=postgresql.dialect())))
source = '"""Frozen initial PostgreSQL schema; generated offline, review before migration."""\nfrom alembic import op\n\nrevision = "0001"\ndown_revision = None\nbranch_labels = None\ndepends_on = None\n\ndef upgrade():\n'
source += "".join(f"    op.execute({statement!r})\n" for statement in statements)
source += "\ndef downgrade():\n" + "".join(
    f"    op.drop_table({table.name!r})\n" for table in reversed(Base.metadata.sorted_tables)
)
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(source, encoding="utf-8")
