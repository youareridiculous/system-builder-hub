"""Add test_project tables

Revision ID: 842b710d82cf
Revises: 694e7cbf6b05
Create Date: 2025-09-02T06:26:33.259657

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '842b710d82cf'
down_revision = '694e7cbf6b05'
branch_labels = None
depends_on = None

def upgrade():
    """Create test_project tables"""
    # TODO: Implement table creation based on features: ['projects', 'tasks', 'timeline']
    
    # Example table creation (customize based on actual features):

    op.create_table('projects',
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
    op.create_index('ix_projects_tenant_id', 'projects', ['tenant_id'])

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

    op.create_table('timeline',
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
    op.create_index('ix_timeline_tenant_id', 'timeline', ['tenant_id'])


def downgrade():
    """Drop test_project tables"""
    # TODO: Implement table dropping

    op.drop_index('ix_projects_tenant_id', table_name='projects')
    op.drop_table('projects')

    op.drop_index('ix_tasks_tenant_id', table_name='tasks')
    op.drop_table('tasks')

    op.drop_index('ix_timeline_tenant_id', table_name='timeline')
    op.drop_table('timeline')
