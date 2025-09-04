"""Add marketplace and templates support

Revision ID: 0006
Revises: 0005
Create Date: 2024-01-15 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create templates table
    op.create_table('templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('slug', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('short_desc', sa.Text, nullable=True),
        sa.Column('long_desc', sa.Text, nullable=True),
        sa.Column('category', sa.String(100), nullable=False, index=True),
        sa.Column('tags', postgresql.JSONB, nullable=True),
        sa.Column('price_cents', sa.Integer, nullable=True),
        sa.Column('requires_plan', sa.String(50), nullable=True),
        sa.Column('author_user_id', sa.String(255), nullable=False),
        sa.Column('is_public', sa.Boolean, nullable=False, default=False, index=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Index('idx_templates_category_public', 'category', 'is_public'),
        sa.Index('idx_templates_author', 'author_user_id')
    )

    # Create template_variants table
    op.create_table('template_variants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('templates.id'), nullable=False),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('default', sa.Boolean, nullable=False, default=False),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Index('idx_template_variants_template_id', 'template_id'),
        sa.Index('idx_template_variants_default', 'default')
    )

    # Create template_assets table
    op.create_table('template_assets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('templates.id'), nullable=False),
        sa.Column('cover_image_url', sa.Text, nullable=True),
        sa.Column('gallery', postgresql.JSONB, nullable=True),
        sa.Column('sample_screens', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Index('idx_template_assets_template_id', 'template_id')
    )

    # Create template_guided_schemas table
    op.create_table('template_guided_schemas',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('templates.id'), nullable=False),
        sa.Column('schema', postgresql.JSONB, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Index('idx_template_guided_schemas_template_id', 'template_id')
    )

    # Create template_builder_states table
    op.create_table('template_builder_states',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('templates.id'), nullable=False),
        sa.Column('variant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('template_variants.id'), nullable=True),
        sa.Column('builder_state', postgresql.JSONB, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Index('idx_template_builder_states_template_id', 'template_id'),
        sa.Index('idx_template_builder_states_variant_id', 'variant_id')
    )


def downgrade() -> None:
    op.drop_table('template_builder_states')
    op.drop_table('template_guided_schemas')
    op.drop_table('template_assets')
    op.drop_table('template_variants')
    op.drop_table('templates')
