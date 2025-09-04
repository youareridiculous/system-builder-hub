"""eval_lab_v1_1_upgrade

Revision ID: 5ecd76ed3373
Revises: a3744149f72e
Create Date: 2025-08-27 06:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '5ecd76ed3373'
down_revision = 'a3744149f72e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create eval_quarantine_cases table
    op.create_table('eval_quarantine_cases',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('suite_id', sa.String(length=255), nullable=False),
        sa.Column('case_id', sa.String(length=255), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('flake_score', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_eval_quarantine_cases_tenant_id'), 'eval_quarantine_cases', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_eval_quarantine_cases_suite_id'), 'eval_quarantine_cases', ['suite_id'], unique=False)
    op.create_index(op.f('ix_eval_quarantine_cases_case_id'), 'eval_quarantine_cases', ['case_id'], unique=False)
    op.create_index(op.f('ix_eval_quarantine_cases_status'), 'eval_quarantine_cases', ['status'], unique=False)
    op.create_index(op.f('ix_eval_quarantine_cases_expires_at'), 'eval_quarantine_cases', ['expires_at'], unique=False)

    # Add rerun cost columns to eval_cases
    op.add_column('eval_cases', sa.Column('rerun_count', sa.Integer(), nullable=True, default=0))
    op.add_column('eval_cases', sa.Column('base_cost_usd', sa.Float(), nullable=True))
    op.add_column('eval_cases', sa.Column('rerun_cost_usd', sa.Float(), nullable=True))
    op.add_column('eval_cases', sa.Column('total_cost_usd', sa.Float(), nullable=True))
    op.add_column('eval_cases', sa.Column('flake_score', sa.Float(), nullable=True))
    op.add_column('eval_cases', sa.Column('result_class', sa.String(length=50), nullable=True))

    # Add budget and guard breach columns to eval_runs
    op.add_column('eval_runs', sa.Column('budget_exceeded', sa.Boolean(), nullable=True, default=False))
    op.add_column('eval_runs', sa.Column('guard_breaches', sa.Integer(), nullable=True, default=0))
    op.add_column('eval_runs', sa.Column('quarantined_cases', sa.Integer(), nullable=True, default=0))
    op.add_column('eval_runs', sa.Column('rerun_cases', sa.Integer(), nullable=True, default=0))

    # Add indexes for performance
    op.create_index(op.f('ix_eval_runs_created_at_desc'), 'eval_runs', ['created_at'], unique=False, postgresql_ops={'created_at': 'DESC'})
    op.create_index(op.f('ix_eval_runs_suite_id'), 'eval_runs', ['suite_name'], unique=False)
    op.create_index(op.f('ix_eval_cases_case_id'), 'eval_cases', ['case_name'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_eval_cases_case_id'), table_name='eval_cases')
    op.drop_index(op.f('ix_eval_runs_suite_id'), table_name='eval_runs')
    op.drop_index(op.f('ix_eval_runs_created_at_desc'), table_name='eval_runs')
    
    # Drop columns from eval_runs
    op.drop_column('eval_runs', 'rerun_cases')
    op.drop_column('eval_runs', 'quarantined_cases')
    op.drop_column('eval_runs', 'guard_breaches')
    op.drop_column('eval_runs', 'budget_exceeded')
    
    # Drop columns from eval_cases
    op.drop_column('eval_cases', 'result_class')
    op.drop_column('eval_cases', 'flake_score')
    op.drop_column('eval_cases', 'total_cost_usd')
    op.drop_column('eval_cases', 'rerun_cost_usd')
    op.drop_column('eval_cases', 'base_cost_usd')
    op.drop_column('eval_cases', 'rerun_count')
    
    # Drop eval_quarantine_cases table
    op.drop_index(op.f('ix_eval_quarantine_cases_expires_at'), table_name='eval_quarantine_cases')
    op.drop_index(op.f('ix_eval_quarantine_cases_status'), table_name='eval_quarantine_cases')
    op.drop_index(op.f('ix_eval_quarantine_cases_case_id'), table_name='eval_quarantine_cases')
    op.drop_index(op.f('ix_eval_quarantine_cases_suite_id'), table_name='eval_quarantine_cases')
    op.drop_index(op.f('ix_eval_quarantine_cases_tenant_id'), table_name='eval_quarantine_cases')
    op.drop_table('eval_quarantine_cases')
