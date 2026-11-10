from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Group(Base):
    """
    A roster group, e.g. "08".

    group_number is fixed once created: rosters and Excel files refer
    to it (roster name "2026-09-Group-08", Excel cell A1 "Group = 08").
    name is an optional display name the TL can change freely.
    """

    __tablename__ = "groups"

    group_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    group_number: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        unique=True,
    )

    name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )