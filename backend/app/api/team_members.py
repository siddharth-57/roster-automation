from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.team_member import TeamMember
from app.schemas.team_member import (
    TeamMemberCreate,
    TeamMemberResponse,
)


router = APIRouter(
    prefix="/team-members",
    tags=["Team Members"],
)


@router.get(
    "",
    response_model=list[TeamMemberResponse],
)
def get_team_members(
    db: Session = Depends(get_db),
):
    statement = (
        select(TeamMember)
        .where(TeamMember.active.is_(True))
        .order_by(TeamMember.display_order)
    )

    return db.scalars(statement).all()


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

    active_members = db.scalars(
        select(TeamMember)
        .where(TeamMember.active.is_(True))
        .order_by(TeamMember.display_order)
    ).all()

    new_display_order = len(active_members) + 1

    new_member = TeamMember(
        employee_id=member.employee_id,
        name=member.name,
        active=True,
        display_order=new_display_order,
    )

    db.add(new_member)
    db.commit()
    db.refresh(new_member)

    return new_member


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

    active_members = db.scalars(
        select(TeamMember)
        .where(
            TeamMember.active.is_(True),
            TeamMember.employee_id != employee_id,
        )
        .order_by(TeamMember.display_order)
    ).all()

    for index, active_member in enumerate(
        active_members,
        start=1,
    ):
        active_member.display_order = index

    db.commit()

    return {
        "message": "Team member deactivated"
    }