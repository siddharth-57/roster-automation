from app.scheduler.context import RosterContext
from app.scheduler.validator import validate_roster
import random
from app.scheduler.constraints import (
    can_assign_shift,
    get_working_streak_before_day,
)

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
    
    
    def _assign_member_requirements(self):
        """
        Load every validated member requirement into the roster.
    
        This phase intentionally does NOT enforce roster constraints.
    
        The incoming requirements have already been validated by the
        frontend, so a member cannot have two different requested
        shifts on the same day.
    
        The roster is therefore allowed to be temporarily invalid
        after this step.
        """
    
        for employee_id in self.context.members:
        
            member_requirement = self.context.requirements.get(
                employee_id
            )
    
            if not member_requirement:
                continue
            
            for shift, days in member_requirement.requirements.items():
            
                for day in days:
                
                    self.roster[employee_id][day] = shift
    
    
    











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
    
        1. Load all member requirements first.
        2. Complete and reconcile the roster.
        3. Validate the final roster.
        """
    
        self._initialize_from_previous_month()
    
        self._assign_member_requirements()
    
        self._complete_roster()
    
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
    
# Gets all the requirements of the members
    def _get_requirement_days(
        self,
        employee_id: str,
        shift: str,
    ) -> list[int]:

        member_requirement = self.context.requirements.get(
            employee_id
        )

        if not member_requirement:
            return []

        return member_requirement.requirements.get(
            shift,
            [],
        )
  
    
# Track how many W/H/L assignments exist
    def _get_shift_count(
        self,
        employee_id: str,
        shift: str,
    ) -> int:

        return sum(
            assigned_shift == shift
            for assigned_shift
            in self.roster[employee_id].values()
        )
    

    
# Determine W/H availability
# This ensures that W/H/L still respect things like: one assignment per day, C → W/H/L, previous-month constraints
    def _can_assign_non_working_shift(
        self,
        employee_id: str,
        day: int,
        shift: str,
    ) -> bool:

        return can_assign_shift(
            self.roster,
            employee_id,
            day,
            shift,
            self.context.previous_assignments,
        )
    
# Requested L handling
    def _try_assign_requested_leave(
        self,
        employee_id: str,
        day: int,
    ) -> bool:

        if day not in self._get_requirement_days(
            employee_id,
            "L",
        ):
            return False

        if self._can_assign_non_working_shift(
            employee_id,
            day,
            "L",
        ):
            return self._assign(
                employee_id,
                day,
                "L",
            )

        return False


# Requested W handling
    def _try_assign_requested_w(
        self,
        employee_id: str,
        day: int,
    ) -> bool:

        if day not in self._get_requirement_days(
            employee_id,
            "W",
        ):
            return False

        # Priority 1: W
        if self._can_assign_non_working_shift(
            employee_id,
            day,
            "W",
        ):
            return self._assign(
                employee_id,
                day,
                "W",
            )

        # Priority 2: H
        if (
            self._get_shift_count(
                employee_id,
                "H",
            )
            < self.context.public_holidays
        ):
            if self._can_assign_non_working_shift(
                employee_id,
                day,
                "H",
            ):
                return self._assign(
                    employee_id,
                    day,
                    "H",
                )

        # Priority 3: L
        if self._can_assign_non_working_shift(
            employee_id,
            day,
            "L",
        ):
            return self._assign(
                employee_id,
                day,
                "L",
            )

        return False


# Process explicit L/W requirements
    def _assign_requested_non_working_days(self):
        for day in range(
            1,
            self.context.days_in_month + 1,
        ):

            for employee_id in self.context.members:

                if day in self._get_requirement_days(
                    employee_id,
                    "L",
                ):

                    if self._try_assign_requested_leave(
                        employee_id,
                        day,
                    ):
                        continue

                if day in self._get_requirement_days(
                    employee_id,
                    "W",
                ):

                    self._try_assign_requested_w(
                        employee_id,
                        day,
                    )
    
# This gives us a generic way to calculate remaining W or H after the ones that have been assigned.
    def _get_remaining_shift_quota(
        self,
        employee_id: str,
        shift: str,
        required_count: int,
    ) -> int:

        assigned_count = self._get_shift_count(
            employee_id,
            shift,
        )

        return max(
            required_count - assigned_count,
            0,
        )
    
# Add W remaining quota calculation
    def _get_remaining_w(
        self,
        employee_id: str,
    ) -> int:

        return self._get_remaining_shift_quota(
            employee_id,
            "W",
            self.context.required_w_days,
        )
    
    
# Add H remaining quota calculation
    def _get_remaining_h(
        self,
        employee_id: str,
    ) -> int:

        return self._get_remaining_shift_quota(
            employee_id,
            "H",
            self.context.public_holidays,
        )
    
# Add a daily shift counter. this helps us count the number of members in any shift on any day
    def _get_daily_shift_count(
        self,
        day: int,
        shift: str,
    ) -> int:

        return sum(
            assignments.get(day) == shift
            for assignments in self.roster.values()
        )
    
# Find members who can take a required shift on a given day
    def _get_shift_candidates(
        self,
        day: int,
        shift: str,
    ) -> list[str]:

        candidates = []

        for employee_id in self.context.members:

            if day in self.roster[employee_id]:
                continue

            if not can_assign_shift(
                self.roster,
                employee_id,
                day,
                shift,
                self.context.previous_assignments,
            ):
                continue

            candidates.append(employee_id)

        return candidates
    
# for assigning a shift on any day we need to see if any candidate requested that shift and assign it to that member
    def _get_requested_shift_candidates(
        self,
        candidates: list[str],
        day: int,
        shift: str,
    ) -> list[str]:

        return [
            employee_id
            for employee_id in candidates
            if day in self._get_requirement_days(
                employee_id,
                shift,
            )
        ]
    
    
# Select an A/B candidate. If 2 candidates requirements conflict then we should randomly chose one member for assigning the shift
    def _select_shift_candidate(
        self,
        candidates: list[str],
        day: int,
        shift: str,
    ) -> str | None:

        if not candidates:
            return None

        requested_candidates = (
            self._get_requested_shift_candidates(
                candidates,
                day,
                shift,
            )
        )

        if requested_candidates:
            return random.choice(
                requested_candidates
            )

        return random.choice(candidates)
    
    
# helper to find empty days
    def _get_unassigned_days(
        self,
        employee_id: str,
    ) -> list[int]:

        return [
            day
            for day in range(
                1,
                self.context.days_in_month + 1,
            )
            if day not in self.roster[employee_id]
        ]
    
 
# Determine whether a day is a good W/H candidate
    def _can_assign_w_or_h(
        self,
        employee_id: str,
        day: int,
        shift: str,
    ) -> bool:

        return can_assign_shift(
            self.roster,
            employee_id,
            day,
            shift,
            self.context.previous_assignments,
        )


# Finds the best non working day rather than just assigning non working day to the first available day
    def _get_best_non_working_day(
        self,
        employee_id: str,
        shift: str,
    ) -> int | None:

        candidates = [
            day
            for day in self._get_unassigned_days(
                employee_id
            )
            if self._can_assign_w_or_h(
                employee_id,
                day,
                shift,
            )
        ]

        if not candidates:
            return None

        return candidates[0]


# assign the remaining W's for a candidate based on best options
    def _assign_remaining_w(
        self,
    ):
        for employee_id in self.context.members:

            remaining_w = self._get_remaining_w(
                employee_id
            )

            for _ in range(remaining_w):

                day = self._get_best_non_working_day(
                    employee_id,
                    "W",
                )

                if day is None:
                    raise ValueError(
                        f"Unable to assign remaining W "
                        f"days to {employee_id}."
                    )

                self._assign(
                    employee_id,
                    day,
                    "W",
                )


# # assign the remaining H's for a candidate based on best options
    def _assign_remaining_h(
        self,
    ):

        for employee_id in self.context.members:

            remaining_h = self._get_remaining_h(
                employee_id
            )

            for _ in range(remaining_h):

                day = self._get_best_non_working_day(
                    employee_id,
                    "H",
                )

                if day is None:
                    raise ValueError(
                        f"Unable to assign remaining H "
                        f"days to {employee_id}."
                    )

                self._assign(
                    employee_id,
                    day,
                    "H",
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
    
    
    
# ensures daily A/B/C shifts are assigned
    def _ensure_daily_abc_coverage(self):

        for day in range(
            1,
            self.context.days_in_month + 1,
        ):

            # C has already been assigned and is fixed.
            if self._get_daily_shift_count(day, "C") < 1:

                candidates = self._get_shift_candidates(
                    day,
                    "C",
                )

                employee_id = self._select_shift_candidate(
                    candidates,
                    day,
                    "C",
                )

                if employee_id is None:
                    raise ValueError(
                        f"Unable to satisfy C coverage "
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

            # A coverage
            if self._get_daily_shift_count(day, "A") < 1:

                candidates = self._get_shift_candidates(
                    day,
                    "A",
                )

                employee_id = self._select_shift_candidate(
                    candidates,
                    day,
                    "A",
                )

                if employee_id is None:
                    raise ValueError(
                        f"Unable to satisfy A coverage "
                        f"on day {day}."
                    )

                if not self._assign(
                    employee_id,
                    day,
                    "A",
                ):
                    raise ValueError(
                        f"Unable to assign A shift "
                        f"on day {day}."
                    )

            # B coverage
            if self._get_daily_shift_count(day, "B") < 1:

                candidates = self._get_shift_candidates(
                    day,
                    "B",
                )

                employee_id = self._select_shift_candidate(
                    candidates,
                    day,
                    "B",
                )

                if employee_id is None:
                    raise ValueError(
                        f"Unable to satisfy B coverage "
                        f"on day {day}."
                    )

                if not self._assign(
                    employee_id,
                    day,
                    "B",
                ):
                    raise ValueError(
                        f"Unable to assign B shift "
                        f"on day {day}."
                    )

    def _fill_remaining_days(self):
        """
        Fill unassigned days with A/B/G according
        to requirements and staffing needs.
        """

        pass