from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.schemas.roster import RosterGenerationRequest
from app.services.roster_validation import validate_roster_request
from app.services.previous_roster import get_previous_month_assignments
from app.services.roster_persistence import save_roster

from app.scheduler.context import MemberRequirement
from app.scheduler.context_builder import build_roster_context
from app.scheduler.orchestrator import generate_roster

from app.models.roster import Roster

from app.database import get_db


router = APIRouter(
    prefix="/rosters",
    tags=["Rosters"],
)


# ------------------------------------------------------
# VALIDATE ROSTER REQUIREMENTS
# ------------------------------------------------------

@router.post("/validate")
def validate_roster(
    request: RosterGenerationRequest,
):
    """
    Validate roster requirements without generating a roster.
    """

    validated_request = validate_roster_request(
        request
    )

    return {
        "message": "Roster requirements are valid",
        "request": validated_request,
    }


# ------------------------------------------------------
# GENERATE ROSTER
# ------------------------------------------------------

@router.post("/generate")
def generate_roster_endpoint(
    request: RosterGenerationRequest,
    db: Session = Depends(get_db),
):
    """
    Validate the roster request, check for an existing roster,
    retrieve previous-roster history, build the scheduling
    context, execute all five scheduling passes, save the
    generated roster, and return the result.
    """

    # --------------------------------------------------
    # 1. Validate the incoming request.
    # --------------------------------------------------

    validated_request = validate_roster_request(
        request
    )

    # --------------------------------------------------
    # 2. Generate the roster name.
    # --------------------------------------------------

    roster_name = (
        f"{validated_request.year}-"
        f"{validated_request.month:02d}-"
        f"Group-{validated_request.group_number}"
    )

    # --------------------------------------------------
    # 3. Check whether this roster already exists.
    # --------------------------------------------------

    existing_roster = db.scalar(
        select(Roster).where(
            Roster.roster_name == roster_name
        )
    )

    if existing_roster:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Roster '{roster_name}' already exists."
            ),
        )

    # --------------------------------------------------
    # 4. Convert API requirements into scheduler
    #    MemberRequirement objects.
    # --------------------------------------------------

    requirements = {}

    for member in validated_request.requirements:

        requirements[member.employee_id] = MemberRequirement(
            employee_id=member.employee_id,
            requirements={
                "A": member.a,
                "B": member.b,
                "C": member.c,
                "G": member.g,
                "L": member.l,
                "W": member.w,
                "H": [],
            },
        )

    # --------------------------------------------------
    # 5. Extract the member list.
    # --------------------------------------------------

    members = [
        member.employee_id
        for member in validated_request.requirements
    ]

    # --------------------------------------------------
    # 6. Retrieve the previous month's roster history
    #    for the SAME group.
    # --------------------------------------------------

    previous_assignments = get_previous_month_assignments(
        db=db,
        year=validated_request.year,
        month=validated_request.month,
        group_number=validated_request.group_number,
    )

    # --------------------------------------------------
    # 7. Build the RosterContext.
    # --------------------------------------------------

    context = build_roster_context(
        year=validated_request.year,
        month=validated_request.month,
        group_number=validated_request.group_number,
        public_holidays=validated_request.public_holidays,
        members=members,
        requirements=requirements,
        previous_assignments=previous_assignments,
    )

    # --------------------------------------------------
    # 8. Run Pass 1 → Pass 2 → Pass 3 → Pass 4 → Pass 5.
    # --------------------------------------------------

    scheduler = generate_roster(
        context
    )

    # --------------------------------------------------
    # 9. Save the generated roster to PostgreSQL.
    # --------------------------------------------------

    roster_record = save_roster(
        db=db,
        year=validated_request.year,
        month=validated_request.month,
        group_number=validated_request.group_number,
        roster=scheduler.roster,
    )

    # --------------------------------------------------
    # 10. Return the generated roster and scheduling
    #     metadata.
    # --------------------------------------------------

    return {
        "message": "Roster generated successfully",
        "roster_id": roster_record.roster_id,
        "roster_name": roster_record.roster_name,
        "roster": scheduler.roster,
        "warnings": scheduler.warnings,
        "relaxed_requirements": scheduler.relaxed_requirements,
    }