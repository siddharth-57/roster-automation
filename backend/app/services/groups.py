# Shared group helpers used by the groups, team members and roster APIs.

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.group import Group
from app.models.team_member import TeamMember


def get_group_or_404(
    db: Session,
    group_number: str,
) -> Group:
    group = db.scalar(
        select(Group).where(
            Group.group_number == group_number.strip()
        )
    )

    if not group:
        raise HTTPException(
            status_code=404,
            detail=f"Group '{group_number.strip()}' does not exist.",
        )

    return group


def get_active_group_or_error(
    db: Session,
    group_number: str,
) -> Group:
    group = get_group_or_404(db, group_number)

    if not group.active:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Group '{group.group_number}' is inactive. "
                f"Activate it first."
            ),
        )

    return group


def count_active_members(
    db: Session,
    group_id: int,
) -> int:
    return db.scalar(
        select(func.count())
        .select_from(TeamMember)
        .where(
            TeamMember.group_id == group_id,
            TeamMember.active.is_(True),
        )
    )


def renumber_group(
    db: Session,
    group_id: int,
) -> None:
    """Give the group's active members positions 1, 2, 3, ... in their current order."""

    members = db.scalars(
        select(TeamMember)
        .where(
            TeamMember.group_id == group_id,
            TeamMember.active.is_(True),
        )
        .order_by(TeamMember.display_order)
    ).all()

    for position, member in enumerate(members, start=1):
        member.display_order = position


def validate_members_belong_to_group(
    db: Session,
    group: Group,
    employee_ids: list[str],
) -> None:
    """
    Every employee in a roster request must exist, be active,
    and belong to the roster's group.
    """

    members = db.scalars(
        select(TeamMember).where(
            TeamMember.employee_id.in_(employee_ids)
        )
    ).all()

    found = {member.employee_id: member for member in members}

    unknown = [
        employee_id
        for employee_id in employee_ids
        if employee_id not in found
    ]

    if unknown:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unknown employee ID(s): "
                + ", ".join(unknown)
                + "."
            ),
        )

    other_group = [
        f"{member.name} ({member.group_number})"
        for member in members
        if member.group_id != group.group_id
    ]

    if other_group:
        raise HTTPException(
            status_code=400,
            detail=(
                f"These members are not in group "
                f"{group.group_number}: "
                + ", ".join(other_group)
                + "."
            ),
        )

    inactive = [
        member.name
        for member in members
        if not member.active
    ]

    if inactive:
        raise HTTPException(
            status_code=400,
            detail=(
                "These members are inactive: "
                + ", ".join(inactive)
                + "."
            ),
        )