from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schemas.roster import RosterGenerationRequest
from app.services.roster_validation import validate_roster_request
from app.services.previous_roster import get_previous_month_assignments
from app.services.roster_persistence import save_roster

from app.scheduler.context import MemberRequirement
from app.scheduler.context_builder import build_roster_context
from app.scheduler.orchestrator import generate_roster

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
    Validate the roster request, retrieve previous-roster
    history, build the scheduling context, execute all five
    scheduling passes, save the generated roster, and return it.
    """

    # --------------------------------------------------
    # 1. Validate the incoming request.
    # --------------------------------------------------
    validated_request = validate_roster_request(
        request
    )

    # --------------------------------------------------
    # 2. Convert API requirements into scheduler
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
    # 3. Extract the member list.
    # --------------------------------------------------
    members = [
        member.employee_id
        for member in validated_request.requirements
    ]

    # --------------------------------------------------
    # 4. Retrieve the previous month's roster history
    #    for the SAME group.
    # --------------------------------------------------
    previous_assignments = get_previous_month_assignments(
        db=db,
        year=validated_request.year,
        month=validated_request.month,
        group_number=validated_request.group_number,
    )

    # --------------------------------------------------
    # 5. Build the RosterContext.
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
    # 6. Run Pass 1 → Pass 2 → Pass 3 → Pass 4 → Pass 5.
    # --------------------------------------------------
    scheduler = generate_roster(
        context
    )

    # --------------------------------------------------
    # 7. Save the generated roster to PostgreSQL.
    # --------------------------------------------------
    roster_record = save_roster(
        db=db,
        year=validated_request.year,
        month=validated_request.month,
        group_number=validated_request.group_number,
        roster=scheduler.roster,
    )

    # --------------------------------------------------
    # 8. Return the generated roster.
    # --------------------------------------------------
    return {
        "message": "Roster generated successfully",
        "roster_id": roster_record.roster_id,
        "roster_name": roster_record.roster_name,
        "roster": scheduler.roster,
        "relaxed_requirements": scheduler.relaxed_requirements,
    }