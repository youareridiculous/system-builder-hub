"""Add GTM billing and events tables

Revision ID: 694e7cbf6b05
Revises: a4127a24f441
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '694e7cbf6b05'
down_revision = 'a4127a24f441'
branch_labels = None
depends_on = None


def upgrade():
    # Create billing_subscriptions table
    op.create_table('billing_subscriptions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('module', sa.String(100), nullable=False),
        sa.Column('plan', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),  # trial, active, canceled, expired
        sa.Column('trial_ends_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('metadata', sa.JSON, nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create unique index on (tenant_id, module)
    op.create_index('ix_billing_subscriptions_tenant_module', 'billing_subscriptions', ['tenant_id', 'module'], unique=True)
    
    # Create index on status for querying
    op.create_index('ix_billing_subscriptions_status', 'billing_subscriptions', ['status'])
    
    # Create sbh_events table
    op.create_table('sbh_events',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('module', sa.String(100), nullable=True),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('metadata', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for events
    op.create_index('ix_sbh_events_tenant_id', 'sbh_events', ['tenant_id'])
    op.create_index('ix_sbh_events_module', 'sbh_events', ['module'])
    op.create_index('ix_sbh_events_event_type', 'sbh_events', ['event_type'])
    op.create_index('ix_sbh_events_created_at', 'sbh_events', ['created_at'])


def downgrade():
    # Drop indexes first
    op.drop_index('ix_sbh_events_created_at', table_name='sbh_events')
    op.drop_index('ix_sbh_events_event_type', table_name='sbh_events')
    op.drop_index('ix_sbh_events_module', table_name='sbh_events')
    op.drop_index('ix_sbh_events_tenant_id', table_name='sbh_events')
    op.drop_index('ix_billing_subscriptions_status', table_name='billing_subscriptions')
    op.drop_index('ix_billing_subscriptions_tenant_module', table_name='billing_subscriptions')
    
    # Drop tables
    op.drop_table('sbh_events')
    op.drop_table('billing_subscriptions')
