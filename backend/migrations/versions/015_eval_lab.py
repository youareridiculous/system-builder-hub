"""Create Evaluation Lab tables

Revision ID: 015
Revises: 014
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade():
    """Create Evaluation Lab tables."""
    
    # Evaluation runs
    op.create_table('eval_runs',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('tenant_id', sa.String(50), nullable=False),
        sa.Column('suite', sa.String(100), nullable=False),
        sa.Column('sha', sa.String(40), nullable=True),
        sa.Column('tag', sa.String(100), nullable=True),
        sa.Column('v_lineage', sa.String(10), nullable=False),  # v2, v3, v4
        sa.Column('privacy_mode', sa.String(20), nullable=False),
        sa.Column('started_at', sa.DateTime, nullable=False),
        sa.Column('finished_at', sa.DateTime, nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='running'),
        sa.Column('total_cases', sa.Integer, nullable=False, default=0),
        sa.Column('passed_cases', sa.Integer, nullable=False, default=0),
        sa.Column('failed_cases', sa.Integer, nullable=False, default=0),
        sa.Column('skipped_cases', sa.Integer, nullable=False, default=0),
        sa.Column('total_execution_time_ms', sa.Float, nullable=False, default=0.0),
        sa.Column('total_cost_usd', sa.Float, nullable=False, default=0.0),
        sa.Column('total_tokens_prompt', sa.Integer, nullable=False, default=0),
        sa.Column('total_tokens_output', sa.Integer, nullable=False, default=0),
        sa.Column('metadata', sa.JSON, nullable=True)
    )
    op.create_index('ix_eval_runs_tenant_id', 'eval_runs', ['tenant_id'])
    op.create_index('ix_eval_runs_suite', 'eval_runs', ['suite'])
    op.create_index('ix_eval_runs_started_at', 'eval_runs', ['started_at'])
    op.create_index('ix_eval_runs_status', 'eval_runs', ['status'])
    
    # Evaluation cases
    op.create_table('eval_cases',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('run_id', sa.String(50), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('type', sa.String(20), nullable=False),  # golden, scenario, benchmark
        sa.Column('agent_set', sa.String(100), nullable=True),
        sa.Column('sla_class', sa.String(20), nullable=False, default='normal'),
        sa.Column('passed', sa.Boolean, nullable=False, default=False),
        sa.Column('execution_time_ms', sa.Float, nullable=False, default=0.0),
        sa.Column('assertions_total', sa.Integer, nullable=False, default=0),
        sa.Column('assertions_passed', sa.Integer, nullable=False, default=0),
        sa.Column('tokens_prompt', sa.Integer, nullable=False, default=0),
        sa.Column('tokens_output', sa.Integer, nullable=False, default=0),
        sa.Column('cost_usd', sa.Float, nullable=False, default=0.0),
        sa.Column('retries', sa.Integer, nullable=False, default=0),
        sa.Column('replans', sa.Integer, nullable=False, default=0),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('output', sa.JSON, nullable=True),
        sa.Column('metadata', sa.JSON, nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['eval_runs.id'], ondelete='CASCADE')
    )
    op.create_index('ix_eval_cases_run_id', 'eval_cases', ['run_id'])
    op.create_index('ix_eval_cases_name', 'eval_cases', ['name'])
    op.create_index('ix_eval_cases_type', 'eval_cases', ['type'])
    op.create_index('ix_eval_cases_passed', 'eval_cases', ['passed'])
    
    # Evaluation metrics
    op.create_table('eval_metrics',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('case_id', sa.String(50), nullable=False),
        sa.Column('metric_name', sa.String(100), nullable=False),
        sa.Column('metric_value', sa.Float, nullable=False),
        sa.Column('metric_unit', sa.String(20), nullable=True),
        sa.Column('timestamp', sa.DateTime, nullable=False),
        sa.Column('metadata', sa.JSON, nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['eval_cases.id'], ondelete='CASCADE')
    )
    op.create_index('ix_eval_metrics_case_id', 'eval_metrics', ['case_id'])
    op.create_index('ix_eval_metrics_name', 'eval_metrics', ['metric_name'])
    op.create_index('ix_eval_metrics_timestamp', 'eval_metrics', ['timestamp'])
    
    # Evaluation artifacts
    op.create_table('eval_artifacts',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('case_id', sa.String(50), nullable=False),
        sa.Column('kind', sa.String(50), nullable=False),  # json, html, junit, log
        sa.Column('uri', sa.String(500), nullable=False),
        sa.Column('digest', sa.String(64), nullable=False),
        sa.Column('size', sa.BigInteger, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('metadata', sa.JSON, nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['eval_cases.id'], ondelete='CASCADE')
    )
    op.create_index('ix_eval_artifacts_case_id', 'eval_artifacts', ['case_id'])
    op.create_index('ix_eval_artifacts_kind', 'eval_artifacts', ['kind'])
    op.create_index('ix_eval_artifacts_digest', 'eval_artifacts', ['digest'])
    
    # Evaluation regressions
    op.create_table('eval_regressions',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('run_id', sa.String(50), nullable=False),
        sa.Column('case_name', sa.String(200), nullable=False),
        sa.Column('metric', sa.String(100), nullable=False),
        sa.Column('baseline_value', sa.Float, nullable=False),
        sa.Column('current_value', sa.Float, nullable=False),
        sa.Column('delta', sa.Float, nullable=False),
        sa.Column('delta_percent', sa.Float, nullable=False),
        sa.Column('severity', sa.String(20), nullable=False, default='warning'),
        sa.Column('threshold', sa.Float, nullable=False),
        sa.Column('passed', sa.Boolean, nullable=False, default=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['eval_runs.id'], ondelete='CASCADE')
    )
    op.create_index('ix_eval_regressions_run_id', 'eval_regressions', ['run_id'])
    op.create_index('ix_eval_regressions_case_name', 'eval_regressions', ['case_name'])
    op.create_index('ix_eval_regressions_metric', 'eval_regressions', ['metric'])
    op.create_index('ix_eval_regressions_severity', 'eval_regressions', ['severity'])


def downgrade():
    """Drop Evaluation Lab tables."""
    op.drop_table('eval_regressions')
    op.drop_table('eval_artifacts')
    op.drop_table('eval_metrics')
    op.drop_table('eval_cases')
    op.drop_table('eval_runs')
