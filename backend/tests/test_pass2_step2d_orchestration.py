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


def test_step2d_does_nothing_when_abc_are_already_covered():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements=empty_requirements(),
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements=empty_requirements(),
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
    scheduler.roster["E003"][2] = "C"

    original_roster = {
        employee_id: dict(assignments)
        for employee_id, assignments
        in scheduler.roster.items()
    }

    result = scheduler._run_pass2_step2d(2)

    assert result is True
    assert scheduler.roster == original_roster
    assert scheduler.warnings == []


def test_step2d_assigns_missing_c_before_b_and_a():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements=empty_requirements(),
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements=empty_requirements(),
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

    result = scheduler._run_pass2_step2d(2)

    assert result is True

    # C and B must be filled before the already-covered A.
    assert scheduler.roster["E002"][2] == "C"
    assert scheduler.roster["E003"][2] == "B"


def test_step2d_recalculates_candidate_map_after_each_assignment():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements=empty_requirements(),
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements=empty_requirements(),
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

    # Initially:
    #
    # B -> E002
    # C -> E002, E003
    #
    # Once E002 is used for B, the candidate map must be
    # rebuilt so E003 can subsequently cover C.

    original_get_candidates = (
        scheduler._get_step2d_coverage_candidates
    )

    calls = []

    def tracked_candidates(day):
        candidate_map = original_get_candidates(day)
        calls.append(candidate_map)
        return candidate_map

    scheduler._get_step2d_coverage_candidates = (
        tracked_candidates
    )

    result = scheduler._run_pass2_step2d(2)

    assert result is True

    # The map must have been rebuilt rather than reused.
    assert len(calls) >= 2


def test_step2d_continues_while_any_remaining_shift_has_candidate():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements=empty_requirements(),
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements=empty_requirements(),
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

    result = scheduler._run_pass2_step2d(2)

    assert result is True

    # There were still valid candidates for B/C, so Step 2(d)
    # must not stop prematurely.
    assert scheduler.roster["E002"][2] in {"B", "C"}
    assert scheduler.roster["E003"][2] in {"B", "C"}


def test_step2d_stops_when_no_candidate_exists_for_any_remaining_shift():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements=empty_requirements(),
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements=empty_requirements(),
        ),
        "E003": MemberRequirement(
            employee_id="E003",
            requirements=empty_requirements(),
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    # Leave only A/B/C coverage incomplete but make all remaining
    # free members unable to take the missing shifts by forcing
    # the candidate generator to return no candidates.

    scheduler.roster["E001"][2] = "A"

    scheduler._get_step2d_coverage_candidates = (
        lambda day: {
            "B": [],
            "C": [],
        }
    )

    result = scheduler._run_pass2_step2d(2)

    assert result is False


def test_step2d_generates_warning_when_coverage_remains_incomplete():

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

    scheduler.roster["E001"][2] = "A"

    scheduler._get_step2d_coverage_candidates = (
        lambda day: {
            "B": [],
            "C": [],
        }
    )

    result = scheduler._run_pass2_step2d(2)

    assert result is False

    assert (
        "Pending to allocate 2 shifts on 2 "
        "due to conflicting requirements"
        in scheduler.warnings
    )


def test_step2d_does_not_generate_warning_when_coverage_completes():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements=empty_requirements(),
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements=empty_requirements(),
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

    result = scheduler._run_pass2_step2d(2)

    assert result is True
    assert scheduler.warnings == []


def test_step2d_does_not_modify_requirement_state():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "W": [3],
            },
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements=empty_requirements(),
        ),
        "E003": MemberRequirement(
            employee_id="E003",
            requirements=empty_requirements(),
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    from copy import deepcopy

    original_active = deepcopy(
        scheduler.active_requirements
    )

    original_relaxed = deepcopy(
        scheduler.relaxed_requirements
    )

    scheduler.roster["E001"][2] = "A"

    scheduler._run_pass2_step2d(2)

    assert scheduler.active_requirements == original_active
    assert scheduler.relaxed_requirements == original_relaxed