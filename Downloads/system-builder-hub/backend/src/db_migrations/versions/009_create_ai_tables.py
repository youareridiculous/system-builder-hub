"""Create AI tables (conversations, messages, reports, embeddings, voice sessions, config)

Revision ID: 009
Revises: 008
Create Date: 2024-01-15 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None

def upgrade():
    # Create ai_conversations table
    op.create_table('ai_conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('agent', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('is_pinned', sa.Boolean(), nullable=True),
        sa.Column('last_message_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_conversations_tenant_id'), 'ai_conversations', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_ai_conversations_user_id'), 'ai_conversations', ['user_id'], unique=False)

    # Create ai_messages table
    op.create_table('ai_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tool_calls', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('tokens_in', sa.Integer(), nullable=True),
        sa.Column('tokens_out', sa.Integer(), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_messages_conversation_id'), 'ai_messages', ['conversation_id'], unique=False)

    # Create ai_reports table
    op.create_table('ai_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('params', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('file_key', sa.String(), nullable=True),
        sa.Column('file_url', sa.String(), nullable=True),
        sa.Column('scheduled_cron', sa.String(), nullable=True),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('next_run_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_reports_tenant_id'), 'ai_reports', ['tenant_id'], unique=False)

    # Create ai_embeddings table
    op.create_table('ai_embeddings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('source_type', sa.String(), nullable=False),
        sa.Column('source_id', sa.String(), nullable=False),
        sa.Column('chunk_id', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('vector', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('meta', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_embeddings_tenant_id'), 'ai_embeddings', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_ai_embeddings_source_id'), 'ai_embeddings', ['source_id'], unique=False)

    # Create ai_voice_sessions table
    op.create_table('ai_voice_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('audio_file_key', sa.String(), nullable=True),
        sa.Column('transcript', sa.Text(), nullable=True),
        sa.Column('intent', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('actions', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_voice_sessions_tenant_id'), 'ai_voice_sessions', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_ai_voice_sessions_user_id'), 'ai_voice_sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_ai_voice_sessions_session_id'), 'ai_voice_sessions', ['session_id'], unique=True)

    # Create ai_configs table
    op.create_table('ai_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('rag_enabled', sa.Boolean(), nullable=True),
        sa.Column('voice_enabled', sa.Boolean(), nullable=True),
        sa.Column('copilot_enabled', sa.Boolean(), nullable=True),
        sa.Column('analytics_enabled', sa.Boolean(), nullable=True),
        sa.Column('reports_enabled', sa.Boolean(), nullable=True),
        sa.Column('rate_limits', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('model_config', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_configs_tenant_id'), 'ai_configs', ['tenant_id'], unique=True)

def downgrade():
    op.drop_index(op.f('ix_ai_configs_tenant_id'), table_name='ai_configs')
    op.drop_table('ai_configs')
    op.drop_index(op.f('ix_ai_voice_sessions_session_id'), table_name='ai_voice_sessions')
    op.drop_index(op.f('ix_ai_voice_sessions_user_id'), table_name='ai_voice_sessions')
    op.drop_index(op.f('ix_ai_voice_sessions_tenant_id'), table_name='ai_voice_sessions')
    op.drop_table('ai_voice_sessions')
    op.drop_index(op.f('ix_ai_embeddings_source_id'), table_name='ai_embeddings')
    op.drop_index(op.f('ix_ai_embeddings_tenant_id'), table_name='ai_embeddings')
    op.drop_table('ai_embeddings')
    op.drop_index(op.f('ix_ai_reports_tenant_id'), table_name='ai_reports')
    op.drop_table('ai_reports')
    op.drop_index(op.f('ix_ai_messages_conversation_id'), table_name='ai_messages')
    op.drop_table('ai_messages')
    op.drop_index(op.f('ix_ai_conversations_user_id'), table_name='ai_conversations')
    op.drop_index(op.f('ix_ai_conversations_tenant_id'), table_name='ai_conversations')
    op.drop_table('ai_conversations')
