"""Add crm_lite tables

Revision ID: 9200a4be8fbf
Revises: 694e7cbf6b05
Create Date: 2025-09-02T16:59:18.873702

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '9200a4be8fbf'
down_revision = '694e7cbf6b05'
branch_labels = None
depends_on = None

def upgrade():
    """Create crm_lite tables"""
    # TODO: Implement table creation based on features: ['contacts', 'deals', 'tasks']
    
    # Example table creation (customize based on actual features):

    op.create_table('contacts',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('metadata', sa.JSON),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_contacts_tenant_id', 'contacts', ['tenant_id'])

    op.create_table('deals',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('metadata', sa.JSON),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_deals_tenant_id', 'deals', ['tenant_id'])

    op.create_table('tasks',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('metadata', sa.JSON),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tasks_tenant_id', 'tasks', ['tenant_id'])


def downgrade():
    """Drop crm_lite tables"""
    # TODO: Implement table dropping

    op.drop_index('ix_contacts_tenant_id', table_name='contacts')
    op.drop_table('contacts')

    op.drop_index('ix_deals_tenant_id', table_name='deals')
    op.drop_table('deals')

    op.drop_index('ix_tasks_tenant_id', table_name='tasks')
    op.drop_table('tasks')
