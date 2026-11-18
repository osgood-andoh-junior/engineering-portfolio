"""Persist operator sessions, benchmark runs, and audit verification."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    ts = sa.DateTime(timezone=True)
    op.create_table(
        "operators",
        sa.Column("username", sa.String(48), primary_key=True),
        sa.Column("password", sa.String(160), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "operator_sessions",
        sa.Column("digest", sa.String(64), primary_key=True),
        sa.Column("username", sa.String(48), sa.ForeignKey("operators.username"), nullable=False),
        sa.Column("expires_at", ts, nullable=False),
    )
    op.create_table(
        "audit_chain",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("previous", sa.String(64), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.Column("payload", JSONB, nullable=False),
    )
    for table, document in (("audit_verifications", "result"), ("benchmark_runs", "payload")):
        op.create_table(
            table,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("actor", sa.String(64), nullable=False),
            sa.Column(document, JSONB, nullable=False),
            sa.Column("created_at", ts, nullable=False, server_default=sa.func.now()),
        )


def downgrade():
    for table in (
        "benchmark_runs",
        "audit_verifications",
        "audit_chain",
        "operator_sessions",
        "operators",
    ):
        op.drop_table(table)
