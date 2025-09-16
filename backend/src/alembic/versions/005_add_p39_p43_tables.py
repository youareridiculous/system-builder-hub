"""Add P39-P43 tables
Revision ID: 005
Revises: 004
Create Date: 2024-01-01 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None

def upgrade():
    # P39: GTM Engine tables
    op.create_table('gtm_plans',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('system_id', sa.String(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('summary_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('gtm_assets',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('plan_id', sa.String(), nullable=False),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('content_md', sa.Text(), nullable=False),
        sa.Column('meta_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['plan_id'], ['gtm_plans.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('gtm_metrics',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('plan_id', sa.String(), nullable=False),
        sa.Column('kpi', sa.String(), nullable=False),
        sa.Column('value', sa.Numeric(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['plan_id'], ['gtm_plans.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # P40: Investor Pack Generator tables
    op.create_table('investor_packs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('system_id', sa.String(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('summary_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('financial_models',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('pack_id', sa.String(), nullable=False),
        sa.Column('model_type', sa.String(), nullable=False),
        sa.Column('assumptions_json', sa.Text(), nullable=False),
        sa.Column('projections_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['pack_id'], ['investor_packs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # P41: Growth AI Agent tables
    op.create_table('experiments',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('system_id', sa.String(), nullable=False),
        sa.Column('hypothesis', sa.Text(), nullable=False),
        sa.Column('variant_json', sa.Text(), nullable=False),
        sa.Column('kpi', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('experiment_results',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('experiment_id', sa.String(), nullable=False),
        sa.Column('metrics_json', sa.Text(), nullable=False),
        sa.Column('winner', sa.String(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['experiment_id'], ['experiments.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # P42: Conversational Builder tables
    op.create_table('builder_sessions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('system_id', sa.String(), nullable=True),
        sa.Column('transcript_md', sa.Text(), nullable=False),
        sa.Column('decisions_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('session_utterances',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('utterance_type', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['builder_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # P43: Context Ingest tables
    op.create_table('context_artifacts',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('uri', sa.String(), nullable=False),
        sa.Column('summary_md', sa.Text(), nullable=False),
        sa.Column('derived_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indices for better performance
    op.create_index('idx_gtm_plans_tenant_system', 'gtm_plans', ['tenant_id', 'system_id'])
    op.create_index('idx_gtm_assets_plan_id', 'gtm_assets', ['plan_id'])
    op.create_index('idx_gtm_metrics_plan_id', 'gtm_metrics', ['plan_id'])
    op.create_index('idx_investor_packs_tenant_system', 'investor_packs', ['tenant_id', 'system_id'])
    op.create_index('idx_financial_models_pack_id', 'financial_models', ['pack_id'])
    op.create_index('idx_experiments_system_id', 'experiments', ['system_id'])
    op.create_index('idx_experiment_results_experiment_id', 'experiment_results', ['experiment_id'])
    op.create_index('idx_builder_sessions_tenant_id', 'builder_sessions', ['tenant_id'])
    op.create_index('idx_session_utterances_session_id', 'session_utterances', ['session_id'])
    op.create_index('idx_context_artifacts_project_id', 'context_artifacts', ['project_id'])

def downgrade():
    # Drop indices
    op.drop_index('idx_context_artifacts_project_id')
    op.drop_index('idx_session_utterances_session_id')
    op.drop_index('idx_builder_sessions_tenant_id')
    op.drop_index('idx_experiment_results_experiment_id')
    op.drop_index('idx_experiments_system_id')
    op.drop_index('idx_financial_models_pack_id')
    op.drop_index('idx_investor_packs_tenant_system')
    op.drop_index('idx_gtm_metrics_plan_id')
    op.drop_index('idx_gtm_assets_plan_id')
    op.drop_index('idx_gtm_plans_tenant_system')
    
    # Drop tables
    op.drop_table('context_artifacts')
    op.drop_table('session_utterances')
    op.drop_table('builder_sessions')
    op.drop_table('experiment_results')
    op.drop_table('experiments')
    op.drop_table('financial_models')
    op.drop_table('investor_packs')
    op.drop_table('gtm_metrics')
    op.drop_table('gtm_assets')
    op.drop_table('gtm_plans')
