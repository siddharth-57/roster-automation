from copy import deepcopy
from unittest.mock import patch

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


def test_step2d_assigns_a_to_free_member():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements=empty_requirements(),
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    with patch(
        "app.scheduler.scheduler.can_assign_shift",
        return_value=True,
    ):
        result = scheduler._commit_step2d_coverage_assignment(
            "E001",
            2,
            "A",
        )

    assert result is True
    assert scheduler.roster["E001"][2] == "A"


def test_step2d_assigns_b_to_free_member():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements=empty_requirements(),
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    with patch(
        "app.scheduler.scheduler.can_assign_shift",
        return_value=True,
    ):
        result = scheduler._commit_step2d_coverage_assignment(
            "E001",
            2,
            "B",
        )

    assert result is True
    assert scheduler.roster["E001"][2] == "B"


def test_step2d_assigns_c_and_updates_c_tracking():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements=empty_requirements(),
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    initial_c_count = scheduler.c_shift_counts["E001"]

    with patch(
        "app.scheduler.scheduler.can_assign_shift",
        return_value=True,
    ):
        result = scheduler._commit_step2d_coverage_assignment(
            "E001",
            2,
            "C",
        )

    assert result is True
    assert scheduler.roster["E001"][2] == "C"
    assert scheduler.c_shift_counts["E001"] == initial_c_count + 1


def test_step2d_assignment_makes_member_no_longer_free():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements=empty_requirements(),
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    assert "E001" in scheduler._get_free_members(2)

    with patch(
        "app.scheduler.scheduler.can_assign_shift",
        return_value=True,
    ):
        result = scheduler._commit_step2d_coverage_assignment(
            "E001",
            2,
            "C",
        )

    assert result is True
    assert "E001" not in scheduler._get_free_members(2)


def test_step2d_rejects_member_who_is_not_free():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements=empty_requirements(),
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler.roster["E001"][2] = "W"

    original_roster = dict(
        scheduler.roster["E001"]
    )
    original_c_count = scheduler.c_shift_counts["E001"]

    with patch(
        "app.scheduler.scheduler.can_assign_shift",
        return_value=True,
    ):
        result = scheduler._commit_step2d_coverage_assignment(
            "E001",
            2,
            "C",
        )

    assert result is False
    assert scheduler.roster["E001"] == original_roster
    assert scheduler.c_shift_counts["E001"] == original_c_count


def test_step2d_rejects_invalid_hard_rule_assignment():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements=empty_requirements(),
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    original_roster = dict(
        scheduler.roster["E001"]
    )
    original_c_count = scheduler.c_shift_counts["E001"]

    with patch(
        "app.scheduler.scheduler.can_assign_shift",
        return_value=False,
    ):
        result = scheduler._commit_step2d_coverage_assignment(
            "E001",
            2,
            "A",
        )

    assert result is False
    assert scheduler.roster["E001"] == original_roster
    assert scheduler.c_shift_counts["E001"] == original_c_count


def test_step2d_rejection_does_not_change_c_tracking():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements=empty_requirements(),
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    initial_c_count = scheduler.c_shift_counts["E001"]

    with patch(
        "app.scheduler.scheduler.can_assign_shift",
        return_value=False,
    ):
        result = scheduler._commit_step2d_coverage_assignment(
            "E001",
            2,
            "C",
        )

    assert result is False
    assert scheduler.c_shift_counts["E001"] == initial_c_count
    assert 2 not in scheduler.roster["E001"]


def test_step2d_assignment_does_not_modify_requirement_state():

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

    with patch(
        "app.scheduler.scheduler.can_assign_shift",
        return_value=True,
    ):
        result = scheduler._commit_step2d_coverage_assignment(
            "E001",
            2,
            "C",
        )

    assert result is True

    assert (
        scheduler.active_requirements
        == original_active_requirements
    )

    assert (
        scheduler.relaxed_requirements
        == original_relaxed_requirements
    )


def test_step2d_does_not_modify_original_context_requirements():

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

    original_context_requirements = deepcopy(
        scheduler.context.requirements
    )

    with patch(
        "app.scheduler.scheduler.can_assign_shift",
        return_value=True,
    ):
        result = scheduler._commit_step2d_coverage_assignment(
            "E001",
            2,
            "C",
        )

    assert result is True

    assert (
        scheduler.context.requirements
        == original_context_requirements
    )


def test_step2d_commit_only_accepts_abc_shift():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements=empty_requirements(),
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    original_roster = dict(
        scheduler.roster["E001"]
    )

    with patch(
        "app.scheduler.scheduler.can_assign_shift",
        return_value=True,
    ):
        result = scheduler._commit_step2d_coverage_assignment(
            "E001",
            2,
            "W",
        )

    assert result is False
    assert scheduler.roster["E001"] == original_roster