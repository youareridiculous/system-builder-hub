"""add_growth_metrics_table

Revision ID: e0ffd2e9987d
Revises: fba15934b27a
Create Date: 2025-09-01 16:11:46.222073

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite


# revision identifiers, used by Alembic.
revision = 'e0ffd2e9987d'
down_revision = 'fba15934b27a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create growth_metrics table
    op.create_table('growth_metrics',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('module', sa.String(255), nullable=False),
        sa.Column('metric', sa.String(255), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('metadata', sa.Text()),  # JSON as text for SQLite
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Index('idx_growth_metrics_date', 'date'),
        sa.Index('idx_growth_metrics_tenant', 'tenant_id'),
        sa.Index('idx_growth_metrics_module', 'module'),
        sa.Index('idx_growth_metrics_metric', 'metric')
    )


def downgrade() -> None:
    op.drop_table('growth_metrics')
