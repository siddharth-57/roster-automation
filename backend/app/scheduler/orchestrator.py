from app.scheduler.config import SOLVER_TIME_LIMIT_SECONDS
from app.scheduler.context import RosterContext
from app.scheduler.cp_solver import RosterSolver, ScheduleResult


def generate_roster(
    context: RosterContext,
) -> ScheduleResult:
    """
    Generate a complete roster using the CP-SAT constraint solver.

    Replaces the old 5-pass greedy scheduler (scheduler.py). The returned
    ScheduleResult has the same attributes the API already uses:

        .roster                 -> {employee_id: {day: shift}}
        .warnings               -> list of messages for the frontend
        .relaxed_requirements   -> requests that had to be broken
        .status                 -> solver status (OPTIMAL / FEASIBLE / INFEASIBLE ...)

    If no valid roster exists, .roster is empty and .warnings explains why.

    No random seed is passed, so when requirements must be relaxed,
    who gets relaxed is chosen at random on each run (Rule 4).
    """

    solver = RosterSolver(
        context,
        time_limit_seconds=SOLVER_TIME_LIMIT_SECONDS,
    )

    return solver.solve()