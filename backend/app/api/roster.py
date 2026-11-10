from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
)
from fastapi.responses import StreamingResponse
from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.schemas.roster import RosterGenerationRequest
from app.services.roster_validation import validate_roster_request
from app.services.previous_roster import get_previous_month_assignments
from app.services.roster_persistence import save_roster
from app.services.roster_excel import create_roster_excel
from app.services.roster_excel import read_roster_excel

from app.scheduler.context import MemberRequirement
from app.scheduler.context_builder import build_roster_context
from app.scheduler.orchestrator import generate_roster

from app.models.roster import Roster
from app.models.roster_assignment import RosterAssignment

from app.database import get_db
from app.services.groups import (
    get_active_group_or_error,
    get_group_or_404,
    validate_members_belong_to_group,
)

import logging

from app.scheduler.validator import validate_roster as validate_generated_roster

logger = logging.getLogger(__name__)


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
    db: Session = Depends(get_db),
):
    """
    Validate roster requirements without generating a roster.
    """

    validated_request = validate_roster_request(
        request
    )

    # The group must exist and be active, and every member in the
    # request must belong to it.
    group = get_active_group_or_error(
        db,
        validated_request.group_number,
    )

    validate_members_belong_to_group(
        db,
        group,
        [member.employee_id for member in validated_request.requirements],
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
    context, run the CP-SAT solver, save the generated roster,
    and return the result.
    """

    # --------------------------------------------------
    # 1. Validate the incoming request.
    # --------------------------------------------------

    validated_request = validate_roster_request(
        request
    )

    # The group must exist and be active, and every member in the
    # request must belong to it.
    group = get_active_group_or_error(
        db,
        validated_request.group_number,
    )

    validate_members_belong_to_group(
        db,
        group,
        [member.employee_id for member in validated_request.requirements],
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
    # 8. Run the CP-SAT solver.
    # --------------------------------------------------

    result = generate_roster(
        context
    )

    # --------------------------------------------------
    # 9. No valid roster exists (hard rules can't all be
    #    met, e.g. too few members). Don't save anything.
    # --------------------------------------------------

    if not result.roster:
        raise HTTPException(
            status_code=422,
            detail=(
                "Roster could not be generated. "
                + " ".join(result.warnings)
            ),
        )



    # --------------------------------------------------
    # Safety net: re-check every hard rule before saving.
    # Should never fail; if it does, the solver has a bug.
    # --------------------------------------------------

    validation_errors = validate_generated_roster(
        result.roster,
        validated_request.year,
        validated_request.month,
        validated_request.public_holidays,
        previous_assignments,
    )

    if validation_errors:

        # Full details for the developer (docker compose logs backend)
        logger.error(
            "Generated roster %s failed validation: %s",
            roster_name,
            validation_errors,
        )

        # Clear explanation for the TL
        raise HTTPException(
            status_code=500,
            detail={
                "message": (
                    "The roster was generated but failed the final "
                    "rule check, so it was NOT saved. This is a "
                    "problem in the application, not in the "
                    "requirements you entered. Please report it to "
                    "the developer along with the details below."
                ),
                "errors": validation_errors,
            },
        )


    # --------------------------------------------------
    # 10. Save the generated roster to PostgreSQL.
    # --------------------------------------------------

    roster_record = save_roster(
        db=db,
        year=validated_request.year,
        month=validated_request.month,
        group_number=validated_request.group_number,
        roster=result.roster,
    )

    # --------------------------------------------------
    # 11. Return the generated roster and scheduling
    #     metadata.
    # --------------------------------------------------

    return {
        "message": "Roster generated successfully",
        "roster_id": roster_record.roster_id,
        "roster_name": roster_record.roster_name,
        "roster": result.roster,
        "warnings": result.warnings,
        "relaxed_requirements": result.relaxed_requirements,
    }


# ------------------------------------------------------
# DOWNLOAD ROSTER
# ------------------------------------------------------

@router.get("/{year}/{month}/{group_number}/download")
def download_roster(
    year: int,
    month: int,
    group_number: str,
    db: Session = Depends(get_db),
):
    """
    Download an existing roster as an Excel file.
    """

    # --------------------------------------------------
    # 1. Find the roster.
    # --------------------------------------------------

    roster_name = (
        f"{year}-"
        f"{month:02d}-Group-{group_number}"
    )

    roster = db.scalar(
        select(Roster).where(
            Roster.roster_name == roster_name
        )
    )

    # --------------------------------------------------
    # 2. Roster doesn't exist.
    # --------------------------------------------------

    if not roster:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Roster '{roster_name}' "
                f"does not exist."
            ),
        )

    # --------------------------------------------------
    # 3. Generate the Excel file.
    # --------------------------------------------------

    excel_file = create_roster_excel(
        db=db,
        roster=roster,
    )

    # --------------------------------------------------
    # 4. Return the Excel file.
    # --------------------------------------------------

    filename = f"{roster_name}.xlsx"

    return StreamingResponse(
        excel_file,
        media_type=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            )
        },
    )



# ------------------------------------------------------
# UPLOAD ROSTER
# ------------------------------------------------------

@router.post("/{year}/{month}/{group_number}/upload")
def upload_roster(
    year: int,
    month: int,
    group_number: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload an Excel roster.

    If the roster does not exist, it is created.

    If the roster already exists, all of its existing
    assignments are replaced by the uploaded roster.
    """

    # --------------------------------------------------
    # 1. Validate file type.
    # --------------------------------------------------

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file was provided.",
        )

    if not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=400,
            detail="Only .xlsx Excel files are supported.",
        )

    # The group must exist (inactive groups are allowed, so old
    # rosters can still be re-uploaded).
    group_number = get_group_or_404(db, group_number).group_number

    # --------------------------------------------------
    # 2. Read the uploaded file.
    # --------------------------------------------------

    file_contents = file.file.read()

    if not file_contents:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    # --------------------------------------------------
    # 3. Convert the Excel file into our internal
    #    roster representation.
    # --------------------------------------------------

    try:
        uploaded_roster = read_roster_excel(
            db=db,
            file_contents=file_contents,
            year=year,
            month=month,
            group_number=group_number,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Unable to read the uploaded Excel file.",
        )

    # --------------------------------------------------
    # 4. Generate the database roster name.
    # --------------------------------------------------

    roster_name = (
        f"{year}-"
        f"{month:02d}-Group-{group_number}"
    )

    # --------------------------------------------------
    # 5. Find an existing roster.
    # --------------------------------------------------

    roster = db.scalar(
        select(Roster).where(
            Roster.roster_name == roster_name
        )
    )

    try:

        # --------------------------------------------------
        # 6. Create the roster if it doesn't exist.
        # --------------------------------------------------

        if not roster:

            roster = Roster(
                roster_name=roster_name,
                year=year,
                month=month,
                group_number=group_number,
            )

            db.add(roster)

            db.flush()

            created = True

        else:

            # --------------------------------------------------
            # Existing roster → overwrite.
            #
            # Delete its old assignments first.
            # --------------------------------------------------

            db.query(RosterAssignment).filter(
                RosterAssignment.roster_id
                == roster.roster_id
            ).delete(
                synchronize_session=False
            )

            created = False

        # --------------------------------------------------
        # 7. Insert uploaded assignments.
        # --------------------------------------------------

        for employee_id, assignments in uploaded_roster.items():

            for day, shift in assignments.items():

                assignment = RosterAssignment(
                    roster_id=roster.roster_id,
                    employee_id=employee_id,
                    date=date(
                        year,
                        month,
                        day,
                    ),
                    shift=shift,
                )

                db.add(assignment)

        # --------------------------------------------------
        # 8. Commit the complete operation.
        # --------------------------------------------------

        db.commit()

        db.refresh(roster)

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=(
                "The roster could not be saved. "
                "No changes were made to the database."
            ),
        )

    # --------------------------------------------------
    # 9. Return result.
    # --------------------------------------------------

    if created:

        return {
            "message": "Roster uploaded successfully",
            "action": "created",
            "roster_id": roster.roster_id,
            "roster_name": roster.roster_name,
        }

    return {
        "message": "Roster uploaded successfully",
        "action": "overwritten",
        "roster_id": roster.roster_id,
        "roster_name": roster.roster_name,
    }
    
# ------------------------------------------------------
# DELETE ROSTER
# ------------------------------------------------------

@router.delete("/{year}/{month}/{group_number}")
def delete_roster(
    year: int,
    month: int,
    group_number: str,
    db: Session = Depends(get_db),
):
    """
    Delete a roster and all of its assignments.

    Assignments are deleted first, then the roster itself,
    in a single transaction: either both go, or nothing changes.
    """

    # --------------------------------------------------
    # 1. Find the roster.
    # --------------------------------------------------

    roster_name = (
        f"{year}-"
        f"{month:02d}-Group-{group_number}"
    )

    roster = db.scalar(
        select(Roster).where(
            Roster.roster_name == roster_name
        )
    )

    if not roster:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Roster '{roster_name}' "
                f"does not exist."
            ),
        )

    # --------------------------------------------------
    # 2. Delete assignments, then the roster.
    # --------------------------------------------------

    try:
        deleted_assignments = (
            db.query(RosterAssignment)
            .filter(
                RosterAssignment.roster_id
                == roster.roster_id
            )
            .delete(synchronize_session=False)
        )

        db.delete(roster)

        db.commit()

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "The roster could not be deleted. "
                "No changes were made to the database."
            ),
        )

    # --------------------------------------------------
    # 3. Return result.
    # --------------------------------------------------

    return {
        "message": f"Roster '{roster_name}' deleted successfully.",
        "roster_name": roster_name,
        "deleted_assignments": deleted_assignments,
    }