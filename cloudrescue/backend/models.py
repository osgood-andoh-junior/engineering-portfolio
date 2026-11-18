from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Service(Base):
    __tablename__ = "services"

    slug: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(12), default="healthy")
    consecutive_failures: Mapped[int] = mapped_column(default=0)
    recovery_streak: Mapped[int] = mapped_column(default=0)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class HealthCheck(Base):
    __tablename__ = "health_checks"
    __table_args__ = (Index("ix_checks_service_time", "service_slug", "checked_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    service_slug: Mapped[str] = mapped_column(ForeignKey("services.slug"))
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status_code: Mapped[int | None]
    latency_ms: Mapped[float]
    available: Mapped[bool]
    error: Mapped[str | None] = mapped_column(String(32))
    graph_id: Mapped[int | None] = mapped_column(
        ForeignKey("dependency_graphs.id", name="fk_health_checks_graph")
    )
    blocked_by: Mapped[str | None] = mapped_column(String(32))


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        Index(
            "uq_incidents_open_service",
            "service_slug",
            unique=True,
            postgresql_where=text("closed_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    service_slug: Mapped[str] = mapped_column(ForeignKey("services.slug"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    recovery_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IncidentEvent(Base):
    __tablename__ = "incident_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), index=True)
    check_id: Mapped[int] = mapped_column(ForeignKey("health_checks.id"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    kind: Mapped[str] = mapped_column(String(32))


class FaultConfiguration(Base):
    __tablename__ = "fault_configurations"

    service_slug: Mapped[str] = mapped_column(ForeignKey("services.slug"), primary_key=True)
    mode: Mapped[str] = mapped_column(String(16))
    latency_ms: Mapped[int]
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ApplicationSetting(Base):
    __tablename__ = "application_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSONB)


class DependencyGraph(Base):
    __tablename__ = "dependency_graphs"

    id: Mapped[int] = mapped_column(primary_key=True)
    edges: Mapped[list[list[str]]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FaultEvent(Base):
    __tablename__ = "fault_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    service_slug: Mapped[str] = mapped_column(ForeignKey("services.slug"))
    mode: Mapped[str] = mapped_column(String(16))
    latency_ms: Mapped[int]
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReplaySession(Base):
    __tablename__ = "replay_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
