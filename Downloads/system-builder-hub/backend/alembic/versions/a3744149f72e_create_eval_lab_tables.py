"""create_eval_lab_tables

Revision ID: a3744149f72e
Revises: 001
Create Date: 2025-08-27 06:04:23.175277

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a3744149f72e'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create eval_runs table
    op.create_table('eval_runs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('suite_name', sa.String(length=255), nullable=False),
        sa.Column('suite_version', sa.String(length=50), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('total_cases', sa.Integer(), nullable=False),
        sa.Column('passed_cases', sa.Integer(), nullable=False),
        sa.Column('failed_cases', sa.Integer(), nullable=False),
        sa.Column('pass_rate', sa.Float(), nullable=True),
        sa.Column('avg_latency_ms', sa.Float(), nullable=True),
        sa.Column('p95_latency_ms', sa.Float(), nullable=True),
        sa.Column('p99_latency_ms', sa.Float(), nullable=True),
        sa.Column('total_cost_usd', sa.Float(), nullable=True),
        sa.Column('cost_per_case_usd', sa.Float(), nullable=True),
        sa.Column('privacy_mode', sa.String(length=50), nullable=False),
        sa.Column('meta_builder_version', sa.String(length=10), nullable=True),
        sa.Column('environment', sa.String(length=50), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_eval_runs_suite_name'), 'eval_runs', ['suite_name'], unique=False)
    op.create_index(op.f('ix_eval_runs_started_at'), 'eval_runs', ['started_at'], unique=False)
    op.create_index(op.f('ix_eval_runs_status'), 'eval_runs', ['status'], unique=False)

    # Create eval_cases table
    op.create_table('eval_cases',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('eval_run_id', sa.String(length=36), nullable=False),
        sa.Column('case_name', sa.String(length=255), nullable=False),
        sa.Column('case_type', sa.String(length=50), nullable=False),
        sa.Column('sla_class', sa.String(length=50), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('passed', sa.Boolean(), nullable=True),
        sa.Column('latency_ms', sa.Float(), nullable=True),
        sa.Column('cost_usd', sa.Float(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('assertion_results', sa.JSON(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['eval_run_id'], ['eval_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_eval_cases_eval_run_id'), 'eval_cases', ['eval_run_id'], unique=False)
    op.create_index(op.f('ix_eval_cases_case_name'), 'eval_cases', ['case_name'], unique=False)
    op.create_index(op.f('ix_eval_cases_status'), 'eval_cases', ['status'], unique=False)

    # Create eval_metrics table
    op.create_table('eval_metrics',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('eval_run_id', sa.String(length=36), nullable=False),
        sa.Column('metric_name', sa.String(length=255), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('metric_unit', sa.String(length=50), nullable=True),
        sa.Column('metric_type', sa.String(length=50), nullable=False),
        sa.Column('threshold', sa.Float(), nullable=True),
        sa.Column('operator', sa.String(length=10), nullable=True),
        sa.Column('passed', sa.Boolean(), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['eval_run_id'], ['eval_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_eval_metrics_eval_run_id'), 'eval_metrics', ['eval_run_id'], unique=False)
    op.create_index(op.f('ix_eval_metrics_metric_name'), 'eval_metrics', ['metric_name'], unique=False)

    # Create eval_artifacts table
    op.create_table('eval_artifacts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('eval_run_id', sa.String(length=36), nullable=False),
        sa.Column('eval_case_id', sa.String(length=36), nullable=True),
        sa.Column('artifact_type', sa.String(length=100), nullable=False),
        sa.Column('artifact_name', sa.String(length=255), nullable=False),
        sa.Column('artifact_path', sa.String(length=500), nullable=False),
        sa.Column('artifact_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('content_type', sa.String(length=100), nullable=True),
        sa.Column('checksum', sa.String(length=64), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['eval_case_id'], ['eval_cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['eval_run_id'], ['eval_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_eval_artifacts_eval_run_id'), 'eval_artifacts', ['eval_run_id'], unique=False)
    op.create_index(op.f('ix_eval_artifacts_eval_case_id'), 'eval_artifacts', ['eval_case_id'], unique=False)
    op.create_index(op.f('ix_eval_artifacts_artifact_type'), 'eval_artifacts', ['artifact_type'], unique=False)

    # Create eval_regressions table
    op.create_table('eval_regressions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('baseline_run_id', sa.String(length=36), nullable=False),
        sa.Column('current_run_id', sa.String(length=36), nullable=False),
        sa.Column('metric_name', sa.String(length=255), nullable=False),
        sa.Column('baseline_value', sa.Float(), nullable=False),
        sa.Column('current_value', sa.Float(), nullable=False),
        sa.Column('change_percent', sa.Float(), nullable=False),
        sa.Column('threshold', sa.Float(), nullable=False),
        sa.Column('regression_detected', sa.Boolean(), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['baseline_run_id'], ['eval_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['current_run_id'], ['eval_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_eval_regressions_baseline_run_id'), 'eval_regressions', ['baseline_run_id'], unique=False)
    op.create_index(op.f('ix_eval_regressions_current_run_id'), 'eval_regressions', ['current_run_id'], unique=False)
    op.create_index(op.f('ix_eval_regressions_metric_name'), 'eval_regressions', ['metric_name'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_eval_regressions_metric_name'), table_name='eval_regressions')
    op.drop_index(op.f('ix_eval_regressions_current_run_id'), table_name='eval_regressions')
    op.drop_index(op.f('ix_eval_regressions_baseline_run_id'), table_name='eval_regressions')
    op.drop_table('eval_regressions')
    
    op.drop_index(op.f('ix_eval_artifacts_artifact_type'), table_name='eval_artifacts')
    op.drop_index(op.f('ix_eval_artifacts_eval_case_id'), table_name='eval_artifacts')
    op.drop_index(op.f('ix_eval_artifacts_eval_run_id'), table_name='eval_artifacts')
    op.drop_table('eval_artifacts')
    
    op.drop_index(op.f('ix_eval_metrics_metric_name'), table_name='eval_metrics')
    op.drop_index(op.f('ix_eval_metrics_eval_run_id'), table_name='eval_metrics')
    op.drop_table('eval_metrics')
    
    op.drop_index(op.f('ix_eval_cases_status'), table_name='eval_cases')
    op.drop_index(op.f('ix_eval_cases_case_name'), table_name='eval_cases')
    op.drop_index(op.f('ix_eval_cases_eval_run_id'), table_name='eval_cases')
    op.drop_table('eval_cases')
    
    op.drop_index(op.f('ix_eval_runs_status'), table_name='eval_runs')
    op.drop_index(op.f('ix_eval_runs_started_at'), table_name='eval_runs')
    op.drop_index(op.f('ix_eval_runs_suite_name'), table_name='eval_runs')
    op.drop_table('eval_runs')
