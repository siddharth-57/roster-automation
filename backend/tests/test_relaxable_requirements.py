# this test helps find the members whose requirements can be relaxed on a given day to fullfill shift coverage requirements

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


def test_relaxing_requirement_can_make_c_assignable():

    context = create_context()

    scheduler = RosterScheduler(context)

    scheduler._assign_member_requirements()

    result = scheduler._can_resolve_coverage_by_relaxing(
        employee_id="E003",
        day=1,
        requested_shift="C",
    )

    assert result is True

    # The simulation must restore the original requirement.
    assert scheduler.roster["E003"][1] == "A"


def test_relaxable_requirements_are_identified():

    context = create_context()

    scheduler = RosterScheduler(context)

    scheduler._assign_member_requirements()

    relaxable = scheduler._get_relaxable_requirements(
        day=1,
        shift="C",
    )

    employee_ids = {
        requirement["employee_id"]
        for requirement in relaxable
    }

    assert employee_ids == {
        "E001",
        "E002",
        "E003",
        "E004",
        "E005",
    }