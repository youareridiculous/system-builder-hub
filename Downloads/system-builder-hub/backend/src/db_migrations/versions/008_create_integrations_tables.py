"""Create integrations tables (Slack, Zapier, Salesforce, HubSpot, Google Drive)

Revision ID: 008
Revises: 007
Create Date: 2024-01-15 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None

def upgrade():
    # Create slack_integrations table
    op.create_table('slack_integrations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('team_id', sa.String(), nullable=False),
        sa.Column('team_name', sa.String(), nullable=True),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('bot_user_id', sa.String(), nullable=True),
        sa.Column('bot_access_token', sa.Text(), nullable=True),
        sa.Column('channels_config', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('installed_at', sa.DateTime(), nullable=True),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_slack_integrations_tenant_id'), 'slack_integrations', ['tenant_id'], unique=False)

    # Create zapier_integrations table
    op.create_table('zapier_integrations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('api_key', sa.String(), nullable=False),
        sa.Column('webhook_url', sa.String(), nullable=True),
        sa.Column('triggers_enabled', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('actions_enabled', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_zapier_integrations_tenant_id'), 'zapier_integrations', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_zapier_integrations_api_key'), 'zapier_integrations', ['api_key'], unique=True)

    # Create salesforce_integrations table
    op.create_table('salesforce_integrations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('instance_url', sa.String(), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(), nullable=True),
        sa.Column('org_id', sa.String(), nullable=True),
        sa.Column('org_name', sa.String(), nullable=True),
        sa.Column('field_mappings', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_salesforce_integrations_tenant_id'), 'salesforce_integrations', ['tenant_id'], unique=False)

    # Create hubspot_integrations table
    op.create_table('hubspot_integrations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(), nullable=True),
        sa.Column('portal_id', sa.String(), nullable=True),
        sa.Column('portal_name', sa.String(), nullable=True),
        sa.Column('field_mappings', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_hubspot_integrations_tenant_id'), 'hubspot_integrations', ['tenant_id'], unique=False)

    # Create google_drive_integrations table
    op.create_table('google_drive_integrations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(), nullable=True),
        sa.Column('user_email', sa.String(), nullable=True),
        sa.Column('drive_folder_id', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_google_drive_integrations_tenant_id'), 'google_drive_integrations', ['tenant_id'], unique=False)

    # Create integration_syncs table
    op.create_table('integration_syncs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('integration_type', sa.String(), nullable=False),
        sa.Column('sync_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('records_processed', sa.Integer(), nullable=True),
        sa.Column('records_created', sa.Integer(), nullable=True),
        sa.Column('records_updated', sa.Integer(), nullable=True),
        sa.Column('records_skipped', sa.Integer(), nullable=True),
        sa.Column('records_failed', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_integration_syncs_tenant_id'), 'integration_syncs', ['tenant_id'], unique=False)

    # Create file_attachments table
    op.create_table('file_attachments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('entity_type', sa.String(), nullable=False),
        sa.Column('entity_id', sa.String(), nullable=False),
        sa.Column('file_name', sa.String(), nullable=False),
        sa.Column('file_type', sa.String(), nullable=True),
        sa.Column('file_url', sa.String(), nullable=True),
        sa.Column('file_id', sa.String(), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('uploaded_by', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_file_attachments_tenant_id'), 'file_attachments', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_file_attachments_entity_id'), 'file_attachments', ['entity_id'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_file_attachments_entity_id'), table_name='file_attachments')
    op.drop_index(op.f('ix_file_attachments_tenant_id'), table_name='file_attachments')
    op.drop_table('file_attachments')
    op.drop_index(op.f('ix_integration_syncs_tenant_id'), table_name='integration_syncs')
    op.drop_table('integration_syncs')
    op.drop_index(op.f('ix_google_drive_integrations_tenant_id'), table_name='google_drive_integrations')
    op.drop_table('google_drive_integrations')
    op.drop_index(op.f('ix_hubspot_integrations_tenant_id'), table_name='hubspot_integrations')
    op.drop_table('hubspot_integrations')
    op.drop_index(op.f('ix_salesforce_integrations_tenant_id'), table_name='salesforce_integrations')
    op.drop_table('salesforce_integrations')
    op.drop_index(op.f('ix_zapier_integrations_api_key'), table_name='zapier_integrations')
    op.drop_index(op.f('ix_zapier_integrations_tenant_id'), table_name='zapier_integrations')
    op.drop_table('zapier_integrations')
    op.drop_index(op.f('ix_slack_integrations_tenant_id'), table_name='slack_integrations')
    op.drop_table('slack_integrations')
