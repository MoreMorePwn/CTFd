"""Add announcer bot logs

Revision ID: a9b8c7d6e5f4
Revises: f6a7b8c9d0e1
Create Date: 2026-09-02 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a9b8c7d6e5f4"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "announcer_bot_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("account_name", sa.Text(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("team_id", sa.Integer(), nullable=True),
        sa.Column("challenge_id", sa.Integer(), nullable=True),
        sa.Column("challenge_name", sa.Text(), nullable=True),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["challenge_id"], ["challenges.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_announcer_bot_logs_created", "announcer_bot_logs", ["created"]
    )
    op.create_index(
        "ix_announcer_bot_logs_event_type", "announcer_bot_logs", ["event_type"]
    )


def downgrade():
    op.drop_index("ix_announcer_bot_logs_event_type", table_name="announcer_bot_logs")
    op.drop_index("ix_announcer_bot_logs_created", table_name="announcer_bot_logs")
    op.drop_table("announcer_bot_logs")
