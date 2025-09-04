"""merge_heads

Revision ID: fba15934b27a
Revises: 175f8c1c6302, c99cb5bd07b3, cc92cbc0937d
Create Date: 2025-09-01 16:11:39.152565

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fba15934b27a'
down_revision = ('175f8c1c6302', 'c99cb5bd07b3', 'cc92cbc0937d')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
