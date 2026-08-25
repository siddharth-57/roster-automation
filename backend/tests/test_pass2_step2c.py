from app.scheduler.context import (
    MemberRequirement,
    RosterContext,
)
from app.scheduler.scheduler import RosterScheduler


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


def create_context(requirements, days_in_month=10):
    members = list(requirements.keys())

    return RosterContext(
        year=2026,
        month=8,
        group_number="01",
        public_holidays=2,
        members=members,
        requirements=requirements,
        previous_assignments={},
        days_in_month=days_in_month,
        required_w_days=4,
    )


def test_members_with_active_requirements_are_identified():

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
            requirements=empty_requirements(),
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler._assign_member_requirements()

    members = scheduler._get_members_with_active_requirements(1)

    assert members == ["E001", "E002"]


def test_relaxed_requirement_is_not_active():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "A": [1, 2, 3, 4, 5, 6, 7],
            },
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements={
                **empty_requirements(),
                "B": [1],
            },
        ),
    }

    scheduler = RosterScheduler(
        create_context(
            requirements,
            days_in_month=7,
        )
    )

    scheduler._assign_member_requirements()

    # Day 7 is invalid because E001 already worked
    # six consecutive days.
    scheduler._validate_existing_requirement(
        "E001",
        7,
    )

    assert (
        "E001"
        not in scheduler._get_members_with_active_requirements(7)
    )


def test_requirement_coverage_candidates_use_active_requirements():

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
                "A": [1],
            },
        ),
        "E003": MemberRequirement(
            employee_id="E003",
            requirements={
                **empty_requirements(),
                "B": [1],
            },
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler.roster["E001"][1] = "A"
    scheduler.roster["E002"][1] = "A"
    scheduler.roster["E003"][1] = "B"

    candidates = scheduler._get_requirement_coverage_candidates(1)

    assert "C" in candidates
    assert "E001" in candidates["C"]


def test_free_members_are_not_in_requirement_candidates():

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
                "A": [1],
            },
        ),
        "E003": MemberRequirement(
            employee_id="E003",
            requirements=empty_requirements(),
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    # E001 has an active requirement and currently has
    # that requirement assigned.
    scheduler.roster["E001"][1] = "A"
    scheduler.roster["E002"][1] = "A"

    candidates = scheduler._get_requirement_coverage_candidates(1)

    # A is already covered.
    assert "A" not in candidates

    # E003 is free, so E003 must not appear in
    # requirement candidates.
    assert "E003" not in candidates["B"]
    assert "E003" not in candidates["C"]

    # E001 has an active requirement and can safely
    # replace A with C because E002 continues covering A.
    assert "E001" in candidates["C"]


def test_next_day_requirement_is_still_considered():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "A": [1],
                "B": [2],
            },
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler._assign_member_requirements()

    candidates = scheduler._get_requirement_coverage_candidates(1)

    # C today would conflict with tomorrow's B requirement.
    assert "E001" not in candidates["C"]


def test_six_previous_working_days_are_considered():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "A": [1, 2, 3, 4, 5, 6],
                "B": [7],
            },
        ),
    }

    scheduler = RosterScheduler(
        create_context(
            requirements,
            days_in_month=7,
        )
    )

    scheduler._assign_member_requirements()

    candidates = scheduler._get_requirement_coverage_candidates(7)

    # E001 has six consecutive working days before Day 7,
    # therefore no working shift can be assigned on Day 7.
    assert "E001" not in candidates.get("A", [])
    assert "E001" not in candidates.get("B", [])
    assert "E001" not in candidates.get("C", [])