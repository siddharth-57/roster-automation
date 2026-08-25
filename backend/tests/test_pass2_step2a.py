from app.scheduler.context import (
    MemberRequirement,
    RosterContext,
)
from app.scheduler.scheduler import RosterScheduler


def create_context(requirements):
    members = list(requirements.keys())

    return RosterContext(
        year=2026,
        month=8,
        group_number="01",
        public_holidays=2,
        members=members,
        requirements=requirements,
        previous_assignments={},
        days_in_month=5,
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


def test_daily_abc_coverage_is_detected():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "A": [1],
            },
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements={
                **empty_requirements(),
                "C": [1],
            },
        ),
        "E003": MemberRequirement(
            employee_id="E003",
            requirements={
                **empty_requirements(),
                "W": [1],
            },
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler._assign_member_requirements()

    assert scheduler._get_daily_abc_coverage(1) == {
        "A",
        "C",
    }


def test_missing_abc_shifts_are_detected():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "A": [1],
            },
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements={
                **empty_requirements(),
                "C": [1],
            },
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler._assign_member_requirements()

    assert scheduler._get_missing_abc_shifts(1) == {
        "B",
    }


def test_no_missing_abc_shifts_when_all_are_covered():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "A": [1],
            },
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements={
                **empty_requirements(),
                "B": [1],
            },
        ),
        "E003": MemberRequirement(
            employee_id="E003",
            requirements={
                **empty_requirements(),
                "C": [1],
            },
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler._assign_member_requirements()

    assert scheduler._get_daily_abc_coverage(1) == {
        "A",
        "B",
        "C",
    }

    assert scheduler._get_missing_abc_shifts(1) == set()


def test_missing_all_abc_shifts_when_no_one_is_assigned():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements=empty_requirements(),
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements=empty_requirements(),
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler._assign_member_requirements()

    assert scheduler._get_daily_abc_coverage(1) == set()

    assert scheduler._get_missing_abc_shifts(1) == {
        "A",
        "B",
        "C",
    }