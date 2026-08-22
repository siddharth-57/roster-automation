# returns all the people who have posted some requirement on a specific day to find out whose requirement can be relaxed 
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


def test_blocking_requirements_are_identified():

    context = create_context()

    scheduler = RosterScheduler(context)

    scheduler._assign_member_requirements()

    blocking = scheduler._get_blocking_requirements(
        day=1,
        shift="C",
    )

    employee_ids = {
        requirement["employee_id"]
        for requirement in blocking
    }

    assert employee_ids == {
        "E001",
        "E002",
        "E003",
        "E004",
        "E005",
    }


def test_unrequested_assignment_is_not_a_blocking_requirement():

    context = create_context()

    scheduler = RosterScheduler(context)

    scheduler._assign_member_requirements()

    # Add an assignment that was not requested by the member.
    scheduler.roster["E001"][1] = "G"

    blocking = scheduler._get_blocking_requirements(
        day=1,
        shift="C",
    )

    employee_ids = {
        requirement["employee_id"]
        for requirement in blocking
    }

    assert "E001" not in employee_ids