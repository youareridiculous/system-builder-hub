"""Add multi-tenancy support

Revision ID: 0002
Revises: 0001
Create Date: 2024-01-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tenants table
    op.create_table('tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('slug', sa.String(63), unique=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('plan', sa.String(50), nullable=False, default='free'),
        sa.Column('status', sa.String(50), nullable=False, default='active'),
        sa.Column('stripe_customer_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Index('idx_tenants_slug', 'slug')
    )
    
    # Create tenant_users table
    op.create_table('tenant_users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('role', sa.Enum('owner', 'admin', 'member', 'viewer', name='tenant_role_enum'), 
                  nullable=False, default='member'),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Index('idx_tenant_users_tenant_user', 'tenant_id', 'user_id', unique=True),
        sa.Index('idx_tenant_users_user', 'user_id')
    )
    
    # Create users table if it doesn't exist (for SQLite compatibility)
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), default='user', nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Index('idx_users_email', 'email')
    )
    
    # Add tenant_id to existing tables
    op.add_column('projects', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=True))
    op.add_column('builder_states', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=True))
    op.add_column('audit_events', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=True))
    op.add_column('file_store_configs', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=True))
    
    # Create indexes for tenant_id columns
    op.create_index('idx_projects_tenant', 'projects', ['tenant_id', 'id'])
    op.create_index('idx_builder_states_tenant', 'builder_states', ['tenant_id', 'id'])
    op.create_index('idx_audit_events_tenant', 'audit_events', ['tenant_id', 'id'])
    op.create_index('idx_file_store_configs_tenant', 'file_store_configs', ['tenant_id', 'id'])
    
    # Create default tenant
    default_tenant_id = uuid.uuid4()
    op.execute(f"""
        INSERT INTO tenants (id, slug, name, plan, status, created_at, updated_at)
        VALUES ('{default_tenant_id}', 'primary', 'Primary Tenant', 'free', 'active', NOW(), NOW())
    """)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_file_store_configs_tenant', 'file_store_configs')
    op.drop_index('idx_audit_events_tenant', 'audit_events')
    op.drop_index('idx_builder_states_tenant', 'builder_states')
    op.drop_index('idx_projects_tenant', 'projects')
    
    # Drop tenant_id columns
    op.drop_column('file_store_configs', 'tenant_id')
    op.drop_column('audit_events', 'tenant_id')
    op.drop_column('builder_states', 'tenant_id')
    op.drop_column('projects', 'tenant_id')
    
    # Drop tenant tables
    op.drop_table('tenant_users')
    op.drop_table('tenants')
    
    # Note: Don't drop users table as it may be used by other parts of the system
