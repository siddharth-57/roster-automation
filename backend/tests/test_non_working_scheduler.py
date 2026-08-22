# We'll test the most important behavior first:
#     Requested L gets L when possible.
#     Requested W gets W when possible.
#     If W isn't possible but H is, W request gets H.
#     If W and H aren't possible but L is, W request gets L.
#     If none are possible, the request is eventually relaxed.
# For now, let's start with the first two.

from app.scheduler.context import (
    MemberRequirement,
    RosterContext,
)
from app.scheduler.scheduler import RosterScheduler


def create_context():

    members = [
        "E001",
        "E002",
    ]

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                "A": [],
                "B": [],
                "C": [],
                "G": [],
                "L": [5],
                "W": [],
            },
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements={
                "A": [],
                "B": [],
                "C": [],
                "G": [],
                "L": [],
                "W": [6],
            },
        ),
    }

    return RosterContext(
        year=2026,
        month=8,
        group_number="01",
        public_holidays=1,
        members=members,
        requirements=requirements,
        previous_assignments={},
        days_in_month=10,
        required_w_days=4,
    )


def test_requested_leave_is_assigned():

    context = create_context()

    scheduler = RosterScheduler(context)

    scheduler._assign_requested_non_working_days()

    assert scheduler.roster["E001"][5] == "L"


def test_requested_w_is_assigned():

    context = create_context()

    scheduler = RosterScheduler(context)

    scheduler._assign_requested_non_working_days()

    assert scheduler.roster["E002"][6] == "W"


def test_remaining_w_quota():

    context = create_context()

    scheduler = RosterScheduler(context)

    scheduler.roster["E001"][1] = "W"
    scheduler.roster["E001"][2] = "W"

    remaining = scheduler._get_remaining_w(
        "E001"
    )

    assert remaining == 2


def test_remaining_h_quota():

    context = create_context()

    scheduler = RosterScheduler(context)

    scheduler.roster["E001"][1] = "H"

    remaining = scheduler._get_remaining_h(
        "E001"
    )

    assert remaining == 0