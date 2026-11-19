import calendar
from datetime import date

from app.scheduler.config import (
    DEFAULT_C_PER_WEEKDAY,
    DEFAULT_C_PER_WEEKEND,
)
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
    c_per_weekday: int = DEFAULT_C_PER_WEEKDAY,
    c_per_weekend: int = DEFAULT_C_PER_WEEKEND,
    previous_c_counts: dict[str, int] | None = None,
    previous_weekend_work: dict[str, int] | None = None,
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
        c_per_weekday=c_per_weekday,
        c_per_weekend=c_per_weekend,
        previous_c_counts=previous_c_counts or {},
        previous_weekend_work=previous_weekend_work or {},
    )