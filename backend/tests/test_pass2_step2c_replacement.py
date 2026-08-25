from datetime import date

from app.scheduler.context import MemberRequirement
from app.scheduler.context_builder import build_roster_context
from app.scheduler.scheduler import RosterScheduler


def empty_requirements():
    return {
        "A": [],
        "B": [],
        "C": [],
        "G": [],
        "W": [],
        "H": [],
        "L": [],
    }


def create_context(requirements):
    members = list(requirements.keys())

    return build_roster_context(
        year=2026,
        month=8,
        group_number="1",
        public_holidays=2,
        members=members,
        requirements=requirements,
        previous_assignments={
            employee_id: {}
            for employee_id in members
        },
    )


# ---------------------------------------------------------
# 1. A requirement can be replaced if the old A coverage
#    remains covered by another member.
# ---------------------------------------------------------

def test_replacement_is_allowed_when_old_shift_remains_covered():

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

    # C is missing.
    # E001 can temporarily change A -> C.
    # E002 continues covering A.
    # E003 covers B.

    assert scheduler._can_replace_requirement_for_coverage(
        "E001",
        2,
        "C",
    ) is True


# ---------------------------------------------------------
# 2. Replacement must be rejected if removing the old
#    A shift leaves A uncovered.
# ---------------------------------------------------------

def test_replacement_is_rejected_when_old_shift_becomes_uncovered():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "A": [2],
            },
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler.roster["E001"][2] = "A"

    assert scheduler._can_replace_requirement_for_coverage(
        "E001",
        2,
        "C",
    ) is False


# ---------------------------------------------------------
# 3. The proposed replacement must satisfy hard constraints.
#
#    Previous day = C
#    Today requirement = W
#
#    W -> A is invalid because C -> A is prohibited.
# ---------------------------------------------------------

def test_w_requirement_cannot_be_replaced_with_invalid_a_after_c():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "W": [2],
            },
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    scheduler.roster["E001"][1] = "C"
    scheduler.roster["E001"][2] = "W"

    assert scheduler._can_replace_requirement_for_coverage(
        "E001",
        2,
        "A",
    ) is False


# ---------------------------------------------------------
# 4. The same member may be eligible for C even though
#    A is invalid after C.
#
#    C -> C is allowed by the hard constraint.
# ---------------------------------------------------------

def test_w_requirement_can_be_replaced_with_c_when_c_is_valid():

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

    scheduler.roster["E001"][1] = "C"
    scheduler.roster["E001"][2] = "W"

    scheduler.roster["E002"][2] = "A"
    scheduler.roster["E003"][2] = "B"

    assert scheduler._can_replace_requirement_for_coverage(
        "E001",
        2,
        "C",
    ) is True


# ---------------------------------------------------------
# 5. C replacement must respect the maximum C shifts
#    per member.
# ---------------------------------------------------------

def test_c_replacement_is_rejected_when_member_is_at_c_limit():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "W": [7],
            },
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements={
                **empty_requirements(),
                "A": [7],
            },
        ),
        "E003": MemberRequirement(
            employee_id="E003",
            requirements={
                **empty_requirements(),
                "B": [7],
            },
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    # E001 already has the maximum configured number of C shifts.
    for day in range(1, 6):
        scheduler.roster["E001"][day] = "C"

    scheduler.roster["E001"][7] = "W"

    scheduler.roster["E002"][7] = "A"
    scheduler.roster["E003"][7] = "B"

    assert scheduler._can_replace_requirement_for_coverage(
        "E001",
        7,
        "C",
    ) is False


# ---------------------------------------------------------
# 6. Temporary replacement must restore the original
#    roster assignment.
# ---------------------------------------------------------

def test_temporary_replacement_restores_original_assignment():

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

    scheduler.roster["E001"][1] = "C"
    scheduler.roster["E001"][2] = "W"

    scheduler.roster["E002"][2] = "A"
    scheduler.roster["E003"][2] = "B"

    result = scheduler._can_replace_requirement_for_coverage(
        "E001",
        2,
        "C",
    )

    assert result is True

    # The temporary simulation must not permanently change the roster.
    assert scheduler.roster["E001"][2] == "W"


# ---------------------------------------------------------
# 7. Temporary replacement must not modify active
#    requirements.
# ---------------------------------------------------------

def test_temporary_replacement_does_not_remove_active_requirement():

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

    scheduler.roster["E001"][1] = "C"
    scheduler.roster["E001"][2] = "W"

    scheduler.roster["E002"][2] = "A"
    scheduler.roster["E003"][2] = "B"

    scheduler._can_replace_requirement_for_coverage(
        "E001",
        2,
        "C",
    )

    assert (
        2
        in scheduler.active_requirements[
            "E001"
        ].requirements["W"]
    )


# ---------------------------------------------------------
# 8. A member whose proposed replacement violates the
#    six-continuous-working-days rule is rejected.
# ---------------------------------------------------------

def test_replacement_is_rejected_after_six_previous_working_days():

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                **empty_requirements(),
                "W": [7],
            },
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements={
                **empty_requirements(),
                "A": [7],
            },
        ),
        "E003": MemberRequirement(
            employee_id="E003",
            requirements={
                **empty_requirements(),
                "B": [7],
            },
        ),
    }

    scheduler = RosterScheduler(
        create_context(requirements)
    )

    # Six consecutive working days before day 7.
    for day in range(1, 7):
        scheduler.roster["E001"][day] = "A"

    scheduler.roster["E001"][7] = "W"

    scheduler.roster["E002"][7] = "A"
    scheduler.roster["E003"][7] = "B"

    assert scheduler._can_replace_requirement_for_coverage(
        "E001",
        7,
        "C",
    ) is False