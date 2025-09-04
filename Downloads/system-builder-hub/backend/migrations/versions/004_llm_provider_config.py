"""LLM Provider Configuration

Revision ID: 004_llm_provider_config
Revises: 003_p61_p65_tables
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlite3
import json
import uuid
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '004_llm_provider_config'
down_revision = '003_p61_p65_tables'
branch_labels = None
depends_on = None

def upgrade():
    """Upgrade to add LLM provider configuration tables"""
    
    # Create llm_provider_configs table
    op.create_table('llm_provider_configs',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('tenant_id', sa.Text(), nullable=False),
        sa.Column('provider', sa.Text(), nullable=False),  # openai, anthropic, groq, local
        sa.Column('api_key_encrypted', sa.Text(), nullable=False),
        sa.Column('default_model', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('last_tested', sa.TIMESTAMP(), nullable=True),
        sa.Column('test_latency_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('metadata', sa.Text(), nullable=True),  # JSON for additional config
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indices
    op.create_index('idx_llm_provider_configs_tenant_id', 'llm_provider_configs', ['tenant_id'])
    op.create_index('idx_llm_provider_configs_provider', 'llm_provider_configs', ['provider'])
    op.create_index('idx_llm_provider_configs_active', 'llm_provider_configs', ['is_active'])
    
    # Create llm_usage_logs table for tracking API calls
    op.create_table('llm_usage_logs',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('tenant_id', sa.Text(), nullable=False),
        sa.Column('provider_config_id', sa.Text(), nullable=False),
        sa.Column('provider', sa.Text(), nullable=False),
        sa.Column('model', sa.Text(), nullable=False),
        sa.Column('endpoint', sa.Text(), nullable=False),  # chat, completion, embedding
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('metadata', sa.Text(), nullable=True),  # JSON for request/response details
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indices for usage logs
    op.create_index('idx_llm_usage_logs_tenant_id', 'llm_usage_logs', ['tenant_id'])
    op.create_index('idx_llm_usage_logs_provider', 'llm_usage_logs', ['provider'])
    op.create_index('idx_llm_usage_logs_created_at', 'llm_usage_logs', ['created_at'])
    op.create_index('idx_llm_usage_logs_success', 'llm_usage_logs', ['success'])

def downgrade():
    """Downgrade to remove LLM provider configuration tables"""
    
    # Drop indices
    op.drop_index('idx_llm_usage_logs_success', 'llm_usage_logs')
    op.drop_index('idx_llm_usage_logs_created_at', 'llm_usage_logs')
    op.drop_index('idx_llm_usage_logs_provider', 'llm_usage_logs')
    op.drop_index('idx_llm_usage_logs_tenant_id', 'llm_usage_logs')
    op.drop_index('idx_llm_provider_configs_active', 'llm_provider_configs')
    op.drop_index('idx_llm_provider_configs_provider', 'llm_provider_configs')
    op.drop_index('idx_llm_provider_configs_tenant_id', 'llm_provider_configs')
    
    # Drop tables
    op.drop_table('llm_usage_logs')
    op.drop_table('llm_provider_configs')
