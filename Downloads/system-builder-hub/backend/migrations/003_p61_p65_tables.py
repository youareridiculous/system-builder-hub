"""P61-P65: Performance & Scale, Workspaces, Auto-Tuner, DX, Compliance Evidence

Revision ID: 003_p61_p65_tables
Revises: 002_p57_p60_tables
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '003_p61_p65_tables'
down_revision = '002_p57_p60_tables'
branch_labels = None
depends_on = None


def upgrade():
    """Create tables for P61-P65"""
    
    # P61: Performance & Scale Framework
    op.create_table('perf_budgets',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('scope', sa.String(), nullable=False),
        sa.Column('thresholds_json', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('perf_runs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('scope', sa.String(), nullable=False),
        sa.Column('results_json', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indices for performance
    op.create_index('idx_perf_budgets_tenant_id', 'perf_budgets', ['tenant_id'])
    op.create_index('idx_perf_budgets_scope', 'perf_budgets', ['scope'])
    op.create_index('idx_perf_runs_scope', 'perf_runs', ['scope'])
    op.create_index('idx_perf_runs_created_at', 'perf_runs', ['created_at'])
    
    # P62: Team Workspaces & Shared Libraries
    op.create_table('workspaces',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('settings_json', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('workspace_members',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('shared_assets',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('uri', sa.String(), nullable=False),
        sa.Column('meta_json', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indices for workspaces
    op.create_index('idx_workspaces_tenant_id', 'workspaces', ['tenant_id'])
    op.create_index('idx_workspace_members_workspace_id', 'workspace_members', ['workspace_id'])
    op.create_index('idx_workspace_members_user_id', 'workspace_members', ['user_id'])
    op.create_index('idx_shared_assets_workspace_id', 'shared_assets', ['workspace_id'])
    op.create_index('idx_shared_assets_kind', 'shared_assets', ['kind'])
    
    # P63: Continuous Auto-Tuning Orchestrator
    op.create_table('tuning_policies',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('system_id', sa.String(), nullable=False),
        sa.Column('mode', sa.String(), nullable=False),
        sa.Column('guardrails_json', sa.String(), nullable=False),
        sa.Column('budgets_json', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('tuning_runs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('policy_id', sa.String(), nullable=False),
        sa.Column('system_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('metrics_json', sa.String(), nullable=False),
        sa.Column('gate_result_json', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['policy_id'], ['tuning_policies.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indices for auto-tuner
    op.create_index('idx_tuning_policies_tenant_id', 'tuning_policies', ['tenant_id'])
    op.create_index('idx_tuning_policies_system_id', 'tuning_policies', ['system_id'])
    op.create_index('idx_tuning_runs_policy_id', 'tuning_runs', ['policy_id'])
    op.create_index('idx_tuning_runs_system_id', 'tuning_runs', ['system_id'])
    op.create_index('idx_tuning_runs_status', 'tuning_runs', ['status'])
    
    # P64: Developer Experience (DX) & IDE/CLI Enhancements
    op.create_table('playground_calls',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('endpoint', sa.String(), nullable=False),
        sa.Column('method', sa.String(), nullable=False),
        sa.Column('request_data', sa.String(), nullable=False),
        sa.Column('response_data', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indices for playground calls
    op.create_index('idx_playground_calls_created_at', 'playground_calls', ['created_at'])
    op.create_index('idx_playground_calls_status', 'playground_calls', ['status'])
    
    # P65: Enterprise Compliance Evidence & Attestations
    op.create_table('evidence_packets',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('scope', sa.String(), nullable=False),
        sa.Column('bundle_uri', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('attestations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('system_id', sa.String(), nullable=False),
        sa.Column('version', sa.String(), nullable=False),
        sa.Column('summary_json', sa.String(), nullable=False),
        sa.Column('bundle_uri', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indices for compliance evidence
    op.create_index('idx_evidence_packets_tenant_id', 'evidence_packets', ['tenant_id'])
    op.create_index('idx_evidence_packets_scope', 'evidence_packets', ['scope'])
    op.create_index('idx_evidence_packets_created_at', 'evidence_packets', ['created_at'])
    op.create_index('idx_attestations_system_id', 'attestations', ['system_id'])
    op.create_index('idx_attestations_version', 'attestations', ['version'])
    op.create_index('idx_attestations_created_at', 'attestations', ['created_at'])


def downgrade():
    """Drop tables for P61-P65"""
    
    # Drop indices first
    op.drop_index('idx_attestations_created_at', 'attestations')
    op.drop_index('idx_attestations_version', 'attestations')
    op.drop_index('idx_attestations_system_id', 'attestations')
    op.drop_index('idx_evidence_packets_created_at', 'evidence_packets')
    op.drop_index('idx_evidence_packets_scope', 'evidence_packets')
    op.drop_index('idx_evidence_packets_tenant_id', 'evidence_packets')
    op.drop_index('idx_playground_calls_status', 'playground_calls')
    op.drop_index('idx_playground_calls_created_at', 'playground_calls')
    op.drop_index('idx_tuning_runs_status', 'tuning_runs')
    op.drop_index('idx_tuning_runs_system_id', 'tuning_runs')
    op.drop_index('idx_tuning_runs_policy_id', 'tuning_runs')
    op.drop_index('idx_tuning_policies_system_id', 'tuning_policies')
    op.drop_index('idx_tuning_policies_tenant_id', 'tuning_policies')
    op.drop_index('idx_shared_assets_kind', 'shared_assets')
    op.drop_index('idx_shared_assets_workspace_id', 'shared_assets')
    op.drop_index('idx_workspace_members_user_id', 'workspace_members')
    op.drop_index('idx_workspace_members_workspace_id', 'workspace_members')
    op.drop_index('idx_workspaces_tenant_id', 'workspaces')
    op.drop_index('idx_perf_runs_created_at', 'perf_runs')
    op.drop_index('idx_perf_runs_scope', 'perf_runs')
    op.drop_index('idx_perf_budgets_scope', 'perf_budgets')
    op.drop_index('idx_perf_budgets_tenant_id', 'perf_budgets')
    
    # Drop tables
    op.drop_table('attestations')
    op.drop_table('evidence_packets')
    op.drop_table('playground_calls')
    op.drop_table('tuning_runs')
    op.drop_table('tuning_policies')
    op.drop_table('shared_assets')
    op.drop_table('workspace_members')
    op.drop_table('workspaces')
    op.drop_table('perf_runs')
    op.drop_table('perf_budgets')
