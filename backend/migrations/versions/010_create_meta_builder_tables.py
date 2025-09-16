"""Create meta-builder tables

Revision ID: 010
Revises: 009
Create Date: 2024-08-26 00:00:00.000000

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
        sa.Column('mode', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('guided_input', sa.JSON(), nullable=True),
        sa.Column('pattern_slugs', sa.JSON(), nullable=True),
        sa.Column('template_slugs', sa.JSON(), nullable=True),
        sa.Column('composition_rules', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_scaffold_sessions_tenant_user', 'scaffold_sessions', ['tenant_id', 'user_id'], unique=False)
    op.create_index('idx_scaffold_sessions_status', 'scaffold_sessions', ['tenant_id', 'status'], unique=False)
    op.create_index('idx_scaffold_sessions_created', 'scaffold_sessions', ['tenant_id', 'created_at'], unique=False)

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
        sa.Column('build_job_id', sa.String(length=100), nullable=True),
        sa.Column('build_results', sa.JSON(), nullable=True),
        sa.Column('preview_urls', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['scaffold_sessions.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_scaffold_plans_session_version', 'scaffold_plans', ['session_id', 'version'], unique=False)
    op.create_index('idx_scaffold_plans_build_status', 'scaffold_plans', ['tenant_id', 'build_status'], unique=False)

    # Create pattern_library table
    op.create_table('pattern_library',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('tags', sa.JSON(), nullable=False),
        sa.Column('inputs_schema', sa.JSON(), nullable=False),
        sa.Column('outputs_schema', sa.JSON(), nullable=False),
        sa.Column('compose_points', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_seeded', sa.Boolean(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index('idx_pattern_library_slug', 'pattern_library', ['slug'], unique=False)
    op.create_index('idx_pattern_library_tags', 'pattern_library', ['tenant_id', 'tags'], unique=False)
    op.create_index('idx_pattern_library_active', 'pattern_library', ['tenant_id', 'is_active'], unique=False)

    # Create template_links table
    op.create_table('template_links',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('template_slug', sa.String(length=100), nullable=False),
        sa.Column('template_version', sa.String(length=20), nullable=False),
        sa.Column('before_hooks', sa.JSON(), nullable=True),
        sa.Column('after_hooks', sa.JSON(), nullable=True),
        sa.Column('merge_strategy', sa.String(length=50), nullable=False),
        sa.Column('compose_points', sa.JSON(), nullable=False),
        sa.Column('dependencies', sa.JSON(), nullable=True),
        sa.Column('conflicts', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_template_links_slug_version', 'template_links', ['template_slug', 'template_version'], unique=False)
    op.create_index('idx_template_links_active', 'template_links', ['tenant_id', 'is_active'], unique=False)

    # Create prompt_templates table
    op.create_table('prompt_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('version', sa.String(length=20), nullable=False),
        sa.Column('schema', sa.JSON(), nullable=False),
        sa.Column('default_values', sa.JSON(), nullable=True),
        sa.Column('validation_rules', sa.JSON(), nullable=True),
        sa.Column('pattern_slugs', sa.JSON(), nullable=True),
        sa.Column('template_slugs', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index('idx_prompt_templates_slug', 'prompt_templates', ['slug'], unique=False)
    op.create_index('idx_prompt_templates_active', 'prompt_templates', ['tenant_id', 'is_active'], unique=False)

    # Create evaluation_cases table
    op.create_table('evaluation_cases',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('goal_text', sa.Text(), nullable=False),
        sa.Column('expected_patterns', sa.JSON(), nullable=True),
        sa.Column('expected_templates', sa.JSON(), nullable=True),
        sa.Column('assertions', sa.JSON(), nullable=False),
        sa.Column('min_score', sa.Integer(), nullable=True),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('last_run_results', sa.JSON(), nullable=True),
        sa.Column('pass_rate', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_evaluation_cases_category', 'evaluation_cases', ['tenant_id', 'category'], unique=False)
    op.create_index('idx_evaluation_cases_active', 'evaluation_cases', ['tenant_id', 'is_active'], unique=False)

    # Create plan_artifacts table
    op.create_table('plan_artifacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('artifact_type', sa.String(length=50), nullable=False),
        sa.Column('filename', sa.String(length=200), nullable=False),
        sa.Column('file_key', sa.String(length=500), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('content_type', sa.String(length=100), nullable=True),
        sa.Column('github_pr_url', sa.String(length=500), nullable=True),
        sa.Column('github_repo', sa.String(length=200), nullable=True),
        sa.Column('github_branch', sa.String(length=100), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['scaffold_sessions.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_plan_artifacts_session_type', 'plan_artifacts', ['session_id', 'artifact_type'], unique=False)
    op.create_index('idx_plan_artifacts_created', 'plan_artifacts', ['tenant_id', 'created_at'], unique=False)

    # Create scaffold_evaluations table
    op.create_table('scaffold_evaluations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('errors', sa.JSON(), nullable=True),
        sa.Column('execution_time', sa.Integer(), nullable=True),
        sa.Column('memory_usage', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['evaluation_cases.id'], ),
        sa.ForeignKeyConstraint(['plan_id'], ['scaffold_plans.id'], ),
        sa.ForeignKeyConstraint(['session_id'], ['scaffold_sessions.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_scaffold_evaluations_session', 'scaffold_evaluations', ['session_id'], unique=False)
    op.create_index('idx_scaffold_evaluations_status', 'scaffold_evaluations', ['tenant_id', 'status'], unique=False)
    op.create_index('idx_scaffold_evaluations_score', 'scaffold_evaluations', ['tenant_id', 'score'], unique=False)


def downgrade():
    op.drop_index('idx_scaffold_evaluations_score', table_name='scaffold_evaluations')
    op.drop_index('idx_scaffold_evaluations_status', table_name='scaffold_evaluations')
    op.drop_index('idx_scaffold_evaluations_session', table_name='scaffold_evaluations')
    op.drop_table('scaffold_evaluations')
    op.drop_index('idx_plan_artifacts_created', table_name='plan_artifacts')
    op.drop_index('idx_plan_artifacts_session_type', table_name='plan_artifacts')
    op.drop_table('plan_artifacts')
    op.drop_index('idx_evaluation_cases_active', table_name='evaluation_cases')
    op.drop_index('idx_evaluation_cases_category', table_name='evaluation_cases')
    op.drop_table('evaluation_cases')
    op.drop_index('idx_prompt_templates_active', table_name='prompt_templates')
    op.drop_index('idx_prompt_templates_slug', table_name='prompt_templates')
    op.drop_table('prompt_templates')
    op.drop_index('idx_template_links_active', table_name='template_links')
    op.drop_index('idx_template_links_slug_version', table_name='template_links')
    op.drop_table('template_links')
    op.drop_index('idx_pattern_library_active', table_name='pattern_library')
    op.drop_index('idx_pattern_library_tags', table_name='pattern_library')
    op.drop_index('idx_pattern_library_slug', table_name='pattern_library')
    op.drop_table('pattern_library')
    op.drop_index('idx_scaffold_plans_build_status', table_name='scaffold_plans')
    op.drop_index('idx_scaffold_plans_session_version', table_name='scaffold_plans')
    op.drop_table('scaffold_plans')
    op.drop_index('idx_scaffold_sessions_created', table_name='scaffold_sessions')
    op.drop_index('idx_scaffold_sessions_status', table_name='scaffold_sessions')
    op.drop_index('idx_scaffold_sessions_tenant_user', table_name='scaffold_sessions')
    op.drop_table('scaffold_sessions')
