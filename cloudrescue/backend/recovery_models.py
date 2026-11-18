from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.models import Base


class RecoveryPolicy(Base):
    __tablename__ = "recovery_policies"

    name: Mapped[str] = mapped_column(String(32), primary_key=True)


class PolicyVersion(Base):
    __tablename__ = "recovery_policy_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    policy: Mapped[str] = mapped_column(ForeignKey("recovery_policies.name"))
    parameters: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RecoveryExperiment(Base):
    __tablename__ = "recovery_experiments"

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("recovery_policy_versions.id"))
    replay_id: Mapped[int | None] = mapped_column(ForeignKey("replay_sessions.id"))
    scenario: Mapped[str] = mapped_column(String(32))
    seed: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExperimentResult(Base):
    __tablename__ = "recovery_experiment_results"

    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("recovery_experiments.id"), primary_key=True
    )
    policy: Mapped[str] = mapped_column(ForeignKey("recovery_policies.name"), primary_key=True)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB)


class Recommendation(Base):
    __tablename__ = "recovery_recommendations"

    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), primary_key=True)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Approval(Base):
    __tablename__ = "recovery_approvals"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(36), unique=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"))
    target: Mapped[str] = mapped_column(ForeignKey("services.slug"))
    action: Mapped[str] = mapped_column(String(24))
    operator: Mapped[str] = mapped_column(String(64))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Execution(Base):
    __tablename__ = "recovery_executions"

    approval_id: Mapped[int] = mapped_column(ForeignKey("recovery_approvals.id"), primary_key=True)
    status: Mapped[str] = mapped_column(String(24))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB)


class AuditEvent(Base):
    __tablename__ = "recovery_audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    approval_id: Mapped[int | None] = mapped_column(ForeignKey("recovery_approvals.id"))
    operator: Mapped[str] = mapped_column(String(64))
    event: Mapped[str] = mapped_column(String(32))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB)


class SimulatorRuntime(Base):
    __tablename__ = "simulator_runtime"

    service_slug: Mapped[str] = mapped_column(ForeignKey("services.slug"), primary_key=True)
    restarting_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
