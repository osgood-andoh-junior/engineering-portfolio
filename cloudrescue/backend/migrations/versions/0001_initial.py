"""Create the initial CloudRescue schema."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    timestamp = sa.DateTime(timezone=True)
    op.create_table(
        "services",
        sa.Column("slug", sa.String(32), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("state", sa.String(12), nullable=False),
        sa.Column("consecutive_failures", sa.Integer, nullable=False),
        sa.Column("recovery_streak", sa.Integer, nullable=False),
        sa.Column("last_success_at", timestamp),
        sa.Column("failure_started_at", timestamp),
    )
    op.create_table(
        "health_checks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("service_slug", sa.String(32), sa.ForeignKey("services.slug"), nullable=False),
        sa.Column("checked_at", timestamp, nullable=False),
        sa.Column("status_code", sa.Integer),
        sa.Column("latency_ms", sa.Float, nullable=False),
        sa.Column("available", sa.Boolean, nullable=False),
        sa.Column("error", sa.String(32)),
    )
    op.create_index("ix_checks_service_time", "health_checks", ["service_slug", "checked_at"])
    op.create_index("ix_health_checks_checked_at", "health_checks", ["checked_at"])
    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("service_slug", sa.String(32), sa.ForeignKey("services.slug"), nullable=False),
        sa.Column("started_at", timestamp, nullable=False),
        sa.Column("detected_at", timestamp, nullable=False),
        sa.Column("recovery_started_at", timestamp),
        sa.Column("closed_at", timestamp),
    )
    op.create_index("ix_incidents_service_slug", "incidents", ["service_slug"])
    op.create_index("ix_incidents_detected_at", "incidents", ["detected_at"])
    op.create_index(
        "uq_incidents_open_service",
        "incidents",
        ["service_slug"],
        unique=True,
        postgresql_where=sa.text("closed_at IS NULL"),
    )
    op.create_table(
        "incident_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("incident_id", sa.Integer, sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column("check_id", sa.Integer, sa.ForeignKey("health_checks.id"), nullable=False),
        sa.Column("occurred_at", timestamp, nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
    )
    op.create_index("ix_incident_events_incident_id", "incident_events", ["incident_id"])
    op.create_table(
        "fault_configurations",
        sa.Column("service_slug", sa.String(32), sa.ForeignKey("services.slug"), primary_key=True),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("latency_ms", sa.Integer, nullable=False),
        sa.Column("updated_at", timestamp, nullable=False),
    )
    op.create_table(
        "application_settings",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("value", JSONB, nullable=False),
    )


def downgrade() -> None:
    for name in (
        "application_settings",
        "fault_configurations",
        "incident_events",
        "incidents",
        "health_checks",
        "services",
    ):
        op.drop_table(name)
