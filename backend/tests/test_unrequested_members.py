# tests the methods to assign working shifts to members on any day 
# where they have not posted any requirements and can work a shift

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


def test_members_without_requirements_are_identified():

    context = create_context()

    scheduler = RosterScheduler(context)

    scheduler._assign_member_requirements()

    members = scheduler._get_members_without_requirement(
        day=1
    )

    assert members == [
        "E003",
        "E004",
    ]


def test_unrequested_member_gets_a_working_shift_when_possible():

    context = create_context()

    scheduler = RosterScheduler(context)

    scheduler._assign_member_requirements()

    scheduler._fill_unrequested_members(
        day=1
    )

    assert 1 in scheduler.roster["E003"]
    assert scheduler.roster["E003"][1] in {
        "A",
        "B",
        "C",
        "G",
        "W",
        "H",
        "L",
    }


def test_non_working_day_is_used_when_no_working_shift_is_possible():

    context = create_context()

    scheduler = RosterScheduler(context)

    scheduler._assign_member_requirements()

    # Give E003 a six-day working streak.
    for day in range(1, 7):
        scheduler.roster["E003"][day] = "A"

    # Day 7 cannot receive another working shift.
    scheduler._fill_unrequested_members(
        day=7
    )

    assert scheduler.roster["E003"][7] in {
        "W",
        "H",
        "L",
    }