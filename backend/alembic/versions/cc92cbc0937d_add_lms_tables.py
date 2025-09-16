"""Add lms tables

Revision ID: cc92cbc0937d
Revises: 694e7cbf6b05
Create Date: 2025-09-01T21:39:56.133343

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'cc92cbc0937d'
down_revision = '694e7cbf6b05'
branch_labels = None
depends_on = None

def upgrade():
    """Create lms tables"""
    # TODO: Implement table creation based on features: ['courses', 'lessons', 'quizzes', 'progress']
    
    # Example table creation (customize based on actual features):

    op.create_table('courses',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('metadata', sa.JSON),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_courses_tenant_id', 'courses', ['tenant_id'])

    op.create_table('lessons',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('metadata', sa.JSON),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_lessons_tenant_id', 'lessons', ['tenant_id'])

    op.create_table('quizzes',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('metadata', sa.JSON),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_quizzes_tenant_id', 'quizzes', ['tenant_id'])

    op.create_table('progress',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('metadata', sa.JSON),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_progress_tenant_id', 'progress', ['tenant_id'])


def downgrade():
    """Drop lms tables"""
    # TODO: Implement table dropping

    op.drop_index('ix_courses_tenant_id', table_name='courses')
    op.drop_table('courses')

    op.drop_index('ix_lessons_tenant_id', table_name='lessons')
    op.drop_table('lessons')

    op.drop_index('ix_quizzes_tenant_id', table_name='quizzes')
    op.drop_table('quizzes')

    op.drop_index('ix_progress_tenant_id', table_name='progress')
    op.drop_table('progress')
