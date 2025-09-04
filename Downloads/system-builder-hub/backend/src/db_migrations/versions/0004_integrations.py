"""Add integrations support (API keys, webhooks, emails)

Revision ID: 0004
Revises: 0003
Create Date: 2024-01-15 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create api_keys table
    op.create_table('api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('prefix', sa.String(8), nullable=False),
        sa.Column('hash', sa.String(255), nullable=False),
        sa.Column('scope', postgresql.JSONB, nullable=True),
        sa.Column('rate_limit_per_min', sa.Integer, nullable=False, default=120),
        sa.Column('status', sa.Enum('active', 'revoked', name='api_key_status_enum'), 
                  nullable=False, default='active'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Index('idx_api_keys_tenant_id', 'tenant_id'),
        sa.Index('idx_api_keys_prefix', 'prefix'),
        sa.Index('idx_api_keys_status', 'status')
    )

    # Create webhooks table
    op.create_table('webhooks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('target_url', sa.Text, nullable=False),
        sa.Column('secret', sa.String(255), nullable=False),
        sa.Column('events', postgresql.JSONB, nullable=False),
        sa.Column('status', sa.Enum('active', 'paused', name='webhook_status_enum'), 
                  nullable=False, default='active'),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Index('idx_webhooks_tenant_id', 'tenant_id'),
        sa.Index('idx_webhooks_status', 'status')
    )

    # Create webhook_deliveries table
    op.create_table('webhook_deliveries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('webhook_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('webhooks.id'), nullable=False),
        sa.Column('event_type', sa.String(255), nullable=False),
        sa.Column('payload', postgresql.JSONB, nullable=True),
        sa.Column('attempt', sa.Integer, nullable=False, default=1),
        sa.Column('status', sa.Enum('queued', 'success', 'failed', 'retrying', name='webhook_delivery_status_enum'), 
                  nullable=False, default='queued'),
        sa.Column('response_status', sa.Integer, nullable=True),
        sa.Column('response_ms', sa.Integer, nullable=True),
        sa.Column('error', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Index('idx_webhook_deliveries_webhook_id', 'webhook_id'),
        sa.Index('idx_webhook_deliveries_status', 'status'),
        sa.Index('idx_webhook_deliveries_created_at', 'created_at')
    )

    # Create emails_outbound table
    op.create_table('emails_outbound',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('to_email', sa.String(255), nullable=False),
        sa.Column('template', sa.String(255), nullable=False),
        sa.Column('payload', postgresql.JSONB, nullable=True),
        sa.Column('status', sa.Enum('queued', 'sent', 'failed', name='email_status_enum'), 
                  nullable=False, default='queued'),
        sa.Column('provider_message_id', sa.String(255), nullable=True),
        sa.Column('error', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Index('idx_emails_outbound_tenant_id', 'tenant_id'),
        sa.Index('idx_emails_outbound_status', 'status'),
        sa.Index('idx_emails_outbound_created_at', 'created_at')
    )


def downgrade() -> None:
    op.drop_table('emails_outbound')
    op.drop_table('webhook_deliveries')
    op.drop_table('webhooks')
    op.drop_table('api_keys')
    op.execute('DROP TYPE api_key_status_enum')
    op.execute('DROP TYPE webhook_status_enum')
    op.execute('DROP TYPE webhook_delivery_status_enum')
    op.execute('DROP TYPE email_status_enum')
