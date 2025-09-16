"""P57-P60: Recycle Bin, Data Residency, Supply Chain, Builder LLM Controls

Revision ID: 002_p57_p60_tables
Revises: 001_p53_p56_tables
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlite3
import json

# revision identifiers, used by Alembic.
revision = '002_p57_p60_tables'
down_revision = '001_p53_p56_tables'
branch_labels = None
depends_on = None

def upgrade():
    """Upgrade to add P57-P60 tables"""
    
    # P57: Recycle Bin & Storage Policy
    # Add soft-delete columns to existing files table
    op.execute('ALTER TABLE files ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE')
    op.execute('ALTER TABLE files ADD COLUMN deleted_at TIMESTAMP')
    op.execute('ALTER TABLE files ADD COLUMN deleted_by TEXT')
    
    # Create recycle_bin_events table
    op.create_table('recycle_bin_events',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('file_id', sa.Text(), nullable=False),
        sa.Column('tenant_id', sa.Text(), nullable=False),
        sa.Column('action', sa.Text(), nullable=False),
        sa.Column('actor', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.TIMESTAMP(), nullable=False),
        sa.Column('meta_json', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['file_id'], ['files.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indices for recycle_bin_events
    op.create_index('idx_recycle_events_file_id', 'recycle_bin_events', ['file_id'])
    op.create_index('idx_recycle_events_tenant_id', 'recycle_bin_events', ['tenant_id'])
    op.create_index('idx_recycle_events_timestamp', 'recycle_bin_events', ['timestamp'])
    op.create_index('idx_files_is_deleted', 'files', ['is_deleted'])
    op.create_index('idx_files_deleted_at', 'files', ['deleted_at'])
    
    # P58: Data Residency & Sovereign Data Mesh
    # Create residency_policies table
    op.create_table('residency_policies',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('tenant_id', sa.Text(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('regions_allowed', sa.Text(), nullable=False),
        sa.Column('storage_classes', sa.Text(), nullable=False),
        sa.Column('processor_allowlist', sa.Text(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create residency_events table
    op.create_table('residency_events',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('tenant_id', sa.Text(), nullable=False),
        sa.Column('system_id', sa.Text(), nullable=True),
        sa.Column('object_uri', sa.Text(), nullable=False),
        sa.Column('region', sa.Text(), nullable=False),
        sa.Column('action', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.TIMESTAMP(), nullable=False),
        sa.Column('meta_json', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indices for residency tables
    op.create_index('idx_residency_policies_tenant_id', 'residency_policies', ['tenant_id'])
    op.create_index('idx_residency_events_tenant_id', 'residency_events', ['tenant_id'])
    op.create_index('idx_residency_events_timestamp', 'residency_events', ['timestamp'])
    op.create_index('idx_residency_events_system_id', 'residency_events', ['system_id'])
    
    # P59: Supply Chain & Secrets Hardening
    # Create secret_metadata table
    op.create_table('secret_metadata',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('tenant_id', sa.Text(), nullable=True),
        sa.Column('scope', sa.Text(), nullable=False),
        sa.Column('key_id', sa.Text(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('rotated_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create sbom_manifests table
    op.create_table('sbom_manifests',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('system_id', sa.Text(), nullable=False),
        sa.Column('version', sa.Text(), nullable=False),
        sa.Column('manifest_uri', sa.Text(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indices for supply chain tables
    op.create_index('idx_secret_metadata_tenant_id', 'secret_metadata', ['tenant_id'])
    op.create_index('idx_secret_metadata_scope', 'secret_metadata', ['scope'])
    op.create_index('idx_secret_metadata_rotated_at', 'secret_metadata', ['rotated_at'])
    op.create_index('idx_sbom_manifests_system_id', 'sbom_manifests', ['system_id'])
    op.create_index('idx_sbom_manifests_version', 'sbom_manifests', ['version'])
    
    # P60: SBH Builder LLM Controls
    # Create builder_model_policies table
    op.create_table('builder_model_policies',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('tenant_id', sa.Text(), nullable=True),
        sa.Column('default_model', sa.Text(), nullable=False),
        sa.Column('allowed_models', sa.Text(), nullable=False),
        sa.Column('fallback_chain', sa.Text(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create builder_eval_runs table
    op.create_table('builder_eval_runs',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('policy_id', sa.Text(), nullable=True),
        sa.Column('task_suite', sa.Text(), nullable=False),
        sa.Column('results_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['policy_id'], ['builder_model_policies.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indices for builder LLM tables
    op.create_index('idx_builder_policies_tenant_id', 'builder_model_policies', ['tenant_id'])
    op.create_index('idx_builder_eval_runs_policy_id', 'builder_eval_runs', ['policy_id'])
    op.create_index('idx_builder_eval_runs_created_at', 'builder_eval_runs', ['created_at'])

def downgrade():
    """Downgrade to remove P57-P60 tables"""
    
    # Drop P60: Builder LLM Controls tables
    op.drop_index('idx_builder_eval_runs_created_at', 'builder_eval_runs')
    op.drop_index('idx_builder_eval_runs_policy_id', 'builder_eval_runs')
    op.drop_index('idx_builder_policies_tenant_id', 'builder_model_policies')
    op.drop_table('builder_eval_runs')
    op.drop_table('builder_model_policies')
    
    # Drop P59: Supply Chain tables
    op.drop_index('idx_sbom_manifests_version', 'sbom_manifests')
    op.drop_index('idx_sbom_manifests_system_id', 'sbom_manifests')
    op.drop_index('idx_secret_metadata_rotated_at', 'secret_metadata')
    op.drop_index('idx_secret_metadata_scope', 'secret_metadata')
    op.drop_index('idx_secret_metadata_tenant_id', 'secret_metadata')
    op.drop_table('sbom_manifests')
    op.drop_table('secret_metadata')
    
    # Drop P58: Data Residency tables
    op.drop_index('idx_residency_events_system_id', 'residency_events')
    op.drop_index('idx_residency_events_timestamp', 'residency_events')
    op.drop_index('idx_residency_events_tenant_id', 'residency_events')
    op.drop_index('idx_residency_policies_tenant_id', 'residency_policies')
    op.drop_table('residency_events')
    op.drop_table('residency_policies')
    
    # Drop P57: Recycle Bin tables
    op.drop_index('idx_files_deleted_at', 'files')
    op.drop_index('idx_files_is_deleted', 'files')
    op.drop_index('idx_recycle_events_timestamp', 'recycle_bin_events')
    op.drop_index('idx_recycle_events_tenant_id', 'recycle_bin_events')
    op.drop_index('idx_recycle_events_file_id', 'recycle_bin_events')
    op.drop_table('recycle_bin_events')
    
    # Note: Cannot easily drop columns from files table in SQLite
    # The soft-delete columns will remain but be unused
