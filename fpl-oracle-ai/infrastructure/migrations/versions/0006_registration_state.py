"""Separate confirmed football membership from verified FPL registration state."""
from alembic import op
import sqlalchemy as sa
revision='0006'
down_revision='0005'
branch_labels=None
depends_on=None
def upgrade():
    op.add_column('players',sa.Column('registration_state',sa.String(32),nullable=False,server_default='unknown'))
def downgrade():op.drop_column('players','registration_state')
