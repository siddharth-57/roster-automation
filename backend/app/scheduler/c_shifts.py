# C shift numbers for a month, shared by the solver and the validator,
# so both always work from exactly the same figures.

import calendar

from app.scheduler.config import C_SHARE_TOLERANCE


def is_weekend(year: int, month: int, day: int) -> bool:
    return calendar.weekday(year, month, day) >= 5


def required_c_per_day(
    year: int,
    month: int,
    c_per_weekday: int,
    c_per_weekend: int,
) -> dict[int, int]:
    """Number of people needed on C for every day: {day: count}."""

    days_in_month = calendar.monthrange(year, month)[1]

    return {
        day: (
            c_per_weekend
            if is_weekend(year, month, day)
            else c_per_weekday
        )
        for day in range(1, days_in_month + 1)
    }


def c_limits_per_member(
    total_c: int,
    member_count: int,
) -> tuple[int, int]:
    """
    Lowest and highest number of C shifts one member may get.

    Fair share = total C shifts / members, e.g. 31 / 8 = 3.875,
    so a fair split gives everyone 3 or 4. The limits allow
    C_SHARE_TOLERANCE either side of that: 2 to 5.
    """

    if member_count == 0:
        return 0, 0

    fair_low = total_c // member_count
    fair_high = -(-total_c // member_count)  # rounded up

    return (
        max(0, fair_low - C_SHARE_TOLERANCE),
        fair_high + C_SHARE_TOLERANCE,
    )