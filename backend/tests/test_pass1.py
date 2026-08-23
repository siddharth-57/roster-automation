from app.scheduler.context import (
    MemberRequirement,
    RosterContext,
)
from app.scheduler.scheduler import RosterScheduler


def create_context():
    members = [
        "E001",
        "E002",
        "E003",
    ]

    requirements = {
        "E001": MemberRequirement(
            employee_id="E001",
            requirements={
                "A": [1],
                "B": [2],
                "C": [3],
                "G": [],
                "L": [],
                "W": [4],
                "H": [5],
            },
        ),
        "E002": MemberRequirement(
            employee_id="E002",
            requirements={
                "A": [1],
                "B": [],
                "C": [3, 4],
                "G": [],
                "L": [],
                "W": [5],
                "H": [],
            },
        ),
        "E003": MemberRequirement(
            employee_id="E003",
            requirements={
                "A": [],
                "B": [],
                "C": [],
                "G": [1],
                "L": [2],
                "W": [],
                "H": [3],
            },
        ),
    }

    return RosterContext(
        year=2026,
        month=8,
        group_number="01",
        public_holidays=2,
        members=members,
        requirements=requirements,
        previous_assignments={},
        days_in_month=5,
        required_w_days=4,
    )


def test_pass1_loads_all_member_requirements():

    context = create_context()

    scheduler = RosterScheduler(context)

    scheduler._assign_member_requirements()

    assert scheduler.roster["E001"] == {
        1: "A",
        2: "B",
        3: "C",
        4: "W",
        5: "H",
    }

    assert scheduler.roster["E002"] == {
        1: "A",
        3: "C",
        4: "C",
        5: "W",
    }

    assert scheduler.roster["E003"] == {
        1: "G",
        2: "L",
        3: "H",
    }


def test_pass1_does_not_apply_roster_constraints():

    context = create_context()

    # Deliberately make all three members request A on the
    # same day. This violates the desired roster composition,
    # but Pass 1 must still load all requirements.
    context.requirements["E001"].requirements = {
        "A": [1],
        "B": [],
        "C": [],
        "G": [],
        "L": [],
        "W": [],
        "H": [],
    }

    context.requirements["E002"].requirements = {
        "A": [1],
        "B": [],
        "C": [],
        "G": [],
        "L": [],
        "W": [],
        "H": [],
    }

    context.requirements["E003"].requirements = {
        "A": [1],
        "B": [],
        "C": [],
        "G": [],
        "L": [],
        "W": [],
        "H": [],
    }

    scheduler = RosterScheduler(context)

    scheduler._assign_member_requirements()

    assert scheduler.roster["E001"][1] == "A"
    assert scheduler.roster["E002"][1] == "A"
    assert scheduler.roster["E003"][1] == "A"


def test_pass1_tracks_remaining_w_days():

    context = create_context()

    scheduler = RosterScheduler(context)

    scheduler._assign_member_requirements()

    # E001:
    # Required W quota = 4
    # Requested W = 1
    # Remaining = 3
    assert scheduler._get_remaining_w("E001") == 3

    # E002:
    # Required W quota = 4
    # Requested W = 1
    # Remaining = 3
    assert scheduler._get_remaining_w("E002") == 3

    # E003:
    # Required W quota = 4
    # Requested W = 0
    # Remaining = 4
    assert scheduler._get_remaining_w("E003") == 4


def test_pass1_tracks_remaining_h_days():

    context = create_context()

    scheduler = RosterScheduler(context)

    scheduler._assign_member_requirements()

    # Public holidays = 2
    #
    # E001 requested H once → remaining = 1
    assert scheduler._get_remaining_h("E001") == 1

    # E002 requested H zero times → remaining = 2
    assert scheduler._get_remaining_h("E002") == 2

    # E003 requested H once → remaining = 1
    assert scheduler._get_remaining_h("E003") == 1


def test_pass1_tracks_c_shift_counts():

    context = create_context()

    scheduler = RosterScheduler(context)

    scheduler._assign_member_requirements()

    assert scheduler._get_c_count("E001") == 1
    assert scheduler._get_c_count("E002") == 2
    assert scheduler._get_c_count("E003") == 0