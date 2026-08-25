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


def test_step2c_returns_true_when_abc_is_already_covered():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "A": [2],
            },
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements={
                **empty_requirements(),
                "B": [2],
            },
        ),
        "E003": MemberRequirement(
            employee_id="E003",
            requirements={
                **empty_requirements(),
                "C": [2],
            },
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler.roster["E001"][2] = "A"
    scheduler.roster["E002"][2] = "B"
    scheduler.roster["E003"][2] = "C"

    result = scheduler._run_pass_2_step_2c(2)

    assert result is True

    assert scheduler.roster["E001"][2] == "A"
    assert scheduler.roster["E002"][2] == "B"
    assert scheduler.roster["E003"][2] == "C"

    assert scheduler.relaxed_requirements == []


def test_step2c_can_fill_one_missing_shift():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "A": [2],
            },
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements={
                **empty_requirements(),
                "B": [2],
            },
        ),
        "E003": MemberRequirement(
            employee_id="E003",
            requirements={
                **empty_requirements(),
                "W": [2],
            },
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler.roster["E001"][2] = "A"
    scheduler.roster["E002"][2] = "B"
    scheduler.roster["E003"][2] = "W"

    result = scheduler._run_pass_2_step_2c(2)

    assert result is True

    assert scheduler._get_daily_abc_coverage(2) == {
        "A",
        "B",
        "C",
    }

    assert scheduler.roster["E003"][2] == "C"

    assert {
        "employee_id": "E003",
        "day": 2,
        "shift": "W",
    } in scheduler.relaxed_requirements


def test_step2c_can_fill_multiple_missing_shifts():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "A": [2],
            },
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements={
                **empty_requirements(),
                "W": [2],
            },
        ),
        "E003": MemberRequirement(
            employee_id="E003",
            requirements={
                **empty_requirements(),
                "H": [2],
            },
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler.roster["E001"][2] = "A"
    scheduler.roster["E002"][2] = "W"
    scheduler.roster["E003"][2] = "H"

    result = scheduler._run_pass_2_step_2c(2)

    assert result is True

    assert scheduler._get_daily_abc_coverage(2) == {
        "A",
        "B",
        "C",
    }

    assert len(scheduler.relaxed_requirements) == 2


def test_step2c_recalculates_missing_shifts_after_each_commit():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "A": [2],
            },
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements={
                **empty_requirements(),
                "W": [2],
            },
        ),
        "E003": MemberRequirement(
            employee_id="E003",
            requirements={
                **empty_requirements(),
                "H": [2],
            },
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler.roster["E001"][2] = "A"
    scheduler.roster["E002"][2] = "W"
    scheduler.roster["E003"][2] = "H"

    result = scheduler._run_pass_2_step_2c(2)

    assert result is True

    coverage = scheduler._get_daily_abc_coverage(2)

    assert "A" in coverage
    assert "B" in coverage
    assert "C" in coverage


def test_step2c_does_not_reuse_relaxed_requirement():

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
        "E003": MemberRequirement(
            employee_id="E003",
            requirements={
                **empty_requirements(),
                "B": [2],
            },
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler.roster["E001"][2] = "W"
    scheduler.roster["E002"][2] = "A"
    scheduler.roster["E003"][2] = "B"

    result = scheduler._run_pass_2_step_2c(2)

    assert result is True

    relaxed = [
        item["employee_id"]
        for item in scheduler.relaxed_requirements
    ]

    # E001 may be relaxed once, but once its requirement
    # is relaxed it must no longer be an active requirement.
    assert "E001" in relaxed

    active_members = (
        scheduler._get_members_with_active_requirements(2)
    )

    assert "E001" not in active_members


def test_step2c_returns_false_when_no_valid_candidate_exists():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "A": [2],
            },
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements={
                **empty_requirements(),
                "B": [2],
            },
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler.roster["E001"][2] = "A"
    scheduler.roster["E002"][2] = "B"

    result = scheduler._run_pass_2_step_2c(2)

    assert result is False

    assert scheduler._get_missing_abc_shifts(2) == {
        "C",
    }


def test_step2c_does_not_modify_roster_when_no_candidate_exists():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "A": [2],
            },
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements={
                **empty_requirements(),
                "B": [2],
            },
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler.roster["E001"][2] = "A"
    scheduler.roster["E002"][2] = "B"

    original_roster = {
        employee_id: dict(assignments)
        for employee_id, assignments
        in scheduler.roster.items()
    }

    result = scheduler._run_pass_2_step_2c(2)

    assert result is False
    assert scheduler.roster == original_roster


def test_step2c_only_relaxes_active_requirements():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "A": [2],
            },
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements={
                **empty_requirements(),
                "B": [2],
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

    scheduler.roster["E001"][2] = "A"
    scheduler.roster["E002"][2] = "B"

    # E003 is free. Step 2(c) must not use it because
    # Step 2(c) is specifically for relaxing requirements.
    candidates = scheduler._get_requirement_coverage_candidates(2)

    assert "E003" not in candidates.get("C", [])

    # E001/E002 are active requirements, so they may appear
    # only if the proposed replacement passes validation.
    assert isinstance(candidates, dict)