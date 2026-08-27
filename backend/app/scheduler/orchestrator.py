from app.scheduler.context import RosterContext
from app.scheduler.scheduler import RosterScheduler


def generate_roster(
    context: RosterContext,
) -> RosterScheduler:
    """
    Generate a complete roster by executing all scheduling passes
    in the required order.

    Pass order:

        Pass 1
            ↓
        Pass 2
            ↓
        Pass 3
            ↓
        Pass 4
            ↓
        Pass 5

    Returns the completed RosterScheduler instance so that callers
    can access the final roster as well as scheduling metadata such
    as warnings, relaxed requirements, active requirements, and
    remaining quotas.
    """

    scheduler = RosterScheduler(context)

    # ------------------------------------------------------
    # Pass 1
    # Load the requirements into the roster.
    # ------------------------------------------------------
    scheduler._assign_member_requirements()

    # ------------------------------------------------------
    # Pass 2
    # Handle daily A/B/C coverage and Pass 2 logic.
    # ------------------------------------------------------
    scheduler._run_pass_2()

    # ------------------------------------------------------
    # Pass 3
    # Allocate remaining W/H where possible without
    # relaxing active requirements.
    # ------------------------------------------------------
    scheduler._run_pass3()

    # ------------------------------------------------------
    # Pass 4
    # Allocate remaining W/H where necessary, including
    # relaxing active requirements when allowed.
    # ------------------------------------------------------
    scheduler._run_pass4()

    # ------------------------------------------------------
    # Pass 5
    # Balance A/B and introduce G where appropriate.
    # ------------------------------------------------------
    scheduler._run_pass5()

    return scheduler