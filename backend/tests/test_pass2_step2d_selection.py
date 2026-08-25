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


def test_step2d_selection_returns_none_when_no_candidates():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements=empty_requirements(),
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    result = scheduler._select_step2d_coverage_candidate(
        day=2,
        shift="C",
        candidates=[],
        candidate_map={"C": []},
    )

    assert result is None


def test_step2d_selection_prefers_previous_day_same_shift():

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

    # Both members are candidates for C today.
    #
    # E002 worked C yesterday, so E002 must be preferred.

    scheduler.roster["E002"][1] = "C"

    candidates = ["E001", "E002"]

    result = scheduler._select_step2d_coverage_candidate(
        day=2,
        shift="C",
        candidates=candidates,
        candidate_map={
            "C": ["E001", "E002"],
        },
    )

    assert result == "E002"


def test_step2d_selection_prefers_candidate_that_preserves_other_shift():

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

    # Missing shifts:
    #
    # B
    # C
    #
    # Candidates:
    #
    # E001 -> C only
    # E002 -> C only
    # E003 -> B only
    #
    # We are choosing someone for C.
    #
    # Both E001 and E002 are equivalent with respect to C,
    # and neither is needed for B.
    #
    # E001 should therefore be selected deterministically.

    candidates = ["E001", "E002"]

    candidate_map = {
        "B": ["E003"],
        "C": ["E001", "E002"],
    }

    result = scheduler._select_step2d_coverage_candidate(
        day=2,
        shift="C",
        candidates=candidates,
        candidate_map=candidate_map,
    )

    assert result == "E001"


def test_step2d_selection_preserves_only_candidate_for_other_shift():

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

    # Missing:
    #
    # B
    # C
    #
    # Candidates:
    #
    # E001 -> B or C
    # E002 -> C only
    #
    # We are selecting for C.
    #
    # E001 is also the only candidate for B, so E002
    # should be selected for C.

    candidates = ["E001", "E002"]

    candidate_map = {
        "B": ["E001"],
        "C": ["E001", "E002"],
    }

    result = scheduler._select_step2d_coverage_candidate(
        day=2,
        shift="C",
        candidates=candidates,
        candidate_map=candidate_map,
    )

    assert result == "E002"


def test_step2d_selection_is_deterministic_when_candidates_are_equal():

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

    candidates = ["E001", "E002"]

    candidate_map = {
        "C": ["E001", "E002"],
    }

    result = scheduler._select_step2d_coverage_candidate(
        day=2,
        shift="C",
        candidates=candidates,
        candidate_map=candidate_map,
    )

    assert result == "E001"


def test_step2d_selection_does_not_modify_roster():

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

    scheduler.roster["E001"][1] = "A"
    scheduler.roster["E002"][1] = "C"

    original_roster = {
        employee_id: dict(assignments)
        for employee_id, assignments in scheduler.roster.items()
    }

    result = scheduler._select_step2d_coverage_candidate(
        day=2,
        shift="C",
        candidates=["E001", "E002"],
        candidate_map={
            "C": ["E001", "E002"],
        },
    )

    assert result == "E002"

    assert scheduler.roster == original_roster


def test_step2d_selection_uses_step2d_candidate_map():

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

    # E001 is the only candidate for B.
    #
    # E001 and E002 can both perform C.
    #
    # Therefore E002 should be selected for C so E001
    # remains available for B.

    candidates = ["E001", "E002"]

    step2d_candidate_map = {
        "B": ["E001"],
        "C": ["E001", "E002"],
    }

    result = scheduler._select_step2d_coverage_candidate(
        day=2,
        shift="C",
        candidates=candidates,
        candidate_map=step2d_candidate_map,
    )

    assert result == "E002"