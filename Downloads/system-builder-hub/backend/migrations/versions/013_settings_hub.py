"""Create Settings Hub tables

Revision ID: 013
Revises: 012
Create Date: 2024-12-26 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade():
    # Create user_settings table
    op.create_table('user_settings',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), nullable=False, unique=True),
        
        # Profile settings
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('timezone', sa.String(length=50), nullable=False, default='UTC'),
        sa.Column('locale', sa.String(length=10), nullable=False, default='en-US'),
        
        # Notification settings
        sa.Column('email_digest_daily', sa.Boolean(), nullable=False, default=False),
        sa.Column('email_digest_weekly', sa.Boolean(), nullable=False, default=True),
        sa.Column('mention_emails', sa.Boolean(), nullable=False, default=True),
        sa.Column('approvals_emails', sa.Boolean(), nullable=False, default=True),
        
        # Security settings
        sa.Column('two_factor_enabled', sa.Boolean(), nullable=False, default=False),
        sa.Column('recovery_codes', sa.Text(), nullable=True),  # Encrypted
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create user_sessions table
    op.create_table('user_sessions',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('session_token', sa.String(length=255), nullable=False, unique=True),
        sa.Column('device_fingerprint', sa.String(length=255), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create tenant_settings table
    op.create_table('tenant_settings',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('tenant_id', sa.String(length=36), nullable=False, unique=True),
        
        # Profile settings
        sa.Column('display_name', sa.String(length=255), nullable=True),
        sa.Column('brand_color', sa.String(length=7), nullable=True),  # Hex color
        sa.Column('logo_url', sa.String(length=500), nullable=True),
        
        # Developer settings
        sa.Column('default_llm_provider', sa.String(length=50), nullable=True),
        sa.Column('default_llm_model', sa.String(length=100), nullable=True),
        sa.Column('temperature_default', sa.Float(), nullable=False, default=0.7),
        sa.Column('http_allowlist', sa.Text(), nullable=True),  # JSON array
        
        # Privacy reference
        sa.Column('privacy_settings_id', sa.String(length=36), nullable=True),
        
        # Diagnostics settings
        sa.Column('allow_anonymous_metrics', sa.Boolean(), nullable=False, default=True),
        sa.Column('trace_sample_rate', sa.Float(), nullable=False, default=0.1),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['privacy_settings_id'], ['privacy_settings.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create tenant_api_tokens table
    op.create_table('tenant_api_tokens',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('token_prefix', sa.String(length=8), nullable=False),
        sa.Column('token_hash', sa.String(length=255), nullable=False),
        sa.Column('permissions', sa.Text(), nullable=True),  # JSON array
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('created_by', sa.String(length=36), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Create outbound_webhooks table
    op.create_table('outbound_webhooks',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('target_url', sa.String(length=500), nullable=False),
        sa.Column('events', sa.Text(), nullable=False),  # JSON array
        sa.Column('signing_key', sa.Text(), nullable=True),  # Encrypted
        sa.Column('enabled', sa.Boolean(), nullable=False, default=True),
        sa.Column('last_delivery_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_delivery_status', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('created_by', sa.String(length=36), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Create audit_security_events table
    op.create_table('audit_security_events',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', sa.String(length=36), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('before_values', sa.Text(), nullable=True),  # JSON, redacted
        sa.Column('after_values', sa.Text(), nullable=True),   # JSON, redacted
        sa.Column('metadata', sa.Text(), nullable=True),       # JSON
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for better performance
    op.create_index(op.f('ix_user_settings_user_id'), 'user_settings', ['user_id'], unique=True)
    op.create_index(op.f('ix_user_sessions_user_id'), 'user_sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_sessions_session_token'), 'user_sessions', ['session_token'], unique=True)
    op.create_index(op.f('ix_user_sessions_revoked_at'), 'user_sessions', ['revoked_at'], unique=False)
    op.create_index(op.f('ix_tenant_settings_tenant_id'), 'tenant_settings', ['tenant_id'], unique=True)
    op.create_index(op.f('ix_tenant_api_tokens_tenant_id'), 'tenant_api_tokens', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_tenant_api_tokens_token_prefix'), 'tenant_api_tokens', ['token_prefix'], unique=False)
    op.create_index(op.f('ix_tenant_api_tokens_revoked_at'), 'tenant_api_tokens', ['revoked_at'], unique=False)
    op.create_index(op.f('ix_outbound_webhooks_tenant_id'), 'outbound_webhooks', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_outbound_webhooks_enabled'), 'outbound_webhooks', ['enabled'], unique=False)
    op.create_index(op.f('ix_audit_security_events_tenant_id'), 'audit_security_events', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_audit_security_events_user_id'), 'audit_security_events', ['user_id'], unique=False)
    op.create_index(op.f('ix_audit_security_events_created_at'), 'audit_security_events', ['created_at'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index(op.f('ix_audit_security_events_created_at'), table_name='audit_security_events')
    op.drop_index(op.f('ix_audit_security_events_user_id'), table_name='audit_security_events')
    op.drop_index(op.f('ix_audit_security_events_tenant_id'), table_name='audit_security_events')
    op.drop_index(op.f('ix_outbound_webhooks_enabled'), table_name='outbound_webhooks')
    op.drop_index(op.f('ix_outbound_webhooks_tenant_id'), table_name='outbound_webhooks')
    op.drop_index(op.f('ix_tenant_api_tokens_revoked_at'), table_name='tenant_api_tokens')
    op.drop_index(op.f('ix_tenant_api_tokens_token_prefix'), table_name='tenant_api_tokens')
    op.drop_index(op.f('ix_tenant_api_tokens_tenant_id'), table_name='tenant_api_tokens')
    op.drop_index(op.f('ix_tenant_settings_tenant_id'), table_name='tenant_settings')
    op.drop_index(op.f('ix_user_sessions_revoked_at'), table_name='user_sessions')
    op.drop_index(op.f('ix_user_sessions_session_token'), table_name='user_sessions')
    op.drop_index(op.f('ix_user_sessions_user_id'), table_name='user_sessions')
    op.drop_index(op.f('ix_user_settings_user_id'), table_name='user_settings')

    # Drop tables
    op.drop_table('audit_security_events')
    op.drop_table('outbound_webhooks')
    op.drop_table('tenant_api_tokens')
    op.drop_table('tenant_settings')
    op.drop_table('user_sessions')
    op.drop_table('user_settings')
