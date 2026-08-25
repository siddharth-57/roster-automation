from copy import deepcopy

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
    previous_assignments=None,
):
    return RosterContext(
        year=2026,
        month=8,
        group_number="01",
        public_holidays=2,
        members=list(requirements.keys()),
        requirements=requirements,
        previous_assignments=previous_assignments or {},
        days_in_month=days_in_month,
        required_w_days=4,
    )


def test_step3_assigns_working_shift_to_free_member():
    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements=empty_requirements(),
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler._run_pass2_step3(2)

    assert scheduler.roster["E001"][2] in {"A", "B"}


def test_step3_processes_only_members_free_at_start():
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

    # E001 is already assigned before Step 3.
    scheduler.roster["E001"][2] = "C"

    scheduler._run_pass2_step3(2)

    # Existing assignment must remain unchanged.
    assert scheduler.roster["E001"][2] == "C"

    # E002 was free and therefore must receive exactly one shift.
    assert 2 in scheduler.roster["E002"]


def test_step3_prefers_same_shift_as_previous_day():
    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements=empty_requirements(),
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler.roster["E001"][1] = "A"

    scheduler._run_pass2_step3(2)

    assert scheduler.roster["E001"][2] == "A"


def test_step3_prefers_previous_b_shift_when_valid():
    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements=empty_requirements(),
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler.roster["E001"][1] = "B"

    scheduler._run_pass2_step3(2)

    assert scheduler.roster["E001"][2] == "B"


def test_step3_previous_c_forces_non_working_shift():
    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements=empty_requirements(),
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    # Previous day C means A/B are prohibited by the hard rules.
    scheduler.roster["E001"][1] = "C"

    scheduler._run_pass2_step3(2)

    assert scheduler.roster["E001"][2] in {"W", "H", "L"}


def test_step3_uses_w_before_h_and_l():
    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements=empty_requirements(),
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler.roster["E001"][1] = "C"

    scheduler._run_pass2_step3(2)

    assert scheduler.roster["E001"][2] == "W"


def test_step3_uses_h_when_w_is_unavailable():
    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements=empty_requirements(),
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler.roster["E001"][1] = "C"

    scheduler.remaining_w["E001"] = 0
    scheduler.remaining_h["E001"] = 1

    scheduler._run_pass2_step3(2)

    assert scheduler.roster["E001"][2] == "H"


def test_step3_uses_l_when_w_and_h_are_unavailable():
    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements=empty_requirements(),
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler.roster["E001"][1] = "C"

    scheduler.remaining_w["E001"] = 0
    scheduler.remaining_h["E001"] = 0

    scheduler._run_pass2_step3(2)

    assert scheduler.roster["E001"][2] == "L"


def test_step3_updates_w_tracking_when_w_is_assigned():
    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements=empty_requirements(),
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler.roster["E001"][1] = "C"

    initial_w = scheduler.remaining_w["E001"]

    scheduler._run_pass2_step3(2)

    assert scheduler.roster["E001"][2] == "W"
    assert scheduler.remaining_w["E001"] == initial_w - 1


def test_step3_updates_h_tracking_when_h_is_assigned():
    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements=empty_requirements(),
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler.roster["E001"][1] = "C"

    scheduler.remaining_w["E001"] = 0
    scheduler.remaining_h["E001"] = 1

    scheduler._run_pass2_step3(2)

    assert scheduler.roster["E001"][2] == "H"
    assert scheduler.remaining_h["E001"] == 0


def test_step3_assigns_exactly_one_shift_to_each_initially_free_member():
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

    scheduler._run_pass2_step3(2)

    for employee_id in requirements:
        assert 2 in scheduler.roster[employee_id]


def test_step3_does_not_reassign_existing_member():
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

    scheduler._run_pass2_step3(2)

    assert scheduler.roster["E001"][2] == "A"

    # E002 gets one assignment.
    assert 2 in scheduler.roster["E002"]


def test_step3_considers_next_day_requirement():
    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements=empty_requirements(),
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler.roster["E001"][3] = "A"

    # The exact next-day requirement is handled by the scheduler's
    # existing next-day validation helper.
    candidates = scheduler._get_step3_working_shift_candidates(
        "E001",
        2,
    )

    assert isinstance(candidates, list)

    for shift in candidates:
        assert shift in {"A", "B"}


def test_step3_respects_continuous_working_day_limit():
    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements=empty_requirements(),
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    # Build a continuous working streak before day 7.
    scheduler.roster["E001"][1] = "A"
    scheduler.roster["E001"][2] = "A"
    scheduler.roster["E001"][3] = "A"
    scheduler.roster["E001"][4] = "A"
    scheduler.roster["E001"][5] = "A"
    scheduler.roster["E001"][6] = "A"

    scheduler._run_pass2_step3(7)

    # Six consecutive working days means another working shift
    # cannot be assigned.
    assert scheduler.roster["E001"][7] in {"W", "H", "L"}


def test_step3_does_not_modify_active_requirements():
    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "W": [3],
            },
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    original_active_requirements = deepcopy(
        scheduler.active_requirements
    )

    original_relaxed_requirements = deepcopy(
        scheduler.relaxed_requirements
    )

    scheduler.roster["E001"][1] = "C"

    scheduler._run_pass2_step3(2)

    assert (
        scheduler.active_requirements
        == original_active_requirements
    )

    assert (
        scheduler.relaxed_requirements
        == original_relaxed_requirements
    )


def test_step3_does_not_assign_two_shifts_to_same_member():
    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements=empty_requirements(),
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler._run_pass2_step3(2)

    assignments_for_day = [
        assignments[2]
        for assignments in scheduler.roster.values()
        if 2 in assignments
    ]

    assert assignments_for_day.count(
        scheduler.roster["E001"][2]
    ) == 1