"""merge heads

Revision ID: merge_heads
Revises: 4b58e5229031, 7398cfb33053, 842b710d82cf, 9200a4be8fbf, add_crm_lite_contacts, fa561e27aa80
Create Date: 2025-09-02T11:40:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'merge_heads'
down_revision = ('4b58e5229031', '7398cfb33053', '842b710d82cf', '9200a4be8fbf', 'add_crm_lite_contacts', 'fa561e27aa80')
branch_labels = None
depends_on = None

def upgrade():
    """Merge all heads - no schema changes needed"""
    pass

def downgrade():
    """Cannot downgrade merge"""
    pass
