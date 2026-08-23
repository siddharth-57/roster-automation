# test to check if daily shift coverage is being handled by the scheduler
import pytest

from app.scheduler.context import (
    MemberRequirement,
    RosterContext,
)
from app.scheduler.scheduler import RosterScheduler


def create_context():
    members = [
        "E001",
        "E002",
        "E003",
        "E004",
        "E005",
    ]

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                "A": [1],
                "B": [],
                "C": [],
                "G": [],
                "L": [],
                "W": [],
            },
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements={
                "A": [],
                "B": [1],
                "C": [],
                "G": [],
                "L": [],
                "W": [],
            },
        ),
        "E003": MemberRequirement(
            employee_id="E003",
            requirements={
                "A": [],
                "B": [],
                "C": [],
                "G": [],
                "L": [],
                "W": [1],
            },
        ),
        "E004": MemberRequirement(
            employee_id="E004",
            requirements={
                "A": [],
                "B": [],
                "C": [],
                "G": [],
                "L": [],
                "W": [],
            },
        ),
        "E005": MemberRequirement(
            employee_id="E005",
            requirements={
                "A": [],
                "B": [],
                "C": [],
                "G": [],
                "L": [],
                "W": [],
            },
        ),
    }

    return RosterContext(
        year=2026,
        month=8,
        group_number="01",
        public_holidays=1,
        members=members,
        requirements=requirements,
        previous_assignments={},
        days_in_month=5,
        required_w_days=2,
    )


def test_daily_abc_coverage_is_completed():

    context = create_context()

    scheduler = RosterScheduler(context)

    scheduler._assign_member_requirements()

    scheduler._complete_daily_coverage(1)

    assert scheduler._get_daily_shift_count(
        1,
        "A",
    ) >= 1

    assert scheduler._get_daily_shift_count(
        1,
        "B",
    ) >= 1

    assert scheduler._get_daily_shift_count(
        1,
        "C",
    ) >= 1


def test_existing_requirements_are_preserved_when_possible():

    context = create_context()

    scheduler = RosterScheduler(context)

    scheduler._assign_member_requirements()

    scheduler._complete_daily_coverage(1)

    assert scheduler.roster["E001"][1] == "A"
    assert scheduler.roster["E002"][1] == "B"


def test_conflicting_requirement_is_relaxed_when_needed():

    context = create_context()

    # Everyone is already occupied by a requirement.
    context.requirements["E004"].requirements["W"] = [1]
    context.requirements["E005"].requirements["W"] = [1]

    scheduler = RosterScheduler(context)

    scheduler._assign_member_requirements()

    scheduler._complete_daily_coverage(1)

    assert scheduler._get_daily_shift_count(
        1,
        "A",
    ) >= 1

    assert scheduler._get_daily_shift_count(
        1,
        "B",
    ) >= 1

    assert scheduler._get_daily_shift_count(
        1,
        "C",
    ) >= 1

    assert len(
        scheduler.unfulfilled_requirements
    ) >= 1