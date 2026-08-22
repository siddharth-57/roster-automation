# Test the random relaxation
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
                "A": [],
                "B": [],
                "C": [],
                "G": [],
                "L": [],
                "W": [1],
            },
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements={
                "A": [],
                "B": [],
                "C": [],
                "G": [],
                "L": [],
                "W": [1],
            },
        ),
        "E003": MemberRequirement(
            employee_id="E003",
            requirements={
                "A": [1],
                "B": [],
                "C": [],
                "G": [],
                "L": [],
                "W": [],
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
                "W": [1],
            },
        ),
        "E005": MemberRequirement(
            employee_id="E005",
            requirements={
                "A": [],
                "B": [1],
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


def test_random_requirement_is_relaxed(monkeypatch):

    context = create_context()

    scheduler = RosterScheduler(context)

    scheduler._assign_member_requirements()

    # Force random.choice() to select E003 so that
    # the test is deterministic.
    monkeypatch.setattr(
        "app.scheduler.scheduler.random.choice",
        lambda values: next(
            value
            for value in values
            if value["employee_id"] == "E003"
        ),
    )

    employee_id = scheduler._relax_random_requirement(
        day=1,
        shift="C",
    )

    assert employee_id == "E003"

    assert scheduler.roster["E003"][1] == "C"

    assert scheduler.unfulfilled_requirements == [
        {
            "employee_id": "E003",
            "day": 1,
            "requested_shift": "A",
            "reason": (
                "Requirement relaxed to satisfy "
                "C coverage."
            ),
        }
    ]


def test_no_relaxation_when_no_requirement_can_be_relaxed():

    context = create_context()

    scheduler = RosterScheduler(context)

    scheduler._assign_member_requirements()

    # Remove every assignment from the roster.
    # There are therefore no existing requirements
    # blocking C coverage.
    for employee_id in context.members:
        scheduler.roster[employee_id].clear()

    result = scheduler._relax_random_requirement(
        day=1,
        shift="C",
    )

    assert result is None