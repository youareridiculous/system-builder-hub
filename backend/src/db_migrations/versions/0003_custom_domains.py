"""Add custom domains support

Revision ID: 0003
Revises: 0002
Create Date: 2024-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create custom_domains table
    op.create_table('custom_domains',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('hostname', sa.String(255), unique=True, nullable=False),
        sa.Column('status', sa.Enum('pending', 'verifying', 'active', 'failed', name='domain_status_enum'), 
                  nullable=False, default='pending'),
        sa.Column('verification_token', sa.String(255), nullable=True),
        sa.Column('acm_arn', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Index('idx_custom_domains_tenant_hostname', 'tenant_id', 'hostname'),
        sa.Index('idx_custom_domains_hostname', 'hostname'),
        sa.Index('idx_custom_domains_status', 'status')
    )


def downgrade() -> None:
    op.drop_table('custom_domains')
    op.execute('DROP TYPE domain_status_enum')
