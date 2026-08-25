from unittest.mock import patch

from app.scheduler.context import MemberRequirement
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


def create_context(requirements, days_in_month=3):
    from app.scheduler.context import RosterContext

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


def create_scheduler(days_in_month=3):
    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements=empty_requirements(),
        ),
    }

    return RosterScheduler(
        create_context(
            requirements,
            days_in_month=days_in_month,
        )
    )


def test_pass2_runs_step1_before_step2_for_each_day():
    scheduler = create_scheduler(days_in_month=2)

    call_order = []

    def step1(day):
        call_order.append(("step1", day))

    def step2b(day):
        call_order.append(("step2b", day))
        return True

    def step3(day):
        call_order.append(("step3", day))

    with patch.object(
        scheduler,
        "_validate_day_requirements",
        side_effect=step1,
    ), patch.object(
        scheduler,
        "_fill_abc_coverage_from_free_members",
        side_effect=step2b,
    ), patch.object(
        scheduler,
        "_run_pass2_step3",
        side_effect=step3,
    ), patch.object(
        scheduler,
        "_get_missing_abc_shifts",
        return_value={"A"},
    ):
        scheduler._run_pass_2()

    assert call_order == [
        ("step1", 1),
        ("step2b", 1),
        ("step3", 1),
        ("step1", 2),
        ("step2b", 2),
        ("step3", 2),
    ]


def test_pass2_skips_step2_when_abc_coverage_is_already_complete():
    scheduler = create_scheduler(days_in_month=1)

    with patch.object(
        scheduler,
        "_validate_day_requirements",
    ) as step1, patch.object(
        scheduler,
        "_fill_abc_coverage_from_free_members",
    ) as step2b, patch.object(
        scheduler,
        "_run_pass_2_step_2c",
    ) as step2c, patch.object(
        scheduler,
        "_run_pass2_step2d",
    ) as step2d, patch.object(
        scheduler,
        "_run_pass2_step3",
    ) as step3, patch.object(
        scheduler,
        "_get_missing_abc_shifts",
        return_value=set(),
    ):
        scheduler._run_pass_2()

    step1.assert_called_once_with(1)
    step2b.assert_not_called()
    step2c.assert_not_called()
    step2d.assert_not_called()
    step3.assert_called_once_with(1)


def test_pass2_moves_from_step2b_to_step3_when_coverage_is_completed():
    scheduler = create_scheduler(days_in_month=1)

    with patch.object(
        scheduler,
        "_validate_day_requirements",
    ), patch.object(
        scheduler,
        "_get_missing_abc_shifts",
        side_effect=[
            {"A"},
            set(),
        ],
    ), patch.object(
        scheduler,
        "_fill_abc_coverage_from_free_members",
        return_value=True,
    ) as step2b, patch.object(
        scheduler,
        "_run_pass_2_step_2c",
    ) as step2c, patch.object(
        scheduler,
        "_run_pass2_step2d",
    ) as step2d, patch.object(
        scheduler,
        "_run_pass2_step3",
    ) as step3:
        scheduler._run_pass_2()

    step2b.assert_called_once_with(1)
    step2c.assert_not_called()
    step2d.assert_not_called()
    step3.assert_called_once_with(1)


def test_pass2_moves_from_step2b_to_step2c_when_coverage_remains_incomplete():
    scheduler = create_scheduler(days_in_month=1)

    with patch.object(
        scheduler,
        "_validate_day_requirements",
    ), patch.object(
        scheduler,
        "_get_missing_abc_shifts",
        side_effect=[
            {"A"},
            {"A"},
            set(),
        ],
    ), patch.object(
        scheduler,
        "_fill_abc_coverage_from_free_members",
        return_value=False,
    ) as step2b, patch.object(
        scheduler,
        "_run_pass_2_step_2c",
        return_value=True,
    ) as step2c, patch.object(
        scheduler,
        "_run_pass2_step2d",
    ) as step2d, patch.object(
        scheduler,
        "_run_pass2_step3",
    ) as step3:
        scheduler._run_pass_2()

    step2b.assert_called_once_with(1)
    step2c.assert_called_once_with(1)
    step2d.assert_not_called()
    step3.assert_called_once_with(1)


def test_pass2_moves_from_step2c_to_step2d_when_coverage_remains_incomplete():
    scheduler = create_scheduler(days_in_month=1)

    with patch.object(
        scheduler,
        "_validate_day_requirements",
    ), patch.object(
        scheduler,
        "_get_missing_abc_shifts",
        side_effect=[
            {"A"},
            {"A"},
            {"A"},
            set(),
        ],
    ), patch.object(
        scheduler,
        "_fill_abc_coverage_from_free_members",
        return_value=False,
    ), patch.object(
        scheduler,
        "_run_pass_2_step_2c",
        return_value=False,
    ) as step2c, patch.object(
        scheduler,
        "_run_pass2_step2d",
        return_value=True,
    ) as step2d, patch.object(
        scheduler,
        "_run_pass2_step3",
    ) as step3:
        scheduler._run_pass_2()

    step2c.assert_called_once_with(1)
    step2d.assert_called_once_with(1)
    step3.assert_called_once_with(1)


def test_pass2_runs_step3_even_when_step2d_cannot_complete_coverage():
    scheduler = create_scheduler(days_in_month=1)

    with patch.object(
        scheduler,
        "_validate_day_requirements",
    ), patch.object(
        scheduler,
        "_get_missing_abc_shifts",
        side_effect=[
            {"A"},
            {"A"},
            {"A"},
        ],
    ), patch.object(
        scheduler,
        "_fill_abc_coverage_from_free_members",
        return_value=False,
    ), patch.object(
        scheduler,
        "_run_pass_2_step_2c",
        return_value=False,
    ), patch.object(
        scheduler,
        "_run_pass2_step2d",
        return_value=False,
    ) as step2d, patch.object(
        scheduler,
        "_run_pass2_step3",
    ) as step3:
        scheduler._run_pass_2()

    step2d.assert_called_once_with(1)
    step3.assert_called_once_with(1)


def test_pass2_completes_entire_day_before_starting_next_day():
    scheduler = create_scheduler(days_in_month=2)

    call_order = []

    def step1(day):
        call_order.append(("step1", day))

    def step2b(day):
        call_order.append(("step2b", day))
        return True

    def step3(day):
        call_order.append(("step3", day))

    with patch.object(
        scheduler,
        "_validate_day_requirements",
        side_effect=step1,
    ), patch.object(
        scheduler,
        "_get_missing_abc_shifts",
        side_effect=[
            {"A"},
            set(),
            {"A"},
            set(),
        ],
    ), patch.object(
        scheduler,
        "_fill_abc_coverage_from_free_members",
        side_effect=step2b,
    ), patch.object(
        scheduler,
        "_run_pass2_step3",
        side_effect=step3,
    ):
        scheduler._run_pass_2()

    assert call_order == [
        ("step1", 1),
        ("step2b", 1),
        ("step3", 1),
        ("step1", 2),
        ("step2b", 2),
        ("step3", 2),
    ]


def test_pass2_step3_runs_exactly_once_per_day():
    scheduler = create_scheduler(days_in_month=4)

    with patch.object(
        scheduler,
        "_validate_day_requirements",
    ), patch.object(
        scheduler,
        "_get_missing_abc_shifts",
        return_value=set(),
    ), patch.object(
        scheduler,
        "_run_pass2_step3",
    ) as step3:
        scheduler._run_pass_2()

    assert step3.call_count == 4

    assert [
        call.args[0]
        for call in step3.call_args_list
    ] == [1, 2, 3, 4]


def test_pass2_step1_is_run_for_each_day_not_as_whole_pass():
    scheduler = create_scheduler(days_in_month=3)

    validated_days = []

    def validate_day(day):
        validated_days.append(day)

    with patch.object(
        scheduler,
        "_validate_day_requirements",
        side_effect=validate_day,
    ), patch.object(
        scheduler,
        "_get_missing_abc_shifts",
        return_value=set(),
    ), patch.object(
        scheduler,
        "_run_pass_2_step_1",
    ) as whole_step1, patch.object(
        scheduler,
        "_run_pass2_step3",
    ):
        scheduler._run_pass_2()

    assert validated_days == [1, 2, 3]

    # The whole-month Step 1 function must not be called
    # from the day-by-day orchestrator.
    whole_step1.assert_not_called()