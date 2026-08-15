from datetime import date

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RosterAssignment(Base):
    __tablename__ = "roster_assignments"

    roster_id: Mapped[int] = mapped_column(
        ForeignKey("rosters.roster_id"),
        primary_key=True,
    )

    employee_id: Mapped[str] = mapped_column(
        ForeignKey("team_members.employee_id"),
        primary_key=True,
    )

    date: Mapped[date] = mapped_column(
        Date,
        primary_key=True,
    )

    shift: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
    )