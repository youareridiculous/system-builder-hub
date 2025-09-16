"""Create Meta-Builder v4 tables

Revision ID: 014
Revises: 013
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade():
    """Create Meta-Builder v4 tables."""
    
    # Canary testing samples
    op.create_table('mb_v4_canary_sample',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('run_id', sa.String(50), nullable=False),
        sa.Column('tenant_id', sa.String(50), nullable=False),
        sa.Column('canary_group', sa.String(20), nullable=False),
        sa.Column('assigned_at', sa.DateTime, nullable=False),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('success', sa.Boolean, nullable=True),
        sa.Column('metrics', sa.JSON, nullable=True),
        sa.Column('cost_usd', sa.Float, nullable=False, default=0.0),
        sa.Column('duration_seconds', sa.Integer, nullable=False, default=0),
        sa.Column('retry_count', sa.Integer, nullable=False, default=0),
        sa.Column('replan_count', sa.Integer, nullable=False, default=0),
        sa.Column('rollback_count', sa.Integer, nullable=False, default=0)
    )
    op.create_index('ix_mb_v4_canary_sample_run_id', 'mb_v4_canary_sample', ['run_id'])
    op.create_index('ix_mb_v4_canary_sample_tenant_id', 'mb_v4_canary_sample', ['tenant_id'])
    
    # Replay bundles
    op.create_table('mb_v4_replay_bundle',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('run_id', sa.String(50), nullable=False),
        sa.Column('prompts', sa.JSON, nullable=False),
        sa.Column('tool_io', sa.JSON, nullable=False),
        sa.Column('diffs', sa.JSON, nullable=False),
        sa.Column('final_state', sa.JSON, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False)
    )
    op.create_index('ix_mb_v4_replay_bundle_run_id', 'mb_v4_replay_bundle', ['run_id'])
    
    # Queue leases
    op.create_table('mb_v4_queue_lease',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('worker_id', sa.String(50), nullable=False),
        sa.Column('queue_class', sa.String(20), nullable=False),
        sa.Column('leased_at', sa.DateTime, nullable=False),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Column('task_id', sa.String(50), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='active')
    )
    op.create_index('ix_mb_v4_queue_lease_worker_id', 'mb_v4_queue_lease', ['worker_id'])
    
    # Run budgets
    op.create_table('mb_v4_run_budget',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('run_id', sa.String(50), nullable=False),
        sa.Column('tenant_id', sa.String(50), nullable=False),
        sa.Column('cost_budget_usd', sa.Float, nullable=False),
        sa.Column('time_budget_seconds', sa.Integer, nullable=False),
        sa.Column('attempt_budget', sa.Integer, nullable=False),
        sa.Column('current_cost_usd', sa.Float, nullable=False, default=0.0),
        sa.Column('current_time_seconds', sa.Integer, nullable=False, default=0),
        sa.Column('current_attempts', sa.Integer, nullable=False, default=0),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False)
    )
    op.create_index('ix_mb_v4_run_budget_run_id', 'mb_v4_run_budget', ['run_id'])
    op.create_index('ix_mb_v4_run_budget_tenant_id', 'mb_v4_run_budget', ['tenant_id'])
    
    # Circuit breaker states
    op.create_table('mb_v4_circuit_breaker_state',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('failure_class', sa.String(50), nullable=False),
        sa.Column('tenant_id', sa.String(50), nullable=False),
        sa.Column('state', sa.String(20), nullable=False),
        sa.Column('failure_count', sa.Integer, nullable=False, default=0),
        sa.Column('threshold', sa.Integer, nullable=False, default=5),
        sa.Column('cooldown_minutes', sa.Integer, nullable=False, default=5),
        sa.Column('last_failure', sa.DateTime, nullable=True),
        sa.Column('last_state_change', sa.DateTime, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False)
    )
    op.create_index('ix_mb_v4_circuit_breaker_state_failure_class', 'mb_v4_circuit_breaker_state', ['failure_class'])
    op.create_index('ix_mb_v4_circuit_breaker_state_tenant_id', 'mb_v4_circuit_breaker_state', ['tenant_id'])
    
    # Chaos events
    op.create_table('mb_v4_chaos_event',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('chaos_type', sa.String(50), nullable=False),
        sa.Column('run_id', sa.String(50), nullable=False),
        sa.Column('step_id', sa.String(50), nullable=False),
        sa.Column('tenant_id', sa.String(50), nullable=False),
        sa.Column('injected_at', sa.DateTime, nullable=False),
        sa.Column('resolved_at', sa.DateTime, nullable=True),
        sa.Column('duration_seconds', sa.Float, nullable=True),
        sa.Column('recovery_successful', sa.Boolean, nullable=True),
        sa.Column('metadata', sa.JSON, nullable=True)
    )
    op.create_index('ix_mb_v4_chaos_event_chaos_type', 'mb_v4_chaos_event', ['chaos_type'])
    op.create_index('ix_mb_v4_chaos_event_run_id', 'mb_v4_chaos_event', ['run_id'])
    op.create_index('ix_mb_v4_chaos_event_tenant_id', 'mb_v4_chaos_event', ['tenant_id'])
    
    # Repair attempts
    op.create_table('mb_v4_repair_attempt',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('run_id', sa.String(50), nullable=False),
        sa.Column('step_id', sa.String(50), nullable=False),
        sa.Column('failure_class', sa.String(50), nullable=False),
        sa.Column('repair_phase', sa.String(20), nullable=False),
        sa.Column('strategy', sa.String(50), nullable=False),
        sa.Column('result', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False)
    )
    op.create_index('ix_mb_v4_repair_attempt_run_id', 'mb_v4_repair_attempt', ['run_id'])


def downgrade():
    """Drop Meta-Builder v4 tables."""
    op.drop_table('mb_v4_repair_attempt')
    op.drop_table('mb_v4_chaos_event')
    op.drop_table('mb_v4_circuit_breaker_state')
    op.drop_table('mb_v4_run_budget')
    op.drop_table('mb_v4_queue_lease')
    op.drop_table('mb_v4_replay_bundle')
    op.drop_table('mb_v4_canary_sample')
