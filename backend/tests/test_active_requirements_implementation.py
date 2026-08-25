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


def test_active_requirements_is_initialized_from_original_requirements():
    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "A": [1, 5],
                "C": [3],
            },
        )
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    assert (
        scheduler.active_requirements["E001"].requirements
        == requirements["E001"].requirements
    )


def test_active_requirements_is_independent_of_original_requirements():
    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "A": [1, 5],
            },
        )
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler._remove_active_requirement(
        "E001",
        1,
        "A",
    )

    # Active requirement was removed.
    assert (
        1
        not in scheduler.active_requirements[
            "E001"
        ].requirements["A"]
    )

    # Original frontend requirement remains untouched.
    assert (
        1
        in scheduler.context.requirements[
            "E001"
        ].requirements["A"]
    )


def test_remove_active_requirement_removes_only_requested_day():
    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "A": [1, 3, 5],
            },
        )
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler._remove_active_requirement(
        "E001",
        3,
        "A",
    )

    assert (
        scheduler.active_requirements[
            "E001"
        ].requirements["A"]
        == [1, 5]
    )


def test_remove_active_requirement_does_not_remove_other_shifts():
    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "A": [1],
                "B": [2],
                "C": [3],
            },
        )
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler._remove_active_requirement(
        "E001",
        1,
        "A",
    )

    assert (
        scheduler.active_requirements[
            "E001"
        ].requirements["A"]
        == []
    )

    assert (
        scheduler.active_requirements[
            "E001"
        ].requirements["B"]
        == [2]
    )

    assert (
        scheduler.active_requirements[
            "E001"
        ].requirements["C"]
        == [3]
    )


def test_invalid_requirement_is_removed_from_active_requirements():
    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "A": [1, 2, 3, 4, 5, 6, 7],
            },
        )
    }

    scheduler = RosterScheduler(
        create_context(
            requirements,
            days_in_month=7,
        )
    )

    scheduler._assign_member_requirements()

    # Day 7 should initially contain the Pass 1 requirement.
    assert scheduler.roster["E001"].get(7) == "A"

    scheduler._validate_existing_requirement(
        "E001",
        7,
    )

    # Day 7 requirement should have been removed from the
    # active requirements because it was invalid.
    assert (
        7
        not in scheduler.active_requirements[
            "E001"
        ].requirements["A"]
    )

    # Original frontend requirement must remain untouched.
    assert (
        7
        in scheduler.context.requirements[
            "E001"
        ].requirements["A"]
    )


def test_invalid_requirement_is_recorded_as_relaxed():
    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "A": [1, 2, 3, 4, 5, 6, 7],
            },
        )
    }

    scheduler = RosterScheduler(
        create_context(
            requirements,
            days_in_month=7,
        )
    )

    scheduler._assign_member_requirements()

    scheduler._validate_existing_requirement(
        "E001",
        7,
    )

    assert {
        "employee_id": "E001",
        "day": 7,
        "shift": "A",
    } in scheduler.relaxed_requirements


def test_removing_active_requirement_for_missing_entry_is_safe():
    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements=empty_requirements(),
        )
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler._remove_active_requirement(
        "E001",
        1,
        "A",
    )

    assert (
        scheduler.active_requirements[
            "E001"
        ].requirements["A"]
        == []
    )