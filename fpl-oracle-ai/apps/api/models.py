from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, JSON, UniqueConstraint, CheckConstraint, Index, Text
from sqlalchemy.orm import Mapped, mapped_column
from apps.api.db import Base, utcnow

class Source(Base):
    __tablename__ = 'sources'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    url: Mapped[str] = mapped_column(String(600))
    official: Mapped[bool] = mapped_column(default=False)
    permitted: Mapped[bool] = mapped_column(default=False)
    license: Mapped[str] = mapped_column(Text, default='Unverified')
    last_success: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)

class Season(Base):
    __tablename__ = 'seasons'
    id: Mapped[str] = mapped_column(String(9), primary_key=True)
    rules: Mapped[dict | None] = mapped_column(JSON)
    rules_verified: Mapped[bool] = mapped_column(default=False)

class Club(Base):
    __tablename__ = 'clubs'
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[int] = mapped_column(unique=True)
    name: Mapped[str] = mapped_column(String(120))
    short_name: Mapped[str] = mapped_column(String(10))

class Player(Base):
    __tablename__ = 'players'
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[int] = mapped_column(unique=True)
    name: Mapped[str] = mapped_column(String(160))
    club_id: Mapped[int | None] = mapped_column(ForeignKey('clubs.id'), index=True)
    position: Mapped[int] = mapped_column(Integer)
    price: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30))
    registration_state: Mapped[str] = mapped_column(String(32),default='unknown')
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (CheckConstraint('position BETWEEN 1 AND 4'), CheckConstraint('price >= 0'))

class Identity(Base):
    __tablename__ = 'player_season_identities'
    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[str] = mapped_column(ForeignKey('seasons.id'))
    fpl_id: Mapped[int] = mapped_column(Integer)
    player_id: Mapped[int | None] = mapped_column(ForeignKey('players.id'))
    code: Mapped[int | None] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(160))
    __table_args__ = (UniqueConstraint('season_id', 'fpl_id'),)

class Fixture(Base):
    __tablename__ = 'fixtures'
    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[str] = mapped_column(ForeignKey('seasons.id'), index=True)
    provider_id: Mapped[int] = mapped_column(Integer)
    event: Mapped[int | None] = mapped_column(Integer)
    home_id: Mapped[int] = mapped_column(ForeignKey('clubs.id'))
    away_id: Mapped[int] = mapped_column(ForeignKey('clubs.id'))
    kickoff: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished: Mapped[bool] = mapped_column(default=False)
    home_score: Mapped[int | None] = mapped_column(Integer)
    away_score: Mapped[int | None] = mapped_column(Integer)
    __table_args__ = (UniqueConstraint('season_id', 'provider_id'),)

class Gameweek(Base):
    __tablename__ = 'gameweeks'
    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[str] = mapped_column(ForeignKey('seasons.id'))
    event: Mapped[int] = mapped_column(Integer)
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    current: Mapped[bool] = mapped_column(default=False)
    finished: Mapped[bool] = mapped_column(default=False)
    __table_args__ = (UniqueConstraint('season_id', 'event'),)

class Evidence(Base):
    __tablename__ = 'source_evidence'
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey('sources.id'))
    digest: Mapped[str] = mapped_column(String(64), unique=True)
    uri: Mapped[str] = mapped_column(Text)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),default=utcnow)
    payload: Mapped[dict] = mapped_column(JSON)

class HistoricalStat(Base):
    __tablename__ = 'player_fixture_stats'
    id: Mapped[int] = mapped_column(primary_key=True)
    season: Mapped[str] = mapped_column(ForeignKey('seasons.id'), index=True)
    fpl_id: Mapped[int] = mapped_column(Integer, index=True)
    fixture: Mapped[int] = mapped_column(Integer)
    kickoff: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    points: Mapped[float] = mapped_column(Float)
    minutes: Mapped[int] = mapped_column(Integer)
    position: Mapped[int | None] = mapped_column(Integer)
    team: Mapped[str | None] = mapped_column(String(120))
    opponent: Mapped[int | None] = mapped_column(Integer)
    home: Mapped[bool] = mapped_column(default=False)
    price: Mapped[int | None] = mapped_column(Integer)
    xg: Mapped[float | None] = mapped_column(Float)
    xa: Mapped[float | None] = mapped_column(Float)
    evidence_id: Mapped[int] = mapped_column(ForeignKey('source_evidence.id'))
    __table_args__ = (UniqueConstraint('season', 'fpl_id', 'fixture'), CheckConstraint('minutes BETWEEN 0 AND 150'))

class Manager(Base):
    __tablename__ = 'managers'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))

class Tenure(Base):
    __tablename__ = 'manager_tenures'
    id: Mapped[int] = mapped_column(primary_key=True)
    manager_id: Mapped[int] = mapped_column(ForeignKey('managers.id'), index=True)
    club_id: Mapped[int] = mapped_column(ForeignKey('clubs.id'), index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_evidence_id: Mapped[int | None] = mapped_column(ForeignKey('source_evidence.id'))
    interim: Mapped[bool] = mapped_column(default=False)
    evidence_id: Mapped[int] = mapped_column(ForeignKey('source_evidence.id'))
    __table_args__ = (CheckConstraint('ends_at IS NULL OR ends_at > starts_at'), Index('one_open_tenure_per_club', 'club_id', unique=True, postgresql_where=__import__('sqlalchemy').text('ends_at IS NULL'), sqlite_where=__import__('sqlalchemy').text('ends_at IS NULL')))

class Membership(Base):
    __tablename__ = 'squad_membership_history'
    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey('players.id'), index=True)
    club_id: Mapped[int | None] = mapped_column(ForeignKey('clubs.id'))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_evidence_id: Mapped[int | None] = mapped_column(ForeignKey('source_evidence.id'))
    evidence_id: Mapped[int] = mapped_column(ForeignKey('source_evidence.id'))
    __table_args__ = (CheckConstraint('ends_at IS NULL OR ends_at > starts_at'), Index('one_open_membership', 'player_id', unique=True, postgresql_where=__import__('sqlalchemy').text('ends_at IS NULL'), sqlite_where=__import__('sqlalchemy').text('ends_at IS NULL')))

class FootballEvent(Base):
    __tablename__ = 'transfer_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True)
    kind: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(12))
    player_id: Mapped[int | None] = mapped_column(ForeignKey('players.id'))
    manager_id: Mapped[int | None] = mapped_column(ForeignKey('managers.id'))
    from_club_id: Mapped[int | None] = mapped_column(ForeignKey('clubs.id'))
    to_club_id: Mapped[int | None] = mapped_column(ForeignKey('clubs.id'))
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    announced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    evidence_id: Mapped[int] = mapped_column(ForeignKey('source_evidence.id'))
    __table_args__ = (CheckConstraint("status IN ('CONFIRMED','REPORTED','RUMORED')"),)

class TacticalRegime(Base):
    __tablename__ = 'tactical_regimes'
    id: Mapped[int] = mapped_column(primary_key=True)
    club_id: Mapped[int] = mapped_column(ForeignKey('clubs.id'), index=True)
    tenure_id: Mapped[int | None] = mapped_column(ForeignKey('manager_tenures.id'))
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str] = mapped_column(String(160))

class TacticalObservation(Base):
    __tablename__ = 'team_tactical_features'
    id: Mapped[int] = mapped_column(primary_key=True)
    club_id: Mapped[int] = mapped_column(ForeignKey('clubs.id'), index=True)
    match_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    formation: Mapped[str | None] = mapped_column(String(30))
    possession: Mapped[float | None] = mapped_column(Float)
    pressing: Mapped[float | None] = mapped_column(Float)
    inferred: Mapped[bool] = mapped_column(default=False)
    evidence_id: Mapped[int] = mapped_column(ForeignKey('source_evidence.id'))
    __table_args__ = (CheckConstraint('possession IS NULL OR possession BETWEEN 0 AND 100'), UniqueConstraint('club_id', 'match_at', 'evidence_id'))

class FeatureSnapshot(Base):
    __tablename__ = 'feature_snapshots'
    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey('players.id'))
    cutoff: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    values: Mapped[dict] = mapped_column(JSON)
    digest: Mapped[str] = mapped_column(String(64))

class ModelVersion(Base):
    __tablename__ = 'model_versions'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    kind: Mapped[str] = mapped_column(String(40))
    trained_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    metrics: Mapped[dict] = mapped_column(JSON)
    artifact: Mapped[str] = mapped_column(Text)
    promoted: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Prediction(Base):
    __tablename__ = 'predictions'
    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey('players.id'), index=True)
    model_id: Mapped[str] = mapped_column(ForeignKey('model_versions.id'))
    batch: Mapped[str] = mapped_column(String(64), index=True)
    event: Mapped[int] = mapped_column(Integer)
    horizon: Mapped[int] = mapped_column(Integer, default=1)
    values: Mapped[dict] = mapped_column(JSON)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint('player_id', 'batch', 'event', 'horizon'),)

class Job(Base):
    __tablename__ = 'background_jobs'
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(160), unique=True)
    kind: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default='pending', index=True)
    attempts: Mapped[int] = mapped_column(default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)

class Audit(Base):
    __tablename__ = 'audit_logs'
    id: Mapped[int] = mapped_column(primary_key=True)
    action: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class ManagerMatchStat(Base):
    __tablename__ = 'manager_match_statistics'
    id: Mapped[int] = mapped_column(primary_key=True)
    tenure_id: Mapped[int] = mapped_column(ForeignKey('manager_tenures.id'),index=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey('fixtures.id'))
    played_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    goals_for: Mapped[int] = mapped_column(Integer)
    goals_against: Mapped[int] = mapped_column(Integer)
    home: Mapped[bool] = mapped_column()
    formation: Mapped[str | None] = mapped_column(String(30))
    possession: Mapped[float | None] = mapped_column(Float)
    pressing: Mapped[float | None] = mapped_column(Float)
    xi_changes: Mapped[int | None] = mapped_column(Integer)
    first_sub_minute: Mapped[int | None] = mapped_column(Integer)
    evidence_id: Mapped[int] = mapped_column(ForeignKey('source_evidence.id'))
    __table_args__ = (UniqueConstraint('tenure_id','fixture_id'),CheckConstraint('goals_for >= 0 AND goals_against >= 0'),CheckConstraint('possession IS NULL OR possession BETWEEN 0 AND 100'),CheckConstraint('xi_changes IS NULL OR xi_changes BETWEEN 0 AND 11'))

class PlayerRole(Base):
    __tablename__ = 'player_tactical_roles'
    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey('players.id'),index=True)
    tenure_id: Mapped[int] = mapped_column(ForeignKey('manager_tenures.id'))
    role: Mapped[str] = mapped_column(String(80))
    inferred: Mapped[bool] = mapped_column(default=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    evidence_id: Mapped[int] = mapped_column(ForeignKey('source_evidence.id'))

class PriceSnapshot(Base):
    __tablename__ = 'player_price_history'
    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey('players.id'),index=True)
    price: Mapped[int] = mapped_column(Integer)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    evidence_id: Mapped[int] = mapped_column(ForeignKey('source_evidence.id'))
    __table_args__ = (UniqueConstraint('player_id','evidence_id'),CheckConstraint('price >= 0'))

class AvailabilitySnapshot(Base):
    __tablename__ = 'player_availability_snapshots'
    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey('players.id'),index=True)
    status: Mapped[str] = mapped_column(String(30))
    chance: Mapped[int | None] = mapped_column(Integer)
    news: Mapped[str | None] = mapped_column(Text)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    evidence_id: Mapped[int] = mapped_column(ForeignKey('source_evidence.id'))
    __table_args__ = (UniqueConstraint('player_id','evidence_id'),CheckConstraint('chance IS NULL OR chance BETWEEN 0 AND 100'))

class ExternalMapping(Base):
    __tablename__ = 'external_entity_mappings'
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey('sources.id'))
    external_id: Mapped[str] = mapped_column(String(160))
    entity_kind: Mapped[str] = mapped_column(String(20))
    manager_id: Mapped[int | None] = mapped_column(ForeignKey('managers.id'))
    player_id: Mapped[int | None] = mapped_column(ForeignKey('players.id'))
    club_id: Mapped[int | None] = mapped_column(ForeignKey('clubs.id'))
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=utcnow)
    __table_args__=(UniqueConstraint('source_id','external_id','entity_kind'),CheckConstraint("(entity_kind='manager' AND manager_id IS NOT NULL AND player_id IS NULL AND club_id IS NULL) OR (entity_kind='player' AND player_id IS NOT NULL AND manager_id IS NULL AND club_id IS NULL) OR (entity_kind='club' AND club_id IS NOT NULL AND manager_id IS NULL AND player_id IS NULL)"))
