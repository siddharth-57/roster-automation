import calendar
from datetime import date
from functools import lru_cache

from app.scheduler.config import MAX_C_PER_MEMBER, MIN_C_PER_MEMBER
from app.scheduler.constraints import WORKING_SHIFTS
from app.scheduler.context import MemberRequirement
from app.scheduler.context_builder import build_roster_context
from app.scheduler.cp_solver import RosterSolver
from app.scheduler.validator import (
    validate_daily_staffing,
    validate_c_shift_daily_limit,
    validate_c_shift_limits,
    validate_w_counts,
    validate_h_counts,
    validate_c_continuation,
    validate_continuous_working_days,
    validate_roster,
    validate_weekend_max_per_shift,
    validate_g_shift_limit,
)


# The solver optimises soft rules, so it usually runs until the time limit.
# The shared no-requirements roster (checked by most tests) gets more time;
# the other tests mainly check hard rules and requirements, so 10 s is enough.
TEST_TIME_LIMIT = 10
DEFAULT_ROSTER_TIME_LIMIT = 30

DEFAULT_MEMBERS = [f"E00{i}" for i in range(1, 9)]  # 8 members


def make_context(
    year=2026,
    month=12,
    public_holidays=1,
    members=None,
    requirements=None,
    previous_assignments=None,
):
    members = members or DEFAULT_MEMBERS
    requirements = requirements or {}

    requirement_objects = {
        m: MemberRequirement(
            employee_id=m,
            requirements=requirements.get(m, {}),
        )
        for m in members
    }

    return build_roster_context(
        year=year,
        month=month,
        group_number="1",
        public_holidays=public_holidays,
        members=members,
        requirements=requirement_objects,
        previous_assignments=previous_assignments or {},
    )


def solve(ctx, seed=42, time_limit=TEST_TIME_LIMIT):
    return RosterSolver(
        ctx,
        time_limit_seconds=time_limit,
        random_seed=seed,
    ).solve()


@lru_cache(maxsize=1)
def default_result():
    """Solve the no-requirements month once and reuse it in many tests."""
    ctx = make_context()
    return ctx, solve(ctx, time_limit=DEFAULT_ROSTER_TIME_LIMIT)


def print_roster(roster, days_in_month):
    width = max(len(m) for m in roster) + 1
    header = " " * width + " ".join(f"{d:>2}" for d in range(1, days_in_month + 1))
    print("\n" + header)
    for m, days in roster.items():
        row = " ".join(f"{days[d]:>2}" for d in range(1, days_in_month + 1))
        print(f"{m:<{width}}{row}")


def count_l(roster):
    return sum(
        shift == "L"
        for days in roster.values()
        for shift in days.values()
    )


def day_count(roster, day, shift):
    return sum(days[day] == shift for days in roster.values())


def is_weekend(ctx, day):
    return calendar.weekday(ctx.year, ctx.month, day) >= 5


def count_switches(roster, days_in_month):
    return sum(
        1
        for days in roster.values()
        for d in range(1, days_in_month)
        if days[d] in WORKING_SHIFTS
        and days[d + 1] in WORKING_SHIFTS
        and days[d] != days[d + 1]
    )


# ------------------------------------------------------
# Steps 2-4: basic hard rules
# ------------------------------------------------------

def test_one_shift_per_member_per_day():
    ctx, result = default_result()

    assert result.status in ("OPTIMAL", "FEASIBLE")

    for m in ctx.members:
        assert len(result.roster[m]) == ctx.days_in_month


def test_daily_abc_coverage():
    ctx, result = default_result()

    errors = validate_daily_staffing(result.roster, ctx.days_in_month)
    assert errors == [], errors


def test_max_c_per_day():
    ctx, result = default_result()

    errors = validate_c_shift_daily_limit(result.roster, ctx.days_in_month)
    assert errors == [], errors


def test_c_count_per_member():
    ctx, result = default_result()

    errors = validate_c_shift_limits(result.roster)
    assert errors == [], errors


def test_w_count():
    ctx, result = default_result()

    errors = validate_w_counts(result.roster, ctx.year, ctx.month)
    assert errors == [], errors


def test_h_count():
    ctx, result = default_result()

    errors = validate_h_counts(result.roster, ctx.public_holidays)
    assert errors == [], errors


# ------------------------------------------------------
# Step 5: sequence rules + previous month
# ------------------------------------------------------

def test_c_followed_by_c_or_off():
    ctx, result = default_result()

    errors = validate_c_continuation(result.roster, ctx.days_in_month)
    assert errors == [], errors


def test_max_consecutive_working_days():
    ctx, result = default_result()

    errors = validate_continuous_working_days(result.roster, ctx.days_in_month)
    assert errors == [], errors


def test_previous_month_history():
    def nov(d):
        return date(2026, 11, d)

    previous = {
        # Worked all 5 last days -> day 1 must be a day off
        "E001": {nov(d): "A" for d in range(26, 31)},

        # Ended on C -> day 1 must be C or a day off
        "E002": {nov(26): "W", nov(27): "W", nov(28): "A", nov(29): "B", nov(30): "C"},

        # 3-day streak at the end -> can't work all of days 1, 2, 3
        "E003": {nov(26): "W", nov(27): "W", nov(28): "A", nov(29): "A", nov(30): "A"},
    }

    ctx = make_context(previous_assignments=previous)
    result = solve(ctx)

    roster = result.roster

    assert roster["E001"][1] in {"W", "H", "L"}
    assert roster["E002"][1] in {"C", "W", "H", "L"}
    assert not all(roster["E003"][d] in WORKING_SHIFTS for d in (1, 2, 3))

    errors = validate_roster(
        roster, ctx.year, ctx.month, ctx.public_holidays, previous,
    )
    assert errors == [], errors


# ------------------------------------------------------
# Step 6: requirements + unrequested L
# ------------------------------------------------------

def test_no_unrequested_l_without_requirements():
    ctx, result = default_result()

    assert count_l(result.roster) == 0
    assert result.relaxed_requirements == []


# The example from the rules document, plus 3 extra members.
# With only 5 members the C rules can't be met: 31 C shifts are needed,
# but 5 members x max 5 C = 25.
EXAMPLE_MEMBERS = [
    "Suraksha", "Suresh", "Shubham", "Sankalp", "Siddharth",
    "Member6", "Member7", "Member8",
]

EXAMPLE_REQUIREMENTS = {
    "Suraksha": {"A": [2, 3, 4], "B": [16, 17, 18], "W": [29, 30, 31]},
    "Suresh": {"C": [2, 3, 4], "B": [16, 17, 18], "W": [30, 31]},
    "Shubham": {"A": [5, 12, 17, 31], "C": [7, 8, 9, 10]},
    "Sankalp": {"L": [27, 28], "W": [29, 30, 31]},
    "Siddharth": {"B": [29, 30, 31]},
}


def test_example_requirements_all_met():
    ctx = make_context(
        members=EXAMPLE_MEMBERS,
        requirements=EXAMPLE_REQUIREMENTS,
    )
    result = solve(ctx)

    print("\n--- Example from rules document ---")
    print_roster(result.roster, ctx.days_in_month)
    print("Relaxed:", result.relaxed_requirements)
    print("Warnings:", result.warnings)

    # Every request can be met here, so none should be broken
    assert result.relaxed_requirements == []

    # Only Sankalp's requested L should appear
    assert count_l(result.roster) == 2
    assert result.roster["Sankalp"][27] == "L"
    assert result.roster["Sankalp"][28] == "L"

    errors = validate_roster(
        result.roster, ctx.year, ctx.month, ctx.public_holidays,
    )
    assert errors == [], errors


def test_conflict_breaks_minimum_requirements():
    # Everyone asks for W on the 31st -> A, B and C still need 1 each,
    # so exactly 3 requests must be broken, no more.
    requirements = {m: {"W": [31]} for m in DEFAULT_MEMBERS}

    ctx = make_context(requirements=requirements)
    result = solve(ctx)

    print("\n--- Everyone wants W on the 31st ---")
    print("Relaxed:", result.relaxed_requirements)

    assert len(result.relaxed_requirements) == 3

    errors = validate_roster(
        result.roster, ctx.year, ctx.month, ctx.public_holidays,
    )
    assert errors == [], errors


def test_relaxation_choice_varies_with_seed():
    # Rule 4: who gets relaxed should be random. Print a few seeds to see it.
    requirements = {m: {"W": [31]} for m in DEFAULT_MEMBERS}

    print("\n--- Who gets relaxed, by seed ---")
    for seed in (1, 2, 3):
        ctx = make_context(requirements=requirements)
        result = solve(ctx, seed=seed)

        relaxed = sorted(r["employee_id"] for r in result.relaxed_requirements)
        print(f"seed {seed}: {relaxed}")

        assert len(relaxed) == 3


# ------------------------------------------------------
# Step 7: remaining soft rules
# ------------------------------------------------------

def test_print_default_roster_and_daily_counts():
    ctx, result = default_result()

    print("\n--- No requirements (all soft rules) ---")
    print_roster(result.roster, ctx.days_in_month)

    print("\nday       A  B  C  G")
    for d in range(1, ctx.days_in_month + 1):
        tag = "WE" if is_weekend(ctx, d) else "  "
        counts = "  ".join(str(day_count(result.roster, d, s)) for s in "ABCG")
        print(f"{d:>2} {tag}    {counts}")

    print("\nShift switches:", count_switches(result.roster, ctx.days_in_month))


def test_c_spread_even():
    ctx, result = default_result()

    c_counts = [
        sum(shift == "C" for shift in result.roster[m].values())
        for m in ctx.members
    ]
    print("\nC per member:", c_counts)

    # 31 C shifts over 8 members -> best possible is 4s and 3s
    assert max(c_counts) - min(c_counts) <= 1
    assert MIN_C_PER_MEMBER <= min(c_counts)
    assert max(c_counts) <= MAX_C_PER_MEMBER


def test_weekend_headcount():
    # Hard rule: at most WEEKEND_MAX_PER_SHIFT (2) in each of A, B, G
    # on weekends. Soft rule: prefer 1 in A, 1 in B and nobody in G;
    # extra people are allowed when they help the balance rules.
    ctx, result = default_result()

    errors = validate_weekend_max_per_shift(
        result.roster, ctx.year, ctx.month,
    )
    assert errors == [], errors

    extra_people = []
    for d in ctx_days(ctx):
        if not is_weekend(ctx, d):
            continue

        a = day_count(result.roster, d, "A")
        b = day_count(result.roster, d, "B")
        g = day_count(result.roster, d, "G")

        if (a, b, g) != (1, 1, 0):
            extra_people.append((d, f"A={a} B={b} G={g}"))

    print("\nWeekend days with extra people:", extra_people)


def test_weekend_cap_beats_requests():
    # 3 people request A on a Saturday: the hard cap of 2 wins,
    # so exactly one of those requests is broken.
    requirements = {m: {"A": [5]} for m in DEFAULT_MEMBERS[:3]}  # 5 Dec 2026 = Sat

    ctx = make_context(requirements=requirements)
    result = solve(ctx)

    assert day_count(result.roster, 5, "A") <= 2
    assert len(result.relaxed_requirements) == 1, result.relaxed_requirements

    errors = validate_roster(
        result.roster, ctx.year, ctx.month, ctx.public_holidays,
    )
    assert errors == [], errors


def count_c_runs(days, days_in_month):
    """Number of separate runs of C in a member's month."""
    return sum(
        1
        for d in range(1, days_in_month + 1)
        if days[d] == "C" and days.get(d - 1) != "C"
    )


def test_c_shifts_in_one_run():
    ctx, result = default_result()

    runs = {
        m: count_c_runs(result.roster[m], ctx.days_in_month)
        for m in ctx.members
    }
    print("\nC runs per member:", runs)

    assert all(r == 1 for r in runs.values()), runs


def test_c_runs_with_requests():
    # The example from the rules document. Here one split is FORCED:
    # Shubham's A on 5 + C on 7-10 means he can't also do C on 6
    # (6 working days in a row), and Suresh (C on 2-4) can do at most
    # 5 C, so days 1, 5 and 6 can't all be covered without someone
    # needing a second run. Expect exactly one member with 2 runs.
    ctx = make_context(
        members=EXAMPLE_MEMBERS,
        requirements=EXAMPLE_REQUIREMENTS,
    )
    result = solve(ctx, time_limit=DEFAULT_ROSTER_TIME_LIMIT)

    runs = {
        m: count_c_runs(result.roster[m], ctx.days_in_month)
        for m in ctx.members
    }
    print("\nC runs per member (example):", runs)

    assert result.relaxed_requirements == []
    assert max(runs.values()) <= 2, runs
    assert sum(r == 2 for r in runs.values()) <= 1, runs


def test_ab_balance_and_g():
    ctx, result = default_result()

    for d in ctx_days(ctx):
        a = day_count(result.roster, d, "A")
        b = day_count(result.roster, d, "B")
        g = day_count(result.roster, d, "G")

        assert abs(a - b) <= 1, f"day {d}: A={a} B={b}"
        assert g <= 1, f"day {d}: G={g}"

        # Rule 13: never a 2-1 split with no G
        assert not ({a, b} == {1, 2} and g == 0), f"day {d}: A={a} B={b} G=0"


def test_weekday_minimum():
    # Lowest-priority rule: it gives way to W spacing / W together
    # (pairs of W on weekdays mean fewer people on some weekdays),
    # so a couple of short days are allowed.
    ctx, result = default_result()

    short_days = [
        d
        for d in ctx_days(ctx)
        if not is_weekend(ctx, d)
        and (
            day_count(result.roster, d, "A") < 2
            or day_count(result.roster, d, "B") < 2
        )
    ]

    print("\nWeekdays with fewer than 2 in A or B:", short_days)
    assert len(short_days) <= 2, short_days


def ctx_days(ctx):
    return range(1, ctx.days_in_month + 1)


# ------------------------------------------------------
# Step 8: member A/B balance + W spacing + W together
# ------------------------------------------------------

def test_member_ab_balance():
    ctx, result = default_result()

    for m in ctx.members:
        a = sum(s == "A" for s in result.roster[m].values())
        b = sum(s == "B" for s in result.roster[m].values())

        assert abs(a - b) <= 4, f"{m}: A={a} B={b}"


def test_w_spacing():
    # Every 7 days in a row should have 2-3 W. It's a soft rule, so a few
    # windows may miss (out of 8 members x 25 windows = 200), more so on
    # slower machines where the solver has less time to polish.
    ctx, result = default_result()

    misses = []
    for m in ctx.members:
        days = result.roster[m]

        for start in range(1, ctx.days_in_month - 7 + 2):
            w = sum(days[d] == "W" for d in range(start, start + 7))
            if not 2 <= w <= 3:
                misses.append((m, start, w))

    print("\n7-day windows outside 2-3 W:", misses)
    assert len(misses) <= 8, misses


def test_w_kept_together():
    ctx, result = default_result()

    lone = []
    for m in ctx.members:
        days = result.roster[m]

        for d in range(1, ctx.days_in_month):  # last day not checked
            if days[d] != "W":
                continue

            before = days.get(d - 1) == "W"
            after = days.get(d + 1) == "W"

            if not before and not after:
                lone.append((m, d))

    print("\nLone W:", lone)
    assert lone == [], lone


# ------------------------------------------------------
# G limit: at most 4 G per member per month
# ------------------------------------------------------

def test_max_g_per_member():
    ctx, result = default_result()

    g_counts = {
        m: sum(s == "G" for s in result.roster[m].values())
        for m in ctx.members
    }
    print("\nG per member:", g_counts)

    errors = validate_g_shift_limit(result.roster)
    assert errors == [], errors


def test_g_limit_beats_requests():
    # One member asks for G on 6 weekdays: the hard limit of 4 wins,
    # so exactly 2 of those requests are broken.
    g_days = [2, 3, 9, 10, 16, 17]  # Wed/Thu in Dec 2026
    requirements = {"E001": {"G": g_days}}

    ctx = make_context(requirements=requirements)
    result = solve(ctx)

    g_count = sum(s == "G" for s in result.roster["E001"].values())

    assert g_count <= 4
    assert len(result.relaxed_requirements) == 2, result.relaxed_requirements

    errors = validate_roster(
        result.roster, ctx.year, ctx.month, ctx.public_holidays,
    )
    assert errors == [], errors