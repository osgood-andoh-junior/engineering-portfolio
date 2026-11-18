"""Version topology and store isolated replay and fault evidence."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    ts = sa.DateTime(timezone=True)
    op.create_table(
        "dependency_graphs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("edges", JSONB, nullable=False),
        sa.Column("created_at", ts, server_default=sa.func.now(), nullable=False),
    )
    op.execute(
        """INSERT INTO dependency_graphs (edges)
        VALUES ('[["messaging", "identity"], ["storage", "identity"]]')"""
    )
    op.add_column(
        "health_checks",
        sa.Column(
            "graph_id",
            sa.Integer,
            sa.ForeignKey("dependency_graphs.id", name="fk_health_checks_graph"),
        ),
    )
    op.add_column("health_checks", sa.Column("blocked_by", sa.String(32)))
    op.add_column("fault_configurations", sa.Column("expires_at", ts))
    op.create_table(
        "fault_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("service_slug", sa.String(32), sa.ForeignKey("services.slug"), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("latency_ms", sa.Integer, nullable=False),
        sa.Column("occurred_at", ts, nullable=False),
        sa.Column("expires_at", ts),
    )
    op.create_index("ix_fault_events_occurred_at", "fault_events", ["occurred_at"])
    op.create_table(
        "replay_sessions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("created_at", ts, server_default=sa.func.now(), nullable=False),
        sa.Column("payload", JSONB, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("replay_sessions")
    op.drop_table("fault_events")
    op.drop_column("fault_configurations", "expires_at")
    op.drop_column("health_checks", "blocked_by")
    op.drop_constraint("fk_health_checks_graph", "health_checks", type_="foreignkey")
    op.drop_column("health_checks", "graph_id")
    op.drop_table("dependency_graphs")
