"""Create automations, calendar, and AI assist tables

Revision ID: 006
Revises: 005
Create Date: 2024-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None

def upgrade():
    # Create automation_rules table
    op.create_table('automation_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=True),
        sa.Column('trigger', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('conditions', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('actions', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('version', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_automation_rules_tenant_id'), 'automation_rules', ['tenant_id'], unique=False)

    # Create automation_runs table
    op.create_table('automation_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('rule_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('input_snapshot', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('result_snapshot', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('event_id', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_automation_runs_tenant_id'), 'automation_runs', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_automation_runs_rule_id'), 'automation_runs', ['rule_id'], unique=False)
    op.create_index(op.f('ix_automation_runs_event_id'), 'automation_runs', ['event_id'], unique=False)

    # Create automation_templates table
    op.create_table('automation_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('trigger', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('conditions', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('actions', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create calendar_events table
    op.create_table('calendar_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=False),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('attendees', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('organizer_email', sa.String(), nullable=False),
        sa.Column('organizer_name', sa.String(), nullable=True),
        sa.Column('related_contact_id', sa.String(), nullable=True),
        sa.Column('related_deal_id', sa.String(), nullable=True),
        sa.Column('external_id', sa.String(), nullable=True),
        sa.Column('external_provider', sa.String(), nullable=True),
        sa.Column('is_all_day', sa.Boolean(), nullable=True),
        sa.Column('created_by', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_calendar_events_tenant_id'), 'calendar_events', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_calendar_events_external_id'), 'calendar_events', ['external_id'], unique=False)

    # Create calendar_invitations table
    op.create_table('calendar_invitations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('attendee_email', sa.String(), nullable=False),
        sa.Column('attendee_name', sa.String(), nullable=True),
        sa.Column('invitation_token', sa.String(), nullable=False),
        sa.Column('rsvp_status', sa.String(), nullable=True),
        sa.Column('rsvp_updated_at', sa.DateTime(), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_calendar_invitations_tenant_id'), 'calendar_invitations', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_calendar_invitations_event_id'), 'calendar_invitations', ['event_id'], unique=False)
    op.create_index(op.f('ix_calendar_invitations_invitation_token'), 'calendar_invitations', ['invitation_token'], unique=True)

    # Create calendar_sync table
    op.create_table('calendar_sync',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=True),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(), nullable=True),
        sa.Column('calendar_id', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_calendar_sync_tenant_id'), 'calendar_sync', ['tenant_id'], unique=False)

    # Create notifications table
    op.create_table('notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=True),
        sa.Column('is_archived', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_tenant_id'), 'notifications', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)

    # Create notification_preferences table
    op.create_table('notification_preferences',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('email_enabled', sa.Boolean(), nullable=True),
        sa.Column('in_app_enabled', sa.Boolean(), nullable=True),
        sa.Column('digest_enabled', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notification_preferences_tenant_id'), 'notification_preferences', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_notification_preferences_user_id'), 'notification_preferences', ['user_id'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_notification_preferences_user_id'), table_name='notification_preferences')
    op.drop_index(op.f('ix_notification_preferences_tenant_id'), table_name='notification_preferences')
    op.drop_table('notification_preferences')
    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_tenant_id'), table_name='notifications')
    op.drop_table('notifications')
    op.drop_index(op.f('ix_calendar_sync_tenant_id'), table_name='calendar_sync')
    op.drop_table('calendar_sync')
    op.drop_index(op.f('ix_calendar_invitations_invitation_token'), table_name='calendar_invitations')
    op.drop_index(op.f('ix_calendar_invitations_event_id'), table_name='calendar_invitations')
    op.drop_index(op.f('ix_calendar_invitations_tenant_id'), table_name='calendar_invitations')
    op.drop_table('calendar_invitations')
    op.drop_index(op.f('ix_calendar_events_external_id'), table_name='calendar_events')
    op.drop_index(op.f('ix_calendar_events_tenant_id'), table_name='calendar_events')
    op.drop_table('calendar_events')
    op.drop_table('automation_templates')
    op.drop_index(op.f('ix_automation_runs_event_id'), table_name='automation_runs')
    op.drop_index(op.f('ix_automation_runs_rule_id'), table_name='automation_runs')
    op.drop_index(op.f('ix_automation_runs_tenant_id'), table_name='automation_runs')
    op.drop_table('automation_runs')
    op.drop_index(op.f('ix_automation_rules_tenant_id'), table_name='automation_rules')
    op.drop_table('automation_rules')
