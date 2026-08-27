from datetime import date

from sqlalchemy.orm import Session

from app.models.roster import Roster
from app.models.roster_assignment import RosterAssignment


def save_roster(
    db: Session,
    year: int,
    month: int,
    group_number: str,
    roster: dict[str, dict[int, str]],
) -> Roster:
    """
    Save a generated roster and all of its assignments
    to PostgreSQL.

    The roster is uniquely identified by:

        year + month + group_number

    The roster name is generated from the same frontend-provided
    details.
    """

    # ------------------------------------------------------
    # Generate a deterministic roster name.
    # ------------------------------------------------------
    roster_name = (
        f"{year}-{month:02d}-Group-{group_number}"
    )

    # ------------------------------------------------------
    # Create the Roster record.
    # ------------------------------------------------------
    roster_record = Roster(
        roster_name=roster_name,
        year=year,
        month=month,
        group_number=group_number,
    )

    db.add(roster_record)

    # ------------------------------------------------------
    # Flush so roster_id is generated before creating
    # RosterAssignment records.
    # ------------------------------------------------------
    db.flush()

    # ------------------------------------------------------
    # Create one assignment for every employee/day.
    # ------------------------------------------------------
    for employee_id, assignments in roster.items():

        for day, shift in assignments.items():

            assignment = RosterAssignment(
                roster_id=roster_record.roster_id,
                employee_id=employee_id,
                date=date(
                    year,
                    month,
                    day,
                ),
                shift=shift,
            )

            db.add(assignment)

    # ------------------------------------------------------
    # Commit the entire roster as one transaction.
    # ------------------------------------------------------
    db.commit()

    # ------------------------------------------------------
    # Refresh the roster so the returned object reflects
    # the committed database state.
    # ------------------------------------------------------
    db.refresh(roster_record)

    return roster_record