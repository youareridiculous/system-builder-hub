"""Create privacy tables

Revision ID: 012
Revises: 011
Create Date: 2024-12-26 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade():
    # Create privacy_settings table
    op.create_table('privacy_settings',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('privacy_mode', sa.String(length=20), nullable=False),
        sa.Column('prompt_retention_seconds', sa.Integer(), nullable=False),
        sa.Column('response_retention_seconds', sa.Integer(), nullable=False),
        sa.Column('do_not_retain_prompts', sa.Boolean(), nullable=False),
        sa.Column('do_not_retain_model_outputs', sa.Boolean(), nullable=False),
        sa.Column('strip_attachments_from_logs', sa.Boolean(), nullable=False),
        sa.Column('disable_third_party_calls', sa.Boolean(), nullable=False),
        sa.Column('byo_openai_key', sa.Text(), nullable=True),
        sa.Column('byo_anthropic_key', sa.Text(), nullable=True),
        sa.Column('byo_aws_access_key', sa.Text(), nullable=True),
        sa.Column('byo_aws_secret_key', sa.Text(), nullable=True),
        sa.Column('byo_slack_token', sa.Text(), nullable=True),
        sa.Column('byo_google_credentials', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.String(length=36), nullable=False),
        sa.Column('updated_by', sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id')
    )

    # Create privacy_audit_log table
    op.create_table('privacy_audit_log',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', sa.String(length=36), nullable=True),
        sa.Column('privacy_mode', sa.String(length=20), nullable=False),
        sa.Column('redactions_applied', sa.Integer(), nullable=False),
        sa.Column('retention_policy_id', sa.String(length=50), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create data_retention_jobs table
    op.create_table('data_retention_jobs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('job_type', sa.String(length=50), nullable=False),
        sa.Column('retention_policy', sa.String(length=20), nullable=False),
        sa.Column('target_table', sa.String(length=50), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('records_processed', sa.Integer(), nullable=False),
        sa.Column('records_deleted', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create privacy_transparency_log table
    op.create_table('privacy_transparency_log',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('data_category', sa.String(length=50), nullable=False),
        sa.Column('data_volume', sa.Integer(), nullable=False),
        sa.Column('privacy_mode', sa.String(length=20), nullable=False),
        sa.Column('retention_applied', sa.Boolean(), nullable=False),
        sa.Column('redaction_applied', sa.Boolean(), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for better performance
    op.create_index(op.f('ix_privacy_settings_tenant_id'), 'privacy_settings', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_privacy_audit_log_tenant_id'), 'privacy_audit_log', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_privacy_audit_log_created_at'), 'privacy_audit_log', ['created_at'], unique=False)
    op.create_index(op.f('ix_data_retention_jobs_tenant_id'), 'data_retention_jobs', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_data_retention_jobs_scheduled_at'), 'data_retention_jobs', ['scheduled_at'], unique=False)
    op.create_index(op.f('ix_data_retention_jobs_status'), 'data_retention_jobs', ['status'], unique=False)
    op.create_index(op.f('ix_privacy_transparency_log_tenant_id'), 'privacy_transparency_log', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_privacy_transparency_log_created_at'), 'privacy_transparency_log', ['created_at'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index(op.f('ix_privacy_transparency_log_created_at'), table_name='privacy_transparency_log')
    op.drop_index(op.f('ix_privacy_transparency_log_tenant_id'), table_name='privacy_transparency_log')
    op.drop_index(op.f('ix_data_retention_jobs_status'), table_name='data_retention_jobs')
    op.drop_index(op.f('ix_data_retention_jobs_scheduled_at'), table_name='data_retention_jobs')
    op.drop_index(op.f('ix_data_retention_jobs_tenant_id'), table_name='data_retention_jobs')
    op.drop_index(op.f('ix_privacy_audit_log_created_at'), table_name='privacy_audit_log')
    op.drop_index(op.f('ix_privacy_audit_log_tenant_id'), table_name='privacy_audit_log')
    op.drop_index(op.f('ix_privacy_settings_tenant_id'), table_name='privacy_settings')

    # Drop tables
    op.drop_table('privacy_transparency_log')
    op.drop_table('data_retention_jobs')
    op.drop_table('privacy_audit_log')
    op.drop_table('privacy_settings')
