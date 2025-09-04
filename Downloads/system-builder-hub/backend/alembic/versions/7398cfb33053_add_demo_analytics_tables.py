"""Add demo_analytics tables

Revision ID: 7398cfb33053
Revises: 694e7cbf6b05
Create Date: 2025-09-02T06:27:11.359533

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '7398cfb33053'
down_revision = '694e7cbf6b05'
branch_labels = None
depends_on = None

def upgrade():
    """Create demo_analytics tables"""
    # TODO: Implement table creation based on features: ['charts', 'reports', 'export']
    
    # Example table creation (customize based on actual features):

    op.create_table('charts',
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
    op.create_index('ix_charts_tenant_id', 'charts', ['tenant_id'])

    op.create_table('reports',
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
    op.create_index('ix_reports_tenant_id', 'reports', ['tenant_id'])

    op.create_table('export',
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
    op.create_index('ix_export_tenant_id', 'export', ['tenant_id'])


def downgrade():
    """Drop demo_analytics tables"""
    # TODO: Implement table dropping

    op.drop_index('ix_charts_tenant_id', table_name='charts')
    op.drop_table('charts')

    op.drop_index('ix_reports_tenant_id', table_name='reports')
    op.drop_table('reports')

    op.drop_index('ix_export_tenant_id', table_name='export')
    op.drop_table('export')
