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
                "C": [1],
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


def test_missing_daily_coverage():

    context = create_context()

    scheduler = RosterScheduler(context)

    scheduler._assign_member_requirements()

    assert scheduler._get_missing_daily_coverage(1) == []


def test_missing_c_coverage():

    context = create_context()

    context.requirements["E003"].requirements["C"] = []

    scheduler = RosterScheduler(context)

    scheduler._assign_member_requirements()

    assert scheduler._get_missing_daily_coverage(1) == ["C"]


def test_missing_a_and_b_coverage():

    context = create_context()

    context.requirements["E001"].requirements["A"] = []
    context.requirements["E002"].requirements["B"] = []

    scheduler = RosterScheduler(context)

    scheduler._assign_member_requirements()

    assert scheduler._get_missing_daily_coverage(1) == [
        "A",
        "B",
    ]