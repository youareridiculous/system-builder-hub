"""Add analytics and usage tracking

Revision ID: 0005
Revises: 0004
Create Date: 2024-01-15 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create analytics_events table
    op.create_table('analytics_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=True),
        sa.Column('source', sa.Enum('app', 'api', 'webhook', 'job', 'payments', 'files', 'builder', 'agent', name='analytics_source_enum'), 
                  nullable=False, default='app'),
        sa.Column('event', sa.Text, nullable=False),
        sa.Column('ts', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('props', postgresql.JSONB, nullable=True),
        sa.Column('ip', sa.Text, nullable=True),
        sa.Column('request_id', sa.Text, nullable=True),
        sa.Index('idx_analytics_events_tenant_ts', 'tenant_id', 'ts'),
        sa.Index('idx_analytics_events_tenant_event_ts', 'tenant_id', 'event', 'ts'),
        sa.Index('idx_analytics_events_ts', 'ts')
    )

    # Create analytics_daily_usage table
    op.create_table('analytics_daily_usage',
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('metric', sa.Text, nullable=False),
        sa.Column('count', sa.BigInteger, nullable=False, default=0),
        sa.Column('meta', postgresql.JSONB, nullable=True),
        sa.PrimaryKeyConstraint('tenant_id', 'date', 'metric'),
        sa.Index('idx_analytics_daily_usage_tenant_date', 'tenant_id', 'date'),
        sa.Index('idx_analytics_daily_usage_metric', 'metric')
    )


def downgrade() -> None:
    op.drop_table('analytics_daily_usage')
    op.drop_table('analytics_events')
    op.execute('DROP TYPE analytics_source_enum')
