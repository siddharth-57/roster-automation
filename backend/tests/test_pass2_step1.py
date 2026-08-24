from datetime import date

from app.scheduler.context import (
    MemberRequirement,
    RosterContext,
)
from app.scheduler.scheduler import RosterScheduler


def create_context(
    requirements,
    previous_assignments=None,
    days_in_month=5,
):
    members = list(requirements.keys())

    return RosterContext(
        year=2026,
        month=8,
        group_number="01",
        public_holidays=2,
        members=members,
        requirements=requirements,
        previous_assignments=previous_assignments or {},
        days_in_month=days_in_month,
        required_w_days=4,
    )


def empty_requirements():
    return {
        "A": [],
        "B": [],
        "C": [],
        "G": [],
        "L": [],
        "W": [],
        "H": [],
    }


def test_valid_requirement_is_kept():
    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "A": [1],
            },
        )
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler._assign_member_requirements()
    scheduler._run_pass_2_step_1()

    assert scheduler.roster["E001"][1] == "A"

    assert scheduler.relaxed_requirements == []


def test_invalid_shift_after_c_is_removed_and_recorded():
    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "C": [1],
                "A": [2],
            },
        )
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler._assign_member_requirements()
    scheduler._run_pass_2_step_1()

    # Day 1 C is valid.
    assert scheduler.roster["E001"][1] == "C"

    # Day 2 A is invalid because C -> A is not allowed.
    assert 2 not in scheduler.roster["E001"]

    assert scheduler.relaxed_requirements == [
        {
            "employee_id": "E001",
            "day": 2,
            "shift": "A",
        }
    ]


def test_invalid_c_is_removed_and_c_count_is_updated():
    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "C": [1, 2],
            },
        )
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler._assign_member_requirements()

    assert scheduler._get_c_count("E001") == 2

    scheduler._run_pass_2_step_1()

    # Day 1 C is valid.
    assert scheduler.roster["E001"][1] == "C"

    # Day 2 C itself is allowed after C, so it remains valid.
    assert scheduler.roster["E001"][2] == "C"

    assert scheduler._get_c_count("E001") == 2


def test_invalid_working_requirement_due_to_max_streak_is_removed():
    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "A": [1, 2, 3, 4, 5, 6, 7],
            },
        )
    }

    scheduler = RosterScheduler(
        create_context(
            requirements,
            days_in_month=7,
        )
    )

    scheduler._assign_member_requirements()
    scheduler._run_pass_2_step_1()

    # Maximum continuous working days is 6.
    assert all(
        day in scheduler.roster["E001"]
        for day in range(1, 7)
    )

    assert 7 not in scheduler.roster["E001"]

    assert scheduler.relaxed_requirements == [
        {
            "employee_id": "E001",
            "day": 7,
            "shift": "A",
        }
    ]


def test_invalid_first_day_assignment_considers_previous_month():
    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "A": [1],
            },
        )
    }

    previous_assignments = {
        "E001": {
            date(2026, 7, 31): "C",
        }
    }

    scheduler = RosterScheduler(
        create_context(
            requirements,
            previous_assignments=previous_assignments,
        )
    )

    scheduler._assign_member_requirements()
    scheduler._run_pass_2_step_1()

    # Previous month ended with C.
    # Therefore Day 1 cannot be A.
    assert 1 not in scheduler.roster["E001"]

    assert scheduler.relaxed_requirements == [
        {
            "employee_id": "E001",
            "day": 1,
            "shift": "A",
        }
    ]


def test_relaxing_w_restores_remaining_w_quota():
    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "C": [1],
                "W": [2],
            },
        )
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler._assign_member_requirements()

    # required W = 4, requested W = 1
    assert scheduler._get_remaining_w("E001") == 3

    scheduler._run_pass_2_step_1()

    # W is valid after C, so it should remain.
    assert scheduler.roster["E001"][2] == "W"
    assert scheduler._get_remaining_w("E001") == 3


def test_relaxing_h_restores_remaining_h_quota():
    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "A": [1, 2, 3, 4, 5, 6],
                "H": [7],
            },
        )
    }

    scheduler = RosterScheduler(
        create_context(
            requirements,
            days_in_month=7,
        )
    )

    scheduler._assign_member_requirements()

    # public holidays = 2, requested H = 1
    assert scheduler._get_remaining_h("E001") == 1

    scheduler._run_pass_2_step_1()

    # H is non-working, so it breaks the working streak.
    assert scheduler.roster["E001"][7] == "H"
    assert scheduler._get_remaining_h("E001") == 1