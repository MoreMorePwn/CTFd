"""Add anti-cheat events

Revision ID: d2e3f4a5b6c7
Revises: c1b2a3d4e5f6
Create Date: 2026-07-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d2e3f4a5b6c7"
down_revision = "c1b2a3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("submissions", sa.Column("user_agent", sa.Text(), nullable=True))
    op.add_column(
        "submissions", sa.Column("browser_fingerprint", sa.String(length=128), nullable=True)
    )
    op.add_column("tracking", sa.Column("user_agent", sa.Text(), nullable=True))
    op.add_column(
        "tracking", sa.Column("browser_fingerprint", sa.String(length=128), nullable=True)
    )

    op.create_table(
        "anti_cheat_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=80), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("team_id", sa.Integer(), nullable=True),
        sa.Column("challenge_id", sa.Integer(), nullable=True),
        sa.Column("submission_id", sa.Integer(), nullable=True),
        sa.Column("ip", sa.String(length=46), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("browser_fingerprint", sa.String(length=128), nullable=True),
        sa.Column(
            "reviewed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("reviewer_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["challenge_id"], ["challenges.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_anti_cheat_events_challenge_id", "anti_cheat_events", ["challenge_id"])
    op.create_index(
        "ix_anti_cheat_events_browser_fingerprint",
        "anti_cheat_events",
        ["browser_fingerprint"],
    )
    op.create_index("ix_anti_cheat_events_created", "anti_cheat_events", ["created"])
    op.create_index("ix_anti_cheat_events_ip", "anti_cheat_events", ["ip"])
    op.create_index("ix_anti_cheat_events_reviewed", "anti_cheat_events", ["reviewed"])
    op.create_index("ix_anti_cheat_events_severity", "anti_cheat_events", ["severity"])
    op.create_index("ix_anti_cheat_events_submission_id", "anti_cheat_events", ["submission_id"])
    op.create_index("ix_anti_cheat_events_team_id", "anti_cheat_events", ["team_id"])
    op.create_index("ix_anti_cheat_events_type", "anti_cheat_events", ["type"])
    op.create_index("ix_anti_cheat_events_user_id", "anti_cheat_events", ["user_id"])


def downgrade():
    op.drop_index("ix_anti_cheat_events_user_id", table_name="anti_cheat_events")
    op.drop_index("ix_anti_cheat_events_type", table_name="anti_cheat_events")
    op.drop_index("ix_anti_cheat_events_team_id", table_name="anti_cheat_events")
    op.drop_index("ix_anti_cheat_events_submission_id", table_name="anti_cheat_events")
    op.drop_index("ix_anti_cheat_events_severity", table_name="anti_cheat_events")
    op.drop_index("ix_anti_cheat_events_reviewed", table_name="anti_cheat_events")
    op.drop_index("ix_anti_cheat_events_ip", table_name="anti_cheat_events")
    op.drop_index("ix_anti_cheat_events_created", table_name="anti_cheat_events")
    op.drop_index("ix_anti_cheat_events_browser_fingerprint", table_name="anti_cheat_events")
    op.drop_index("ix_anti_cheat_events_challenge_id", table_name="anti_cheat_events")
    op.drop_table("anti_cheat_events")

    op.drop_column("tracking", "browser_fingerprint")
    op.drop_column("tracking", "user_agent")
    op.drop_column("submissions", "browser_fingerprint")
    op.drop_column("submissions", "user_agent")
