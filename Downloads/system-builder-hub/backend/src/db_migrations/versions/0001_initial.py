"""Initial migration

Revision ID: 0001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create idempotency table
    op.create_table('idempotency_keys',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('method', sa.String(10), nullable=False),
        sa.Column('path', sa.String(500), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=True),
        sa.Column('tenant_id', sa.String(255), nullable=True),
        sa.Column('response_status', sa.Integer, nullable=False),
        sa.Column('response_body', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Index('idx_idempotency_expires', 'expires_at'),
        sa.Index('idx_idempotency_user', 'user_id'),
        sa.Index('idx_idempotency_tenant', 'tenant_id')
    )
    
    # Create feature flags table
    op.create_table('feature_flags',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('enabled', sa.Boolean, nullable=False, default=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False)
    )
    
    # Create preview sessions table
    op.create_table('preview_sessions',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('system_id', sa.String(255), nullable=False),
        sa.Column('version_id', sa.String(255), nullable=True),
        sa.Column('preview_url', sa.String(500), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('created_by', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Column('metadata', sa.Text, nullable=True),  # JSON
        sa.Index('idx_preview_system', 'system_id'),
        sa.Index('idx_preview_expires', 'expires_at'),
        sa.Index('idx_preview_status', 'status')
    )
    
    # Create backup manifests table
    op.create_table('backup_manifests',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('backup_type', sa.String(50), nullable=False),
        sa.Column('entity_id', sa.String(255), nullable=False),
        sa.Column('checksum', sa.String(64), nullable=False),
        sa.Column('storage_path', sa.String(500), nullable=False),
        sa.Column('created_by', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('metadata', sa.Text, nullable=True),  # JSON
        sa.Index('idx_backup_type', 'backup_type'),
        sa.Index('idx_backup_entity', 'entity_id'),
        sa.Index('idx_backup_created', 'created_at')
    )


def downgrade() -> None:
    op.drop_table('backup_manifests')
    op.drop_table('preview_sessions')
    op.drop_table('feature_flags')
    op.drop_table('idempotency_keys')
