"""Verified source-specific entity identities; names alone never merge people."""
from alembic import op
from infrastructure.migrations.schema_v1 import Base

revision='0004'
down_revision='0003'
branch_labels=None
depends_on=None
def upgrade():Base.metadata.tables['external_entity_mappings'].create(op.get_bind())
def downgrade():Base.metadata.tables['external_entity_mappings'].drop(op.get_bind())
