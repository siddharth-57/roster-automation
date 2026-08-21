import calendar
from datetime import date

from app.scheduler.context import (
    MemberRequirement,
    RosterContext,
)

# This file builds the context which will be used by the scheduling logic to generate the roster

def calculate_required_w_days(
    year: int,
    month: int,
) -> int:

    days_in_month = calendar.monthrange(
        year,
        month,
    )[1]

    required_w_days = 0

    for day in range(1, days_in_month + 1):

        current_date = date(
            year,
            month,
            day,
        )

        if current_date.weekday() >= 5:
            required_w_days += 1

    return required_w_days

# previous_assignments uses actual dates to make the scheduling unambiguous

def build_roster_context(
    year: int,
    month: int,
    group_number: str,
    public_holidays: int,
    members: list[str],
    requirements: dict[str, MemberRequirement],
    previous_assignments: dict[
        str,
        dict[date, str],
    ],
) -> RosterContext:

    days_in_month = calendar.monthrange(
        year,
        month,
    )[1]

    required_w_days = calculate_required_w_days(
        year,
        month,
    )

    return RosterContext(
        year=year,
        month=month,
        group_number=group_number,
        public_holidays=public_holidays,
        members=members,
        requirements=requirements,
        previous_assignments=previous_assignments,
        days_in_month=days_in_month,
        required_w_days=required_w_days,
    )