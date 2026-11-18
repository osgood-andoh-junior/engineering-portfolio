"""Manager match facts, dated roles and player price/availability snapshots."""
from alembic import op
from infrastructure.migrations.schema_v1 import Base

revision='0003'
down_revision='0002'
branch_labels=None
depends_on=None
TABLES={'manager_match_statistics','player_tactical_roles','player_price_history','player_availability_snapshots'}
def upgrade():
    Base.metadata.create_all(op.get_bind(),tables=[t for t in Base.metadata.sorted_tables if t.name in TABLES])
def downgrade():
    Base.metadata.drop_all(op.get_bind(),tables=[t for t in Base.metadata.sorted_tables if t.name in TABLES])
