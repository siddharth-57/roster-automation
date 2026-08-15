from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Roster(Base):
    __tablename__ = "rosters"

    roster_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    roster_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
    )

    year: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    month: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    group_number: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "year",
            "month",
            name="uq_roster_year_month",
        ),
    )