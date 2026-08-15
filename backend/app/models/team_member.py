from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TeamMember(Base):
    __tablename__ = "team_members"

    employee_id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        unique=True,
    )