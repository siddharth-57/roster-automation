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


def create_context(
    requirements,
    days_in_month=10,
):
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


def test_free_member_can_be_candidate_for_valid_shifts():
    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements=empty_requirements(),
        )
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler._assign_member_requirements()

    candidates = scheduler._get_coverage_candidates(1)

    assert "E001" in candidates["A"]
    assert "E001" in candidates["B"]
    assert "E001" in candidates["C"]


def test_assigned_member_is_not_a_candidate():
    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "A": [1],
            },
        )
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler._assign_member_requirements()

    candidates = scheduler._get_coverage_candidates(1)

    assert "A" not in candidates
    assert "E001" not in candidates["B"]
    assert "E001" not in candidates["C"]

def test_c_is_not_candidate_when_next_day_requires_working_shift():
    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "B": [2],
            },
        )
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler._assign_member_requirements()

    candidates = scheduler._get_coverage_candidates(1)

    assert "E001" not in candidates["C"]


def test_c_is_candidate_when_next_day_is_non_working():
    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "W": [2],
            },
        )
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler._assign_member_requirements()

    candidates = scheduler._get_coverage_candidates(1)

    assert "E001" in candidates["C"]


def test_six_previous_working_days_block_new_working_shift():
    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "A": [1, 2, 3, 4, 5, 6],
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

    candidates = scheduler._get_coverage_candidates(7)

    assert "E001" not in candidates["A"]
    assert "E001" not in candidates["B"]
    assert "E001" not in candidates["C"]


def test_candidate_map_contains_only_free_members():
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

    scheduler._assign_member_requirements()

    candidates = scheduler._get_coverage_candidates(1)

    # A is already covered by E001.
    assert "A" not in candidates
    
    # Only free members can be candidates for B and C.
    assert "E001" not in candidates["B"]
    assert "E001" not in candidates["C"]
    
    assert "E002" in candidates["B"]
    assert "E002" in candidates["C"]
    
    assert "E003" in candidates["B"]
    assert "E003" in candidates["C"]


def test_previous_day_same_shift_candidate_is_preferred():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "B": [1],
            },
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

    # E001 worked B yesterday.
    scheduler.roster["E001"][1] = "B"

    candidates = ["E001", "E002"]

    selected = scheduler._select_coverage_candidate(
        day=2,
        shift="B",
        candidates=candidates,
    )

    assert selected == "E001"


def test_candidate_preserving_other_shift_coverage_is_preferred():

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

    # Both are candidates for B.
    # E001 is also the only candidate for C.
    scheduler._can_assign_shift_with_next_day_requirement = (
        lambda employee_id, day, shift: (
            employee_id == "E001"
            if shift == "C"
            else True
        )
    )

    selected = scheduler._select_coverage_candidate(
        day=1,
        shift="B",
        candidates=["E001", "E002"],
    )

    assert selected == "E002"


def test_step_2b_completes_abc_coverage():
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

    scheduler._assign_member_requirements()

    result = scheduler._fill_abc_coverage_from_free_members(1)

    assert result is True

    assert scheduler._get_daily_abc_coverage(1) == {
        "A",
        "B",
        "C",
    }

def test_step_2b_assigns_c_before_b_and_a():
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

    scheduler._assign_member_requirements()

    scheduler._fill_abc_coverage_from_free_members(1)

    assigned_shifts = [
        scheduler.roster[employee_id][1]
        for employee_id in scheduler.context.members
    ]

    assert "C" in assigned_shifts
    assert "B" in assigned_shifts
    assert "A" in assigned_shifts
    
def test_step_2b_returns_false_when_coverage_cannot_be_completed():
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

    scheduler._assign_member_requirements()

    result = scheduler._fill_abc_coverage_from_free_members(1)

    assert result is False

    # C should still be missing.
    assert "C" in scheduler._get_missing_abc_shifts(1)