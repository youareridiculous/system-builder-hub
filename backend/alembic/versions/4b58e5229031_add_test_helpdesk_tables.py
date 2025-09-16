"""Add test_helpdesk tables

Revision ID: 4b58e5229031
Revises: 694e7cbf6b05
Create Date: 2025-09-02T06:25:38.328081

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '4b58e5229031'
down_revision = '694e7cbf6b05'
branch_labels = None
depends_on = None

def upgrade():
    """Create test_helpdesk tables"""
    # TODO: Implement table creation based on features: ['tickets', 'knowledge_base']
    
    # Example table creation (customize based on actual features):

    op.create_table('tickets',
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
    op.create_index('ix_tickets_tenant_id', 'tickets', ['tenant_id'])

    op.create_table('knowledge_base',
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
    op.create_index('ix_knowledge_base_tenant_id', 'knowledge_base', ['tenant_id'])


def downgrade():
    """Drop test_helpdesk tables"""
    # TODO: Implement table dropping

    op.drop_index('ix_tickets_tenant_id', table_name='tickets')
    op.drop_table('tickets')

    op.drop_index('ix_knowledge_base_tenant_id', table_name='knowledge_base')
    op.drop_table('knowledge_base')
