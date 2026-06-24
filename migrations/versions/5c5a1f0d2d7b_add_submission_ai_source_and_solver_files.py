"""Add submission AI source and solver files

Revision ID: 5c5a1f0d2d7b
Revises: 48d8250d19bd
Create Date: 2026-06-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "5c5a1f0d2d7b"
down_revision = "48d8250d19bd"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "challenges",
        sa.Column(
            "require_ai_source",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "challenges",
        sa.Column(
            "require_solver",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column("submissions", sa.Column("ai_source", sa.Text(), nullable=True))
    op.add_column(
        "files",
        sa.Column("submission_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_files_submission_id_submissions",
        "files",
        "submissions",
        ["submission_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade():
    op.drop_constraint(
        "fk_files_submission_id_submissions", "files", type_="foreignkey"
    )
    op.drop_column("files", "submission_id")
    op.drop_column("submissions", "ai_source")
    op.drop_column("challenges", "require_solver")
    op.drop_column("challenges", "require_ai_source")
