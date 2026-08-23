from app.scheduler.context import RosterContext


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



#   ----- PASS 1 -----

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




#   ----- PASS 2 -----
