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


# ---------------------------------------------------------
# 1. No candidates -> None
# ---------------------------------------------------------

def test_selection_returns_none_when_no_candidates():

    scheduler = RosterScheduler(
        create_context(
            {
                "E001": MemberRequirement(
                    employee_id="E001",
                    requirements=empty_requirements(),
                )
            }
        )
    )

    result = scheduler._select_requirement_coverage_candidate(
        day=2,
        shift="C",
        candidates=[],
        candidate_map={
            "C": [],
        },
    )

    assert result is None


# ---------------------------------------------------------
# 2. Prefer the member who worked the same shift
#    on the previous day.
# ---------------------------------------------------------

def test_selection_prefers_previous_day_same_shift():

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
                "W": [2],
            },
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    # E001 worked C yesterday.
    scheduler.roster["E001"][1] = "C"

    # E002 worked a different shift yesterday.
    scheduler.roster["E002"][1] = "A"

    candidates = ["E001", "E002"]

    candidate_map = {
        "C": ["E001", "E002"],
    }

    result = scheduler._select_requirement_coverage_candidate(
        day=2,
        shift="C",
        candidates=candidates,
        candidate_map=candidate_map,
    )

    assert result == "E001"


# ---------------------------------------------------------
# 3. Prefer the candidate that does not eliminate
#    the only candidate for another missing shift.
# ---------------------------------------------------------

def test_selection_prefers_candidate_that_preserves_other_shift():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
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

    # We are selecting someone for C.
    #
    # C can be covered by either E001 or E003.
    #
    # B can ONLY be covered by E001.
    #
    # Therefore:
    #
    # E001 -> C
    #     would eliminate the only B candidate.
    #
    # E003 -> C
    #     preserves E001 as the B candidate.
    #
    # Therefore E003 must be selected.

    candidates = ["E001", "E003"]

    candidate_map = {
        "C": ["E001", "E003"],
        "B": ["E001"],
    }

    result = scheduler._select_requirement_coverage_candidate(
        day=2,
        shift="C",
        candidates=candidates,
        candidate_map=candidate_map,
    )

    assert result == "E003"


# ---------------------------------------------------------
# 4. If candidates are otherwise equivalent, selection
#    is deterministic.
# ---------------------------------------------------------

def test_selection_is_deterministic_when_candidates_are_equal():

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
                "W": [2],
            },
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    candidates = ["E001", "E002"]

    candidate_map = {
        "C": ["E001", "E002"],
    }

    result = scheduler._select_requirement_coverage_candidate(
        day=2,
        shift="C",
        candidates=candidates,
        candidate_map=candidate_map,
    )

    assert result == "E001"


# ---------------------------------------------------------
# 5. Selection must not permanently modify the roster.
# ---------------------------------------------------------

def test_selection_does_not_modify_roster():

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

    scheduler.roster["E001"][2] = "A"
    scheduler.roster["E002"][2] = "A"
    scheduler.roster["E003"][2] = "B"

    original_roster = {
        employee_id: dict(assignments)
        for employee_id, assignments in scheduler.roster.items()
    }

    candidate_map = {
        "C": ["E001", "E002"],
        "B": ["E001", "E002"],
    }

    scheduler._select_requirement_coverage_candidate(
        day=2,
        shift="C",
        candidates=["E001", "E002"],
        candidate_map=candidate_map,
    )

    assert scheduler.roster == original_roster