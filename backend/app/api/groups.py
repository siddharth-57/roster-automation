from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.group import Group
from app.models.team_member import TeamMember
from app.schemas.group import (
    GroupCreate,
    GroupResponse,
    GroupUpdate,
)
from app.services.groups import (
    count_active_members,
    get_group_or_404,
)


router = APIRouter(
    prefix="/groups",
    tags=["Groups"],
)


def to_response(
    group: Group,
    active_member_count: int,
) -> GroupResponse:
    return GroupResponse(
        group_id=group.group_id,
        group_number=group.group_number,
        name=group.name,
        active=group.active,
        active_member_count=active_member_count,
    )


# ------------------------------------------------------
# LIST GROUPS
# ------------------------------------------------------

@router.get(
    "",
    response_model=list[GroupResponse],
)
def list_groups(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
):
    """
    Active groups only by default (for dropdowns).
    ?include_inactive=true also returns deactivated groups
    (for the group management screen).
    """

    statement = select(Group).order_by(Group.group_number)

    if not include_inactive:
        statement = statement.where(Group.active.is_(True))

    groups = db.scalars(statement).all()

    counts = dict(
        db.execute(
            select(TeamMember.group_id, func.count())
            .where(TeamMember.active.is_(True))
            .group_by(TeamMember.group_id)
        ).all()
    )

    return [
        to_response(group, counts.get(group.group_id, 0))
        for group in groups
    ]


# ------------------------------------------------------
# CREATE GROUP
# ------------------------------------------------------

@router.post(
    "",
    response_model=GroupResponse,
    status_code=201,
)
def create_group(
    group: GroupCreate,
    db: Session = Depends(get_db),
):
    existing = db.scalar(
        select(Group).where(
            Group.group_number == group.group_number
        )
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Group '{group.group_number}' already exists.",
        )

    new_group = Group(
        group_number=group.group_number,
        name=group.name,
        active=True,
    )

    db.add(new_group)
    db.commit()
    db.refresh(new_group)

    return to_response(new_group, 0)


# ------------------------------------------------------
# RENAME GROUP (display name only)
# ------------------------------------------------------

@router.patch(
    "/{group_number}",
    response_model=GroupResponse,
)
def rename_group(
    group_number: str,
    update: GroupUpdate,
    db: Session = Depends(get_db),
):
    group = get_group_or_404(db, group_number)

    group.name = update.name

    db.commit()
    db.refresh(group)

    return to_response(
        group,
        count_active_members(db, group.group_id),
    )


# ------------------------------------------------------
# DEACTIVATE / ACTIVATE GROUP
# ------------------------------------------------------

@router.patch(
    "/{group_number}/deactivate",
    response_model=GroupResponse,
)
def deactivate_group(
    group_number: str,
    db: Session = Depends(get_db),
):
    """
    Hide a group from dropdowns. Its rosters are kept.
    Blocked while the group still has active members.
    """

    group = get_group_or_404(db, group_number)

    if not group.active:
        raise HTTPException(
            status_code=400,
            detail=f"Group '{group.group_number}' is already inactive.",
        )

    active_members = count_active_members(db, group.group_id)

    if active_members:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Group '{group.group_number}' still has "
                f"{active_members} active member(s). Move them to "
                f"another group or deactivate them first."
            ),
        )

    group.active = False

    db.commit()
    db.refresh(group)

    return to_response(group, 0)


@router.patch(
    "/{group_number}/activate",
    response_model=GroupResponse,
)
def activate_group(
    group_number: str,
    db: Session = Depends(get_db),
):
    group = get_group_or_404(db, group_number)

    if group.active:
        raise HTTPException(
            status_code=400,
            detail=f"Group '{group.group_number}' is already active.",
        )

    group.active = True

    db.commit()
    db.refresh(group)

    return to_response(
        group,
        count_active_members(db, group.group_id),
    )