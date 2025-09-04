"""Create collaboration tables (comments, saved views, approvals, activity feeds, search index)

Revision ID: 007
Revises: 006
Create Date: 2024-01-15 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None

def upgrade():
    # Create comments table
    op.create_table('comments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('entity_type', sa.String(), nullable=False),
        sa.Column('entity_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('mentions', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('reactions', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_edited', sa.Boolean(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_comments_tenant_id'), 'comments', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_comments_entity_id'), 'comments', ['entity_id'], unique=False)
    op.create_index(op.f('ix_comments_user_id'), 'comments', ['user_id'], unique=False)

    # Create saved_views table
    op.create_table('saved_views',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('entity_type', sa.String(), nullable=False),
        sa.Column('filters_json', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('columns', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('sort', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_shared', sa.Boolean(), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_saved_views_tenant_id'), 'saved_views', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_saved_views_user_id'), 'saved_views', ['user_id'], unique=False)

    # Create approvals table
    op.create_table('approvals',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('entity_type', sa.String(), nullable=False),
        sa.Column('entity_id', sa.String(), nullable=False),
        sa.Column('action_type', sa.String(), nullable=False),
        sa.Column('requested_by', sa.String(), nullable=False),
        sa.Column('approver_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_approvals_tenant_id'), 'approvals', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_approvals_entity_id'), 'approvals', ['entity_id'], unique=False)
    op.create_index(op.f('ix_approvals_requested_by'), 'approvals', ['requested_by'], unique=False)
    op.create_index(op.f('ix_approvals_approver_id'), 'approvals', ['approver_id'], unique=False)

    # Create activity_feeds table
    op.create_table('activity_feeds',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('entity_type', sa.String(), nullable=False),
        sa.Column('entity_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('action_type', sa.String(), nullable=False),
        sa.Column('action_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('icon', sa.String(), nullable=True),
        sa.Column('link', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_activity_feeds_tenant_id'), 'activity_feeds', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_activity_feeds_entity_type'), 'activity_feeds', ['entity_type'], unique=False)
    op.create_index(op.f('ix_activity_feeds_entity_id'), 'activity_feeds', ['entity_id'], unique=False)
    op.create_index(op.f('ix_activity_feeds_user_id'), 'activity_feeds', ['user_id'], unique=False)
    op.create_index(op.f('ix_activity_feeds_created_at'), 'activity_feeds', ['created_at'], unique=False)

    # Create search_index table
    op.create_table('search_index',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('entity_type', sa.String(), nullable=False),
        sa.Column('entity_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_search_index_tenant_id'), 'search_index', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_search_index_entity_type'), 'search_index', ['entity_type'], unique=False)
    op.create_index(op.f('ix_search_index_entity_id'), 'search_index', ['entity_id'], unique=False)

    # Create GIN index for full-text search
    op.execute('CREATE INDEX ix_search_index_search_vector ON search_index USING GIN (search_vector)')

def downgrade():
    op.drop_index(op.f('ix_search_index_search_vector'), table_name='search_index')
    op.drop_index(op.f('ix_search_index_entity_id'), table_name='search_index')
    op.drop_index(op.f('ix_search_index_entity_type'), table_name='search_index')
    op.drop_index(op.f('ix_search_index_tenant_id'), table_name='search_index')
    op.drop_table('search_index')
    op.drop_index(op.f('ix_activity_feeds_created_at'), table_name='activity_feeds')
    op.drop_index(op.f('ix_activity_feeds_user_id'), table_name='activity_feeds')
    op.drop_index(op.f('ix_activity_feeds_entity_id'), table_name='activity_feeds')
    op.drop_index(op.f('ix_activity_feeds_entity_type'), table_name='activity_feeds')
    op.drop_index(op.f('ix_activity_feeds_tenant_id'), table_name='activity_feeds')
    op.drop_table('activity_feeds')
    op.drop_index(op.f('ix_approvals_approver_id'), table_name='approvals')
    op.drop_index(op.f('ix_approvals_requested_by'), table_name='approvals')
    op.drop_index(op.f('ix_approvals_entity_id'), table_name='approvals')
    op.drop_index(op.f('ix_approvals_tenant_id'), table_name='approvals')
    op.drop_table('approvals')
    op.drop_index(op.f('ix_saved_views_user_id'), table_name='saved_views')
    op.drop_index(op.f('ix_saved_views_tenant_id'), table_name='saved_views')
    op.drop_table('saved_views')
    op.drop_index(op.f('ix_comments_user_id'), table_name='comments')
    op.drop_index(op.f('ix_comments_entity_id'), table_name='comments')
    op.drop_index(op.f('ix_comments_tenant_id'), table_name='comments')
    op.drop_table('comments')
