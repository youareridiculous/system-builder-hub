"""
Create Meta-Builder v3 tables for auto-fix system.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '011_create_meta_builder_v3_tables'
down_revision = '010_create_meta_builder_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Create auto_fix_runs table
    op.create_table('auto_fix_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('step_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('signal_type', sa.String(length=50), nullable=False),
        sa.Column('strategy', sa.String(length=50), nullable=True),
        sa.Column('outcome', sa.String(length=50), nullable=False),
        sa.Column('attempt', sa.Integer(), nullable=False, default=1),
        sa.Column('backoff', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['run_id'], ['build_runs.id'], ),
        sa.ForeignKeyConstraint(['step_id'], ['build_steps.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for auto_fix_runs
    op.create_index('idx_auto_fix_runs_run_id', 'auto_fix_runs', ['run_id'])
    op.create_index('idx_auto_fix_runs_step_id', 'auto_fix_runs', ['step_id'])
    op.create_index('idx_auto_fix_runs_created_at', 'auto_fix_runs', ['created_at'])
    
    # Create plan_deltas table
    op.create_table('plan_deltas',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('original_plan_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('new_plan_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('delta_data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('triggered_by', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['original_plan_id'], ['scaffold_plans.id'], ),
        sa.ForeignKeyConstraint(['new_plan_id'], ['scaffold_plans.id'], ),
        sa.ForeignKeyConstraint(['run_id'], ['build_runs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for plan_deltas
    op.create_index('idx_plan_deltas_run_id', 'plan_deltas', ['run_id'])
    op.create_index('idx_plan_deltas_original_plan', 'plan_deltas', ['original_plan_id'])
    op.create_index('idx_plan_deltas_new_plan', 'plan_deltas', ['new_plan_id'])
    
    # Create retry_states table
    op.create_table('retry_states',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('attempt_counter', sa.Integer(), nullable=False, default=0),
        sa.Column('per_step_attempts', postgresql.JSON(astext_type=sa.Text()), nullable=False, default='{}'),
        sa.Column('total_attempts', sa.Integer(), nullable=False, default=0),
        sa.Column('last_backoff_seconds', sa.Float(), nullable=True),
        sa.Column('max_total_attempts', sa.Integer(), nullable=False, default=6),
        sa.Column('max_per_step_attempts', sa.Integer(), nullable=False, default=3),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['run_id'], ['build_runs.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('run_id')
    )
    
    # Create index for retry_states
    op.create_index('idx_retry_states_run_id', 'retry_states', ['run_id'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_retry_states_run_id', table_name='retry_states')
    op.drop_index('idx_plan_deltas_new_plan', table_name='plan_deltas')
    op.drop_index('idx_plan_deltas_original_plan', table_name='plan_deltas')
    op.drop_index('idx_plan_deltas_run_id', table_name='plan_deltas')
    op.drop_index('idx_auto_fix_runs_created_at', table_name='auto_fix_runs')
    op.drop_index('idx_auto_fix_runs_step_id', table_name='auto_fix_runs')
    op.drop_index('idx_auto_fix_runs_run_id', table_name='auto_fix_runs')
    
    # Drop tables
    op.drop_table('retry_states')
    op.drop_table('plan_deltas')
    op.drop_table('auto_fix_runs')
