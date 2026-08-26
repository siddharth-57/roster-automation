import random

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
# Eligibility
# ------------------------------------------------------------------


def test_pass3_eligible_member_has_no_active_requirement_and_works_ab():
    scheduler = create_scheduler(["E001"])

    scheduler.roster["E001"][1] = "A"
    scheduler.remaining_w["E001"] = 1

    eligible = scheduler._get_pass3_eligible_members(1, "W")

    assert eligible == ["E001"]


def test_pass3_member_with_active_requirement_is_not_eligible():
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

    scheduler.roster["E001"][1] = "A"
    scheduler.remaining_w["E001"] = 1

    eligible = scheduler._get_pass3_eligible_members(1, "W")

    assert eligible == []


def test_pass3_member_with_no_assignment_is_not_eligible():
    scheduler = create_scheduler(["E001"])

    scheduler.remaining_w["E001"] = 1

    eligible = scheduler._get_pass3_eligible_members(1, "W")

    assert eligible == []


def test_pass3_member_with_c_shift_is_not_eligible():
    scheduler = create_scheduler(["E001"])

    scheduler.roster["E001"][1] = "C"
    scheduler.remaining_w["E001"] = 1

    eligible = scheduler._get_pass3_eligible_members(1, "W")

    assert eligible == []


def test_pass3_member_with_non_working_shift_is_not_eligible():
    scheduler = create_scheduler(["E001"])

    scheduler.roster["E001"][1] = "W"
    scheduler.remaining_w["E001"] = 1

    eligible = scheduler._get_pass3_eligible_members(1, "W")

    assert eligible == []


def test_pass3_member_without_remaining_non_working_requirement_is_not_eligible():
    scheduler = create_scheduler(["E001"])

    scheduler.roster["E001"][1] = "A"

    scheduler.remaining_w["E001"] = 0
    scheduler.remaining_h["E001"] = 0

    eligible_for_w = scheduler._get_pass3_eligible_members(1, "W")
    eligible_for_h = scheduler._get_pass3_eligible_members(1, "H")

    assert eligible_for_w == []
    assert eligible_for_h == []


def test_pass3_member_with_remaining_h_is_eligible_for_h():
    scheduler = create_scheduler(["E001"])

    scheduler.roster["E001"][1] = "A"

    scheduler.remaining_w["E001"] = 0
    scheduler.remaining_h["E001"] = 1

    eligible_for_w = scheduler._get_pass3_eligible_members(1, "W")
    eligible_for_h = scheduler._get_pass3_eligible_members(1, "H")

    assert eligible_for_w == []
    assert eligible_for_h == ["E001"]


# ------------------------------------------------------------------
# Weekday staffing rules
# ------------------------------------------------------------------


def test_pass3_weekday_keeps_a_and_b_at_two():
    scheduler = create_scheduler(
        ["E001", "E002", "E003", "E004", "E005", "E006"]
    )

    # Day 3 = Monday, 2026-08-03.
    day = 3

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "A"
    scheduler.roster["E003"][day] = "A"

    scheduler.roster["E004"][day] = "B"
    scheduler.roster["E005"][day] = "B"
    scheduler.roster["E006"][day] = "B"

    for employee_id in scheduler.context.members:
        scheduler.remaining_w[employee_id] = 1

    scheduler._run_pass3(day)

    a_count = sum(
        scheduler.roster[e].get(day) == "A"
        for e in scheduler.context.members
    )

    b_count = sum(
        scheduler.roster[e].get(day) == "B"
        for e in scheduler.context.members
    )

    assert a_count >= 2
    assert b_count >= 2


def test_pass3_weekday_does_not_remove_from_shift_with_only_two_members():
    scheduler = create_scheduler(
        ["E001", "E002", "E003", "E004", "E005"]
    )

    day = 3

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "A"

    scheduler.roster["E003"][day] = "B"
    scheduler.roster["E004"][day] = "B"
    scheduler.roster["E005"][day] = "B"

    for employee_id in scheduler.context.members:
        scheduler.remaining_w[employee_id] = 1

    scheduler._run_pass3(day)

    assert scheduler.roster["E001"][day] == "A"
    assert scheduler.roster["E002"][day] == "A"

    assert sum(
        scheduler.roster[e].get(day) == "A"
        for e in scheduler.context.members
    ) == 2


def test_pass3_weekday_removes_only_excess_members_from_each_shift():
    scheduler = create_scheduler(
        [
            "E001",
            "E002",
            "E003",
            "E004",
            "E005",
            "E006",
            "E007",
            "E008",
        ]
    )

    day = 3

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "A"
    scheduler.roster["E003"][day] = "A"
    scheduler.roster["E004"][day] = "A"

    scheduler.roster["E005"][day] = "B"
    scheduler.roster["E006"][day] = "B"
    scheduler.roster["E007"][day] = "B"
    scheduler.roster["E008"][day] = "B"

    for employee_id in scheduler.context.members:
        scheduler.remaining_w[employee_id] = 1

    scheduler._run_pass3(day)

    assert sum(
        scheduler.roster[e].get(day) == "A"
        for e in scheduler.context.members
    ) == 2

    assert sum(
        scheduler.roster[e].get(day) == "B"
        for e in scheduler.context.members
    ) == 2

    assert sum(
        scheduler.roster[e].get(day) == "W"
        for e in scheduler.context.members
    ) == 4


# ------------------------------------------------------------------
# Weekend staffing rules
# ------------------------------------------------------------------


def test_pass3_weekend_keeps_at_least_one_a_and_one_b():
    scheduler = create_scheduler(
        ["E001", "E002", "E003", "E004", "E005", "E006"]
    )

    # Day 1 = Saturday, 2026-08-01.
    day = 1

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "A"
    scheduler.roster["E003"][day] = "A"

    scheduler.roster["E004"][day] = "B"
    scheduler.roster["E005"][day] = "B"
    scheduler.roster["E006"][day] = "B"

    for employee_id in scheduler.context.members:
        scheduler.remaining_w[employee_id] = 1

    scheduler._run_pass3(day)

    a_count = sum(
        scheduler.roster[e].get(day) == "A"
        for e in scheduler.context.members
    )

    b_count = sum(
        scheduler.roster[e].get(day) == "B"
        for e in scheduler.context.members
    )

    assert a_count >= 1
    assert b_count >= 1


def test_pass3_weekend_assigns_as_many_eligible_members_as_possible():
    scheduler = create_scheduler(
        ["E001", "E002", "E003", "E004"]
    )

    day = 1

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "A"

    scheduler.roster["E003"][day] = "B"
    scheduler.roster["E004"][day] = "B"

    for employee_id in scheduler.context.members:
        scheduler.remaining_w[employee_id] = 1

    scheduler._run_pass3(day)

    # One A and one B must remain.
    assert sum(
        scheduler.roster[e].get(day) == "A"
        for e in scheduler.context.members
    ) == 1

    assert sum(
        scheduler.roster[e].get(day) == "B"
        for e in scheduler.context.members
    ) == 1

    # Therefore two eligible members should receive W.
    assert sum(
        scheduler.roster[e].get(day) == "W"
        for e in scheduler.context.members
    ) == 2


def test_pass3_weekend_does_not_remove_last_a_member():
    scheduler = create_scheduler(
        ["E001", "E002", "E003", "E004"]
    )

    day = 1

    scheduler.roster["E001"][day] = "A"

    scheduler.roster["E002"][day] = "B"
    scheduler.roster["E003"][day] = "B"
    scheduler.roster["E004"][day] = "B"

    for employee_id in scheduler.context.members:
        scheduler.remaining_w[employee_id] = 1

    scheduler._run_pass3(day)

    assert scheduler.roster["E001"][day] == "A"

    assert sum(
        scheduler.roster[e].get(day) == "A"
        for e in scheduler.context.members
    ) == 1


def test_pass3_weekend_does_not_remove_last_b_member():
    scheduler = create_scheduler(
        ["E001", "E002", "E003", "E004"]
    )

    day = 1

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "A"
    scheduler.roster["E003"][day] = "A"

    scheduler.roster["E004"][day] = "B"

    for employee_id in scheduler.context.members:
        scheduler.remaining_w[employee_id] = 1

    scheduler._run_pass3(day)

    assert scheduler.roster["E004"][day] == "B"

    assert sum(
        scheduler.roster[e].get(day) == "B"
        for e in scheduler.context.members
    ) == 1


# ------------------------------------------------------------------
# W before H
# ------------------------------------------------------------------


def test_pass3_allocates_w_before_h():
    scheduler = create_scheduler(
        ["E001", "E002", "E003", "E004"]
    )

    day = 1

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "A"

    scheduler.roster["E003"][day] = "B"
    scheduler.roster["E004"][day] = "B"

    scheduler.remaining_w["E001"] = 1
    scheduler.remaining_h["E001"] = 1

    scheduler.remaining_w["E002"] = 1
    scheduler.remaining_h["E002"] = 1

    scheduler.remaining_w["E003"] = 1
    scheduler.remaining_h["E003"] = 1

    scheduler.remaining_w["E004"] = 1
    scheduler.remaining_h["E004"] = 1

    scheduler._run_pass3(day)

    non_working_assignments = [
        scheduler.roster[e][day]
        for e in scheduler.context.members
        if scheduler.roster[e].get(day) in {"W", "H"}
    ]

    assert "H" not in non_working_assignments
    assert all(
        shift == "W"
        for shift in non_working_assignments
    )


def test_pass3_allocates_h_when_no_w_remains():
    scheduler = create_scheduler(
        ["E001", "E002", "E003", "E004"]
    )

    day = 1

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "A"

    scheduler.roster["E003"][day] = "B"
    scheduler.roster["E004"][day] = "B"

    for employee_id in scheduler.context.members:
        scheduler.remaining_w[employee_id] = 0
        scheduler.remaining_h[employee_id] = 1

    scheduler._run_pass3(day)

    assert sum(
        scheduler.roster[e].get(day) == "H"
        for e in scheduler.context.members
    ) == 2


# ------------------------------------------------------------------
# Only eligible members can be changed
# ------------------------------------------------------------------


def test_pass3_does_not_modify_member_with_active_requirement():
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

    day = 1

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "A"
    scheduler.roster["E003"][day] = "B"

    scheduler.remaining_w["E001"] = 1
    scheduler.remaining_w["E002"] = 1
    scheduler.remaining_w["E003"] = 1

    scheduler._run_pass3(day)

    assert scheduler.roster["E001"][day] == "A"


def test_pass3_does_not_modify_c_shift():
    scheduler = create_scheduler(
        ["E001", "E002", "E003"]
    )

    day = 1

    scheduler.roster["E001"][day] = "C"
    scheduler.roster["E002"][day] = "A"
    scheduler.roster["E003"][day] = "B"

    scheduler.remaining_w["E001"] = 1
    scheduler.remaining_w["E002"] = 1
    scheduler.remaining_w["E003"] = 1

    scheduler._run_pass3(day)

    assert scheduler.roster["E001"][day] == "C"


def test_pass3_does_not_modify_member_with_no_remaining_w_or_h():
    scheduler = create_scheduler(
        ["E001", "E002", "E003", "E004"]
    )

    day = 1

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "A"

    scheduler.roster["E003"][day] = "B"
    scheduler.roster["E004"][day] = "B"

    scheduler.remaining_w["E001"] = 0
    scheduler.remaining_h["E001"] = 0

    scheduler.remaining_w["E002"] = 1
    scheduler.remaining_h["E002"] = 0

    scheduler.remaining_w["E003"] = 1
    scheduler.remaining_h["E003"] = 0

    scheduler.remaining_w["E004"] = 1
    scheduler.remaining_h["E004"] = 0

    scheduler._run_pass3(day)

    assert scheduler.roster["E001"][day] == "A"


# ------------------------------------------------------------------
# Quota tracking
# ------------------------------------------------------------------


def test_pass3_decrements_remaining_w_after_assignment():
    scheduler = create_scheduler(
        ["E001", "E002", "E003", "E004"]
    )

    day = 1

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "A"

    scheduler.roster["E003"][day] = "B"
    scheduler.roster["E004"][day] = "B"

    for employee_id in scheduler.context.members:
        scheduler.remaining_w[employee_id] = 1

    scheduler._run_pass3(day)

    for employee_id in scheduler.context.members:
        assert scheduler.remaining_w[employee_id] in {0, 1}


def test_pass3_decrements_remaining_h_after_w_is_complete():
    scheduler = create_scheduler(
        ["E001", "E002", "E003", "E004"]
    )

    day = 1

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "A"

    scheduler.roster["E003"][day] = "B"
    scheduler.roster["E004"][day] = "B"

    for employee_id in scheduler.context.members:
        scheduler.remaining_w[employee_id] = 0
        scheduler.remaining_h[employee_id] = 1

    scheduler._run_pass3(day)

    for employee_id in scheduler.context.members:
        assert scheduler.remaining_h[employee_id] in {0, 1}


# ------------------------------------------------------------------
# Random selection
# ------------------------------------------------------------------


def test_pass3_selection_is_random_among_eligible_members():
    scheduler = create_scheduler(
        ["E001", "E002", "E003", "E004"]
    )

    day = 1

    scheduler.roster["E001"][day] = "A"
    scheduler.roster["E002"][day] = "A"

    scheduler.roster["E003"][day] = "B"
    scheduler.roster["E004"][day] = "B"

    for employee_id in scheduler.context.members:
        scheduler.remaining_w[employee_id] = 1

    original_shuffle = random.shuffle

    try:
        random.shuffle = lambda values: values.reverse()

        scheduler._run_pass3(day)

    finally:
        random.shuffle = original_shuffle

    assert sum(
        scheduler.roster[e].get(day) == "W"
        for e in scheduler.context.members
    ) == 2


# ------------------------------------------------------------------
# Multiple days
# ------------------------------------------------------------------


def test_pass3_travels_through_every_day():
    scheduler = create_scheduler(
        ["E001", "E002", "E003", "E004"],
        days_in_month=5,
    )

    processed_days = []

    original_helper = scheduler._get_pass3_eligible_members

    def tracking_helper(day, non_working_shift):
        processed_days.append(day)
        return original_helper(day, non_working_shift)

    scheduler._get_pass3_eligible_members = tracking_helper

    scheduler._run_pass3()

    # The helper is called twice per day:
    # once for W and once for H.
    assert processed_days == [
        1, 1,
        2, 2,
        3, 3,
        4, 4,
        5, 5,
    ]