# The purpose of this layer is to collect everything the scheduler needs into one object with a specific format before scheduling begins.
# The scheduler therefore doesn't need to repeatedly ask the database for information.

from dataclasses import dataclass
from datetime import date

from app.scheduler.config import (
    DEFAULT_C_PER_WEEKDAY,
    DEFAULT_C_PER_WEEKEND,
)


@dataclass
class MemberRequirement:
    employee_id: str
    requirements: dict[str, list[int]]


@dataclass
class RosterContext:
    year: int
    month: int
    group_number: str
    public_holidays: int

    members: list[str]

    requirements: dict[str, MemberRequirement]

    previous_assignments: dict[
        str,
        dict[date, str],
    ]

    days_in_month: int
    required_w_days: int

    # How many people the TL wants on C each weekday / weekend day
    c_per_weekday: int = DEFAULT_C_PER_WEEKDAY
    c_per_weekend: int = DEFAULT_C_PER_WEEKEND