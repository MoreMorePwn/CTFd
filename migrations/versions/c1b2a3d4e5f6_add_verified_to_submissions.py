"""Add verified to submissions

Revision ID: c1b2a3d4e5f6
Revises: 9d7f2b4c0a81
Create Date: 2026-07-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c1b2a3d4e5f6"
down_revision = "9d7f2b4c0a81"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "submissions",
        sa.Column(
            "verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade():
    op.drop_column("submissions", "verified")
