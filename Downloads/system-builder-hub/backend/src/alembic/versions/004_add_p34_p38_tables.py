"""Add P34-P38 tables

Revision ID: 004
Revises: 003
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    # P34: Visual Builder & Multimodal System Design
    op.create_table('builder_projects',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('system_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_by', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('builder_canvases',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('layout_json', sa.String(), nullable=False),
        sa.Column('components_json', sa.String(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['builder_projects.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('builder_workflows',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('dsl_json', sa.String(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['builder_projects.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('builder_assets',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('uri', sa.String(), nullable=False),
        sa.Column('meta_json', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['builder_projects.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('ingest_results',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('ingest_type', sa.String(), nullable=False),
        sa.Column('file_type', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('transcript', sa.String(), nullable=True),
        sa.Column('intents', sa.String(), nullable=True),
        sa.Column('entities', sa.String(), nullable=True),
        sa.Column('requirements', sa.String(), nullable=True),
        sa.Column('metadata', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['builder_projects.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # P35: Collaboration & Design Versioning
    op.create_table('collaboration_sessions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('session_name', sa.String(), nullable=False),
        sa.Column('created_by', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('max_participants', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['builder_projects.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('session_participants',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('last_seen', sa.DateTime(), nullable=False),
        sa.Column('joined_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['collaboration_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('session_locks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('lock_type', sa.String(), nullable=False),
        sa.Column('resource_id', sa.String(), nullable=False),
        sa.Column('acquired_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['collaboration_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('design_branches',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('base_branch', sa.String(), nullable=True),
        sa.Column('head_commit', sa.String(), nullable=False),
        sa.Column('created_by', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('metadata', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['builder_projects.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('design_commits',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('branch_id', sa.String(), nullable=False),
        sa.Column('author_id', sa.String(), nullable=False),
        sa.Column('commit_type', sa.String(), nullable=False),
        sa.Column('diff_json', sa.String(), nullable=False),
        sa.Column('message', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['branch_id'], ['design_branches.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('design_reviews',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('branch_id', sa.String(), nullable=False),
        sa.Column('reviewer_id', sa.String(), nullable=False),
        sa.Column('state', sa.String(), nullable=False),
        sa.Column('comments', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['branch_id'], ['design_branches.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # P36: Data Refinery & Managed Data Layer
    op.create_table('datasets',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('version', sa.String(), nullable=False),
        sa.Column('schema_json', sa.String(), nullable=False),
        sa.Column('retention_days', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('dataset_runs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('dataset_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('source_uri', sa.String(), nullable=False),
        sa.Column('bytes_in', sa.Integer(), nullable=True),
        sa.Column('rows_in', sa.Integer(), nullable=True),
        sa.Column('rows_out', sa.Integer(), nullable=True),
        sa.Column('errors_json', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('quality_reports',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('dataset_id', sa.String(), nullable=False),
        sa.Column('run_id', sa.String(), nullable=False),
        sa.Column('metrics_json', sa.String(), nullable=False),
        sa.Column('violations_json', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ),
        sa.ForeignKeyConstraint(['run_id'], ['dataset_runs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('dataset_access_keys',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('dataset_id', sa.String(), nullable=False),
        sa.Column('key_hash', sa.String(), nullable=False),
        sa.Column('scope', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_hash')
    )
    
    # P37: ModelOps
    op.create_table('models',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('task', sa.String(), nullable=False),
        sa.Column('base_model', sa.String(), nullable=False),
        sa.Column('card_json', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('model_versions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('model_id', sa.String(), nullable=False),
        sa.Column('version', sa.String(), nullable=False),
        sa.Column('weights_uri', sa.String(), nullable=False),
        sa.Column('params_json', sa.String(), nullable=False),
        sa.Column('metrics_json', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('published', sa.Boolean(), nullable=True),
        sa.Column('metadata', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['model_id'], ['models.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('training_runs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('model_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('dataset_ids', sa.String(), nullable=False),
        sa.Column('hyperparams_json', sa.String(), nullable=False),
        sa.Column('logs_uri', sa.String(), nullable=True),
        sa.Column('cost_cents', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['model_id'], ['models.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('eval_results',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('model_version_id', sa.String(), nullable=False),
        sa.Column('suite', sa.String(), nullable=False),
        sa.Column('metrics_json', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['model_version_id'], ['model_versions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # P38: Sovereign Deploy
    op.create_table('appliance_nodes',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('capacity_json', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_heartbeat', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('appliance_deployments',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('system_id', sa.String(), nullable=False),
        sa.Column('version', sa.String(), nullable=False),
        sa.Column('target_node_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('logs_uri', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['target_node_id'], ['appliance_nodes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    # P38: Sovereign Deploy
    op.drop_table('appliance_deployments')
    op.drop_table('appliance_nodes')
    
    # P37: ModelOps
    op.drop_table('eval_results')
    op.drop_table('training_runs')
    op.drop_table('model_versions')
    op.drop_table('models')
    
    # P36: Data Refinery & Managed Data Layer
    op.drop_table('dataset_access_keys')
    op.drop_table('quality_reports')
    op.drop_table('dataset_runs')
    op.drop_table('datasets')
    
    # P35: Collaboration & Design Versioning
    op.drop_table('design_reviews')
    op.drop_table('design_commits')
    op.drop_table('design_branches')
    op.drop_table('session_locks')
    op.drop_table('session_participants')
    op.drop_table('collaboration_sessions')
    
    # P34: Visual Builder & Multimodal System Design
    op.drop_table('ingest_results')
    op.drop_table('builder_assets')
    op.drop_table('builder_workflows')
    op.drop_table('builder_canvases')
    op.drop_table('builder_projects')
