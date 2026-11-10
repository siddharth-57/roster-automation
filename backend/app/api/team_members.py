from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.group import Group
from app.models.team_member import TeamMember
from app.schemas.team_member import (
    TeamMemberCreate,
    TeamMemberMove,
    TeamMemberResponse,
)
from app.services.groups import (
    count_active_members,
    get_active_group_or_error,
    get_group_or_404,
    renumber_group,
)


router = APIRouter(
    prefix="/team-members",
    tags=["Team Members"],
)


# ------------------------------------------------------
# LIST ACTIVE MEMBERS
# ------------------------------------------------------

@router.get(
    "",
    response_model=list[TeamMemberResponse],
)
def get_team_members(
    group_number: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Active members, ordered by group and then position.
    ?group_number=08 returns only that group's members.
    """

    statement = (
        select(TeamMember)
        .join(Group, TeamMember.group_id == Group.group_id)
        .where(TeamMember.active.is_(True))
        .order_by(Group.group_number, TeamMember.display_order)
    )

    if group_number:
        group = get_group_or_404(db, group_number)
        statement = statement.where(TeamMember.group_id == group.group_id)

    return db.scalars(statement).all()


# ------------------------------------------------------
# ADD MEMBER
# ------------------------------------------------------

@router.post(
    "",
    response_model=TeamMemberResponse,
    status_code=201,
)
def create_team_member(
    member: TeamMemberCreate,
    db: Session = Depends(get_db),
):
    existing_member = db.get(
        TeamMember,
        member.employee_id,
    )

    if existing_member:
        raise HTTPException(
            status_code=400,
            detail="Employee ID already exists",
        )

    group = get_active_group_or_error(db, member.group_number)

    # New members go to the end of their group
    new_display_order = count_active_members(db, group.group_id) + 1

    new_member = TeamMember(
        employee_id=member.employee_id,
        name=member.name,
        active=True,
        display_order=new_display_order,
        group_id=group.group_id,
    )

    db.add(new_member)
    db.commit()
    db.refresh(new_member)

    return new_member


# ------------------------------------------------------
# MOVE MEMBER TO ANOTHER GROUP
# ------------------------------------------------------

@router.patch(
    "/{employee_id}/group",
    response_model=TeamMemberResponse,
)
def move_team_member(
    employee_id: str,
    move: TeamMemberMove,
    db: Session = Depends(get_db),
):
    """
    Move a member to another group. They go to the end of the new
    group, and the old group's positions close the gap.
    Rosters already saved stay under the old group.
    """

    employee_id = employee_id.strip().upper()

    member = db.get(TeamMember, employee_id)

    if not member:
        raise HTTPException(
            status_code=404,
            detail="Team member not found",
        )

    if not member.active:
        raise HTTPException(
            status_code=400,
            detail="Inactive members can't be moved.",
        )

    new_group = get_active_group_or_error(db, move.group_number)

    if new_group.group_id == member.group_id:
        raise HTTPException(
            status_code=400,
            detail=f"{member.name} is already in group {new_group.group_number}.",
        )

    old_group_id = member.group_id

    member.display_order = count_active_members(db, new_group.group_id) + 1
    member.group_id = new_group.group_id
    member.group = new_group

    db.flush()
    renumber_group(db, old_group_id)

    db.commit()
    db.refresh(member)

    return member


# ------------------------------------------------------
# DEACTIVATE MEMBER
# ------------------------------------------------------

@router.patch(
    "/{employee_id}/deactivate",
)
def deactivate_team_member(
    employee_id: str,
    db: Session = Depends(get_db),
):
    employee_id = employee_id.strip().upper()

    member = db.get(
        TeamMember,
        employee_id,
    )

    if not member:
        raise HTTPException(
            status_code=404,
            detail="Team member not found",
        )

    if not member.active:
        raise HTTPException(
            status_code=400,
            detail="Team member is already inactive",
        )

    member.active = False

    db.flush()

    # Close the gap in this member's group only
    renumber_group(db, member.group_id)

    db.commit()

    return {
        "message": "Team member deactivated"
    }