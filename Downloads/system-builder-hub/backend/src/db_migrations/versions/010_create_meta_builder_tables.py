"""
Create meta-builder tables

Revision ID: 010
Revises: 009
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade():
    # Create scaffold_sessions table
    op.create_table('scaffold_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('goal_text', sa.Text(), nullable=False),
        sa.Column('mode', sa.String(length=20), nullable=False, default='guided'),
        sa.Column('guided_input', sa.JSON(), nullable=True),
        sa.Column('pattern_slugs', sa.JSON(), nullable=True),
        sa.Column('template_slugs', sa.JSON(), nullable=True),
        sa.Column('composition_rules', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, default='draft'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    
    # Create scaffold_plans table
    op.create_table('scaffold_plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('planner_kind', sa.String(length=20), nullable=False),
        sa.Column('plan_json', sa.JSON(), nullable=False),
        sa.Column('diffs_json', sa.JSON(), nullable=True),
        sa.Column('scorecard_json', sa.JSON(), nullable=True),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('risks', sa.JSON(), nullable=True),
        sa.Column('build_status', sa.String(length=20), nullable=True),
        sa.Column('build_results', sa.JSON(), nullable=True),
        sa.Column('preview_urls', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['scaffold_sessions.id'], ondelete='CASCADE')
    )
    
    # Create pattern_library table
    op.create_table('pattern_library',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('inputs_schema', sa.JSON(), nullable=True),
        sa.Column('outputs_schema', sa.JSON(), nullable=True),
        sa.Column('compose_points', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('priority', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id', 'slug')
    )
    
    # Create template_links table
    op.create_table('template_links',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('template_slug', sa.String(length=100), nullable=False),
        sa.Column('template_version', sa.String(length=20), nullable=False),
        sa.Column('merge_strategy', sa.String(length=50), nullable=False, default='append'),
        sa.Column('compose_points', sa.JSON(), nullable=True),
        sa.Column('dependencies', sa.JSON(), nullable=True),
        sa.Column('conflicts', sa.JSON(), nullable=True),
        sa.Column('before_hooks', sa.JSON(), nullable=True),
        sa.Column('after_hooks', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('priority', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id', 'template_slug', 'template_version')
    )
    
    # Create prompt_templates table
    op.create_table('prompt_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('template_schema', sa.JSON(), nullable=False),
        sa.Column('version', sa.String(length=20), nullable=False, default='1.0.0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id', 'slug', 'version')
    )
    
    # Create evaluation_cases table
    op.create_table('evaluation_cases',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('golden_prompt', sa.Text(), nullable=False),
        sa.Column('expected_assertions', sa.JSON(), nullable=False),
        sa.Column('pattern_slugs', sa.JSON(), nullable=True),
        sa.Column('template_slugs', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE')
    )
    
    # Create plan_artifacts table
    op.create_table('plan_artifacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('artifact_type', sa.String(length=50), nullable=False),
        sa.Column('filename', sa.String(length=200), nullable=True),
        sa.Column('file_key', sa.String(length=500), nullable=True),
        sa.Column('file_size', sa.BigInteger(), nullable=True),
        sa.Column('content_type', sa.String(length=100), nullable=True),
        sa.Column('github_pr_url', sa.String(length=500), nullable=True),
        sa.Column('github_repo', sa.String(length=200), nullable=True),
        sa.Column('github_branch', sa.String(length=100), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['scaffold_sessions.id'], ondelete='CASCADE')
    )
    
    # Create scaffold_evaluations table
    op.create_table('scaffold_evaluations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('errors', sa.JSON(), nullable=True),
        sa.Column('execution_time', sa.Float(), nullable=True),
        sa.Column('memory_usage', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['scaffold_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['plan_id'], ['scaffold_plans.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['case_id'], ['evaluation_cases.id'], ondelete='CASCADE')
    )
    
    # Create indexes
    op.create_index('idx_scaffold_sessions_tenant_id', 'scaffold_sessions', ['tenant_id'])
    op.create_index('idx_scaffold_sessions_user_id', 'scaffold_sessions', ['user_id'])
    op.create_index('idx_scaffold_sessions_status', 'scaffold_sessions', ['status'])
    op.create_index('idx_scaffold_plans_tenant_id', 'scaffold_plans', ['tenant_id'])
    op.create_index('idx_scaffold_plans_session_id', 'scaffold_plans', ['session_id'])
    op.create_index('idx_pattern_library_tenant_id', 'pattern_library', ['tenant_id'])
    op.create_index('idx_pattern_library_slug', 'pattern_library', ['slug'])
    op.create_index('idx_template_links_tenant_id', 'template_links', ['tenant_id'])
    op.create_index('idx_template_links_template_slug', 'template_links', ['template_slug'])
    op.create_index('idx_prompt_templates_tenant_id', 'prompt_templates', ['tenant_id'])
    op.create_index('idx_prompt_templates_slug', 'prompt_templates', ['slug'])
    op.create_index('idx_evaluation_cases_tenant_id', 'evaluation_cases', ['tenant_id'])
    op.create_index('idx_plan_artifacts_tenant_id', 'plan_artifacts', ['tenant_id'])
    op.create_index('idx_plan_artifacts_session_id', 'plan_artifacts', ['session_id'])
    op.create_index('idx_scaffold_evaluations_tenant_id', 'scaffold_evaluations', ['tenant_id'])
    op.create_index('idx_scaffold_evaluations_case_id', 'scaffold_evaluations', ['case_id'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_scaffold_evaluations_case_id', 'scaffold_evaluations')
    op.drop_index('idx_scaffold_evaluations_tenant_id', 'scaffold_evaluations')
    op.drop_index('idx_plan_artifacts_session_id', 'plan_artifacts')
    op.drop_index('idx_plan_artifacts_tenant_id', 'plan_artifacts')
    op.drop_index('idx_evaluation_cases_tenant_id', 'evaluation_cases')
    op.drop_index('idx_prompt_templates_slug', 'prompt_templates')
    op.drop_index('idx_prompt_templates_tenant_id', 'prompt_templates')
    op.drop_index('idx_template_links_template_slug', 'template_links')
    op.drop_index('idx_template_links_tenant_id', 'template_links')
    op.drop_index('idx_pattern_library_slug', 'pattern_library')
    op.drop_index('idx_pattern_library_tenant_id', 'pattern_library')
    op.drop_index('idx_scaffold_plans_session_id', 'scaffold_plans')
    op.drop_index('idx_scaffold_plans_tenant_id', 'scaffold_plans')
    op.drop_index('idx_scaffold_sessions_status', 'scaffold_sessions')
    op.drop_index('idx_scaffold_sessions_user_id', 'scaffold_sessions')
    op.drop_index('idx_scaffold_sessions_tenant_id', 'scaffold_sessions')
    
    # Drop tables
    op.drop_table('scaffold_evaluations')
    op.drop_table('plan_artifacts')
    op.drop_table('evaluation_cases')
    op.drop_table('prompt_templates')
    op.drop_table('template_links')
    op.drop_table('pattern_library')
    op.drop_table('scaffold_plans')
    op.drop_table('scaffold_sessions')
