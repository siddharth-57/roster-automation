# test to find out which candidates can be assigned shifts to cover daily coverage

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


def test_only_unassigned_members_are_candidates():

    context = create_context()

    scheduler = RosterScheduler(context)

    scheduler._assign_member_requirements()

    candidates = scheduler._get_valid_coverage_candidates(
        day=1,
        shift="C",
    )

    assert candidates == ["E003"]


def test_assigned_member_is_not_candidate():

    context = create_context()

    scheduler = RosterScheduler(context)

    scheduler._assign_member_requirements()

    candidates = scheduler._get_valid_coverage_candidates(
        day=1,
        shift="A",
    )

    assert candidates == ["E003"]