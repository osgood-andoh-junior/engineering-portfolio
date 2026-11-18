"""Core warehouse and prediction schema."""
from alembic import op
from infrastructure.migrations.schema_v1 import Base

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None
CORE = {'sources','seasons','clubs','players','player_season_identities','fixtures','gameweeks','source_evidence','player_fixture_stats','feature_snapshots','model_versions','predictions','audit_logs'}
def upgrade():
    Base.metadata.create_all(op.get_bind(), tables=[t for t in Base.metadata.sorted_tables if t.name in CORE])
def downgrade():
    Base.metadata.drop_all(op.get_bind(), tables=[t for t in Base.metadata.sorted_tables if t.name in CORE])
