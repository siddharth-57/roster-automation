# The functions in this file validate if the entire roster is valid or not and follows the constraints or not
# This file checks the following core constraints:
# 1. A/B/C shifts everyday have atleast one member
# 2. each member's C count is within the range worked out from the month (see c_shifts.py)
# 3. exactly the chosen number of members in C each day (weekday / weekend)
# 4. the day after a C shift must be C/W/H/L (including previous month's last day)
# 5. max MAX_CONTINUOUS_WORKING_DAYS continuous working days (including previous month's streak)
# 6. all members must receive the required W and H every month
# 7. max WEEKEND_MAX_PER_SHIFT members in each of A/B/G on Saturdays and Sundays
# 8. max MAX_G_PER_MEMBER G shifts per member per month

import calendar
from datetime import date

from app.scheduler.c_shifts import (
    c_limits_per_member,
    required_c_per_day,
)
from app.scheduler.config import (
    DEFAULT_C_PER_WEEKDAY,
    DEFAULT_C_PER_WEEKEND,
    MAX_CONTINUOUS_WORKING_DAYS,
    MAX_G_PER_MEMBER,
    WEEKEND_MAX_PER_SHIFT,
)
from app.scheduler.constraints import (
    WORKING_SHIFTS,
    NON_WORKING_SHIFTS,
    get_previous_working_streak,
)


def get_working_days_in_month(
    year: int,
    month: int,
) -> int:
    return calendar.monthrange(year, month)[1]


def count_shift(
    assignments: dict,
    shift: str,
) -> int:
    return sum(
        value == shift
        for value in assignments.values()
    )


def get_previous_last_shift(
    employee_id: str,
    previous_assignments: dict | None,
) -> str | None:
    """Return the member's shift on the last day of the previous month."""

    if not previous_assignments:
        return None

    employee_history = previous_assignments.get(employee_id, {})

    if not employee_history:
        return None

    return employee_history[max(employee_history)]


def validate_daily_staffing(
    roster: dict,
    days_in_month: int,
) -> list[str]:

    errors = []

    for day in range(1, days_in_month + 1):

        assigned_shifts = {
            assignments.get(day)
            for assignments in roster.values()
        }

        if "A" not in assigned_shifts:
            errors.append(
                f"Day {day}: no member assigned to A shift."
            )

        if "B" not in assigned_shifts:
            errors.append(
                f"Day {day}: no member assigned to B shift."
            )

        if "C" not in assigned_shifts:
            errors.append(
                f"Day {day}: no member assigned to C shift."
            )

    return errors


def validate_c_shift_limits(
    roster: dict,
    year: int,
    month: int,
    c_per_weekday: int = DEFAULT_C_PER_WEEKDAY,
    c_per_weekend: int = DEFAULT_C_PER_WEEKEND,
) -> list[str]:

    errors = []

    total_c = sum(
        required_c_per_day(
            year,
            month,
            c_per_weekday,
            c_per_weekend,
        ).values()
    )

    min_c, max_c = c_limits_per_member(
        total_c,
        len(roster),
    )

    for employee_id, assignments in roster.items():

        c_count = count_shift(
            assignments,
            "C",
        )

        if c_count < min_c:
            errors.append(
                f"{employee_id}: only {c_count} C shifts "
                f"(minimum is {min_c})."
            )

        if c_count > max_c:
            errors.append(
                f"{employee_id}: {c_count} C shifts "
                f"(maximum is {max_c})."
            )

    return errors


def validate_c_shift_daily_limit(
    roster: dict,
    year: int,
    month: int,
    c_per_weekday: int = DEFAULT_C_PER_WEEKDAY,
    c_per_weekend: int = DEFAULT_C_PER_WEEKEND,
) -> list[str]:

    errors = []

    required = required_c_per_day(
        year,
        month,
        c_per_weekday,
        c_per_weekend,
    )

    for day, required_count in required.items():

        c_members = [
            employee_id
            for employee_id, assignments
            in roster.items()
            if assignments.get(day) == "C"
        ]

        if len(c_members) != required_count:
            errors.append(
                f"Day {day}: {len(c_members)} members "
                f"assigned to C shift "
                f"(required: {required_count})."
            )

    return errors


def validate_g_shift_limit(
    roster: dict,
) -> list[str]:

    errors = []

    for employee_id, assignments in roster.items():

        g_count = count_shift(
            assignments,
            "G",
        )

        if g_count > MAX_G_PER_MEMBER:
            errors.append(
                f"{employee_id}: {g_count} G shifts "
                f"(maximum is {MAX_G_PER_MEMBER})."
            )

    return errors


def validate_weekend_max_per_shift(
    roster: dict,
    year: int,
    month: int,
) -> list[str]:

    errors = []

    days_in_month = calendar.monthrange(year, month)[1]

    for day in range(1, days_in_month + 1):

        if date(year, month, day).weekday() < 5:
            continue  # weekday

        for shift in ("A", "B", "G"):

            count = sum(
                assignments.get(day) == shift
                for assignments in roster.values()
            )

            if count > WEEKEND_MAX_PER_SHIFT:
                errors.append(
                    f"Day {day} (weekend): {count} members "
                    f"in {shift} shift "
                    f"(maximum is {WEEKEND_MAX_PER_SHIFT})."
                )

    return errors


def validate_single_shift_per_day(
    roster: dict,
) -> list[str]:

    # The internal roster representation already stores
    # one value per employee/day. This function exists
    # as an explicit hard-rule check.
    errors = []

    for employee_id, assignments in roster.items():

        for day, shift in assignments.items():

            if shift not in (
                WORKING_SHIFTS
                | NON_WORKING_SHIFTS
            ):
                errors.append(
                    f"{employee_id}, day {day}: "
                    f"invalid shift '{shift}'."
                )

    return errors


def validate_c_continuation(
    roster: dict,
    days_in_month: int,
    previous_assignments: dict | None = None,
) -> list[str]:

    errors = []
    allowed_after_c = {"C", "W", "H", "L"}

    for employee_id, assignments in roster.items():

        # Day 1 vs the previous month's last day
        if (
            get_previous_last_shift(employee_id, previous_assignments) == "C"
            and assignments.get(1) not in allowed_after_c
        ):
            errors.append(
                f"{employee_id}: previous month ended on C "
                f"but day 1 is {assignments.get(1)}."
            )

        for day in range(2, days_in_month + 1):

            previous_shift = assignments.get(
                day - 1
            )

            current_shift = assignments.get(day)

            if previous_shift == "C":

                if current_shift not in allowed_after_c:

                    errors.append(
                        f"{employee_id}: day {day - 1} "
                        f"is C but day {day} is "
                        f"{current_shift}."
                    )

    return errors


def validate_continuous_working_days(
    roster: dict,
    days_in_month: int,
    previous_assignments: dict | None = None,
) -> list[str]:

    errors = []

    for employee_id, assignments in roster.items():

        # Start with the working streak carried over from last month
        streak = get_previous_working_streak(
            employee_id,
            previous_assignments,
        )

        for day in range(1, days_in_month + 1):

            shift = assignments.get(day)

            if shift in WORKING_SHIFTS:

                streak += 1

                if streak > MAX_CONTINUOUS_WORKING_DAYS:
                    errors.append(
                        f"{employee_id}: more than "
                        f"{MAX_CONTINUOUS_WORKING_DAYS} "
                        f"continuous working days "
                        f"ending on day {day}."
                    )

            else:
                streak = 0

    return errors


def validate_w_counts(
    roster: dict,
    year: int,
    month: int,
) -> list[str]:

    errors = []

    days_in_month = calendar.monthrange(
        year,
        month,
    )[1]

    expected_w = 0

    for day in range(1, days_in_month + 1):

        weekday = date(
            year,
            month,
            day,
        ).weekday()

        if weekday >= 5:
            expected_w += 1

    for employee_id, assignments in roster.items():

        actual_w = count_shift(
            assignments,
            "W",
        )

        if actual_w != expected_w:
            errors.append(
                f"{employee_id}: has {actual_w} W days; "
                f"expected {expected_w}."
            )

    return errors


def validate_h_counts(
    roster: dict,
    public_holidays: int,
) -> list[str]:

    errors = []

    for employee_id, assignments in roster.items():

        actual_h = count_shift(
            assignments,
            "H",
        )

        if actual_h != public_holidays:
            errors.append(
                f"{employee_id}: has {actual_h} H days; "
                f"expected {public_holidays}."
            )

    return errors


def validate_roster(
    roster: dict,
    year: int,
    month: int,
    public_holidays: int,
    previous_assignments: dict | None = None,
    c_per_weekday: int = DEFAULT_C_PER_WEEKDAY,
    c_per_weekend: int = DEFAULT_C_PER_WEEKEND,
) -> list[str]:

    days_in_month = calendar.monthrange(
        year,
        month,
    )[1]

    errors = []

    errors.extend(
        validate_single_shift_per_day(
            roster
        )
    )

    errors.extend(
        validate_daily_staffing(
            roster,
            days_in_month,
        )
    )

    errors.extend(
        validate_c_shift_limits(
            roster,
            year,
            month,
            c_per_weekday,
            c_per_weekend,
        )
    )

    errors.extend(
        validate_c_shift_daily_limit(
            roster,
            year,
            month,
            c_per_weekday,
            c_per_weekend,
        )
    )

    errors.extend(
        validate_g_shift_limit(
            roster
        )
    )

    errors.extend(
        validate_weekend_max_per_shift(
            roster,
            year,
            month,
        )
    )

    errors.extend(
        validate_c_continuation(
            roster,
            days_in_month,
            previous_assignments,
        )
    )

    errors.extend(
        validate_continuous_working_days(
            roster,
            days_in_month,
            previous_assignments,
        )
    )

    errors.extend(
        validate_w_counts(
            roster,
            year,
            month,
        )
    )

    errors.extend(
        validate_h_counts(
            roster,
            public_holidays,
        )
    )

    return errors