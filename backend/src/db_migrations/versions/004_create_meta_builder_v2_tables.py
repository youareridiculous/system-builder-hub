"""
Create Meta-Builder v2 tables
Multi-agent, iterative scaffold generation with evaluation and approval.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_meta_builder_v2'
down_revision = '003_add_p31_p33_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Create meta_runs table
    op.create_table('meta_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('goal_text', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('spec', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('limits', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('review_config', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('current_iteration', sa.Integer(), nullable=True),
        sa.Column('total_tokens_used', sa.Integer(), nullable=True),
        sa.Column('start_time', sa.DateTime(), nullable=True),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('final_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_meta_runs_tenant_id', 'tenant_id'),
        sa.Index('ix_meta_runs_status', 'status'),
        sa.Index('ix_meta_runs_created_at', 'created_at')
    )

    # Create meta_artifacts table
    op.create_table('meta_artifacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(length=50), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('iteration', sa.Integer(), nullable=False),
        sa.Column('agent_role', sa.String(length=50), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['meta_runs.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_meta_artifacts_tenant_id', 'tenant_id'),
        sa.Index('ix_meta_artifacts_run_id', 'run_id'),
        sa.Index('ix_meta_artifacts_type', 'type'),
        sa.Index('ix_meta_artifacts_agent_role', 'agent_role')
    )

    # Create meta_reports table
    op.create_table('meta_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(length=50), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('iteration', sa.Integer(), nullable=False),
        sa.Column('agent_role', sa.String(length=50), nullable=False),
        sa.Column('report_type', sa.String(length=50), nullable=False),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('passed', sa.Boolean(), nullable=True),
        sa.Column('details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('recommendations', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['meta_runs.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_meta_reports_tenant_id', 'tenant_id'),
        sa.Index('ix_meta_reports_run_id', 'run_id'),
        sa.Index('ix_meta_reports_report_type', 'report_type'),
        sa.Index('ix_meta_reports_agent_role', 'agent_role')
    )

    # Create meta_approvals table
    op.create_table('meta_approvals',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(length=50), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('approved', sa.Boolean(), nullable=False),
        sa.Column('approved_by', sa.String(length=50), nullable=False),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('concerns', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('requested_changes', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('rollback_plan', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['meta_runs.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_meta_approvals_tenant_id', 'tenant_id'),
        sa.Index('ix_meta_approvals_run_id', 'run_id'),
        sa.Index('ix_meta_approvals_approved', 'approved')
    )

    # Create golden_tasks table
    op.create_table('golden_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('setup', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('steps', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('assertions', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('cleanup', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('weight', sa.Float(), nullable=True),
        sa.Column('timeout_s', sa.Integer(), nullable=True),
        sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_golden_tasks_tenant_id', 'tenant_id'),
        sa.Index('ix_golden_tasks_category', 'category'),
        sa.Index('ix_golden_tasks_is_active', 'is_active')
    )

    # Create agent_spans table
    op.create_table('agent_spans',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(length=50), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_role', sa.String(length=50), nullable=False),
        sa.Column('span_name', sa.String(length=255), nullable=False),
        sa.Column('iteration', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('cache_hits', sa.Integer(), nullable=True),
        sa.Column('inputs', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('outputs', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['meta_runs.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_agent_spans_tenant_id', 'tenant_id'),
        sa.Index('ix_agent_spans_run_id', 'run_id'),
        sa.Index('ix_agent_spans_agent_role', 'agent_role'),
        sa.Index('ix_agent_spans_span_name', 'span_name')
    )


def downgrade():
    op.drop_table('agent_spans')
    op.drop_table('golden_tasks')
    op.drop_table('meta_approvals')
    op.drop_table('meta_reports')
    op.drop_table('meta_artifacts')
    op.drop_table('meta_runs')
