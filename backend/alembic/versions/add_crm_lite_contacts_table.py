"""Add crm_lite_contacts table

Revision ID: add_crm_lite_contacts
Revises: e0ffd2e9987d
Create Date: 2025-09-02T10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_crm_lite_contacts'
down_revision = 'e0ffd2e9987d'
branch_labels = None
depends_on = None

def upgrade():
    """Create crm_lite_contacts table"""
    op.create_table('crm_lite_contacts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(64), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(64)),
        sa.Column('company', sa.String(255)),
        sa.Column('created_at', sa.DateTime),
        sa.Column('updated_at', sa.DateTime)
    )
    
    # Create indexes
    op.create_index('ix_crm_lite_contacts_tenant_id', 'crm_lite_contacts', ['tenant_id'])
    op.create_index('ix_crm_lite_contacts_email', 'crm_lite_contacts', ['email'])

def downgrade():
    """Drop crm_lite_contacts table"""
    op.drop_index('ix_crm_lite_contacts_email', 'crm_lite_contacts')
    op.drop_index('ix_crm_lite_contacts_tenant_id', 'crm_lite_contacts')
    op.drop_table('crm_lite_contacts')
