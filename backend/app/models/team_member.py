from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Imported so the "groups" table is registered before team_members
# refers to it (SQLAlchemy needs it when saving members).
from app.models.group import Group


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

    # Position within the member's group (1, 2, 3, ...)
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Each member belongs to exactly one group
    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.group_id"),
        nullable=False,
        index=True,
    )

    # Loaded together with the member, so group_number is always available
    group: Mapped[Group] = relationship(lazy="joined")

    @property
    def group_number(self) -> str:
        return self.group.group_number