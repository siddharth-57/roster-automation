import calendar
import random
from dataclasses import dataclass, field
from datetime import date

from ortools.sat.python import cp_model

from app.scheduler.config import (
    MAX_C_PER_DAY,
    MAX_C_PER_MEMBER,
    MAX_CONTINUOUS_WORKING_DAYS,
    MAX_G_PER_MEMBER,
    MIN_C_PER_MEMBER,
    WEEKEND_MAX_PER_SHIFT,
)
from app.scheduler.constraints import WORKING_SHIFTS
from app.scheduler.context import RosterContext


# Order doesn't matter to the solver; it's only used for iteration.
SHIFTS = ["A", "B", "C", "G", "W", "H", "L"]


# --------------------------------------------------
# Soft-rule penalty weights (higher = more important).
# The solve runs in four phases (see solve()), so a later
# phase can never undo an earlier one. Within a phase, these
# weights decide the trade-offs between its rules.
# --------------------------------------------------
W_REQUIREMENT = 10_000      # per broken requirement day
W_UNREQUESTED_L = 1_000     # per L the member didn't ask for
W_C_SPREAD = 100            # per unit of (most C - fewest C)
W_C_BLOCK = 150             # per separate run of C shifts (ideal: 1 run per member)
W_MEMBER_AB_BALANCE = 80    # per shift a member's |A - B| goes above the allowed gap
W_W_SPACING = 60            # per W missing below 2 / above 3 in any 7 days in a row
W_WEEKEND_EXTRA = 50        # per person above 1 in A/B (or any G) on weekends
W_LONE_W = 40               # per W with no W on the day before or after
W_AB_BALANCE = 20           # per unit of |A - B|, and per G above 1, each day
W_WEEKDAY_MIN = 10          # per person missing below 2 in A or B on weekdays
W_SWITCH = 1                # per change of working shift between consecutive days

WEEKDAY_MIN_PER_SHIFT = 2

# A member's A and B counts may differ by up to this much at no cost
MEMBER_AB_ALLOWED_GAP = 4

# In any 7 days in a row, a member should have between 2 and 3 W
W_SPACING_WINDOW = 7
W_SPACING_MIN = 2
W_SPACING_MAX = 3

# Rule 4: when several requirements are equally costly to break,
# pick at random. Each requirement gets a small random extra weight
# (0-99), so the cheapest one to break differs from run to run.
# 99 < the gap between tiers, so it never changes the priority order.
REQUIREMENT_JITTER = 100


@dataclass
class ScheduleResult:
    """
    Same attributes the API already reads from the old RosterScheduler,
    so api/roster.py doesn't need to change.
    """
    roster: dict[str, dict[int, str]]
    warnings: list[str] = field(default_factory=list)
    relaxed_requirements: list[dict] = field(default_factory=list)
    status: str = ""


class RosterSolver:
    def __init__(
        self,
        context: RosterContext,
        time_limit_seconds: float = 30.0,
        random_seed: int | None = None,
    ):
        self.context = context
        self.members = context.members
        self.days = range(1, context.days_in_month + 1)
        self.time_limit_seconds = time_limit_seconds
        self.random_seed = random_seed

        # Same seed -> same random tie-breaks (reproducible tests).
        # No seed -> different choice each run (Rule 4).
        self.rng = random.Random(random_seed)

        self.model = cp_model.CpModel()

        # x[(member, day, shift)] = 1 if the member works that shift that day
        self.x: dict[tuple[str, int, str], cp_model.IntVar] = {}

        # Previous-month days, numbered relative to this month:
        # day 0 = last day of previous month, -1 = the day before, ...
        # For MAX = 5 this is days -4..0 (5 days).
        self.history_days = range(1 - MAX_CONTINUOUS_WORKING_DAYS, 1)

        # history[member][day] = shift, or None if unknown (treated as off)
        self.history: dict[str, dict[int, str | None]] = {}

        # requested[(member, day)] = shift the TL entered for that day
        self.requested: dict[tuple[str, int], str] = {}

        # Weighted penalty terms, in four tiers (see solve()):
        #   primary  = requirements + unrequested L (what members notice most)
        #   c_block  = C shifts: one run per member, spread evenly
        #   fairness = A/B per member, W spacing,
        #              weekend headcount, W together
        #   polish   = daily A/B/G balance, weekday minimum, smoothness
        self.primary_penalties: list = []
        self.c_block_penalties: list = []
        self.fairness_penalties: list = []
        self.polish_penalties: list = []

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    def _count(self, member: str, shift: str):
        """Number of times a member has a given shift this month."""
        return sum(self.x[member, d, shift] for d in self.days)

    def _day_count(self, day: int, shift: str):
        """Number of members on a given shift on a given day."""
        return sum(self.x[m, day, shift] for m in self.members)

    def _is_working(self, member: str, day: int):
        """
        1 if the member works on this day, else 0.

        Days <= 0 are previous-month days: a fixed number from history.
        Days >= 1 are this month: a solver expression (sum of A/B/C/G).
        Because a member has exactly one shift per day, the sum is 0 or 1.
        """
        if day <= 0:
            return 1 if self.history[member][day] in WORKING_SHIFTS else 0

        return sum(self.x[member, day, s] for s in WORKING_SHIFTS)

    def _is_weekend(self, day: int) -> bool:
        return calendar.weekday(self.context.year, self.context.month, day) >= 5

    # --------------------------------------------------
    # Inputs
    # --------------------------------------------------

    def _build_history(self) -> None:
        """Rule 10: load the previous month's last days."""
        first_day = date(self.context.year, self.context.month, 1)

        self.history = {
            m: {d: None for d in self.history_days}
            for m in self.members
        }

        previous = self.context.previous_assignments or {}

        for m, assignments in previous.items():
            if m not in self.history:
                continue  # member no longer in this group

            for day_date, shift in assignments.items():
                d = (day_date - first_day).days + 1  # e.g. 30 Nov -> 0

                if d in self.history[m]:
                    self.history[m][d] = shift

    def _build_requested(self) -> None:
        """
        Flatten requirements from {shift: [days]} into {(member, day): shift}.

        If the same day appears under two shifts, the last one wins;
        request validation should stop that before it reaches here.
        """
        self.requested = {}

        for m in self.members:
            member_requirement = self.context.requirements.get(m)

            if not member_requirement:
                continue

            for shift, days in member_requirement.requirements.items():
                if shift not in SHIFTS:
                    continue

                for d in days:
                    if d in self.days:
                        self.requested[m, d] = shift

    # --------------------------------------------------
    # Variables
    # --------------------------------------------------

    def _create_variables(self) -> None:
        for m in self.members:
            for d in self.days:
                for s in SHIFTS:
                    self.x[m, d, s] = self.model.new_bool_var(
                        f"x_{m}_{d}_{s}"
                    )

    # ==================================================
    # HARD RULES
    # ==================================================

    # Hard rule 2: exactly one shift per member per day
    def _add_one_shift_per_day(self) -> None:
        for m in self.members:
            for d in self.days:
                self.model.add_exactly_one(
                    self.x[m, d, s] for s in SHIFTS
                )

    # Hard rule 1: at least 1 member in A, B and C every day
    def _add_daily_coverage(self) -> None:
        for d in self.days:
            for s in ("A", "B", "C"):
                self.model.add(self._day_count(d, s) >= 1)

    # Hard rule 6: at most MAX_C_PER_DAY members in C per day
    def _add_max_c_per_day(self) -> None:
        for d in self.days:
            self.model.add(self._day_count(d, "C") <= MAX_C_PER_DAY)

    # G limit: at most MAX_G_PER_MEMBER G shifts per member per month.
    def _add_max_g_per_member(self) -> None:
        for m in self.members:
            self.model.add(self._count(m, "G") <= MAX_G_PER_MEMBER)

    # Weekend limit: at most WEEKEND_MAX_PER_SHIFT members in each of
    # A, B and G on Saturdays and Sundays.
    def _add_weekend_max_per_shift(self) -> None:
        for d in self.days:
            if not self._is_weekend(d):
                continue

            for s in ("A", "B", "G"):
                self.model.add(
                    self._day_count(d, s) <= WEEKEND_MAX_PER_SHIFT
                )

    # Hard rule 5: MIN_C_PER_MEMBER <= C count <= MAX_C_PER_MEMBER
    def _add_c_count_per_member(self) -> None:
        for m in self.members:
            c_count = self._count(m, "C")
            self.model.add(c_count >= MIN_C_PER_MEMBER)
            self.model.add(c_count <= MAX_C_PER_MEMBER)

    # Hard rule 3: every member gets exactly the required W count
    def _add_w_count(self) -> None:
        for m in self.members:
            self.model.add(
                self._count(m, "W") == self.context.required_w_days
            )

    # Hard rule 4: every member gets exactly the required H count
    def _add_h_count(self) -> None:
        for m in self.members:
            self.model.add(
                self._count(m, "H") == self.context.public_holidays
            )

    # Hard rule 7 (+ Rule 10): max continuous working days.
    # In every window of (MAX + 1) days, at most MAX are working days.
    # Windows at the start of the month reach into previous-month history.
    def _add_max_consecutive_working_days(self) -> None:
        window = MAX_CONTINUOUS_WORKING_DAYS + 1

        for m in self.members:
            for end in self.days:
                start = end - window + 1

                self.model.add(
                    sum(
                        self._is_working(m, d)
                        for d in range(start, end + 1)
                    )
                    <= MAX_CONTINUOUS_WORKING_DAYS
                )

    # Hard rule 8 (+ Rule 10): the day after C must be C/W/H/L.
    #     C(d) + A(d+1) + B(d+1) + G(d+1) <= 1
    def _add_c_followed_by_c_or_off(self) -> None:
        for m in self.members:

            # Previous month ended on C -> day 1 can't be A/B/G
            if self.history[m][0] == "C":
                for s in ("A", "B", "G"):
                    self.model.add(self.x[m, 1, s] == 0)

            for d in self.days:
                if d == self.context.days_in_month:
                    continue  # handled next month via history

                self.model.add(
                    self.x[m, d, "C"]
                    + self.x[m, d + 1, "A"]
                    + self.x[m, d + 1, "B"]
                    + self.x[m, d + 1, "G"]
                    <= 1
                )

    # ==================================================
    # SOFT RULES (penalties)
    # ==================================================

    # Rule 11: satisfy member requirements.
    # Penalty = weight x (1 - x): 0 if the requested shift is given, weight if not.
    def _add_requirement_penalties(self) -> None:
        for (m, d), s in self.requested.items():
            weight = W_REQUIREMENT + self.rng.randrange(REQUIREMENT_JITTER)
            self.primary_penalties.append(weight * (1 - self.x[m, d, s]))

    # Rule 9: L only when requested, or when no W/H is left.
    # W and H counts are already exact, so any extra day off must be L,
    # and every unrequested L costs a penalty.
    def _add_unrequested_l_penalties(self) -> None:
        for m in self.members:
            for d in self.days:
                if self.requested.get((m, d)) == "L":
                    continue  # requested L is covered by the requirement penalty

                self.primary_penalties.append(W_UNREQUESTED_L * self.x[m, d, "L"])

    # Spread C shifts evenly: penalise (most C - fewest C).
    # max_c is pushed up to the highest count, min_c down to the lowest;
    # minimising the gap makes the solver even them out.
    def _add_c_spread_penalty(self) -> None:
        days = self.context.days_in_month

        max_c = self.model.new_int_var(0, days, "max_c")
        min_c = self.model.new_int_var(0, days, "min_c")

        for m in self.members:
            c_count = self._count(m, "C")
            self.model.add(max_c >= c_count)
            self.model.add(min_c <= c_count)

        self.c_block_penalties.append(W_C_SPREAD * (max_c - min_c))

    # Keep each member's C shifts together: penalise every day a new
    # run of C starts (C today, not C yesterday). Every member has at
    # least one run, so the ideal is exactly one run each.
    #     start >= C(d) - C(d-1)
    # Day 1 looks back at the previous month's last day, so a run that
    # continues from last month isn't counted as a new one.
    def _add_c_block_penalty(self) -> None:
        for m in self.members:
            for d in self.days:
                if d == 1:
                    previous_c = 1 if self.history[m][0] == "C" else 0
                else:
                    previous_c = self.x[m, d - 1, "C"]

                start = self.model.new_bool_var(f"c_start_{m}_{d}")
                self.model.add(start >= self.x[m, d, "C"] - previous_c)

                self.c_block_penalties.append(W_C_BLOCK * start)

    # Each member's A and B counts should be balanced over the month.
    # A gap of up to MEMBER_AB_ALLOWED_GAP is free; every shift beyond
    # that costs a penalty.
    #     excess >= (A - B) - allowed
    #     excess >= (B - A) - allowed
    def _add_member_ab_balance_penalty(self) -> None:
        days = self.context.days_in_month

        for m in self.members:
            a = self._count(m, "A")
            b = self._count(m, "B")

            excess = self.model.new_int_var(0, days, f"ab_excess_{m}")
            self.model.add(excess >= a - b - MEMBER_AB_ALLOWED_GAP)
            self.model.add(excess >= b - a - MEMBER_AB_ALLOWED_GAP)

            self.fairness_penalties.append(W_MEMBER_AB_BALANCE * excess)

    # W spacing: in every 7 days in a row, each member should have
    # 2 to 3 W. Penalise each W missing below 2 or above 3.
    #     shortfall >= 2 - W_in_window
    #     surplus   >= W_in_window - 3
    def _add_w_spacing_penalty(self) -> None:
        last_start = self.context.days_in_month - W_SPACING_WINDOW + 1

        for m in self.members:
            for start in range(1, last_start + 1):
                w_in_window = sum(
                    self.x[m, d, "W"]
                    for d in range(start, start + W_SPACING_WINDOW)
                )

                shortfall = self.model.new_int_var(
                    0, W_SPACING_MIN, f"w_short_{m}_{start}"
                )
                surplus = self.model.new_int_var(
                    0, W_SPACING_WINDOW, f"w_surplus_{m}_{start}"
                )

                self.model.add(shortfall >= W_SPACING_MIN - w_in_window)
                self.model.add(surplus >= w_in_window - W_SPACING_MAX)

                self.fairness_penalties.append(
                    W_W_SPACING * (shortfall + surplus)
                )

    # Keep W together: penalise a W with no W the day before or after.
    #     lone >= W(d) - W(d-1) - W(d+1)
    # Day 1 looks back at the previous month's last day. A W on the
    # last day of the month isn't penalised, since next month's
    # day 1 may well be a W too.
    def _add_lone_w_penalty(self) -> None:
        last_day = self.context.days_in_month

        for m in self.members:
            for d in self.days:
                if d == last_day:
                    continue

                if d == 1:
                    previous_w = 1 if self.history[m][0] == "W" else 0
                else:
                    previous_w = self.x[m, d - 1, "W"]

                lone = self.model.new_bool_var(f"lone_w_{m}_{d}")
                self.model.add(
                    lone
                    >= self.x[m, d, "W"]
                    - previous_w
                    - self.x[m, d + 1, "W"]
                )

                self.fairness_penalties.append(W_LONE_W * lone)

    # Rule 12: on weekends keep 1 in A, 1 in B and nobody in G.
    # A and B are already >= 1, so the extra people are A + B + G - 2.
    def _add_weekend_headcount_penalty(self) -> None:
        for d in self.days:
            if not self._is_weekend(d):
                continue

            extra = (
                self._day_count(d, "A")
                + self._day_count(d, "B")
                + self._day_count(d, "G")
                - 2
            )
            self.fairness_penalties.append(W_WEEKEND_EXTRA * extra)

    # Rule 13 (generalised, as in old Pass 5): every day, A and B as equal
    # as possible, and at most one G to take the odd person.
    #     imbalance >= |A - B|
    #     extra_g   >= G - 1
    # e.g. 2A + 1B -> best is 1A + 1B + 1G (imbalance 0, extra_g 0).
    def _add_ab_balance_penalty(self) -> None:
        n = len(self.members)

        for d in self.days:
            a = self._day_count(d, "A")
            b = self._day_count(d, "B")
            g = self._day_count(d, "G")

            imbalance = self.model.new_int_var(0, n, f"imbalance_{d}")
            self.model.add(imbalance >= a - b)
            self.model.add(imbalance >= b - a)

            extra_g = self.model.new_int_var(0, n, f"extra_g_{d}")
            self.model.add(extra_g >= g - 1)

            self.polish_penalties.append(W_AB_BALANCE * (imbalance + extra_g))

    # Old Pass 3 preference: at least 2 in A and 2 in B on weekdays.
    #     shortfall >= 2 - count
    def _add_weekday_minimum_penalty(self) -> None:
        for d in self.days:
            if self._is_weekend(d):
                continue

            for s in ("A", "B"):
                shortfall = self.model.new_int_var(
                    0, WEEKDAY_MIN_PER_SHIFT, f"shortfall_{s}_{d}"
                )
                self.model.add(
                    shortfall >= WEEKDAY_MIN_PER_SHIFT - self._day_count(d, s)
                )
                self.polish_penalties.append(W_WEEKDAY_MIN * shortfall)

    # Smooth rosters: penalise a change of working shift between two
    # consecutive working days (e.g. A -> B). Moving to/from a day off
    # is not a switch.
    #
    # For each working shift s:
    #     switch >= s(d) + working(d+1) - s(d+1) - 1
    # i.e. "s today, working tomorrow, but not s tomorrow" forces switch = 1.
    def _add_shift_switch_penalty(self) -> None:
        for m in self.members:
            for d in self.days:
                if d == self.context.days_in_month:
                    continue

                switch = self.model.new_bool_var(f"switch_{m}_{d}")
                working_next = self._is_working(m, d + 1)

                for s in WORKING_SHIFTS:
                    self.model.add(
                        switch
                        >= self.x[m, d, s]
                        + working_next
                        - self.x[m, d + 1, s]
                        - 1
                    )

                self.polish_penalties.append(W_SWITCH * switch)

    # --------------------------------------------------
    # Model assembly: every rule is registered here
    # --------------------------------------------------

    def _build_model(self) -> None:
        self._build_history()
        self._build_requested()
        self._create_variables()

        # Hard rules
        self._add_one_shift_per_day()
        self._add_daily_coverage()
        self._add_max_c_per_day()
        self._add_c_count_per_member()
        self._add_w_count()
        self._add_h_count()
        self._add_max_consecutive_working_days()
        self._add_c_followed_by_c_or_off()
        self._add_weekend_max_per_shift()
        self._add_max_g_per_member()

        # Soft rules, highest priority first
        self._add_requirement_penalties()
        self._add_unrequested_l_penalties()
        self._add_c_spread_penalty()
        self._add_c_block_penalty()
        self._add_member_ab_balance_penalty()
        self._add_w_spacing_penalty()
        self._add_weekend_headcount_penalty()
        self._add_lone_w_penalty()
        self._add_ab_balance_penalty()
        self._add_weekday_minimum_penalty()
        self._add_shift_switch_penalty()

    # --------------------------------------------------
    # Read the solution back
    # --------------------------------------------------

    def _extract_roster(
        self,
        solver: cp_model.CpSolver,
    ) -> dict[str, dict[int, str]]:
        roster = {m: {} for m in self.members}

        for m in self.members:
            for d in self.days:
                for s in SHIFTS:
                    if solver.value(self.x[m, d, s]):
                        roster[m][d] = s
                        break

        return roster

    def _extract_relaxed_requirements(
        self,
        roster: dict[str, dict[int, str]],
    ) -> list[dict]:
        """Same format as the old scheduler: employee_id, day, shift."""
        relaxed = []

        for (m, d), s in sorted(
            self.requested.items(),
            key=lambda item: (item[0][1], item[0][0]),  # by day, then member
        ):
            if roster[m][d] != s:
                relaxed.append(
                    {"employee_id": m, "day": d, "shift": s}
                )

        return relaxed

    def _build_warnings(
        self,
        roster: dict[str, dict[int, str]],
    ) -> list[str]:
        warnings = []

        for m in self.members:
            for d in self.days:
                if roster[m][d] == "L" and self.requested.get((m, d)) != "L":
                    warnings.append(
                        f"{m} was given L on day {d} (not requested; "
                        f"no W/H could be used)."
                    )

        return warnings

    # --------------------------------------------------
    # Entry point
    # --------------------------------------------------

    def _new_solver(self, time_limit: float) -> cp_model.CpSolver:
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = max(time_limit, 0.1)

        if self.random_seed is not None:
            solver.parameters.random_seed = self.random_seed

        return solver

    def solve(self) -> ScheduleResult:
        """
        Four-phase (lexicographic) solve:

        Phase 1: minimise the primary penalties (requirements + L).
        Phase 2: lock phase 1's result (it can't get worse), start from
                 its roster, and arrange C shifts: one run per member,
                 spread evenly.
        Phase 3: lock phase 2's result too, and minimise the fairness
                 penalties.
        Phase 4: lock phase 3's result, and minimise the polish
                 penalties with the remaining time.

        One combined objective would mean the same thing in theory, but in
        practice the solver can spend all its time on small things like
        shift switches before it has settled the important ones.
        """
        self._build_model()

        tiers = [
            ("primary", sum(self.primary_penalties), 0.15),
            ("c_block", sum(self.c_block_penalties), 0.25),
            ("fairness", sum(self.fairness_penalties), 0.35),
            ("polish", sum(self.polish_penalties), None),  # None = remaining time
        ]

        remaining = self.time_limit_seconds
        best_solver = None
        best_status = None

        for index, (name, objective, share) in enumerate(tiers):
            limit = remaining if share is None else self.time_limit_seconds * share

            if best_solver is not None:
                # Start from the previous phase's roster
                self.model.clear_hints()
                for var in self.x.values():
                    self.model.add_hint(var, best_solver.value(var))

            self.model.minimize(objective)
            solver = self._new_solver(min(limit, remaining))
            status = solver.solve(self.model)
            remaining -= solver.wall_time

            if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                if index == 0:
                    return ScheduleResult(
                        roster={},
                        warnings=[
                            "No valid roster found: the hard rules can't all "
                            "be met for this month and team (solver status: "
                            f"{solver.status_name(status)})."
                        ],
                        status=solver.status_name(status),
                    )

                # A later phase found nothing better in time:
                # keep the previous phase's roster.
                break

            best_solver, best_status = solver, status

            # Lock this phase's result before moving on
            self.model.add(objective <= int(round(solver.objective_value)))

        roster = self._extract_roster(best_solver)

        return ScheduleResult(
            roster=roster,
            warnings=self._build_warnings(roster),
            relaxed_requirements=self._extract_relaxed_requirements(roster),
            status=best_solver.status_name(best_status),
        )