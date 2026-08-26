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


def create_scheduler(members, days_in_month=5):
    requirements = {
        employee_id: MemberRequirement(
            employee_id=employee_id,
            requirements=empty_requirements(),
        )
        for employee_id in members
    }

    context = RosterContext(
        members=members,
        year=2026,
        month=8,
        group_number="01",
        public_holidays=0,
        requirements=requirements,
        previous_assignments={},
        days_in_month=days_in_month,
        required_w_days=0,
    )

    return RosterScheduler(context)


# ------------------------------------------------------------------
# A/B BALANCING
# ------------------------------------------------------------------


def test_pass5_changes_a_to_b_when_a_exceeds_b_by_2():
    scheduler = create_scheduler(
        ["E001", "E002", "E003", "E004"]
    )

    day = 1

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "A"
    scheduler.roster["E003"][day] = "A"
    scheduler.roster["E004"][day] = "B"

    scheduler._run_pass5()

    counts = scheduler._get_pass5_shift_counts(day)

    assert counts["A"] == 2
    assert counts["B"] == 2


def test_pass5_changes_b_to_a_when_b_exceeds_a_by_2():
    scheduler = create_scheduler(
        ["E001", "E002", "E003", "E004"]
    )

    day = 1

    scheduler.roster["E001"][day] = "B"
    scheduler.roster["E002"][day] = "B"
    scheduler.roster["E003"][day] = "B"
    scheduler.roster["E004"][day] = "A"

    scheduler._run_pass5()

    counts = scheduler._get_pass5_shift_counts(day)

    assert counts["A"] == 2
    assert counts["B"] == 2


def test_pass5_changes_a_to_g_when_a_exceeds_b_by_1():
    scheduler = create_scheduler(
        ["E001", "E002", "E003"]
    )

    day = 1

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "A"
    scheduler.roster["E003"][day] = "B"

    scheduler._run_pass5()

    counts = scheduler._get_pass5_shift_counts(day)

    assert counts["A"] == 1
    assert counts["B"] == 1
    assert counts["G"] == 1


def test_pass5_changes_b_to_g_when_b_exceeds_a_by_1():
    scheduler = create_scheduler(
        ["E001", "E002", "E003"]
    )

    day = 1

    scheduler.roster["E001"][day] = "B"
    scheduler.roster["E002"][day] = "B"
    scheduler.roster["E003"][day] = "A"

    scheduler._run_pass5()

    counts = scheduler._get_pass5_shift_counts(day)

    assert counts["A"] == 1
    assert counts["B"] == 1
    assert counts["G"] == 1


def test_pass5_difference_of_2_uses_a_to_b_not_g():
    scheduler = create_scheduler(
        ["E001", "E002", "E003", "E004"]
    )

    day = 1

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "A"
    scheduler.roster["E003"][day] = "A"
    scheduler.roster["E004"][day] = "B"

    scheduler._run_pass5()

    assert scheduler.roster["E001"][day] in {"A", "B"}
    assert scheduler.roster["E002"][day] in {"A", "B"}
    assert scheduler.roster["E003"][day] in {"A", "B"}

    assert all(
        scheduler.roster[e][day] != "G"
        for e in scheduler.context.members
    )


def test_pass5_difference_of_2_uses_b_to_a_not_g():
    scheduler = create_scheduler(
        ["E001", "E002", "E003", "E004"]
    )

    day = 1

    scheduler.roster["E001"][day] = "B"
    scheduler.roster["E002"][day] = "B"
    scheduler.roster["E003"][day] = "B"
    scheduler.roster["E004"][day] = "A"

    scheduler._run_pass5()

    assert all(
        scheduler.roster[e][day] != "G"
        for e in scheduler.context.members
    )


def test_pass5_does_not_create_g_if_g_already_exists():
    scheduler = create_scheduler(
        ["E001", "E002", "E003", "E004"]
    )

    day = 1

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "A"
    scheduler.roster["E003"][day] = "B"
    scheduler.roster["E004"][day] = "G"

    before = {
        employee_id: scheduler.roster[employee_id][day]
        for employee_id in scheduler.context.members
    }

    scheduler._run_pass5()

    after = {
        employee_id: scheduler.roster[employee_id][day]
        for employee_id in scheduler.context.members
    }

    assert after == before


def test_pass5_does_nothing_when_a_and_b_are_equal():
    scheduler = create_scheduler(
        ["E001", "E002", "E003", "E004"]
    )

    day = 1

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "A"
    scheduler.roster["E003"][day] = "B"
    scheduler.roster["E004"][day] = "B"

    before = {
        employee_id: scheduler.roster[employee_id][day]
        for employee_id in scheduler.context.members
    }

    scheduler._run_pass5()

    after = {
        employee_id: scheduler.roster[employee_id][day]
        for employee_id in scheduler.context.members
    }

    assert after == before


def test_pass5_does_nothing_when_difference_is_less_than_1():
    scheduler = create_scheduler(
        ["E001", "E002", "E003"]
    )

    day = 1

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "B"
    scheduler.roster["E003"][day] = "G"

    before = {
        employee_id: scheduler.roster[employee_id][day]
        for employee_id in scheduler.context.members
    }

    scheduler._run_pass5()

    after = {
        employee_id: scheduler.roster[employee_id][day]
        for employee_id in scheduler.context.members
    }

    assert after == before


# ------------------------------------------------------------------
# ONLY A/B MEMBERS MAY BE CHANGED
# ------------------------------------------------------------------


def test_pass5_only_changes_a_or_b_members():
    scheduler = create_scheduler(
        ["E001", "E002", "E003", "E004"]
    )

    day = 1

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "A"
    scheduler.roster["E003"][day] = "B"
    scheduler.roster["E004"][day] = "W"

    before = {
        employee_id: scheduler.roster[employee_id][day]
        for employee_id in scheduler.context.members
    }

    scheduler._run_pass5()

    assert scheduler.roster["E004"][day] == before["E004"]


def test_pass5_does_not_modify_w_h_or_l():
    scheduler = create_scheduler(
        ["E001", "E002", "E003", "E004"]
    )

    day = 1

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "A"
    scheduler.roster["E003"][day] = "B"
    scheduler.roster["E004"][day] = "H"

    scheduler._run_pass5()

    assert scheduler.roster["E004"][day] == "H"


# ------------------------------------------------------------------
# REQUIREMENTS
# ------------------------------------------------------------------


def test_pass5_does_not_change_member_with_active_requirement():
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

    context = RosterContext(
        members=["E001", "E002", "E003"],
        year=2026,
        month=8,
        group_number="01",
        public_holidays=0,
        requirements=requirements,
        previous_assignments={},
        days_in_month=5,
        required_w_days=0,
    )

    scheduler = RosterScheduler(context)

    scheduler.roster["E001"][1] = "A"
    scheduler.roster["E002"][1] = "A"
    scheduler.roster["E003"][1] = "B"

    scheduler._run_pass5()

    assert scheduler.roster["E001"][1] == "A"


def test_pass5_does_not_modify_active_requirements():
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

    context = RosterContext(
        members=["E001", "E002", "E003"],
        year=2026,
        month=8,
        group_number="01",
        public_holidays=0,
        requirements=requirements,
        previous_assignments={},
        days_in_month=5,
        required_w_days=0,
    )

    scheduler = RosterScheduler(context)

    scheduler.roster["E001"][1] = "A"
    scheduler.roster["E002"][1] = "A"
    scheduler.roster["E003"][1] = "B"

    before = scheduler.active_requirements[
        "E001"
    ].requirements["A"].copy()

    scheduler._run_pass5()

    after = scheduler.active_requirements[
        "E001"
    ].requirements["A"]

    assert after == before


def test_pass5_does_not_relax_requirements():
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

    context = RosterContext(
        members=["E001", "E002", "E003"],
        year=2026,
        month=8,
        group_number="01",
        public_holidays=0,
        requirements=requirements,
        previous_assignments={},
        days_in_month=5,
        required_w_days=0,
    )

    scheduler = RosterScheduler(context)

    scheduler.roster["E001"][1] = "A"
    scheduler.roster["E002"][1] = "A"
    scheduler.roster["E003"][1] = "B"

    scheduler._run_pass5()

    assert scheduler.relaxed_requirements == []


# ------------------------------------------------------------------
# PREVIOUS-DAY PREFERENCE FOR A/B REASSIGNMENT
# ------------------------------------------------------------------


def test_pass5_prefers_member_with_new_shift_on_previous_day():
    scheduler = create_scheduler(
        ["E001", "E002", "E003", "E004"]
    )

    # Day 1
    scheduler.roster["E001"][1] = "B"
    scheduler.roster["E002"][1] = "A"
    scheduler.roster["E003"][1] = "A"
    scheduler.roster["E004"][1] = "B"

    # Day 2:
    # A = 3, B = 1
    # Therefore A -> B must happen.
    scheduler.roster["E001"][2] = "A"
    scheduler.roster["E002"][2] = "A"
    scheduler.roster["E003"][2] = "A"
    scheduler.roster["E004"][2] = "B"

    scheduler._run_pass5()

    # E001 worked B yesterday, so E001 should be preferred
    # for the A -> B reassignment.
    assert scheduler.roster["E001"][2] == "B"


def test_pass5_prefers_member_with_new_shift_on_previous_day_for_b_to_a_change():
    scheduler = create_scheduler(
        ["E001", "E002", "E003", "E004"]
    )

    # Day 1
    scheduler.roster["E001"][1] = "A"
    scheduler.roster["E002"][1] = "B"
    scheduler.roster["E003"][1] = "B"
    scheduler.roster["E004"][1] = "A"

    # Day 2:
    # B = 3, A = 1
    # Therefore B -> A must happen.
    scheduler.roster["E001"][2] = "B"
    scheduler.roster["E002"][2] = "B"
    scheduler.roster["E003"][2] = "B"
    scheduler.roster["E004"][2] = "A"

    scheduler._run_pass5()

    # E001 worked A yesterday, so E001 should be preferred
    # for the B -> A reassignment.
    assert scheduler.roster["E001"][2] == "A"


# ------------------------------------------------------------------
# G ASSIGNMENT DOES NOT USE PREVIOUS-DAY HISTORY
# ------------------------------------------------------------------


def test_pass5_g_assignment_does_not_require_previous_day_g():
    scheduler = create_scheduler(
        ["E001", "E002", "E003"]
    )

    # Day 1
    scheduler.roster["E001"][1] = "B"
    scheduler.roster["E002"][1] = "A"
    scheduler.roster["E003"][1] = "A"

    # Day 2:
    # A = 2, B = 1
    # No G exists, so one eligible A member becomes G.
    scheduler.roster["E001"][2] = "A"
    scheduler.roster["E002"][2] = "A"
    scheduler.roster["E003"][2] = "B"

    scheduler._run_pass5()

    counts = scheduler._get_pass5_shift_counts(2)

    assert counts["A"] == 1
    assert counts["B"] == 1
    assert counts["G"] == 1


def test_pass5_g_assignment_does_not_require_previous_day_g_for_b():
    scheduler = create_scheduler(
        ["E001", "E002", "E003"]
    )

    # Day 1
    scheduler.roster["E001"][1] = "A"
    scheduler.roster["E002"][1] = "B"
    scheduler.roster["E003"][1] = "B"

    # Day 2:
    # B = 2, A = 1
    # No G exists, so one eligible B member becomes G.
    scheduler.roster["E001"][2] = "A"
    scheduler.roster["E002"][2] = "B"
    scheduler.roster["E003"][2] = "B"

    scheduler._run_pass5()

    counts = scheduler._get_pass5_shift_counts(2)

    assert counts["A"] == 1
    assert counts["B"] == 1
    assert counts["G"] == 1


# ------------------------------------------------------------------
# DAY 1
# ------------------------------------------------------------------


def test_pass5_first_day_does_not_require_previous_day():
    scheduler = create_scheduler(
        ["E001", "E002", "E003"]
    )

    day = 1

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "A"
    scheduler.roster["E003"][day] = "B"

    scheduler._run_pass5()

    counts = scheduler._get_pass5_shift_counts(day)

    assert counts["A"] == 1
    assert counts["B"] == 1
    assert counts["G"] == 1


# ------------------------------------------------------------------
# MULTIPLE DAYS
# ------------------------------------------------------------------


def test_pass5_processes_multiple_days():
    scheduler = create_scheduler(
        ["E001", "E002", "E003"],
        days_in_month=5,
    )

    for day in range(1, 6):
        scheduler.roster["E001"][day] = "A"
        scheduler.roster["E002"][day] = "A"
        scheduler.roster["E003"][day] = "B"

    scheduler._run_pass5()

    for day in range(1, 6):
        counts = scheduler._get_pass5_shift_counts(day)

        assert counts["A"] == 1
        assert counts["B"] == 1
        assert counts["G"] == 1


# ------------------------------------------------------------------
# RANDOM FALLBACK
# ------------------------------------------------------------------


def test_pass5_can_select_random_eligible_member_when_no_previous_match(
    monkeypatch,
):
    scheduler = create_scheduler(
        ["E001", "E002", "E003"]
    )

    day = 1

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "A"
    scheduler.roster["E003"][day] = "B"

    selected = []

    def fake_choice(candidates):
        selected.extend(candidates)
        return candidates[0]

    monkeypatch.setattr(
        "app.scheduler.scheduler.random.choice",
        fake_choice,
    )

    scheduler._run_pass5()

    assert selected


def test_pass5_does_not_change_shift_if_only_candidate_has_requirement():
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

    context = RosterContext(
        members=["E001", "E002", "E003"],
        year=2026,
        month=8,
        group_number="01",
        public_holidays=0,
        requirements=requirements,
        previous_assignments={},
        days_in_month=5,
        required_w_days=0,
    )

    scheduler = RosterScheduler(context)

    scheduler.roster["E001"][1] = "A"
    scheduler.roster["E002"][1] = "A"
    scheduler.roster["E003"][1] = "B"

    scheduler._run_pass5()

    # Both A members have active requirements.
    # Therefore neither may be changed.
    assert scheduler.roster["E001"][1] == "A"
    assert scheduler.roster["E002"][1] == "A"
    assert scheduler.roster["E003"][1] == "B"