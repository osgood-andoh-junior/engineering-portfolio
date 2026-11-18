"""Add recovery policy, experiment and execution records."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None
TS = sa.DateTime(timezone=True)


def reference(name, target, *, primary_key=False, nullable=False):
    kind = sa.String(32) if target in {"services.slug", "recovery_policies.name"} else sa.Integer
    return sa.Column(name, kind, sa.ForeignKey(target), primary_key=primary_key, nullable=nullable)


def created(name):
    return sa.Column(name, TS, nullable=False, server_default=sa.func.now())


def upgrade():
    op.create_table("recovery_policies", sa.Column("name", sa.String(32), primary_key=True))
    op.execute(
        "INSERT INTO recovery_policies (name) VALUES "
        "('baseline'), ('retry'), ('breaker'), ('limit'), ('failover'), ('combined'), ('manual')"
    )
    op.create_table(
        "recovery_policy_versions",
        sa.Column("id", sa.Integer, primary_key=True),
        reference("policy", "recovery_policies.name"),
        sa.Column("parameters", JSONB, nullable=False),
        created("created_at"),
    )
    op.create_table(
        "recovery_experiments",
        sa.Column("id", sa.Integer, primary_key=True),
        reference("version_id", "recovery_policy_versions.id"),
        reference("replay_id", "replay_sessions.id", nullable=True),
        sa.Column("scenario", sa.String(32), nullable=False),
        sa.Column("seed", sa.Integer, nullable=False),
        created("created_at"),
    )
    op.create_table(
        "recovery_experiment_results",
        reference("experiment_id", "recovery_experiments.id", primary_key=True),
        reference("policy", "recovery_policies.name", primary_key=True),
        sa.Column("metrics", JSONB, nullable=False),
    )
    op.create_table(
        "recovery_recommendations",
        reference("incident_id", "incidents.id", primary_key=True),
        sa.Column("evidence", JSONB, nullable=False),
        created("updated_at"),
    )
    op.create_table(
        "recovery_approvals",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("key", sa.String(36), nullable=False, unique=True),
        reference("incident_id", "incidents.id"),
        reference("target", "services.slug"),
        sa.Column("action", sa.String(24), nullable=False),
        sa.Column("operator", sa.String(64), nullable=False),
        sa.Column("requested_at", TS, nullable=False),
        sa.Column("approved_at", TS),
    )
    op.create_table(
        "recovery_executions",
        reference("approval_id", "recovery_approvals.id", primary_key=True),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("started_at", TS, nullable=False),
        sa.Column("deadline", TS, nullable=False),
        sa.Column("evidence", JSONB, nullable=False),
    )
    op.create_table(
        "recovery_audit_events",
        sa.Column("id", sa.Integer, primary_key=True),
        reference("approval_id", "recovery_approvals.id", nullable=True),
        sa.Column("operator", sa.String(64), nullable=False),
        sa.Column("event", sa.String(32), nullable=False),
        created("occurred_at"),
        sa.Column("evidence", JSONB, nullable=False),
    )
    op.create_table(
        "simulator_runtime",
        reference("service_slug", "services.slug", primary_key=True),
        sa.Column("restarting_until", TS, nullable=False),
    )


def downgrade():
    for table in (
        "simulator_runtime",
        "recovery_audit_events",
        "recovery_executions",
        "recovery_approvals",
        "recovery_recommendations",
        "recovery_experiment_results",
        "recovery_experiments",
        "recovery_policy_versions",
        "recovery_policies",
    ):
        op.drop_table(table)
