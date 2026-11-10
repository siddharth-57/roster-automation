"""add groups table and member group

Revision ID: a1f3c9e2b7d4
Revises: 7afe0478e290
Create Date: 2026-11-10 19:30:00

What this migration does:

1. Creates the "groups" table.
2. Creates one group for every group_number already used in "rosters",
   so existing rosters keep a matching group. Group "08" is always
   created, even if no roster uses it yet.
3. Adds "group_id" to "team_members", puts every existing member in
   group "08", then makes the column required.

No existing data is deleted or changed, apart from filling in group_id.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1f3c9e2b7d4"
down_revision: Union[str, Sequence[str], None] = "7afe0478e290"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEFAULT_GROUP_NUMBER = "08"


def upgrade() -> None:
    """Upgrade schema."""

    # --------------------------------------------------
    # 1. Groups table
    # --------------------------------------------------

    op.create_table(
        "groups",
        sa.Column("group_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("group_number", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("group_id"),
        sa.UniqueConstraint("group_number", name="uq_groups_group_number"),
    )

    # --------------------------------------------------
    # 2. One group per group_number already used by rosters,
    #    plus the default group "08".
    # --------------------------------------------------

    op.execute(
        """
        INSERT INTO groups (group_number, active)
        SELECT DISTINCT group_number, TRUE
        FROM rosters
        """
    )

    op.execute(
        f"""
        INSERT INTO groups (group_number, active)
        VALUES ('{DEFAULT_GROUP_NUMBER}', TRUE)
        ON CONFLICT (group_number) DO NOTHING
        """
    )

    # --------------------------------------------------
    # 3. team_members.group_id
    #    Add as optional, fill it, then make it required.
    # --------------------------------------------------

    op.add_column(
        "team_members",
        sa.Column("group_id", sa.Integer(), nullable=True),
    )

    op.execute(
        f"""
        UPDATE team_members
        SET group_id = (
            SELECT group_id
            FROM groups
            WHERE group_number = '{DEFAULT_GROUP_NUMBER}'
        )
        """
    )

    op.alter_column(
        "team_members",
        "group_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.create_foreign_key(
        "fk_team_members_group_id",
        "team_members",
        "groups",
        ["group_id"],
        ["group_id"],
    )

    op.create_index(
        "ix_team_members_group_id",
        "team_members",
        ["group_id"],
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(
        "ix_team_members_group_id",
        table_name="team_members",
    )

    op.drop_constraint(
        "fk_team_members_group_id",
        "team_members",
        type_="foreignkey",
    )

    op.drop_column("team_members", "group_id")

    op.drop_table("groups")