"""P53-P56 Database Tables Migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create P53-P56 tables"""
    
    # P53: Competitive Teardown & Benchmark Lab
    op.create_table('teardowns',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('target_name', sa.String(), nullable=False),
        sa.Column('domain', sa.String(), nullable=False),
        sa.Column('notes_md', sa.Text(), nullable=False),
        sa.Column('jobs_to_be_done', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('benchmarks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('system_id', sa.String(), nullable=False),
        sa.Column('version', sa.String(), nullable=False),
        sa.Column('results_json', sa.Text(), nullable=False),
        sa.Column('artifacts_uri', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('scorecards',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('system_id', sa.String(), nullable=False),
        sa.Column('version', sa.String(), nullable=False),
        sa.Column('architecture', sa.Integer(), nullable=False),
        sa.Column('performance', sa.Integer(), nullable=False),
        sa.Column('ux', sa.Integer(), nullable=False),
        sa.Column('security', sa.Integer(), nullable=False),
        sa.Column('scalability', sa.Integer(), nullable=False),
        sa.Column('extensibility', sa.Integer(), nullable=False),
        sa.Column('business', sa.Integer(), nullable=False),
        sa.Column('total', sa.Integer(), nullable=False),
        sa.Column('evidence_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # P54: Quality Gates, Security/Legal/Ethics Enforcement
    op.create_table('golden_paths',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('system_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('script_uri', sa.String(), nullable=False),
        sa.Column('owner', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('gate_policies',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('min_total', sa.Integer(), nullable=False),
        sa.Column('thresholds_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('gate_results',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('system_id', sa.String(), nullable=False),
        sa.Column('version', sa.String(), nullable=False),
        sa.Column('passed', sa.Boolean(), nullable=False),
        sa.Column('details_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('governance_profiles',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('legal_json', sa.Text(), nullable=False),
        sa.Column('ethical_json', sa.Text(), nullable=False),
        sa.Column('region_policies_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('redteam_runs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('system_id', sa.String(), nullable=False),
        sa.Column('version', sa.String(), nullable=False),
        sa.Column('results_json', sa.Text(), nullable=False),
        sa.Column('severity_max', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # P55: Clone-and-Improve Generator (C&I)
    op.create_table('improve_plans',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('teardown_id', sa.String(), nullable=True),
        sa.Column('target_name', sa.String(), nullable=False),
        sa.Column('deltas_json', sa.Text(), nullable=False),
        sa.Column('success_metrics_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('improve_runs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('plan_id', sa.String(), nullable=False),
        sa.Column('system_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('score_before', sa.Integer(), nullable=False),
        sa.Column('score_after', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['plan_id'], ['improve_plans.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # P56: Synthetic Users & Auto-Tuning (opt-in autonomy)
    op.create_table('synthetic_cohorts',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('system_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('persona_json', sa.Text(), nullable=False),
        sa.Column('volume_profile_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('synthetic_runs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('cohort_id', sa.String(), nullable=False),
        sa.Column('system_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('metrics_json', sa.Text(), nullable=False),
        sa.Column('findings_json', sa.Text(), nullable=False),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['cohort_id'], ['synthetic_cohorts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('optimization_policies',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('system_id', sa.String(), nullable=False),
        sa.Column('mode', sa.String(), nullable=False),
        sa.Column('safe_change_types', sa.Text(), nullable=False),
        sa.Column('approval_gates', sa.Text(), nullable=False),
        sa.Column('rollback_policy', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indices for better performance
    op.create_index('idx_teardowns_tenant_id', 'teardowns', ['tenant_id'])
    op.create_index('idx_benchmarks_system_id', 'benchmarks', ['system_id'])
    op.create_index('idx_scorecards_system_id', 'scorecards', ['system_id'])
    op.create_index('idx_golden_paths_system_id', 'golden_paths', ['system_id'])
    op.create_index('idx_gate_policies_tenant_id', 'gate_policies', ['tenant_id'])
    op.create_index('idx_gate_results_system_id', 'gate_results', ['system_id'])
    op.create_index('idx_governance_profiles_tenant_id', 'governance_profiles', ['tenant_id'])
    op.create_index('idx_redteam_runs_system_id', 'redteam_runs', ['system_id'])
    op.create_index('idx_improve_plans_teardown_id', 'improve_plans', ['teardown_id'])
    op.create_index('idx_improve_runs_plan_id', 'improve_runs', ['plan_id'])
    op.create_index('idx_improve_runs_system_id', 'improve_runs', ['system_id'])
    op.create_index('idx_synthetic_cohorts_tenant_id', 'synthetic_cohorts', ['tenant_id'])
    op.create_index('idx_synthetic_cohorts_system_id', 'synthetic_cohorts', ['system_id'])
    op.create_index('idx_synthetic_runs_cohort_id', 'synthetic_runs', ['cohort_id'])
    op.create_index('idx_synthetic_runs_system_id', 'synthetic_runs', ['system_id'])
    op.create_index('idx_optimization_policies_tenant_id', 'optimization_policies', ['tenant_id'])
    op.create_index('idx_optimization_policies_system_id', 'optimization_policies', ['system_id'])


def downgrade():
    """Drop P53-P56 tables"""
    
    # Drop indices
    op.drop_index('idx_optimization_policies_system_id', 'optimization_policies')
    op.drop_index('idx_optimization_policies_tenant_id', 'optimization_policies')
    op.drop_index('idx_synthetic_runs_system_id', 'synthetic_runs')
    op.drop_index('idx_synthetic_runs_cohort_id', 'synthetic_runs')
    op.drop_index('idx_synthetic_cohorts_system_id', 'synthetic_cohorts')
    op.drop_index('idx_synthetic_cohorts_tenant_id', 'synthetic_cohorts')
    op.drop_index('idx_improve_runs_system_id', 'improve_runs')
    op.drop_index('idx_improve_runs_plan_id', 'improve_runs')
    op.drop_index('idx_improve_plans_teardown_id', 'improve_plans')
    op.drop_index('idx_redteam_runs_system_id', 'redteam_runs')
    op.drop_index('idx_governance_profiles_tenant_id', 'governance_profiles')
    op.drop_index('idx_gate_results_system_id', 'gate_results')
    op.drop_index('idx_gate_policies_tenant_id', 'gate_policies')
    op.drop_index('idx_golden_paths_system_id', 'golden_paths')
    op.drop_index('idx_scorecards_system_id', 'scorecards')
    op.drop_index('idx_benchmarks_system_id', 'benchmarks')
    op.drop_index('idx_teardowns_tenant_id', 'teardowns')
    
    # Drop tables
    op.drop_table('optimization_policies')
    op.drop_table('synthetic_runs')
    op.drop_table('synthetic_cohorts')
    op.drop_table('improve_runs')
    op.drop_table('improve_plans')
    op.drop_table('redteam_runs')
    op.drop_table('governance_profiles')
    op.drop_table('gate_results')
    op.drop_table('gate_policies')
    op.drop_table('golden_paths')
    op.drop_table('scorecards')
    op.drop_table('benchmarks')
    op.drop_table('teardowns')
