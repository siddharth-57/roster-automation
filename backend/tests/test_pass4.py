from app.scheduler.context import MemberRequirement, RosterContext
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
    return RosterContext(
        year=2026,
        month=8,
        group_number="01",
        public_holidays=2,
        members=list(requirements.keys()),
        requirements=requirements,
        previous_assignments={},
        days_in_month=days_in_month,
        required_w_days=4,
    )


def create_scheduler(
    employee_ids,
    days_in_month=10,
):
    requirements = {
        employee_id: MemberRequirement(
            employee_id=employee_id,
            requirements=empty_requirements(),
        )
        for employee_id in employee_ids
    }

    return RosterScheduler(
        create_context(
            requirements,
            days_in_month=days_in_month,
        )
    )


# ------------------------------------------------------------------
# Basic eligibility
# ------------------------------------------------------------------


def test_pass4_member_with_remaining_w_and_ab_shift_can_be_selected():
    scheduler = create_scheduler(
        ["E001", "E002"]
    )

    day = 1

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "A"

    scheduler.remaining_w["E001"] = 1

    assert scheduler.roster["E001"][day] == "A"
    assert scheduler.roster["E002"][day] == "A"


def test_pass4_member_with_remaining_h_and_ab_shift_can_be_selected():
    scheduler = create_scheduler(
        ["E001", "E002"]
    )

    day = 1

    scheduler.roster["E001"][day] = "B"
    scheduler.roster["E002"][day] = "B"

    scheduler.remaining_h["E001"] = 1

    assert scheduler.roster["E001"][day] == "B"
    assert scheduler.roster["E002"][day] == "B"


# ------------------------------------------------------------------
# Same-shift protection
# ------------------------------------------------------------------


def test_pass4_does_not_remove_last_member_from_a_shift():
    scheduler = create_scheduler(
        ["E001", "E002"]
    )

    day = 1

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "B"

    scheduler.remaining_w["E001"] = 1

    scheduler._run_pass4()

    assert scheduler.roster["E001"][day] == "A"


def test_pass4_does_not_remove_last_member_from_b_shift():
    scheduler = create_scheduler(
        ["E001", "E002"]
    )

    day = 1

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "B"

    scheduler.remaining_w["E002"] = 1

    scheduler._run_pass4()

    assert scheduler.roster["E002"][day] == "B"


def test_pass4_can_remove_member_when_another_same_shift_exists():
    scheduler = create_scheduler(
        ["E001", "E002", "E003"]
    )

    day = 1

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "A"
    scheduler.roster["E003"][day] = "B"

    scheduler.remaining_w["E001"] = 1

    scheduler._run_pass4()

    assert scheduler.roster["E001"][day] == "W"
    assert scheduler.roster["E002"][day] == "A"


# ------------------------------------------------------------------
# Active requirement relaxation
# ------------------------------------------------------------------


def test_pass4_can_assign_w_on_day_with_active_requirement():
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
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    day = 1

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "A"

    scheduler.remaining_w["E001"] = 1

    scheduler._run_pass4()

    assert scheduler.roster["E001"][day] == "W"


def test_pass4_removes_relaxed_requirement_from_active_requirements():
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
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    day = 1

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "A"

    scheduler.remaining_w["E001"] = 1

    scheduler._run_pass4()

    active_requirement = scheduler._get_active_requirement_for_day(
        "E001",
        day,
    )

    assert active_requirement is None


def test_pass4_adds_relaxed_requirement_to_relaxed_requirements():
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
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    day = 1

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "A"

    scheduler.remaining_w["E001"] = 1

    scheduler._run_pass4()

    assert {
        "employee_id": "E001",
        "day": 1,
        "shift": "A",
    } in scheduler.relaxed_requirements


def test_pass4_does_not_modify_original_frontend_requirements():
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
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler.roster["E001"][1] = "A"
    scheduler.roster["E002"][1] = "A"

    scheduler.remaining_w["E001"] = 1

    scheduler._run_pass4()

    assert scheduler.context.requirements[
        "E001"
    ].requirements["A"] == [1]


# ------------------------------------------------------------------
# W / H quota handling
# ------------------------------------------------------------------


def test_pass4_decrements_remaining_w():
    scheduler = create_scheduler(
        ["E001", "E002"]
    )

    day = 1

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "A"

    scheduler.remaining_w["E001"] = 2

    scheduler._run_pass4()

    assert scheduler.remaining_w["E001"] == 1


def test_pass4_decrements_remaining_h():
    scheduler = create_scheduler(
        ["E001", "E002"]
    )

    day = 1

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "A"

    # E001 needs H.
    scheduler.remaining_w["E001"] = 0
    scheduler.remaining_h["E001"] = 1

    # E002 is only here to provide the required second
    # A-shift member. E002 must not be changed during Pass 4.
    scheduler.remaining_w["E002"] = 0
    scheduler.remaining_h["E002"] = 0

    scheduler._run_pass4()

    assert scheduler.remaining_h["E001"] == 0
    assert scheduler.roster["E001"][day] == "H"
    assert scheduler.roster["E002"][day] == "A"


def test_pass4_processes_w_before_h():
    scheduler = create_scheduler(
        ["E001", "E002", "E003"]
    )

    day = 1

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "A"
    scheduler.roster["E003"][day] = "B"

    scheduler.remaining_w["E001"] = 1
    scheduler.remaining_h["E001"] = 1

    scheduler._run_pass4()

    # W must be satisfied before H for the same member.
    assert scheduler.remaining_w["E001"] == 0


# ------------------------------------------------------------------
# Eligibility restrictions
# ------------------------------------------------------------------


def test_pass4_does_not_assign_w_to_member_with_no_remaining_w():
    scheduler = create_scheduler(
        ["E001", "E002"]
    )

    day = 1

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "A"

    scheduler.remaining_w["E001"] = 0
    scheduler.remaining_h["E001"] = 0

    scheduler._run_pass4()

    assert scheduler.roster["E001"][day] == "A"


def test_pass4_does_not_assign_h_to_member_with_no_remaining_h():
    scheduler = create_scheduler(
        ["E001", "E002"]
    )

    day = 1

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "A"

    scheduler.remaining_w["E001"] = 0
    scheduler.remaining_h["E001"] = 0

    scheduler._run_pass4()

    assert scheduler.roster["E001"][day] == "A"


def test_pass4_does_not_modify_c_shift():
    scheduler = create_scheduler(
        ["E001", "E002"]
    )

    day = 1

    scheduler.roster["E001"][day] = "C"
    scheduler.roster["E002"][day] = "A"

    scheduler.remaining_w["E001"] = 1

    scheduler._run_pass4()

    assert scheduler.roster["E001"][day] == "C"


def test_pass4_does_not_modify_existing_w_or_h():
    scheduler = create_scheduler(
        ["E001", "E002"]
    )

    day = 1

    scheduler.roster["E001"][day] = "W"
    scheduler.roster["E002"][day] = "A"

    scheduler.remaining_h["E001"] = 1

    scheduler._run_pass4()

    assert scheduler.roster["E001"][day] == "W"


# ------------------------------------------------------------------
# Multiple eligible days
# ------------------------------------------------------------------


def test_pass4_can_assign_remaining_w_on_multiple_days():
    scheduler = create_scheduler(
        ["E001", "E002"],
        days_in_month=5,
    )

    for day in (1, 2, 3):
        scheduler.roster["E001"][day] = "A"
        scheduler.roster["E002"][day] = "A"

    scheduler.remaining_w["E001"] = 2

    scheduler._run_pass4()

    assert scheduler.remaining_w["E001"] == 0

    assert sum(
        scheduler.roster["E001"].get(day) == "W"
        for day in (1, 2, 3)
    ) == 2


def test_pass4_traverses_multiple_days():
    scheduler = create_scheduler(
        ["E001", "E002"],
        days_in_month=5,
    )

    for day in range(1, 6):
        scheduler.roster["E001"][day] = "A"
        scheduler.roster["E002"][day] = "A"

    scheduler.remaining_w["E001"] = 3

    scheduler._run_pass4()

    assert scheduler.remaining_w["E001"] == 0

    assert sum(
        scheduler.roster["E001"].get(day) == "W"
        for day in range(1, 6)
    ) == 3


# ------------------------------------------------------------------
# Requirement relaxation only when actually assigned W/H
# ------------------------------------------------------------------


def test_pass4_does_not_relax_requirement_if_member_is_not_selected():
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

    day = 1

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "A"
    scheduler.roster["E003"][day] = "B"

    # Only E001 requires W.
    scheduler.remaining_w["E001"] = 1
    scheduler.remaining_w["E002"] = 0
    scheduler.remaining_w["E003"] = 0

    scheduler._run_pass4()

    assert scheduler.roster["E001"][day] == "W"

    assert scheduler._get_active_requirement_for_day(
        "E001",
        day,
    ) is None

    # E002 was not selected and therefore its requirement remains active.
    assert scheduler._get_active_requirement_for_day(
        "E002",
        day,
    ) == "A"


# ------------------------------------------------------------------
# Day-specific execution
# ------------------------------------------------------------------


def test_pass4_can_process_single_day():
    scheduler = create_scheduler(
        ["E001", "E002"],
        days_in_month=5,
    )

    scheduler.roster["E001"][1] = "A"
    scheduler.roster["E002"][1] = "A"

    scheduler.roster["E001"][2] = "A"
    scheduler.roster["E002"][2] = "A"

    scheduler.remaining_w["E001"] = 1

    scheduler._run_pass4(day=2)

    assert scheduler.roster["E001"][2] == "W"
    assert scheduler.roster["E001"][1] == "A"