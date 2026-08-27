# previous month's last 5 days roster lookup
# If there is no previous month's roster, this returns: {}
# The scheduler can then generate the month without previous-month history.
# That's necessary for the first roster ever created.

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.roster import Roster
from app.models.roster_assignment import RosterAssignment


def get_previous_month_assignments(
    db: Session,
    year: int,
    month: int,
    group_number: str,
) -> dict[str, dict[date, str]]:

    if month == 1:
        previous_year = year - 1
        previous_month = 12
    else:
        previous_year = year
        previous_month = month - 1

    roster = db.scalar(
        select(Roster).where(
            Roster.year == previous_year,
            Roster.month == previous_month,
            Roster.group_number == group_number,
        )
    )

    if not roster:
        return {}

    first_day_current_month = date(
        year,
        month,
        1,
    )

    last_day_previous_month = (
        first_day_current_month
        - timedelta(days=1)
    )

    first_day_to_include = (
        last_day_previous_month
        - timedelta(days=4)
    )

    assignments = db.scalars(
        select(RosterAssignment).where(
            RosterAssignment.roster_id == roster.roster_id,
            RosterAssignment.date >= first_day_to_include,
            RosterAssignment.date <= last_day_previous_month,
        )
    ).all()

    result: dict[str, dict[date, str]] = {}

    for assignment in assignments:

        result.setdefault(
            assignment.employee_id,
            {},
        )[assignment.date] = assignment.shift

    return result