# Define the shift types
# This file defines all the functions to implement the constraints to check if a single assignment is valid or not
# logic to check if all assignments fit together to generate a valid final roster will be implemented in another file

from collections import Counter

from app.scheduler.config import (
    MAX_C_PER_DAY,
    MAX_C_PER_MEMBER,
    MAX_CONTINUOUS_WORKING_DAYS,
)


WORKING_SHIFTS = {"A", "B", "C", "G"}
NON_WORKING_SHIFTS = {"W", "H", "L"}
ALL_SHIFTS = WORKING_SHIFTS | NON_WORKING_SHIFTS

# roster[employee_id][day] = shift this will be representation of the shifts in the roster while creating the logic


# If: roster["E001"][5] = "C" then: is_day_available(roster, "E001", 5) returns: False
# This enforces: A member can only have one assignment per day.
def is_day_available(
    roster: dict,
    employee_id: str,
    day: int,
) -> bool:
    return day not in roster.get(employee_id, {})


# CHECKS MAXIMUM C SHIFT PER MEMBER AND IF MORE C SHIFTS CAN BE ASSIGNED BASED ON THE MAX LIMIT CONFIGURED
def count_c_shifts(
    roster: dict,
    employee_id: str,
) -> int:
    return sum(
        shift == "C"
        for shift in roster.get(employee_id, {}).values()
    )
def can_assign_c(
    roster: dict,
    employee_id: str,
) -> bool:
    return (
        count_c_shifts(roster, employee_id)
        < MAX_C_PER_MEMBER
    )

# CHECKS Constraint: maximum C shift members per day
def count_c_on_day(
    roster: dict,
    day: int,
) -> int:
    return sum(
        assignments.get(day) == "C"
        for assignments in roster.values()
    )

# so once one person has C on that day, another person cannot receive C.
def can_assign_c_on_day(
    roster: dict,
    day: int,
) -> bool:
    return (
        count_c_on_day(roster, day)
        < MAX_C_PER_DAY
    )

# Checks Constraint: C shift continuation
# C → C/W/H/L       allowed
# C → A/B/G       not-allowed
# Adds previous-month awareness to constraints
def can_assign_after_previous_day(
    roster: dict,
    employee_id: str,
    day: int,
    shift: str,
    previous_assignments: dict | None = None,
) -> bool:

    if day <= 1:
        previous_shift = None

        if previous_assignments:
            employee_history = previous_assignments.get(
                employee_id,
                {},
            )

            if employee_history:
                previous_shift = employee_history.get(
                    max(employee_history)
                )
    else:
        previous_shift = roster.get(
            employee_id,
            {},
        ).get(day - 1)

    if previous_shift != "C":
        return True

    return shift in {
        "C",
        "W",
        "H",
        "L",
    }

# Previous-month continuous working streak
def get_previous_working_streak(
    employee_id: str,
    previous_assignments: dict | None,
) -> int:

    if not previous_assignments:
        return 0

    employee_history = previous_assignments.get(
        employee_id,
        {},
    )

    if not employee_history:
        return 0

    streak = 0

    for current_date in sorted(
        employee_history,
        reverse=True,
    ):

        shift = employee_history[current_date]

        if shift not in WORKING_SHIFTS:
            break

        streak += 1

    return streak


# Implements constraint Maximum six continuous working days and also checks previous month history
def get_working_streak_before_day(
    roster: dict,
    employee_id: str,
    day: int,
    previous_assignments: dict | None = None,
) -> int:

    streak = 0
    current_day = day - 1

    while current_day >= 1:

        shift = roster.get(
            employee_id,
            {},
        ).get(current_day)

        if shift not in WORKING_SHIFTS:
            break

        streak += 1
        current_day -= 1

    if current_day == 0:
        streak += get_previous_working_streak(
            employee_id,
            previous_assignments,
        )

    return streak


def can_assign_working_shift(
    roster: dict,
    employee_id: str,
    day: int,
    previous_assignments: dict | None = None,
) -> bool:

    previous_streak = get_working_streak_before_day(
        roster,
        employee_id,
        day,
        previous_assignments,
    )

    return (
        previous_streak
        < MAX_CONTINUOUS_WORKING_DAYS
    )

# Central Function using all the above functions to determine if a member can receive a specific shift on a specific day or not and we get the answer in bool format
def can_assign_shift(
    roster: dict,
    employee_id: str,
    day: int,
    shift: str,
    previous_assignments: dict | None = None,
) -> bool:

    if shift not in ALL_SHIFTS:
        return False

    if not is_day_available(
        roster,
        employee_id,
        day,
    ):
        return False

    if shift == "C":

        if not can_assign_c(
            roster,
            employee_id,
        ):
            return False

        if not can_assign_c_on_day(
            roster,
            day,
        ):
            return False

    if not can_assign_after_previous_day(
        roster,
        employee_id,
        day,
        shift,
        previous_assignments,
    ):
        return False

    if shift in WORKING_SHIFTS:

        if not can_assign_working_shift(
            roster,
            employee_id,
            day,
            previous_assignments,
        ):
            return False

    return True