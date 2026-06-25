"""Add assistant permissions to users

Revision ID: 9d7f2b4c0a81
Revises: 5c5a1f0d2d7b
Create Date: 2026-06-25 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9d7f2b4c0a81"
down_revision = "5c5a1f0d2d7b"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("assistant_permissions", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("users", "assistant_permissions")
