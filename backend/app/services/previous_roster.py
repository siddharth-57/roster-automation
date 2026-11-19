# previous month's last 5 days roster lookup
# If there is no previous month's roster, this returns: {}
# The scheduler can then generate the month without previous-month history.
# That's necessary for the first roster ever created.

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.roster import Roster
from app.models.roster_assignment import RosterAssignment


def get_previous_month_roster(
    db: Session,
    year: int,
    month: int,
    group_number: str,
) -> Roster | None:

    if month == 1:
        previous_year = year - 1
        previous_month = 12
    else:
        previous_year = year
        previous_month = month - 1

    return db.scalar(
        select(Roster).where(
            Roster.year == previous_year,
            Roster.month == previous_month,
            Roster.group_number == group_number,
        )
    )


def get_previous_month_assignments(
    db: Session,
    year: int,
    month: int,
    group_number: str,
) -> dict[str, dict[date, str]]:

    roster = get_previous_month_roster(
        db,
        year,
        month,
        group_number,
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


# How many C shifts each member got in the previous month (same group),
# e.g. {"E001": 7, "E002": 6}. Members with no C last month are left
# out, which the scheduler treats the same as having the lower number.
# Empty if there is no previous roster.
def get_previous_month_c_counts(
    db: Session,
    year: int,
    month: int,
    group_number: str,
) -> dict[str, int]:

    roster = get_previous_month_roster(
        db,
        year,
        month,
        group_number,
    )

    if not roster:
        return {}

    rows = db.execute(
        select(
            RosterAssignment.employee_id,
            func.count(),
        )
        .where(
            RosterAssignment.roster_id == roster.roster_id,
            RosterAssignment.shift == "C",
        )
        .group_by(RosterAssignment.employee_id)
    ).all()

    return {
        employee_id: count
        for employee_id, count in rows
    }


# How many Saturdays/Sundays each member worked (A, B, C or G) in the
# previous month (same group), e.g. {"E001": 4, "E002": 2}. Members who
# didn't work any weekend day are left out (treated as the lowest).
# Empty if there is no previous roster.
def get_previous_month_weekend_work(
    db: Session,
    year: int,
    month: int,
    group_number: str,
) -> dict[str, int]:

    roster = get_previous_month_roster(
        db,
        year,
        month,
        group_number,
    )

    if not roster:
        return {}

    assignments = db.scalars(
        select(RosterAssignment).where(
            RosterAssignment.roster_id == roster.roster_id,
            RosterAssignment.shift.in_(["A", "B", "C", "G"]),
        )
    ).all()

    result: dict[str, int] = {}

    for assignment in assignments:
        if assignment.date.weekday() >= 5:
            result[assignment.employee_id] = (
                result.get(assignment.employee_id, 0) + 1
            )

    return result