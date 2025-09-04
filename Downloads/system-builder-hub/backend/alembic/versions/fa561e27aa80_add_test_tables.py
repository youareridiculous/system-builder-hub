"""Add test tables

Revision ID: fa561e27aa80
Revises: 694e7cbf6b05
Create Date: 2025-09-02T06:25:46.756622

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'fa561e27aa80'
down_revision = '694e7cbf6b05'
branch_labels = None
depends_on = None

def upgrade():
    """Create test tables"""
    # TODO: Implement table creation based on features: ['feature1']
    
    # Example table creation (customize based on actual features):

    op.create_table('feature1',
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
    op.create_index('ix_feature1_tenant_id', 'feature1', ['tenant_id'])


def downgrade():
    """Drop test tables"""
    # TODO: Implement table dropping

    op.drop_index('ix_feature1_tenant_id', table_name='feature1')
    op.drop_table('feature1')
