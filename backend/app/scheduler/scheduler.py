from app.scheduler.context import RosterContext
from app.scheduler.constraints import can_assign_shift

class RosterScheduler:
    """ Generates a roster using the multi-pass scheduling architecture. """
    
    def __init__(self, context: RosterContext):
        self.context = context

        # employee_id -> {day: shift}
        self.roster: dict[str, dict[int, str]] = {
            employee_id: {}
            for employee_id in context.members
        }

        # Remaining monthly non-working-day quotas.
        #
        # W = number of Saturdays + Sundays in the month
        # H = number of public holidays supplied by the TL
        self.remaining_w: dict[str, int] = {
            employee_id: context.required_w_days
            for employee_id in context.members
        }

        self.remaining_h: dict[str, int] = {
            employee_id: context.public_holidays
            for employee_id in context.members
        }

        # Number of C shifts currently assigned to each member.
        self.c_shift_counts: dict[str, int] = {
            employee_id: 0
            for employee_id in context.members
        }
        
        # Requirements that were removed because they prevented
        # the roster from satisfying hard constraints.
        self.relaxed_requirements: list[dict] = []


    # ------------------------------------------------------------------
    #                           PASS 1
    # ------------------------------------------------------------------

    def _assign_member_requirements(self) -> None:
        """ Pass 1: Load every member requirement into the roster exactly as provided by the frontend.
        No roster constraints are checked or enforced here.
        At the same time, maintain: remaining W quota, remaining H quota, C shift count. """

        for employee_id in self.context.members:
            member_requirement = self.context.requirements[
                employee_id
            ]

            for shift, days in member_requirement.requirements.items():
                for day in days:
                    # Pass 1 intentionally performs a direct assignment.
                    self.roster[employee_id][day] = shift

                    if shift == "W":
                        self.remaining_w[employee_id] -= 1

                    elif shift == "H":
                        self.remaining_h[employee_id] -= 1

                    elif shift == "C":
                        self.c_shift_counts[employee_id] += 1
    # For each member get remaining W after assignments have been completed
    def _get_remaining_w(self, employee_id: str) -> int:
        return self.remaining_w[employee_id]
    # For each member get remaining H after assignments have been completed
    def _get_remaining_h(self, employee_id: str) -> int:
        return self.remaining_h[employee_id]
    # For each member get C shift count after assignments have been completed
    def _get_c_count(self, employee_id: str) -> int:
        return self.c_shift_counts[employee_id]




    # ------------------------------------------------------------------
    #                   PASS 2 - STEP 1
    # ------------------------------------------------------------------

    def _is_existing_assignment_valid(
        self,
        employee_id: str,
        day: int,
        shift: str,
    ) -> bool:
        """
        Check whether an already assigned shift is valid.

        The constraint layer's can_assign_shift() expects the target
        day to be empty, so temporarily remove the existing assignment
        before checking it.

        This method does not permanently modify the roster.
        """

        current_shift = self.roster[employee_id].get(day)

        if current_shift != shift:
            return False

        # Temporarily remove the current assignment so that
        # can_assign_shift() can evaluate it as a new assignment.
        del self.roster[employee_id][day]

        try:
            return can_assign_shift(
                self.roster,
                employee_id,
                day,
                shift,
                self.context.previous_assignments,
            )
        finally:
            # Restore the assignment.
            self.roster[employee_id][day] = shift

    def _record_relaxed_requirement(
        self,
        employee_id: str,
        day: int,
        shift: str,
    ) -> None:
        """
        Record a member requirement that had to be relaxed.
        """

        self.relaxed_requirements.append(
            {
                "employee_id": employee_id,
                "day": day,
                "shift": shift,
            }
        )

    def _remove_assignment(
        self,
        employee_id: str,
        day: int,
    ) -> str | None:
        """
        Permanently remove an assignment from the roster and update
        the associated tracking information.

        Returns the removed shift.
        """

        shift = self.roster[employee_id].pop(day, None)

        if shift is None:
            return None

        if shift == "W":
            self.remaining_w[employee_id] += 1

        elif shift == "H":
            self.remaining_h[employee_id] += 1

        elif shift == "C":
            self.c_shift_counts[employee_id] -= 1

        return shift

    def _validate_existing_requirement(
        self,
        employee_id: str,
        day: int,
    ) -> bool:
        """
        Validate the current assignment for a member on a given day.

        If valid:
            keep it.

        If invalid:
            remove it and record the relaxed requirement.

        Returns True if the assignment remains in the roster,
        otherwise False.
        """

        shift = self.roster[employee_id].get(day)

        if shift is None:
            return False

        if self._is_existing_assignment_valid(
            employee_id,
            day,
            shift,
        ):
            return True

        self._remove_assignment(
            employee_id,
            day,
        )

        self._record_relaxed_requirement(
            employee_id,
            day,
            shift,
        )

        return False

    def _validate_day_requirements(
        self,
        day: int,
    ) -> None:
        """
        Pass 2 Step 1 for a single day.

        Validate all members that currently have an assignment
        for this day.

        Invalid assignments are removed and recorded as relaxed
        requirements.
        """

        for employee_id in self.context.members:
            if day not in self.roster[employee_id]:
                continue

            self._validate_existing_requirement(
                employee_id,
                day,
            )

    def _run_pass_2_step_1(self) -> None:
        """
        Execute Pass 2 Step 1 for every day of the month.

        This only performs validation/removal of existing assignments.
        It does not yet fill A/B/C coverage or assign free members.
        """

        for day in range(
            1,
            self.context.days_in_month + 1,
        ):
            self._validate_day_requirements(day)