from app.scheduler.constraints import (
    can_assign_shift,
)
from app.scheduler.context import RosterContext
from app.scheduler.validator import validate_roster
import random

class RosterScheduler:

    def __init__(self, context: RosterContext):
        self.context = context

        self.roster: dict[
            str,
            dict[int, str],
        ] = {
            employee_id: {}
            for employee_id in context.members
        }

        self.unfulfilled_requirements: list[dict] = []

# Track unfulfilled requirements
    def _record_unfulfilled_requirement(
        self,
        employee_id: str,
        day: int,
        requested_shift: str,
        reason: str,
    ):

        self.unfulfilled_requirements.append(
            {
                "employee_id": employee_id,
                "day": day,
                "requested_shift": requested_shift,
                "reason": reason,
            }
        )
    
# Assignment Helper Function
# every assignment goes through the constraint layer
# The below method will only succeed if all the applicable assignment constraints allow it.
    def _assign(
        self,
        employee_id: str,
        day: int,
        shift: str,
    ) -> bool:

        if not can_assign_shift(
            self.roster,
            employee_id,
            day,
            shift,
            self.context.previous_assignments,
        ):
            return False

        self.roster[employee_id][day] = shift

        return True


    def generate(self) -> dict:
        """
        Generate a complete monthly roster.
        """

        self._initialize_from_previous_month()

        self._assign_required_non_working_days()

        self._assign_c_shifts()

        self._ensure_daily_abc_coverage()

        self._fill_remaining_days()

        errors = validate_roster(
            roster=self.roster,
            year=self.context.year,
            month=self.context.month,
            public_holidays=self.context.public_holidays,
        )

        if errors:
            raise ValueError(
                "Generated roster failed validation: "
                + "; ".join(errors)
            )

        return self.roster

    def _initialize_from_previous_month(self):
        """
        Prepare scheduler state using the previous
        month's last five days.
        """

        # Previous month assignments are not copied
        # into the new roster. They are kept separately
        # and used when evaluating the first days.
        pass

    def _assign_required_non_working_days(self):
        """
        Assign W/H/L where required while respecting
        staffing constraints.
        """

        pass

# Gets C requirements of the members if any
    def _get_c_requirement_days(
        self,
        employee_id: str,
    ) -> list[int]:

        member_requirement = self.context.requirements.get(
            employee_id
        )

        if not member_requirement:
            return []

        return member_requirement.requirements.get(
            "C",
            [],
        )

# Determine whether a C request is possible
    def _is_c_requested(
        self,
        employee_id: str,
        day: int,
    ) -> bool:

        return day in self._get_c_requirement_days(
            employee_id
        )
    

# gets count of total C shifts for an employee
    def _get_c_count(
        self,
        employee_id: str,
    ) -> int:
        return sum(
            shift == "C"
            for shift in self.roster[
                employee_id
            ].values()
        )
    
        
# Finds the best C candidate. This gives us only candidates who don't violate the basic C constraints.
# someone who already has 5 C shifts is never considered for another C.
    def _get_c_candidates(
        self,
        day: int,
    ) -> list[str]:

        candidates = []

        for employee_id in self.context.members:

            if self._get_c_count(employee_id) >= 5:
                continue

            if not can_assign_shift(
                self.roster,
                employee_id,
                day,
                "C",
                self.context.previous_assignments,
            ):
                continue

            candidates.append(employee_id)

        return candidates
    
# Prioritizes explicit C requirements.
# First priority someone who requested C that day and hasnt maxed out the C limit yet and 2nd priority to someone with fewer C shifts so far
    def _get_requested_c_candidates(
        self,
        candidates: list[str],
        day: int,
    ) -> list[str]:

        return [
            employee_id
            for employee_id in candidates
            if self._is_c_requested(
                employee_id,
                day,
            )
        ]
    
# Members who have not requested C shifts
    def _get_flexible_c_candidates(
        self,
        candidates: list[str],
        day: int,
    ) -> list[str]:

        return [
            employee_id
            for employee_id in candidates
            if not self._is_c_requested(
                employee_id,
                day,
            )
        ]
    
    
# Add a safety check for minimum C 
    def _validate_minimum_c_distribution(self):
        for employee_id in self.context.members:

            c_count = self._get_c_count(
                employee_id
            )

            if c_count < 3:
                raise ValueError(
                    f"{employee_id} received only "
                    f"{c_count} C shifts. "
                    f"Minimum required is 3."
                )
    
    
# Randomly resolve conflicting C requests
    def _select_c_candidate(
        self,
        candidates: list[str],
        day: int,
    ) -> str | None:

        if not candidates:
            return None

        requested_candidates = (
            self._get_requested_c_candidates(
                candidates,
                day,
            )
        )

        if requested_candidates:
            return random.choice(
                requested_candidates
            )

        flexible_candidates = (
            self._get_flexible_c_candidates(
                candidates,
                day,
            )
        )

        if not flexible_candidates:
            return None

        flexible_candidates.sort(
            key=self._get_c_count
        )

        return flexible_candidates[0]
    
    
# Assign C day-by-day
    def _assign_c_shifts(self):
        for day in range(
            1,
            self.context.days_in_month + 1,
        ):

            candidates = self._get_c_candidates(
                day
            )

            employee_id = self._select_c_candidate(
                candidates,
                day,
            )

            if employee_id is None:
                raise ValueError(
                    f"Unable to assign C shift "
                    f"on day {day}."
                )

            if not self._assign(
                employee_id,
                day,
                "C",
            ):
                raise ValueError(
                    f"Unable to assign C shift "
                    f"on day {day}."
                )

        self._validate_minimum_c_distribution()
    

    def _ensure_daily_abc_coverage(self):
        """
        Ensure every day has at least:
        A >= 1
        B >= 1
        C >= 1
        """

        pass

    def _fill_remaining_days(self):
        """
        Fill unassigned days with A/B/G according
        to requirements and staffing needs.
        """

        pass