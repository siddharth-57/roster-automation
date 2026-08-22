# Tests the requirement loding phase (tests the requirements given by members are being stored as it is even if they break the roster constraints for the time being)

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
                "B": [],
                "C": [1],
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


def test_all_member_requirements_are_loaded():

    context = create_context()

    scheduler = RosterScheduler(context)

    scheduler._assign_member_requirements()

    assert scheduler.roster["E001"][1] == "A"
    assert scheduler.roster["E002"][1] == "C"
    assert scheduler.roster["E003"][1] == "W"


def test_requirement_loading_does_not_apply_roster_constraints():

    context = create_context()

    # For this test, deliberately create a requirement set
    # where all three members request A on the same day.
    #
    # This is valid input at the member level because each
    # member requests only one shift on day 1.
    context.requirements["E001"].requirements = {
        "A": [1],
        "B": [],
        "C": [],
        "G": [],
        "L": [],
        "W": [],
    }

    context.requirements["E002"].requirements = {
        "A": [1],
        "B": [],
        "C": [],
        "G": [],
        "L": [],
        "W": [],
    }

    context.requirements["E003"].requirements = {
        "A": [1],
        "B": [],
        "C": [],
        "G": [],
        "L": [],
        "W": [],
    }

    scheduler = RosterScheduler(context)

    scheduler._assign_member_requirements()

    # All requirements must be loaded exactly as requested,
    # even though this temporarily violates the daily
    # staffing rules.
    assert scheduler.roster["E001"][1] == "A"
    assert scheduler.roster["E002"][1] == "A"
    assert scheduler.roster["E003"][1] == "A"