"""Add Meta-Builder v2 tables

Revision ID: 004
Revises: 003
Create Date: 2024-08-26 09:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    """Create Meta-Builder v2 tables."""
    
    # Create scaffold_specs table
    op.create_table('scaffold_specs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('mode', sa.String(20), nullable=False, default='freeform'),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('guided_input', sa.JSON(), nullable=True),
        sa.Column('attachments', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='draft'),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create scaffold_plans table
    op.create_table('scaffold_plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('spec_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, default=1),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('risk_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('agents_used', sa.JSON(), nullable=False, default=list),
        sa.Column('plan_graph', sa.JSON(), nullable=False),
        sa.Column('diff_preview', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['spec_id'], ['scaffold_specs.id'], ondelete='CASCADE')
    )
    
    # Create build_runs table
    op.create_table('build_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('spec_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('iteration', sa.Integer(), nullable=False, default=0),
        sa.Column('max_iterations', sa.Integer(), nullable=False, default=4),
        sa.Column('branch_ref', sa.String(255), nullable=True),
        sa.Column('elapsed_ms', sa.Integer(), nullable=True),
        sa.Column('metrics', sa.JSON(), nullable=False, default=dict),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['spec_id'], ['scaffold_specs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['plan_id'], ['scaffold_plans.id'], ondelete='CASCADE')
    )
    
    # Create build_steps table
    op.create_table('build_steps',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('input', sa.JSON(), nullable=False, default=dict),
        sa.Column('output', sa.JSON(), nullable=False, default=dict),
        sa.Column('logs_url', sa.String(500), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['run_id'], ['build_runs.id'], ondelete='CASCADE')
    )
    
    # Create diff_artifacts table
    op.create_table('diff_artifacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('iteration', sa.Integer(), nullable=False),
        sa.Column('unified_diff', sa.Text(), nullable=False),
        sa.Column('files_changed', sa.Integer(), nullable=False, default=0),
        sa.Column('risk', sa.JSON(), nullable=False, default=dict),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['run_id'], ['build_runs.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('run_id', 'iteration', name='uq_run_iteration')
    )
    
    # Create eval_reports table
    op.create_table('eval_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('iteration', sa.Integer(), nullable=False),
        sa.Column('scores', sa.JSON(), nullable=False, default=dict),
        sa.Column('failed_cases', sa.JSON(), nullable=False, default=list),
        sa.Column('junit_xml', sa.Text(), nullable=True),
        sa.Column('html_report_url', sa.String(500), nullable=True),
        sa.Column('pass_rate', sa.Float(), nullable=False, default=0.0),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['run_id'], ['build_runs.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('run_id', 'iteration', name='uq_eval_run_iteration')
    )
    
    # Create approval_gates table
    op.create_table('approval_gates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('iteration', sa.Integer(), nullable=False),
        sa.Column('required', sa.Boolean(), nullable=False, default=True),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('requested_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reviewer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['run_id'], ['build_runs.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('run_id', 'iteration', name='uq_approval_run_iteration')
    )
    
    # Create build_artifacts table
    op.create_table('build_artifacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('kind', sa.String(20), nullable=False),
        sa.Column('url', sa.String(500), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=False, default=dict),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['run_id'], ['build_runs.id'], ondelete='CASCADE')
    )
    
    # Create indices for performance
    op.create_index('idx_scaffold_specs_tenant_status', 'scaffold_specs', ['tenant_id', 'status'])
    op.create_index('idx_scaffold_specs_created_by', 'scaffold_specs', ['created_by'])
    op.create_index('idx_scaffold_plans_spec_version', 'scaffold_plans', ['spec_id', 'version'])
    op.create_index('idx_build_runs_tenant_status', 'build_runs', ['tenant_id', 'status'])
    op.create_index('idx_build_runs_spec', 'build_runs', ['spec_id'])
    op.create_index('idx_build_runs_started_at', 'build_runs', ['started_at'])
    op.create_index('idx_build_steps_run_name', 'build_steps', ['run_id', 'name'])
    op.create_index('idx_build_steps_status', 'build_steps', ['status'])
    op.create_index('idx_diff_artifacts_run_iteration', 'diff_artifacts', ['run_id', 'iteration'])
    op.create_index('idx_eval_reports_run_iteration', 'eval_reports', ['run_id', 'iteration'])
    op.create_index('idx_approval_gates_run_status', 'approval_gates', ['run_id', 'status'])
    op.create_index('idx_approval_gates_reviewer', 'approval_gates', ['reviewer_id'])
    op.create_index('idx_build_artifacts_run_kind', 'build_artifacts', ['run_id', 'kind'])
    op.create_index('idx_build_artifacts_created_at', 'build_artifacts', ['created_at'])


def downgrade():
    """Drop Meta-Builder v2 tables."""
    
    # Drop indices
    op.drop_index('idx_build_artifacts_created_at', table_name='build_artifacts')
    op.drop_index('idx_build_artifacts_run_kind', table_name='build_artifacts')
    op.drop_index('idx_approval_gates_reviewer', table_name='approval_gates')
    op.drop_index('idx_approval_gates_run_status', table_name='approval_gates')
    op.drop_index('idx_eval_reports_run_iteration', table_name='eval_reports')
    op.drop_index('idx_diff_artifacts_run_iteration', table_name='diff_artifacts')
    op.drop_index('idx_build_steps_status', table_name='build_steps')
    op.drop_index('idx_build_steps_run_name', table_name='build_steps')
    op.drop_index('idx_build_runs_started_at', table_name='build_runs')
    op.drop_index('idx_build_runs_spec', table_name='build_runs')
    op.drop_index('idx_build_runs_tenant_status', table_name='build_runs')
    op.drop_index('idx_scaffold_plans_spec_version', table_name='scaffold_plans')
    op.drop_index('idx_scaffold_specs_created_by', table_name='scaffold_specs')
    op.drop_index('idx_scaffold_specs_tenant_status', table_name='scaffold_specs')
    
    # Drop tables
    op.drop_table('build_artifacts')
    op.drop_table('approval_gates')
    op.drop_table('eval_reports')
    op.drop_table('diff_artifacts')
    op.drop_table('build_steps')
    op.drop_table('build_runs')
    op.drop_table('scaffold_plans')
    op.drop_table('scaffold_specs')
