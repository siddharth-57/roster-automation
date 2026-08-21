# scheduler constraint tests
# Verifies:
# Previous-month C → A is rejected.
# Previous-month C → C is allowed.
# Previous-month C → W is allowed.
# A working streak carried over from the previous month correctly prevents another working shift after 6 consecutive working days.

from datetime import date

from app.scheduler.constraints import (
    can_assign_after_previous_day,
    can_assign_working_shift,
)


def test_previous_month_c_then_a_is_not_allowed():

    previous_assignments = {
        "E001": {
            date(2026, 7, 31): "C",
        }
    }

    result = can_assign_after_previous_day(
        roster={},
        employee_id="E001",
        day=1,
        shift="A",
        previous_assignments=previous_assignments,
    )

    assert result is False


def test_previous_month_c_then_c_is_allowed():

    previous_assignments = {
        "E001": {
            date(2026, 7, 31): "C",
        }
    }

    result = can_assign_after_previous_day(
        roster={},
        employee_id="E001",
        day=1,
        shift="C",
        previous_assignments=previous_assignments,
    )

    assert result is True


def test_previous_month_c_then_w_is_allowed():

    previous_assignments = {
        "E001": {
            date(2026, 7, 31): "C",
        }
    }

    result = can_assign_after_previous_day(
        roster={},
        employee_id="E001",
        day=1,
        shift="W",
        previous_assignments=previous_assignments,
    )

    assert result is True


def test_previous_six_working_days_prevent_new_working_shift():

    previous_assignments = {
        "E001": {
            date(2026, 7, 27): "A",
            date(2026, 7, 28): "B",
            date(2026, 7, 29): "A",
            date(2026, 7, 30): "B",
            date(2026, 7, 31): "A",
        }
    }

    roster = {
        "E001": {
            1: "B",
        }
    }

    result = can_assign_working_shift(
        roster=roster,
        employee_id="E001",
        day=2,
        previous_assignments=previous_assignments,
    )

    assert result is False