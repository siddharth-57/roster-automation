"""allow multiple roster groups per month

Revision ID: 7afe0478e290
Revises: d7a1b24c255b
Create Date: 2026-08-26 18:44:19.283778

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7afe0478e290'
down_revision: Union[str, Sequence[str], None] = 'd7a1b24c255b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.drop_constraint(
        "uq_roster_year_month",
        "rosters",
        type_="unique",
    )

    op.create_unique_constraint(
        "uq_roster_year_month_group",
        "rosters",
        [
            "year",
            "month",
            "group_number",
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_constraint(
        "uq_roster_year_month_group",
        "rosters",
        type_="unique",
    )

    op.create_unique_constraint(
        "uq_roster_year_month",
        "rosters",
        [
            "year",
            "month",
        ],
    )
