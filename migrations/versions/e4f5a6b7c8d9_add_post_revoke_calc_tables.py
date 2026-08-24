"""Add post-revoke calculation tables

Revision ID: e4f5a6b7c8d9
Revises: d2e3f4a5b6c7
Create Date: 2026-08-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e4f5a6b7c8d9"
down_revision = "d2e3f4a5b6c7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "post_revoke_calc_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_type", sa.String(length=16), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column(
            "manual_banned",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("updated", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_type", "account_id"),
    )
    op.create_index(
        "ix_post_revoke_calc_accounts_lookup",
        "post_revoke_calc_accounts",
        ["account_type", "account_id"],
    )

    op.create_table(
        "post_revoke_calc_solves",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("solve_id", sa.Integer(), nullable=False),
        sa.Column(
            "percentage",
            sa.Float(),
            nullable=False,
            server_default="100",
        ),
        sa.Column(
            "revoked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("updated", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["solve_id"], ["solves.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("solve_id"),
    )
    op.create_index(
        "ix_post_revoke_calc_solves_solve_id",
        "post_revoke_calc_solves",
        ["solve_id"],
    )

    op.create_table(
        "post_revoke_calc_awards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("award_id", sa.Integer(), nullable=False),
        sa.Column(
            "percentage",
            sa.Float(),
            nullable=False,
            server_default="100",
        ),
        sa.Column(
            "revoked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("updated", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["award_id"], ["awards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("award_id"),
    )
    op.create_index(
        "ix_post_revoke_calc_awards_award_id",
        "post_revoke_calc_awards",
        ["award_id"],
    )


def downgrade():
    op.drop_index(
        "ix_post_revoke_calc_awards_award_id",
        table_name="post_revoke_calc_awards",
    )
    op.drop_table("post_revoke_calc_awards")

    op.drop_index(
        "ix_post_revoke_calc_solves_solve_id",
        table_name="post_revoke_calc_solves",
    )
    op.drop_table("post_revoke_calc_solves")

    op.drop_index(
        "ix_post_revoke_calc_accounts_lookup",
        table_name="post_revoke_calc_accounts",
    )
    op.drop_table("post_revoke_calc_accounts")
