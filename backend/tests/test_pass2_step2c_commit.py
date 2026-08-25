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


def test_w_to_c_updates_w_and_c_tracking():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "W": [2],
            },
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements={
                **empty_requirements(),
                "A": [2],
            },
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler.roster["E001"][2] = "W"
    scheduler.roster["E002"][2] = "A"

    initial_remaining_w = scheduler.remaining_w["E001"]
    initial_c_count = scheduler.c_shift_counts["E001"]

    result = scheduler._commit_requirement_coverage_replacement(
        "E001",
        2,
        "C",
    )

    assert result is True
    assert scheduler.roster["E001"][2] == "C"

    assert scheduler.remaining_w["E001"] == (
        initial_remaining_w + 1
    )

    assert scheduler.c_shift_counts["E001"] == (
        initial_c_count + 1
    )


def test_h_to_c_updates_h_and_c_tracking():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "H": [2],
            },
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements={
                **empty_requirements(),
                "A": [2],
            },
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler.roster["E001"][2] = "H"
    scheduler.roster["E002"][2] = "A"

    initial_remaining_h = scheduler.remaining_h["E001"]
    initial_c_count = scheduler.c_shift_counts["E001"]

    result = scheduler._commit_requirement_coverage_replacement(
        "E001",
        2,
        "C",
    )

    assert result is True
    assert scheduler.roster["E001"][2] == "C"

    assert scheduler.remaining_h["E001"] == (
        initial_remaining_h + 1
    )

    assert scheduler.c_shift_counts["E001"] == (
        initial_c_count + 1
    )


def test_c_to_a_updates_c_tracking_when_c_remains_covered():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "C": [2],
            },
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements={
                **empty_requirements(),
                "C": [2],
            },
        ),
        "E003": MemberRequirement(
            employee_id="E003",
            requirements={
                **empty_requirements(),
                "A": [2],
            },
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler.roster["E001"][2] = "C"
    scheduler.roster["E002"][2] = "C"
    scheduler.roster["E003"][2] = "A"

    initial_c_count = scheduler.c_shift_counts["E001"]

    result = scheduler._commit_requirement_coverage_replacement(
        "E001",
        2,
        "A",
    )

    assert result is True
    assert scheduler.roster["E001"][2] == "A"

    assert scheduler.c_shift_counts["E001"] == (
        initial_c_count - 1
    )


def test_relaxed_requirement_is_removed_from_active_requirements():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "W": [2],
            },
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements={
                **empty_requirements(),
                "A": [2],
            },
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler.roster["E001"][2] = "W"
    scheduler.roster["E002"][2] = "A"

    result = scheduler._commit_requirement_coverage_replacement(
        "E001",
        2,
        "C",
    )

    assert result is True

    assert (
        2
        not in scheduler.active_requirements[
            "E001"
        ].requirements["W"]
    )


def test_relaxed_requirement_is_recorded():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "W": [2],
            },
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements={
                **empty_requirements(),
                "A": [2],
            },
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler.roster["E001"][2] = "W"
    scheduler.roster["E002"][2] = "A"

    result = scheduler._commit_requirement_coverage_replacement(
        "E001",
        2,
        "C",
    )

    assert result is True

    assert {
        "employee_id": "E001",
        "day": 2,
        "shift": "W",
    } in scheduler.relaxed_requirements


def test_new_shift_is_permanently_assigned():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "W": [2],
            },
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements={
                **empty_requirements(),
                "A": [2],
            },
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler.roster["E001"][2] = "W"
    scheduler.roster["E002"][2] = "A"

    result = scheduler._commit_requirement_coverage_replacement(
        "E001",
        2,
        "C",
    )

    assert result is True
    assert scheduler.roster["E001"][2] == "C"


def test_invalid_replacement_is_rejected_without_changes():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "W": [2],
            },
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements={
                **empty_requirements(),
                "A": [2],
            },
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler.roster["E001"][2] = "W"
    scheduler.roster["E002"][2] = "A"

    original_remaining_w = scheduler.remaining_w["E001"]
    original_remaining_h = scheduler.remaining_h["E001"]
    original_c_count = scheduler.c_shift_counts["E001"]

    result = scheduler._commit_requirement_coverage_replacement(
        "E001",
        2,
        "INVALID",
    )

    assert result is False

    assert scheduler.roster["E001"][2] == "W"

    assert scheduler.remaining_w["E001"] == original_remaining_w
    assert scheduler.remaining_h["E001"] == original_remaining_h
    assert scheduler.c_shift_counts["E001"] == original_c_count

    assert (
        2
        in scheduler.active_requirements[
            "E001"
        ].requirements["W"]
    )


def test_non_active_requirement_cannot_be_committed():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements=empty_requirements(),
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements={
                **empty_requirements(),
                "A": [2],
            },
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler.roster["E001"][2] = "W"
    scheduler.roster["E002"][2] = "A"

    original_roster = dict(
        scheduler.roster["E001"]
    )

    result = scheduler._commit_requirement_coverage_replacement(
        "E001",
        2,
        "C",
    )

    assert result is False
    assert scheduler.roster["E001"] == original_roster


def test_replacement_is_rejected_when_old_shift_becomes_uncovered():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "C": [2],
            },
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements={
                **empty_requirements(),
                "A": [2],
            },
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler.roster["E001"][2] = "C"
    scheduler.roster["E002"][2] = "A"

    original_roster = dict(
        scheduler.roster["E001"]
    )

    original_c_count = scheduler.c_shift_counts["E001"]

    result = scheduler._commit_requirement_coverage_replacement(
        "E001",
        2,
        "A",
    )

    assert result is False

    assert scheduler.roster["E001"] == original_roster
    assert scheduler.c_shift_counts["E001"] == original_c_count