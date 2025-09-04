"""Create onboarding tables

Revision ID: 005
Revises: 004
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None

def upgrade():
    # Create onboarding_sessions table
    op.create_table('onboarding_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('step', sa.String(), nullable=True),
        sa.Column('company_name', sa.String(), nullable=True),
        sa.Column('brand_color', sa.String(), nullable=True),
        sa.Column('invited_users', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('selected_plan', sa.String(), nullable=True),
        sa.Column('import_data_type', sa.String(), nullable=True),
        sa.Column('completed', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_onboarding_sessions_tenant_id'), 'onboarding_sessions', ['tenant_id'], unique=False)

    # Create onboarding_invitations table
    op.create_table('onboarding_invitations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('token', sa.String(), nullable=False),
        sa.Column('accepted', sa.Boolean(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_onboarding_invitations_tenant_id'), 'onboarding_invitations', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_onboarding_invitations_token'), 'onboarding_invitations', ['token'], unique=True)

def downgrade():
    op.drop_index(op.f('ix_onboarding_invitations_token'), table_name='onboarding_invitations')
    op.drop_index(op.f('ix_onboarding_invitations_tenant_id'), table_name='onboarding_invitations')
    op.drop_table('onboarding_invitations')
    op.drop_index(op.f('ix_onboarding_sessions_tenant_id'), table_name='onboarding_sessions')
    op.drop_table('onboarding_sessions')
