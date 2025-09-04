"""
Create CRM/Ops Template Tables

Revision ID: a4127a24f441
Revises: 5ecd76ed3373
Create Date: 2024-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import uuid

# revision identifiers, used by Alembic.
revision = 'a4127a24f441'
down_revision = '5ecd76ed3373'
branch_labels = None
depends_on = None

def upgrade():
    """Create CRM/Ops tables"""
    
    # Create tenant_users table
    op.create_table(
        'tenant_users',
        sa.Column('id', sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, default='viewer'),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Create contacts table
    op.create_table(
        'contacts',
        sa.Column('id', sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('company', sa.String(255), nullable=True),
        sa.Column('tags', sa.JSON, nullable=False, default=[]),
        sa.Column('custom_fields', sa.JSON, nullable=False, default={}),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_by', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Create deals table
    op.create_table(
        'deals',
        sa.Column('id', sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('contact_id', sa.String(36), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('value', sa.Numeric(10, 2), nullable=True),
        sa.Column('stage', sa.String(50), nullable=False, default='qualification'),
        sa.Column('probability', sa.Integer, nullable=True),
        sa.Column('expected_close_date', sa.Date, nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('tags', sa.JSON, nullable=False, default=[]),
        sa.Column('custom_fields', sa.JSON, nullable=False, default={}),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_by', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Create activities table
    op.create_table(
        'activities',
        sa.Column('id', sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('deal_id', sa.String(36), nullable=True),
        sa.Column('contact_id', sa.String(36), nullable=True),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('due_date', sa.DateTime, nullable=True),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='pending'),
        sa.Column('priority', sa.String(20), nullable=False, default='medium'),
        sa.Column('assigned_to', sa.String(255), nullable=True),
        sa.Column('tags', sa.JSON, nullable=False, default=[]),
        sa.Column('custom_fields', sa.JSON, nullable=False, default={}),
        sa.Column('created_by', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Create projects table
    op.create_table(
        'projects',
        sa.Column('id', sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='planning'),
        sa.Column('start_date', sa.Date, nullable=True),
        sa.Column('end_date', sa.Date, nullable=True),
        sa.Column('budget', sa.Numeric(10, 2), nullable=True),
        sa.Column('tags', sa.JSON, nullable=False, default=[]),
        sa.Column('custom_fields', sa.JSON, nullable=False, default={}),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_by', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Create tasks table
    op.create_table(
        'tasks',
        sa.Column('id', sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='todo'),
        sa.Column('priority', sa.String(20), nullable=False, default='medium'),
        sa.Column('assigned_to', sa.String(255), nullable=True),
        sa.Column('due_date', sa.DateTime, nullable=True),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('estimated_hours', sa.Numeric(5, 2), nullable=True),
        sa.Column('actual_hours', sa.Numeric(5, 2), nullable=True),
        sa.Column('tags', sa.JSON, nullable=False, default=[]),
        sa.Column('custom_fields', sa.JSON, nullable=False, default={}),
        sa.Column('created_by', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Create message_threads table
    op.create_table(
        'message_threads',
        sa.Column('id', sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('participants', sa.JSON, nullable=False, default=[]),
        sa.Column('tags', sa.JSON, nullable=False, default=[]),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_by', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('thread_id', sa.String(36), nullable=False),
        sa.Column('sender_id', sa.String(255), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('attachments', sa.JSON, nullable=False, default=[]),
        sa.Column('is_read', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime, default=sa.func.now())
    )
    
    # Create crm_ops_audit_logs table
    op.create_table(
        'crm_ops_audit_logs',
        sa.Column('id', sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('table_name', sa.String(100), nullable=False),
        sa.Column('record_id', sa.String(36), nullable=False),
        sa.Column('old_values', sa.JSON, nullable=True),
        sa.Column('new_values', sa.JSON, nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now())
    )
    
    # Create indexes
    op.create_index('idx_tenant_users_tenant_user_unique', 'tenant_users', ['tenant_id', 'user_id'], unique=True)
    op.create_index('idx_contacts_tenant_id', 'contacts', ['tenant_id'])
    op.create_index('idx_contacts_tenant_email', 'contacts', ['tenant_id', 'email'])
    op.create_index('idx_contacts_tenant_company', 'contacts', ['tenant_id', 'company'])
    op.create_index('idx_contacts_tenant_tags', 'contacts', ['tenant_id', 'tags'])
    op.create_index('idx_deals_tenant_id', 'deals', ['tenant_id'])
    op.create_index('idx_deals_tenant_stage', 'deals', ['tenant_id', 'stage'])
    op.create_index('idx_deals_tenant_contact', 'deals', ['tenant_id', 'contact_id'])
    op.create_index('idx_activities_tenant_id', 'activities', ['tenant_id'])
    op.create_index('idx_activities_tenant_status', 'activities', ['tenant_id', 'status'])
    op.create_index('idx_activities_tenant_assigned', 'activities', ['tenant_id', 'assigned_to'])
    op.create_index('idx_projects_tenant_id', 'projects', ['tenant_id'])
    op.create_index('idx_projects_tenant_status', 'projects', ['tenant_id', 'status'])
    op.create_index('idx_tasks_tenant_id', 'tasks', ['tenant_id'])
    op.create_index('idx_tasks_tenant_project', 'tasks', ['tenant_id', 'project_id'])
    op.create_index('idx_tasks_tenant_status', 'tasks', ['tenant_id', 'status'])
    op.create_index('idx_tasks_tenant_assigned', 'tasks', ['tenant_id', 'assigned_to'])
    op.create_index('idx_message_threads_tenant_id', 'message_threads', ['tenant_id'])
    op.create_index('idx_message_threads_tenant_participants', 'message_threads', ['tenant_id', 'participants'])
    op.create_index('idx_messages_tenant_id', 'messages', ['tenant_id'])
    op.create_index('idx_messages_tenant_thread', 'messages', ['tenant_id', 'thread_id'])
    op.create_index('idx_audit_logs_tenant_id', 'crm_ops_audit_logs', ['tenant_id'])
    op.create_index('idx_audit_logs_tenant_user', 'crm_ops_audit_logs', ['tenant_id', 'user_id'])
    op.create_index('idx_audit_logs_tenant_table', 'crm_ops_audit_logs', ['tenant_id', 'table_name'])

def downgrade():
    """Drop CRM/Ops tables"""
    op.drop_table('crm_ops_audit_logs')
    op.drop_table('messages')
    op.drop_table('message_threads')
    op.drop_table('tasks')
    op.drop_table('projects')
    op.drop_table('activities')
    op.drop_table('deals')
    op.drop_table('contacts')
    op.drop_table('tenant_users')
