"""Temporal coaching, transfer provenance and durable refresh jobs."""
from alembic import op
from infrastructure.migrations.schema_v1 import Base

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None
TABLES = {'managers','manager_tenures','squad_membership_history','transfer_events','tactical_regimes','team_tactical_features','background_jobs'}
def upgrade():
    Base.metadata.create_all(op.get_bind(), tables=[t for t in Base.metadata.sorted_tables if t.name in TABLES])
def downgrade():
    Base.metadata.drop_all(op.get_bind(), tables=[t for t in Base.metadata.sorted_tables if t.name in TABLES])
