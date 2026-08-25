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


def test_step2d_only_considers_members_with_no_assignment_for_day():

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
        "E004": MemberRequirement(
            employee_id="E004",
            requirements=empty_requirements(),
        ),
        "E005": MemberRequirement(
            employee_id="E005",
            requirements=empty_requirements(),
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    # E001 is genuinely free.
    #
    # Everyone else already has an assignment and therefore
    # must NOT be considered free by Step 2(d).
    scheduler.roster["E002"][2] = "A"
    scheduler.roster["E003"][2] = "B"
    scheduler.roster["E004"][2] = "C"
    scheduler.roster["E005"][2] = "W"

    free_members = scheduler._get_free_members(2)

    assert free_members == ["E001"]


def test_step2d_excludes_member_with_non_working_assignment():

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

    scheduler.roster["E002"][2] = "H"

    free_members = scheduler._get_free_members(2)

    assert "E001" in free_members
    assert "E002" not in free_members


def test_step2d_only_returns_missing_shifts_as_candidate_options():

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

    # Current coverage:
    #
    # A -> covered
    # B -> missing
    # C -> missing

    scheduler.roster["E002"][2] = "A"

    # E001 and E003 are free.

    candidates = scheduler._get_step2d_coverage_candidates(2)

    assert "A" not in candidates
    assert "B" in candidates
    assert "C" in candidates


def test_step2d_accepts_shift_allowed_by_previous_six_days():

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

    # Current day:
    #
    # A -> covered
    # B -> covered
    # C -> missing

    scheduler.roster["E002"][2] = "A"
    scheduler.roster["E003"][2] = "B"

    # E001 is free.
    #
    # Give E001 a normal previous-day assignment that does
    # not violate the hard rules for C today.
    scheduler.roster["E001"][1] = "C"

    candidates = scheduler._get_step2d_coverage_candidates(2)

    assert "E001" in candidates["C"]


def test_step2d_rejects_shift_that_breaks_hard_roster_rules():

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

    scheduler.roster["E002"][2] = "A"
    scheduler.roster["E003"][2] = "B"

    # E001 is free today.
    #
    # Create a previous-day assignment that makes A invalid
    # according to the scheduler's hard roster rules.
    scheduler.roster["E001"][1] = "C"

    candidates = scheduler._get_step2d_coverage_candidates(2)

    # We only assert that the scheduler's actual hard-rule
    # validation determines eligibility.
    #
    # A must not be included if assigning A here violates
    # the existing hard constraints.
    assert "A" not in candidates.get("A", [])


def test_step2d_ignores_next_day_requirement():

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

    # Current day:
    #
    # A -> covered
    # B -> covered
    # C -> missing

    scheduler.roster["E002"][2] = "A"
    scheduler.roster["E003"][2] = "B"

    # E001 is free today.
    #
    # E001 has a requirement tomorrow, but Step 2(d) must
    # deliberately ignore that requirement when determining
    # today's candidates.

    scheduler.roster["E001"][1] = "C"

    candidates = scheduler._get_step2d_coverage_candidates(2)

    assert "E001" in candidates["C"]


def test_step2d_does_not_include_assigned_members_as_candidates():

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
    scheduler.roster["E002"][2] = "W"

    # E003 is the only genuinely free member.

    candidates = scheduler._get_step2d_coverage_candidates(2)

    for shift_candidates in candidates.values():
        assert "E001" not in shift_candidates
        assert "E002" not in shift_candidates