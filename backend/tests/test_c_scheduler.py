# tests for C distribution

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
        employee_id: MemberRequirement(
            employee_id=employee_id,
            requirements={
                "A": [],
                "B": [],
                "C": [],
                "G": [],
                "L": [],
                "W": [],
            },
        )
        for employee_id in members
    }

    return RosterContext(
        year=2026,
        month=8,
        group_number="01",
        public_holidays=0,
        members=members,
        requirements=requirements,
        previous_assignments={},
        days_in_month=12,
        required_w_days=4,
    )


def test_c_shifts_are_distributed():

    context = create_context()

    scheduler = RosterScheduler(context)

    scheduler._assign_c_shifts()

    counts = [
        scheduler._get_c_count(employee_id)
        for employee_id in context.members
    ]

    assert all(
        count >= 3
        for count in counts
    )

    assert all(
        count <= 5
        for count in counts
    )

# exactly one request is selected, and the other member remains available for a later valid assignment.
def test_conflicting_c_requirements_select_one_member():

    context = create_context()

    context.requirements["E001"].requirements["C"] = [5]
    context.requirements["E002"].requirements["C"] = [5]

    scheduler = RosterScheduler(context)

    scheduler._assign_c_shifts()

    e001_c_days = [
        day
        for day, shift
        in scheduler.roster["E001"].items()
        if shift == "C"
    ]

    e002_c_days = [
        day
        for day, shift
        in scheduler.roster["E002"].items()
        if shift == "C"
    ]

    assert (
        (5 in e001_c_days)
        !=
        (5 in e002_c_days)
    )