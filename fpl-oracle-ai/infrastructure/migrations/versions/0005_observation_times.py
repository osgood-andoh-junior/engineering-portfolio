"""Separate observation/ingestion and record when temporal departures became known."""
from alembic import op
import sqlalchemy as sa
revision='0005'
down_revision='0004'
branch_labels=None
depends_on=None
def upgrade():
    bind=op.get_bind()
    for table in ('manager_tenures','squad_membership_history'):
        names={c['name'] for c in sa.inspect(bind).get_columns(table)}
        if 'ends_observed_at' not in names:op.add_column(table,sa.Column('ends_observed_at',sa.DateTime(timezone=True),nullable=True))
        if 'end_evidence_id' not in names:
            if bind.dialect.name=='sqlite':
                op.execute(sa.text(f'ALTER TABLE {table} ADD COLUMN end_evidence_id INTEGER REFERENCES source_evidence(id)'))
            else:
                op.add_column(table,sa.Column('end_evidence_id',sa.Integer(),sa.ForeignKey('source_evidence.id',name=f'fk_{table}_end_evidence'),nullable=True))
    names={c['name'] for c in sa.inspect(bind).get_columns('source_evidence')}
    if 'ingested_at' not in names:
        op.add_column('source_evidence',sa.Column('ingested_at',sa.DateTime(timezone=True),nullable=True))
        bind.execute(sa.text('UPDATE source_evidence SET ingested_at=observed_at WHERE ingested_at IS NULL'))
def downgrade():
    op.drop_column('source_evidence','ingested_at')
    for table in ('manager_tenures','squad_membership_history'):
        if op.get_bind().dialect.name!='sqlite':op.drop_constraint(f'fk_{table}_end_evidence',table,type_='foreignkey')
        op.drop_column(table,'end_evidence_id');op.drop_column(table,'ends_observed_at')
