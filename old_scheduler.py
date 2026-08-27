import copy
import random

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
        
        # Stores the active requirements only after all the deletions and everything
        self.active_requirements = copy.deepcopy(
            self.context.requirements
        )
        
        # This stores the warnings for the dates on which the basic A/B/C coverage couldn't be satisfied
        self.warnings: list[str] = []


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


    def _remove_active_requirement(
        self,
        employee_id: str,
        day: int,
        shift: str,
    ) -> None:
        """
        Remove a requirement from the active requirement set.

        The original frontend requirement is not modified.
        """

        member_requirements = self.active_requirements.get(
            employee_id
        )

        if not member_requirements:
            return

        days = member_requirements.requirements.get(shift)

        if not days:
            return

        if day in days:
            days.remove(day)


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
        
        self._remove_active_requirement(
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

# This function might not be used as it goes through all the days of the month before implementing steps 2 or 3 from 2nd Pass
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
            
            


    # ------------------------------------------------------------------
    #              PASS 2 - STEP 2(a) Helper Functions
    # ------------------------------------------------------------------
    
    def _get_daily_abc_coverage(
        self,
        day: int,
    ) -> set[str]:
        """
        Return the A/B/C shifts already covered on a given day.

        Only shifts currently present in the roster are considered.
        """

        covered_shifts = set()

        for employee_id in self.context.members:
            shift = self.roster[employee_id].get(day)

            if shift in {"A", "B", "C"}:
                covered_shifts.add(shift)

        return covered_shifts


    def _get_missing_abc_shifts(
        self,
        day: int,
    ) -> set[str]:
        """
        Return the A/B/C shifts that are not yet covered on a given day.
        """

        required_shifts = {"A", "B", "C"}

        return required_shifts - self._get_daily_abc_coverage(day)
    
    
    # ------------------------------------------------------------------
    #              PASS 2 - STEP 2(b) Helper Functions
    # ------------------------------------------------------------------
    
    def _get_free_members(
        self,
        day: int,
    ) -> list[str]:
        """
        Return members who currently have no assignment
        on the given day.
        """

        return [
            employee_id
            for employee_id in self.context.members
            if day not in self.roster[employee_id]
        ]
    
    def _get_next_day_requirement(
        self,
        employee_id: str,
        day: int,
    ) -> str | None:
        """
        Return the member's requirement for the next day, if one exists.

        This reads the original frontend requirement rather than the
        current roster because Pass 2 may modify the roster.
        """

        next_day = day + 1

        if next_day > self.context.days_in_month:
            return None

        member_requirement = self.context.requirements.get(
            employee_id
        )

        if not member_requirement:
            return None

        for shift, days in member_requirement.requirements.items():
            if next_day in days:
                return shift

        return None

    def _get_previous_six_days(
        self,
        employee_id: str,
        day: int,
    ) -> dict[int, str]:
        """
        Return the member's assignments from the previous
        6 calendar days.

        Only the current month's roster is returned here.
        Previous-month history is handled by the constraint layer.
        """

        history = {}

        for previous_day in range(
            day - 1,
            max(day - 7, 0),
            -1,
        ):
            if previous_day in self.roster[employee_id]:
                history[previous_day] = self.roster[
                    employee_id
                ][previous_day]

        return history

    def _can_assign_shift_with_next_day_requirement(
        self,
        employee_id: str,
        day: int,
        shift: str,
    ) -> bool:
        """
        Return True only if the member can receive the shift today
        while preserving their next-day requirement.

        No roster changes are made.

        This is used by Pass 2 Step 2(b), where requirements
        must NOT be relaxed.
        """

        # The hard roster constraints must allow today's shift.
        if not can_assign_shift(
            self.roster,
            employee_id,
            day,
            shift,
            self.context.previous_assignments,
        ):
            return False

        next_day_requirement = self._get_next_day_requirement(
            employee_id,
            day,
        )

        # No requirement tomorrow means there is nothing to preserve.
        if next_day_requirement is None:
            return True

        # If today is C, tomorrow cannot be a working shift
        # that follows C.
        if shift == "C":
            return next_day_requirement in {
                "C",
                "W",
                "H",
                "L",
            }

        return True

    def _get_coverage_candidates(
        self,
        day: int,
    ) -> dict[str, list[str]]:
        """
        Build a mapping of each uncovered A/B/C shift to the
        free members who can perform that shift.

        Pass 2 Step 2(b):

        - Only currently free members are considered.
        - Previous 6 days are considered through the hard
          constraint layer.
        - Next-day requirements are preserved.
        - No requirements are relaxed.
        - The roster is not modified.
        """

        missing_shifts = self._get_missing_abc_shifts(day)

        candidates = {
            shift: []
            for shift in missing_shifts
        }

        for employee_id in self._get_free_members(day):

            for shift in missing_shifts:

                if self._can_assign_shift_with_next_day_requirement(
                    employee_id,
                    day,
                    shift,
                ):
                    candidates[shift].append(employee_id)

        return candidates
    
    def _get_previous_day_same_shift_candidates(
        self,
        candidates: list[str],
        day: int,
        shift: str,
    ) -> list[str]:
        """
        Return candidates who worked the same shift on the
        previous day.

        Does not modify the roster.
        """

        if day <= 1:
            return []

        previous_day = day - 1

        return [
            employee_id
            for employee_id in candidates
            if self.roster[employee_id].get(previous_day) == shift
        ]
    
    def _preserves_other_shift_coverage(
        self,
        day: int,
        candidate: str,
        shift: str,
    ) -> bool:
        """
        Return True if assigning the candidate to the requested shift
        would leave at least one candidate for every other currently
        uncovered shift.

        The current roster is not permanently modified.
        """

        missing_shifts = self._get_missing_abc_shifts(day)

        remaining_shifts = missing_shifts - {shift}

        if not remaining_shifts:
            return True

        # Temporarily assign the candidate.
        self.roster[candidate][day] = shift

        try:
            for other_shift in remaining_shifts:

                other_candidates = self._get_coverage_candidates(
                    day
                ).get(other_shift, [])

                if not other_candidates:
                    return False

            return True

        finally:
            del self.roster[candidate][day]
    
    def _select_coverage_candidate(
        self,
        day: int,
        shift: str,
        candidates: list[str],
    ) -> str | None:
        """
        Select the best candidate for a coverage shift.

        Priority:
        1. Member who worked the same shift yesterday.
        2. Member whose assignment preserves coverage of all
           other currently uncovered shifts.
        3. If multiple candidates still remain, select the first
           candidate.
        """

        if not candidates:
            return None

        # Priority 1: same shift as previous day.
        previous_day_candidates = (
            self._get_previous_day_same_shift_candidates(
                candidates,
                day,
                shift,
            )
        )

        if previous_day_candidates:
            candidates = previous_day_candidates

        # Priority 2: preserve coverage for other missing shifts.
        preserving_candidates = [
            employee_id
            for employee_id in candidates
            if self._preserves_other_shift_coverage(
                day,
                employee_id,
                shift,
            )
        ]

        if preserving_candidates:
            candidates = preserving_candidates

        return candidates[0]

    # ------------------------------------------------------------------
    #              PASS 2 - STEP 2(b) Main Function
    # ------------------------------------------------------------------

    def _fill_abc_coverage_from_free_members(
        self,
        day: int,
    ) -> bool:
        """
        Pass 2 Step 2(b).

        Attempt to complete the missing A/B/C coverage for the
        given day using only currently free members.

        Candidate eligibility considers:
        - hard roster constraints
        - previous 6 days of roster history
        - next-day requirement

        No requirements are relaxed in this step.

        Returns:
            True  -> A/B/C coverage is complete.
            False -> Some A/B/C coverage is still missing and
                     Step 2(c) should be attempted.
        """

        while True:
            missing_shifts = self._get_missing_abc_shifts(day)

            # Step 2(b) succeeded.
            if not missing_shifts:
                return True

            # Always process C before B before A.
            shift = next(
                (
                    candidate_shift
                    for candidate_shift in ("C", "B", "A")
                    if candidate_shift in missing_shifts
                ),
                None,
            )

            if shift is None:
                return True

            candidates = self._get_coverage_candidates(day).get(
                shift,
                []
            )

            # No free member can perform this shift.
            # Stop Step 2(b) and let Step 2(c) expand the
            # candidate pool.
            if not candidates:
                return False

            selected_member = self._select_coverage_candidate(
                day=day,
                shift=shift,
                candidates=candidates,
            )

            if selected_member is None:
                return False

            # Assign the selected shift.
            self.roster[selected_member][day] = shift

            # Keep C tracking accurate.
            if shift == "C":
                self.c_shift_counts[selected_member] += 1



    # ------------------------------------------------------------------
    #              PASS 2 - STEP 2(c) Helper Functions
    # ------------------------------------------------------------------

    def _get_members_with_active_requirements(
        self,
        day: int,
    ) -> list[str]:
        """
        Return members who currently have an active requirement
        for the given day.

        Requirements removed during Pass 2 are no longer considered
        active.
        """

        members = []

        for employee_id in self.context.members:
            member_requirements = self.active_requirements.get(
                employee_id
            )

            if not member_requirements:
                continue

            for days in member_requirements.requirements.values():
                if day in days:
                    members.append(employee_id)
                    break

        return members


    def _can_replace_requirement_for_coverage(
        self,
        employee_id: str,
        day: int,
        new_shift: str,
    ) -> bool:
        """
        Check whether the member's active requirement can be
        temporarily replaced by new_shift.

        The replacement is valid only if:

        1. The new shift satisfies all hard constraints.
        2. The next-day requirement remains valid.
        3. The member's existing A/B/C shift does not become
           uncovered.

        No permanent roster or requirement changes are made.
        """

        current_shift = self.roster[employee_id].get(day)

        if current_shift is None:
            return False

        active_requirement = self._get_active_requirement_for_day(
            employee_id,
            day,
        )

        if active_requirement != current_shift:
            return False

        # Temporarily remove the existing requirement.
        self.roster[employee_id].pop(day)

        try:
            # Check whether the proposed working shift itself is valid.
            if not self._can_assign_shift_with_next_day_requirement(
                employee_id,
                day,
                new_shift,
            ):
                return False

            # Temporarily assign the replacement.
            self.roster[employee_id][day] = new_shift
            
            coverage = self._get_daily_abc_coverage(day)

            # If the old assignment was an A/B/C shift,
            # its coverage must remain after the replacement.
            if current_shift in {"A", "B", "C"}:
                return current_shift in coverage

            # W/H/L do not provide A/B/C coverage,
            # so there is nothing to preserve.
            return True

        finally:
            # Always restore the original requirement.
            self.roster[employee_id][day] = current_shift


    def _get_active_requirement_for_day(
        self,
        employee_id: str,
        day: int,
    ) -> str | None:
        """
        Return the active requirement for a member on a given day.
        """

        member_requirements = self.active_requirements.get(
            employee_id
        )

        if not member_requirements:
            return None

        for shift, days in member_requirements.requirements.items():
            if day in days:
                return shift

        return None


    def _get_requirement_coverage_candidates(
        self,
        day: int,
    ) -> dict[str, list[str]]:
        """
        Build a mapping of each uncovered A/B/C shift to members
        whose active requirement can safely be replaced by that shift.

        No permanent changes are made.
        """

        missing_shifts = self._get_missing_abc_shifts(day)

        candidates = {
            shift: []
            for shift in missing_shifts
        }

        for employee_id in self._get_members_with_active_requirements(
            day
        ):
            for shift in missing_shifts:

                if self._can_replace_requirement_for_coverage(
                    employee_id,
                    day,
                    shift,
                ):
                    candidates[shift].append(employee_id)

        return candidates


    def _select_requirement_coverage_candidate(
        self,
        day: int,
        shift: str,
        candidates: list[str],
        candidate_map: dict[str, list[str]],
    ) -> str | None:
        """
        Select the best candidate for Pass 2 Step 2(c).
    
        Priority:
        1. Prefer a member who worked the same shift on the previous day.
        2. If there is no previous-day match, prefer a member whose
           selection does not remove the only candidate for another
           currently missing shift.
        3. If multiple candidates still remain, select the first one.
    
        This method does not permanently modify the roster.
        """
    
        if not candidates:
            return None
    
        candidates = list(candidates)
    
        # ------------------------------------------------------
        # Priority 1:
        # Prefer a member who worked the same shift yesterday.
        # ------------------------------------------------------
    
        previous_day_candidates = (
            self._get_previous_day_same_shift_candidates(
                candidates,
                day,
                shift,
            )
        )
    
        if previous_day_candidates:
            candidates = previous_day_candidates
    
        # ------------------------------------------------------
        # Priority 2:
        # Preserve the possibility of covering other shifts.
        # ------------------------------------------------------
    
        preserving_candidates = [
            employee_id
            for employee_id in candidates
            if self._preserves_requirement_coverage(
                employee_id,
                shift,
                candidate_map,
            )
        ]
    
        if preserving_candidates:
            candidates = preserving_candidates
    
        return candidates[0]
    
    def _preserves_requirement_coverage(
        self,
        candidate: str,
        shift: str,
        candidate_map: dict[str, list[str]],
    ) -> bool:
        """
        Return True if selecting this candidate for the current shift
        does not eliminate the only candidate for another currently
        missing shift.

        This method does not modify the roster.
        """

        for other_shift, other_candidates in candidate_map.items():

            # Ignore the shift we are currently trying to cover.
            if other_shift == shift:
                continue

            # No candidates already exist for this shift.
            if not other_candidates:
                continue

            # If this candidate is the only option for another shift,
            # selecting them now would remove that option.
            if (
                candidate in other_candidates
                and len(other_candidates) == 1
            ):
                return False

        return True

    def _commit_requirement_coverage_replacement(
        self,
        employee_id: str,
        day: int,
        new_shift: str,
    ) -> bool:
        """
        Permanently replace an active requirement assignment
        with a working A/B/C coverage shift.

        Validation is delegated to
        _can_replace_requirement_for_coverage().

        Returns True if the replacement was committed.
        Returns False if the replacement cannot be committed.
        """

        current_shift = self.roster[employee_id].get(day)

        if current_shift is None:
            return False

        # The member must still have an active requirement
        # for this day.
        active_requirement = self._get_active_requirement_for_day(
            employee_id,
            day,
        )

        if active_requirement != current_shift:
            return False

        # Step 2(c) only replaces requirements with A/B/C.
        if new_shift not in {"A", "B", "C"}:
            return False

        # Re-check before making any permanent change.
        if not self._can_replace_requirement_for_coverage(
            employee_id,
            day,
            new_shift,
        ):
            return False

        # Remove the old requirement assignment.
        #
        # This also updates:
        # - remaining_w
        # - remaining_h
        # - c_shift_counts
        self._remove_assignment(
            employee_id,
            day,
        )

        # Assign the new coverage shift.
        self.roster[employee_id][day] = new_shift

        # Update C-shift tracking for the new assignment.
        if new_shift == "C":
            self.c_shift_counts[employee_id] += 1

        # The old requirement has now been permanently relaxed.
        self._record_relaxed_requirement(
            employee_id,
            day,
            current_shift,
        )

        self._remove_active_requirement(
            employee_id,
            day,
            current_shift,
        )

        return True


    # ------------------------------------------------------------------
    #              PASS 2 - STEP 2(c) Main Function
    # ------------------------------------------------------------------


    def _run_pass_2_step_2c(
        self,
        day: int,
    ) -> bool:
        """
        Pass 2 Step 2(c).

        Attempt to complete A/B/C coverage for the given day by
        temporarily relaxing active member requirements.

        The process continues until:

        1. A/B/C coverage is complete, or
        2. No valid requirement replacement can make further progress.

        Returns:
            True  -> A/B/C coverage is complete.
            False -> A/B/C coverage is still incomplete.
        """

        while True:
            # ------------------------------------------------------
            # Step 1:
            # Recalculate the current missing A/B/C shifts.
            # ------------------------------------------------------

            missing_shifts = self._get_missing_abc_shifts(day)

            # Coverage is complete.
            if not missing_shifts:
                return True

            # ------------------------------------------------------
            # Step 2:
            # Build the candidate map from the CURRENT roster
            # and CURRENT active requirements.
            #
            # This must be rebuilt after every successful
            # replacement because the roster and active
            # requirements change.
            # ------------------------------------------------------

            candidate_map = (
                self._get_requirement_coverage_candidates(day)
            )

            # ------------------------------------------------------
            # Step 3:
            # Process missing shifts in deterministic order.
            #
            # We use C -> B -> A, matching Step 2(b).
            # ------------------------------------------------------

            shift = next(
                (
                    candidate_shift
                    for candidate_shift in ("C", "B", "A")
                    if candidate_shift in missing_shifts
                ),
                None,
            )

            if shift is None:
                return True

            candidates = candidate_map.get(shift, [])

            # No active-requirement member can cover this shift.
            #
            # Step 2(c) cannot make further progress.
            if not candidates:
                return False

            # ------------------------------------------------------
            # Step 4:
            # Select the best requirement candidate.
            # ------------------------------------------------------

            selected_member = (
                self._select_requirement_coverage_candidate(
                    day=day,
                    shift=shift,
                    candidates=candidates,
                    candidate_map=candidate_map,
                )
            )

            if selected_member is None:
                return False

            # ------------------------------------------------------
            # Step 5:
            # Permanently commit the replacement.
            #
            # The commit method performs its own final validation.
            # ------------------------------------------------------

            committed = (
                self._commit_requirement_coverage_replacement(
                    employee_id=selected_member,
                    day=day,
                    new_shift=shift,
                )
            )

            if not committed:
                # The candidate was valid when the candidate map
                # was built, but the final validation rejected it.
                #
                # Rebuild the candidate map once more and try again.
                #
                # If nothing remains valid, the next iteration
                # will return False.
                return False

            # ------------------------------------------------------
            # Step 6:
            # A replacement was successfully committed.
            #
            # DO NOT reuse candidate_map.
            #
            # The next loop iteration will recalculate:
            # - current A/B/C coverage
            # - missing shifts
            # - active requirements
            # - valid candidates
            #
            # This is essential because the committed replacement
            # changed the scheduler state.
            # ------------------------------------------------------



    # ------------------------------------------------------------------
    #              PASS 2 - STEP 2(d) Helper Functions
    # ------------------------------------------------------------------

    def _get_step2d_coverage_candidates(
        self,
        day: int,
    ) -> dict[str, list[str]]:
        """
        Build a mapping of each missing A/B/C shift to the
        free members who can perform that shift.

        Pass 2 Step 2(d):

        - Only genuinely free members are considered.
        - Only currently missing A/B/C shifts are considered.
        - Existing hard roster constraints are enforced.
        - The previous 6 days are therefore respected through
          can_assign_shift().
        - The next-day requirement is deliberately ignored.
        - No requirements are relaxed.
        - The roster is not modified.
        """

        missing_shifts = self._get_missing_abc_shifts(day)

        candidates = {
            shift: []
            for shift in missing_shifts
        }

        if not candidates:
            return candidates

        for employee_id in self._get_free_members(day):

            for shift in missing_shifts:

                if can_assign_shift(
                    self.roster,
                    employee_id,
                    day,
                    shift,
                    self.context.previous_assignments,
                ):
                    candidates[shift].append(employee_id)

        return candidates
    
    
    def _select_step2d_coverage_candidate(
        self,
        day: int,
        shift: str,
        candidates: list[str],
        candidate_map: dict[str, list[str]],
    ) -> str | None:
        """
        Select the best free member for a Step 2(d) coverage shift.

        Priority:
        1. Member who worked the same shift on the previous day.
        2. Member whose selection preserves another missing shift.
        3. Deterministic employee ID ordering.

        The supplied candidate_map is the Step 2(d) candidate map.
        No roster state is modified.
        """

        if not candidates:
            return None

        # ------------------------------------------------------
        # Priority 1:
        # Prefer a member who worked the same shift yesterday.
        # ------------------------------------------------------

        previous_day_candidates = (
            self._get_previous_day_same_shift_candidates(
                candidates,
                day,
                shift,
            )
        )

        if previous_day_candidates:
            return sorted(previous_day_candidates)[0]

        # ------------------------------------------------------
        # Priority 2:
        # Preserve candidates needed by another missing shift.
        #
        # A candidate is "needed" if they are the only candidate
        # for another missing shift.
        # ------------------------------------------------------

        preservation_scores = {}

        for employee_id in candidates:
            score = 0

            for other_shift, other_candidates in candidate_map.items():

                if other_shift == shift:
                    continue

                if (
                    employee_id in other_candidates
                    and len(other_candidates) == 1
                ):
                    score += 1

            preservation_scores[employee_id] = score

        # Lower score is better:
        # 0 = not needed by another shift
        # 1+ = removing this member would eliminate another
        #      shift's only candidate.

        best_score = min(
            preservation_scores.values()
        )

        best_candidates = [
            employee_id
            for employee_id, score
            in preservation_scores.items()
            if score == best_score
        ]

        # ------------------------------------------------------
        # Priority 3:
        # Deterministic tie-break.
        # ------------------------------------------------------

        return sorted(best_candidates)[0]

    def _commit_step2d_coverage_assignment(
        self,
        employee_id: str,
        day: int,
        shift: str,
    ) -> bool:
        """
        Permanently assign an A/B/C coverage shift to a free member
        during Pass 2 Step 2(d).

        The member must:
        - have no assignment for the day,
        - receive only A/B/C,
        - satisfy the existing hard roster constraints.

        Step 2(d) deliberately does not consider the member's
        next-day requirement.

        No requirement is relaxed or modified.
        """

        # ------------------------------------------------------
        # Step 1:
        # The member must actually be free on this day.
        # ------------------------------------------------------

        if day in self.roster[employee_id]:
            return False

        # ------------------------------------------------------
        # Step 2:
        # Step 2(d) only assigns A/B/C.
        # ------------------------------------------------------

        if shift not in {"A", "B", "C"}:
            return False

        # ------------------------------------------------------
        # Step 3:
        # Re-run the hard-rule validation immediately before
        # making the permanent assignment.
        #
        # IMPORTANT:
        # We intentionally call can_assign_shift() directly.
        #
        # This checks the roster hard rules and previous history,
        # but does NOT check the next-day requirement.
        # ------------------------------------------------------

        if not can_assign_shift(
            self.roster,
            employee_id,
            day,
            shift,
            self.context.previous_assignments,
        ):
            return False

        # ------------------------------------------------------
        # Step 4:
        # Permanently assign the shift.
        # ------------------------------------------------------

        self.roster[employee_id][day] = shift

        # ------------------------------------------------------
        # Step 5:
        # Keep C-shift tracking accurate.
        # ------------------------------------------------------

        if shift == "C":
            self.c_shift_counts[employee_id] += 1

        # ------------------------------------------------------
        # IMPORTANT:
        #
        # Do NOT:
        # - modify active_requirements
        # - modify context.requirements
        # - modify relaxed_requirements
        # - modify W/H quotas
        #
        # The member was genuinely free, so there is no
        # requirement being replaced or relaxed.
        # ------------------------------------------------------

        return True


    
        # ------------------------------------------------------
        # Step 2(d): Main Function
        # ------------------------------------------------------

    def _run_pass2_step2d(self, day: int) -> bool:
        """
        Pass 2 - Step 2(d).

        Fill remaining A/B/C coverage using genuinely free
        members.

        Priority:
            C > B > A

        The candidate map is rebuilt after every successful
        assignment because the roster state changes.

        The next-day requirement is intentionally ignored.

        Returns:
            True  -> A/B/C coverage is complete.
            False -> coverage remains incomplete because no
                     valid candidate remains for any missing shift.

        A False result does NOT block Step 3. The caller is
        responsible for continuing to Step 3.
        """

        while True:

            # --------------------------------------------------
            # 1. Determine the shifts that are currently missing.
            # --------------------------------------------------

            missing_shifts = self._get_missing_abc_shifts(day)

            if not missing_shifts:
                return True

            # --------------------------------------------------
            # 2. Build a fresh candidate map.
            #
            # This must happen every iteration because the
            # roster changes after every successful assignment.
            # --------------------------------------------------

            candidate_map = (
                self._get_step2d_coverage_candidates(day)
            )

            # --------------------------------------------------
            # 3. Determine whether ANY remaining shift has at
            #    least one candidate.
            #
            # It is not enough for one particular shift to have
            # no candidates. Another missing shift may still be
            # assignable.
            # --------------------------------------------------

            has_any_candidate = any(
                candidate_map.get(shift)
                for shift in missing_shifts
            )

            if not has_any_candidate:
                break

            # --------------------------------------------------
            # 4. Process shifts according to:
            #
            # C > B > A
            # --------------------------------------------------

            committed = False

            for shift in ("C", "B", "A"):

                if shift not in missing_shifts:
                    continue

                candidates = candidate_map.get(
                    shift,
                    [],
                )

                if not candidates:
                    continue

                # ----------------------------------------------
                # 5. Select the best candidate.
                #
                # Selection priority:
                #   - same shift yesterday
                #   - preserve another shift's only candidate
                #   - deterministic employee ID
                # ----------------------------------------------

                employee_id = (
                    self._select_step2d_coverage_candidate(
                        day=day,
                        shift=shift,
                        candidates=candidates,
                        candidate_map=candidate_map,
                    )
                )

                if employee_id is None:
                    continue

                # ----------------------------------------------
                # 6. Commit the assignment.
                # ----------------------------------------------

                if self._commit_step2d_coverage_assignment(
                    employee_id,
                    day,
                    shift,
                ):
                    committed = True
                    break

            # --------------------------------------------------
            # 7. If an assignment succeeded, restart the loop.
            #
            # This rebuilds:
            #   - missing shifts
            #   - free members
            #   - candidate map
            #   - candidate selection state
            # --------------------------------------------------

            if committed:
                continue

            # --------------------------------------------------
            # 8. We had candidates in the map, but none could be
            #    committed.
            #
            # Rebuild the candidate map on the next iteration.
            #
            # If no candidates remain, the loop will terminate.
            # --------------------------------------------------

            continue

        # ------------------------------------------------------
        # 9. No candidate remains for ANY remaining missing shift.
        # ------------------------------------------------------

        remaining = self._get_missing_abc_shifts(day)

        if not remaining:
            return True

        # ------------------------------------------------------
        # 10. Coverage is incomplete.
        #
        # Record the frontend-visible warning.
        # ------------------------------------------------------

        warning = (
            f"Pending to allocate {len(remaining)} shifts "
            f"on {day} due to conflicting requirements"
        )

        self.warnings.append(warning)

        # ------------------------------------------------------
        # 11. Return False to indicate incomplete coverage.
        #
        # This does NOT prevent Step 3 from running.
        # ------------------------------------------------------

        return False
    
    
    # ------------------------------------------------------
    # Step 3: Helper Functions
    # ------------------------------------------------------

    def _get_step3_working_shift_candidates(
        self,
        employee_id: str,
        day: int,
    ) -> list[str]:
        """
        Return valid working shifts (A/B) for Step 3.

        The check considers:
        - existing roster assignments
        - hard constraints
        - previous working history
        - next-day requirement

        The next-day requirement is intentionally considered here,
        unlike Step 2(d).
        """

        candidates = []

        for shift in ("A", "B"):
            if self._can_assign_shift_with_next_day_requirement(
                employee_id,
                day,
                shift,
            ):
                candidates.append(shift)

        return candidates


    def _select_step3_working_shift(
        self,
        employee_id: str,
        day: int,
        candidates: list[str],
    ) -> str | None:
        """
        Select A/B for a free member.

        Prefer the same working shift as the previous day when
        that shift is still a valid candidate.

        Otherwise use a deterministic A/B ordering.
        """

        if not candidates:
            return None

        previous_day = day - 1

        if previous_day >= 1:
            previous_shift = self.roster[employee_id].get(
                previous_day
            )

            if previous_shift in candidates:
                return previous_shift

        if "A" in candidates:
            return "A"

        if "B" in candidates:
            return "B"

        return None


    def _assign_step3_non_working_shift(
        self,
        employee_id: str,
        day: int,
    ) -> str:
        """
        Assign the highest-priority available non-working shift.

        Priority:
            W > H > L
        """

        if self.remaining_w[employee_id] > 0:
            self.roster[employee_id][day] = "W"
            self.remaining_w[employee_id] -= 1
            return "W"

        if self.remaining_h[employee_id] > 0:
            self.roster[employee_id][day] = "H"
            self.remaining_h[employee_id] -= 1
            return "H"

        self.roster[employee_id][day] = "L"
        return "L"


# ------------------------------------------------------
#           Step 3: Main Function
# ------------------------------------------------------

    def _run_pass2_step3(self, day: int) -> None:
        """
        Pass 2 - Step 3.

        Process every member who is free when Step 3 begins.

        For each free member:
            1. Try A/B while respecting hard rules and the
               next-day requirement.
            2. Prefer the same A/B shift as yesterday when valid.
            3. If neither A nor B is valid, assign W/H/L using
               W > H > L.

        Each member receives exactly one assignment.
        """

        free_members = self._get_free_members(day)

        for employee_id in free_members:

            candidates = self._get_step3_working_shift_candidates(
                employee_id,
                day,
            )

            if candidates:
                shift = self._select_step3_working_shift(
                    employee_id,
                    day,
                    candidates,
                )

                if shift is not None:
                    self.roster[employee_id][day] = shift
                    continue

            self._assign_step3_non_working_shift(
                employee_id,
                day,
            )


# ------------------------------------------------------
#             PASS 2: ORCHESTRATION FUNCTION
# ------------------------------------------------------


    def _run_pass_2(self) -> None:
        """
        Run Pass 2 for every day in the roster.

        Each day is processed completely before moving to the next day.

        Per-day flow:

            Step 1
                ↓
            Step 2(a) - check A/B/C coverage
                ↓
            Step 2(b) - if coverage incomplete
                ↓
            Step 2(c) - if coverage still incomplete
                ↓
            Step 2(d) - if coverage still incomplete
                ↓
            Step 3 - always runs after Step 2

        Step 2(d) may leave A/B/C coverage incomplete. That does not
        prevent Step 3 from running.
        """

        for day in range(1, self.context.days_in_month + 1):

            # ------------------------------------------------------
            # Step 1
            #
            # Validate and handle invalid requirements for this day.
            #
            # IMPORTANT:
            # _run_pass_2_step_1() processes the entire month, so the
            # day-level orchestrator uses _validate_day_requirements()
            # directly.
            # ------------------------------------------------------
            self._validate_day_requirements(day)

            # ------------------------------------------------------
            # Step 2(a)
            #
            # Check whether the minimum daily A/B/C coverage is already
            # satisfied.
            #
            # If there are no missing A/B/C shifts, go directly to
            # Step 3.
            # ------------------------------------------------------
            if not self._get_missing_abc_shifts(day):

                self._run_pass2_step3(day)
                continue

            # ------------------------------------------------------
            # Step 2(b)
            #
            # Try to cover the remaining A/B/C shifts using free
            # members.
            # ------------------------------------------------------
            self._fill_abc_coverage_from_free_members(day)

            # ------------------------------------------------------
            # Check A/B/C coverage again.
            #
            # If Step 2(b) completed coverage, skip 2(c) and 2(d)
            # and move directly to Step 3.
            # ------------------------------------------------------
            if not self._get_missing_abc_shifts(day):

                self._run_pass2_step3(day)
                continue

            # ------------------------------------------------------
            # Step 2(c)
            #
            # Try requirement-coverage replacements.
            # ------------------------------------------------------
            self._run_pass_2_step_2c(day)

            # ------------------------------------------------------
            # Check A/B/C coverage again.
            #
            # If Step 2(c) completed coverage, skip 2(d) and move
            # directly to Step 3.
            # ------------------------------------------------------
            if not self._get_missing_abc_shifts(day):

                self._run_pass2_step3(day)
                continue

            # ------------------------------------------------------
            # Step 2(d)
            #
            # Try the remaining free members.
            #
            # Step 2(d) itself handles its internal candidate loop and
            # generates the pending-allocation warning if it exhausts
            # all candidates while coverage is still incomplete.
            # ------------------------------------------------------
            self._run_pass2_step2d(day)

            # ------------------------------------------------------
            # Step 3
            #
            # Step 3 ALWAYS runs after Step 2(d), regardless of whether
            # Step 2(d) completed A/B/C coverage.
            # ------------------------------------------------------
            self._run_pass2_step3(day)
        
        
        
# ------------------------------------------------------
#                       PASS 3
# ------------------------------------------------------


# ------------------------------------------------------
#                   PASS 3 Helper Functions
# ------------------------------------------------------

    def _get_pass3_eligible_members(
        self,
        day: int,
        non_working_shift: str,
    ) -> list[str]:
        """
        Return members eligible to receive the specified non-working
        shift during Pass 3.

        A member is eligible only when ALL of the following are true:

        1. The member has no active requirement on this day.
        2. The member is currently assigned A or B.
        3. The member still has the requested non-working shift
           available in their monthly quota.

        For W:
            remaining_w[employee_id] > 0

        For H:
            remaining_h[employee_id] > 0
        """

        if non_working_shift not in {"W", "H"}:
            return []

        eligible_members = []

        for employee_id in self.context.members:

            # --------------------------------------------------
            # Condition 1:
            # The member must have NO active requirement today.
            # --------------------------------------------------
            if self._get_active_requirement_for_day(
                employee_id,
                day,
            ) is not None:
                continue

            # --------------------------------------------------
            # Condition 2:
            # The member must currently be working A or B.
            # --------------------------------------------------
            current_shift = self.roster[employee_id].get(day)

            if current_shift not in {"A", "B"}:
                continue

            # --------------------------------------------------
            # Condition 3:
            # The member must still require this non-working shift.
            # --------------------------------------------------
            if non_working_shift == "W":
                if self.remaining_w[employee_id] <= 0:
                    continue

            elif non_working_shift == "H":
                if self.remaining_h[employee_id] <= 0:
                    continue

            eligible_members.append(employee_id)

        return eligible_members


    def _get_pass3_shift_counts(
        self,
        day: int,
    ) -> dict[str, int]:
        """
        Return the current number of A and B assignments for a day.
        """

        counts = {
            "A": 0,
            "B": 0,
        }

        for employee_id in self.context.members:
            shift = self.roster[employee_id].get(day)

            if shift in {"A", "B"}:
                counts[shift] += 1

        return counts


    def _get_pass3_staffing_minimum(
        self,
        day: int,
    ) -> int:
        """
        Return the minimum number of members that must remain
        on each A/B shift after Pass 3 allocation.

        Weekday:
            A >= 2
            B >= 2

        Weekend:
            A >= 1
            B >= 1
        """

        # Day 1 of the roster corresponds to the first day of
        # context.year/context.month.
        import calendar

        weekday = calendar.weekday(
            self.context.year,
            self.context.month,
            day,
        )

        # Monday = 0 ... Friday = 4
        if weekday < 5:
            return 2

        return 1


    def _select_pass3_members(
        self,
        eligible_members: list[str],
        shift: str,
        removable_count: int,
    ) -> list[str]:
        """
        Randomly select eligible members for Pass 3.

        The caller has already calculated how many members may safely
        be removed from the A/B shift.

        Only eligible members supplied by the caller are considered.
        """

        if removable_count <= 0:
            return []

        if not eligible_members:
            return []

        candidates = list(eligible_members)

        random.shuffle(candidates)

        return candidates[:removable_count]


    def _get_pass3_removable_members(
        self,
        day: int,
        non_working_shift: str,
    ) -> list[str]:
        """
        Return the members who may actually be converted from A/B
        to the requested non-working shift on this day.

        Eligibility is determined first.

        Then the staffing minimum is applied:

        Weekday:
            A >= 2
            B >= 2

        Weekend:
            A >= 1
            B >= 1
        """

        eligible_members = self._get_pass3_eligible_members(
            day,
            non_working_shift,
        )

        if not eligible_members:
            return []

        shift_counts = self._get_pass3_shift_counts(day)

        minimum_members = self._get_pass3_staffing_minimum(day)

        removable_members = []

        # ------------------------------------------------------
        # Process A and B independently.
        #
        # We can only remove:
        #
        #     current_count - minimum
        #
        # members from each shift.
        # ------------------------------------------------------
        for working_shift in ("A", "B"):

            candidates_for_shift = [
                employee_id
                for employee_id in eligible_members
                if self.roster[employee_id].get(day) == working_shift
            ]

            removable_count = max(
                0,
                shift_counts[working_shift] - minimum_members,
            )

            selected_members = self._select_pass3_members(
                candidates_for_shift,
                working_shift,
                removable_count,
            )

            removable_members.extend(selected_members)

        return removable_members


    def _assign_pass3_non_working_shift(
        self,
        employee_id: str,
        day: int,
        non_working_shift: str,
    ) -> bool:
        """
        Replace the member's current A/B assignment with W or H.

        The member must already be eligible for this shift.

        Returns:
            True  -> assignment was made.
            False -> assignment was rejected.
        """

        if non_working_shift not in {"W", "H"}:
            return False

        # ------------------------------------------------------
        # The member must currently be assigned A or B.
        # ------------------------------------------------------
        current_shift = self.roster[employee_id].get(day)

        if current_shift not in {"A", "B"}:
            return False

        # ------------------------------------------------------
        # The member must have NO active requirement.
        # ------------------------------------------------------
        if self._get_active_requirement_for_day(
            employee_id,
            day,
        ) is not None:
            return False

        # ------------------------------------------------------
        # The member must still have the requested quota.
        # ------------------------------------------------------
        if non_working_shift == "W":

            if self.remaining_w[employee_id] <= 0:
                return False

        else:

            if self.remaining_h[employee_id] <= 0:
                return False

        # ------------------------------------------------------
        # Replace A/B with W/H.
        # ------------------------------------------------------
        self.roster[employee_id][day] = non_working_shift

        # ------------------------------------------------------
        # Update the appropriate remaining quota.
        # ------------------------------------------------------
        if non_working_shift == "W":
            self.remaining_w[employee_id] -= 1

        else:
            self.remaining_h[employee_id] -= 1

        return True


    def _run_pass3_for_non_working_shift(
        self,
        day: int,
        non_working_shift: str,
    ) -> None:
        """
        Allocate one type of non-working shift for a single day.

        W is processed before H by the caller.

        On both weekdays and weekends, only eligible members are
        considered.

        Weekday:
            keep A >= 2 and B >= 2.

        Weekend:
            keep A >= 1 and B >= 1.

        Among eligible members, selection is random.
        """

        removable_members = self._get_pass3_removable_members(
            day,
            non_working_shift,
        )

        for employee_id in removable_members:

            self._assign_pass3_non_working_shift(
                employee_id,
                day,
                non_working_shift,
            )


# ------------------------------------------------------
#               PASS 3 MAIN FUNCTION
# ------------------------------------------------------

    def _run_pass3(
        self,
        day: int | None = None,
    ) -> None:
        """
        Pass 3.

        Traverse the roster day by day.

        For every day:

            1. Allocate remaining W requirements.
            2. Once W allocation is processed, allocate remaining H
               requirements.

        A member is eligible only if:

            - they have no active requirement on that day;
            - they currently work A or B;
            - they still have the requested W/H quota.

        Weekday staffing:
            A >= 2
            B >= 2

        Weekend staffing:
            A >= 1
            B >= 1

        If multiple eligible members exist, selection is random.

        If day is supplied, only that day is processed. This is useful
        for unit testing.

        If day is None, every day of the roster is processed.
        """

        # ------------------------------------------------------
        # Determine which days to process.
        # ------------------------------------------------------
        if day is not None:
            days = [day]
        else:
            days = range(
                1,
                self.context.days_in_month + 1,
            )

        # ------------------------------------------------------
        # W must always be allocated before H.
        # ------------------------------------------------------
        for current_day in days:

            # --------------------------------------------------
            # First allocate W.
            # --------------------------------------------------
            self._run_pass3_for_non_working_shift(
                current_day,
                "W",
            )

            # --------------------------------------------------
            # Then allocate H.
            # --------------------------------------------------
            self._run_pass3_for_non_working_shift(
                current_day,
                "H",
            )




# ------------------------------------------------------
#                       PASS 4
# ------------------------------------------------------


# ------------------------------------------------------
#               PASS 4 Helper Functions
# ------------------------------------------------------

    def _get_pass4_eligible_days(
        self,
        employee_id: str,
    ) -> list[int]:
        """
        Return days on which the member can receive a remaining
        W/H assignment during Pass 4.

        A day is eligible when:

        1. The member is currently assigned A or B.
        2. There is at least one OTHER member on the same shift.

        Unlike Pass 3, an active requirement on the day does NOT
        make the day ineligible.

        Pass 4 is specifically allowed to relax that requirement.
        """

        eligible_days = []

        for day in range(
            1,
            self.context.days_in_month + 1,
        ):
            current_shift = self.roster[employee_id].get(day)

            # The member must currently be working A or B.
            if current_shift not in {"A", "B"}:
                continue

            # There must be another member on the same shift.
            other_member_exists = any(
                other_employee_id != employee_id
                and self.roster[other_employee_id].get(day)
                == current_shift
                for other_employee_id in self.context.members
            )

            if not other_member_exists:
                continue

            eligible_days.append(day)

        return eligible_days


    def _assign_pass4_non_working_shift(
        self,
        employee_id: str,
        day: int,
        non_working_shift: str,
    ) -> bool:
        """
        Assign W or H to a member during Pass 4.

        The member must:

        - still have the requested W/H requirement;
        - currently be assigned A or B;
        - have another member working the same shift.

        If the member has an active requirement on this day,
        that requirement is relaxed:

            active requirement
                    ↓
              relaxed requirement

        The original frontend requirement is not modified.
        """

        if non_working_shift not in {"W", "H"}:
            return False

        current_shift = self.roster[employee_id].get(day)

        # ------------------------------------------------------
        # The member must currently be on A or B.
        # ------------------------------------------------------
        if current_shift not in {"A", "B"}:
            return False

        # ------------------------------------------------------
        # The member must still have the requested quota.
        # ------------------------------------------------------
        if non_working_shift == "W":
            if self.remaining_w[employee_id] <= 0:
                return False
        else:
            if self.remaining_h[employee_id] <= 0:
                return False

        # ------------------------------------------------------
        # There must be another member on the same shift.
        # ------------------------------------------------------
        other_member_exists = any(
            other_employee_id != employee_id
            and self.roster[other_employee_id].get(day)
            == current_shift
            for other_employee_id in self.context.members
        )

        if not other_member_exists:
            return False

        # ------------------------------------------------------
        # Check whether this day currently has an active
        # requirement for this member.
        # ------------------------------------------------------
        active_requirement = self._get_active_requirement_for_day(
            employee_id,
            day,
        )

        # ------------------------------------------------------
        # If there is an active requirement, Pass 4 explicitly
        # relaxes it because we are replacing that requirement
        # with W/H.
        # ------------------------------------------------------
        if active_requirement is not None:

            self._record_relaxed_requirement(
                employee_id,
                day,
                active_requirement,
            )

            self._remove_active_requirement(
                employee_id,
                day,
                active_requirement,
            )

        # ------------------------------------------------------
        # Replace the A/B assignment with W/H.
        # ------------------------------------------------------
        self.roster[employee_id][day] = non_working_shift

        # ------------------------------------------------------
        # Update the remaining monthly quota.
        # ------------------------------------------------------
        if non_working_shift == "W":
            self.remaining_w[employee_id] -= 1
        else:
            self.remaining_h[employee_id] -= 1

        return True


# ------------------------------------------------------
#               PASS 4 Main Function
# ------------------------------------------------------

    def _run_pass4(
        self,
        day: int | None = None,
    ) -> None:
        """
        Pass 4.

        Allocate remaining W and H requirements that could not be
        satisfied during Pass 3.

        W is always processed before H.

        Unlike Pass 3, the member may have an active requirement
        on the selected day.

        When an active requirement is replaced by W/H:

            active_requirements
                    ↓
            relaxed_requirements

        The replacement is only allowed when another member is
        still working the same A/B shift.

        If day is supplied, only that day is processed.
        If day is None, the complete roster is processed.
        """

        if day is not None:
            days = [day]
        else:
            days = list(
                range(
                    1,
                    self.context.days_in_month + 1,
                )
            )

        # W must always be completed before H.
        for non_working_shift in ("W", "H"):

            for employee_id in self.context.members:

                if non_working_shift == "W":
                    if self.remaining_w[employee_id] <= 0:
                        continue
                else:
                    if self.remaining_h[employee_id] <= 0:
                        continue

                for current_day in days:

                    # Stop once this member's quota is satisfied.
                    if non_working_shift == "W":
                        if self.remaining_w[employee_id] <= 0:
                            break
                    else:
                        if self.remaining_h[employee_id] <= 0:
                            break

                    current_shift = self.roster[
                        employee_id
                    ].get(current_day)

                    # Member must currently be working A/B.
                    if current_shift not in {"A", "B"}:
                        continue

                    # There must be another member on the same shift.
                    other_member_exists = any(
                        other_employee_id != employee_id
                        and self.roster[
                            other_employee_id
                        ].get(current_day) == current_shift
                        for other_employee_id in self.context.members
                    )

                    if not other_member_exists:
                        continue

                    self._assign_pass4_non_working_shift(
                        employee_id=employee_id,
                        day=current_day,
                        non_working_shift=non_working_shift,
                    )

    
# ------------------------------------------------------
#                       PASS 5
# ------------------------------------------------------


# ------------------------------------------------------
#               PASS 5 Helper Functions
# ------------------------------------------------------

    def _get_pass5_shift_counts(
        self,
        day: int,
    ) -> dict[str, int]:
        """
        Return the number of members assigned to A, B and G
        on the specified day.
        """

        counts = {
            "A": 0,
            "B": 0,
            "G": 0,
        }

        for employee_id in self.context.members:
            shift = self.roster[employee_id].get(day)

            if shift in counts:
                counts[shift] += 1

        return counts


    def _get_pass5_eligible_members(
        self,
        day: int,
        current_shift: str,
    ) -> list[str]:
        """
        Return members who are eligible for a Pass 5 shift change.

        A member is eligible only when:

        1. They are currently assigned current_shift.
        2. They have no active requirement for that day.

        Pass 5 only considers members currently assigned A or B.
        """

        if current_shift not in {"A", "B"}:
            return []

        eligible_members = []

        for employee_id in self.context.members:

            # --------------------------------------------------
            # Member must currently have the requested shift.
            # --------------------------------------------------
            if self.roster[employee_id].get(day) != current_shift:
                continue

            # --------------------------------------------------
            # Member must have no active requirement on this day.
            # --------------------------------------------------
            active_requirement = (
                self._get_active_requirement_for_day(
                    employee_id,
                    day,
                )
            )

            if active_requirement is not None:
                continue

            eligible_members.append(employee_id)

        return eligible_members


    def _select_pass5_member(
        self,
        candidates: list[str],
        day: int,
        new_shift: str,
    ) -> str | None:

        if not candidates:
            return None

        # --------------------------------------------------
        # G assignment:
        # previous-day shift does NOT matter.
        # --------------------------------------------------
        if new_shift == "G":
            return random.choice(candidates)

        # --------------------------------------------------
        # A/B reassignment:
        # prefer candidates who had the new shift yesterday.
        # --------------------------------------------------
        previous_day_candidates = (
            self._get_previous_day_same_shift_candidates(
                candidates,
                day,
                new_shift,
            )
        )

        if previous_day_candidates:
            return random.choice(previous_day_candidates)

        return random.choice(candidates)


    def _assign_pass5_shift(
        self,
        employee_id: str,
        day: int,
        new_shift: str,
    ) -> bool:
        """
        Change a member's shift during Pass 5.

        Pass 5 only changes the roster assignment.

        It does not:
        - modify active requirements;
        - modify relaxed requirements;
        - modify W/H quotas;
        - modify frontend requirements.
        """

        if new_shift not in {"A", "B", "G"}:
            return False

        current_shift = self.roster[
            employee_id
        ].get(day)

        # ------------------------------------------------------
        # Only A/B members may be changed.
        # ------------------------------------------------------
        if current_shift not in {"A", "B"}:
            return False

        # ------------------------------------------------------
        # The member must have no active requirement.
        # ------------------------------------------------------
        active_requirement = (
            self._get_active_requirement_for_day(
                employee_id,
                day,
            )
        )

        if active_requirement is not None:
            return False

        # ------------------------------------------------------
        # Assign the new shift.
        # ------------------------------------------------------
        self.roster[employee_id][day] = new_shift

        return True
    
# ------------------------------------------------------
#               PASS 5 Main Function
# ------------------------------------------------------

    def _run_pass5(
        self,
        day: int | None = None,
    ) -> None:
        """
        Pass 5.

        Balance A/B assignments and, where appropriate,
        introduce a G assignment.

        For every day:

        1. If A exceeds B by 2 or more, change one eligible
           A member to B.

        2. Else if B exceeds A by 2 or more, change one eligible
           B member to A.

        3. If there is no G assignment:
             - if A exceeds B by exactly 1, change one eligible
               A member to G;
             - else if B exceeds A by exactly 1, change one
               eligible B member to G.

        Candidate selection for A/B reassignment prefers a member
        who had the new A/B shift on the previous day.
        For G assignment, previous-day shift history is ignored.

        Day 1 has no previous-day preference.

        Pass 5 does not relax requirements or modify W/H quotas.
        """

        # ------------------------------------------------------
        # Determine which days to process.
        # ------------------------------------------------------
        if day is not None:
            days = [day]
        else:
            days = list(
                range(
                    1,
                    self.context.days_in_month + 1,
                )
            )

        # ------------------------------------------------------
        # Process each day independently.
        # ------------------------------------------------------
        for current_day in days:

            counts = self._get_pass5_shift_counts(
                current_day
            )

            a_count = counts["A"]
            b_count = counts["B"]
            g_count = counts["G"]

            # --------------------------------------------------
            # First: A/B balancing when difference is >= 2.
            #
            # This is an if / elif structure exactly as specified.
            # --------------------------------------------------

            if a_count - b_count >= 2:

                candidates = (
                    self._get_pass5_eligible_members(
                        current_day,
                        "A",
                    )
                )

                selected_employee = (
                    self._select_pass5_member(
                        candidates=candidates,
                        day=current_day,
                        new_shift="B",
                    )
                )

                if selected_employee is not None:
                    self._assign_pass5_shift(
                        employee_id=selected_employee,
                        day=current_day,
                        new_shift="B",
                    )

            elif b_count - a_count >= 2:

                candidates = (
                    self._get_pass5_eligible_members(
                        current_day,
                        "B",
                    )
                )

                selected_employee = (
                    self._select_pass5_member(
                        candidates=candidates,
                        day=current_day,
                        new_shift="A",
                    )
                )

                if selected_employee is not None:
                    self._assign_pass5_shift(
                        employee_id=selected_employee,
                        day=current_day,
                        new_shift="A",
                    )

            # --------------------------------------------------
            # Second: G assignment.
            #
            # G is considered only when there was no G before
            # the Pass 5 operation for this day.
            # --------------------------------------------------

            # After A/B rebalancing
            counts = self._get_pass5_shift_counts(current_day)

            a_count = counts["A"]
            b_count = counts["B"]
            g_count = counts["G"]
            
            if g_count == 0:

                # --------------------------------------------------
                # A exceeds B by exactly 1.
                # --------------------------------------------------
                if a_count - b_count == 1:

                    candidates = (
                        self._get_pass5_eligible_members(
                            current_day,
                            "A",
                        )
                    )

                    selected_employee = (
                        self._select_pass5_member(
                            candidates=candidates,
                            day=current_day,
                            new_shift="G",
                        )
                    )

                    if selected_employee is not None:
                        self._assign_pass5_shift(
                            employee_id=selected_employee,
                            day=current_day,
                            new_shift="G",
                        )

                # --------------------------------------------------
                # B exceeds A by exactly 1.
                # --------------------------------------------------
                elif b_count - a_count == 1:

                    candidates = (
                        self._get_pass5_eligible_members(
                            current_day,
                            "B",
                        )
                    )

                    selected_employee = (
                        self._select_pass5_member(
                            candidates=candidates,
                            day=current_day,
                            new_shift="G",
                        )
                    )

                    if selected_employee is not None:
                        self._assign_pass5_shift(
                            employee_id=selected_employee,
                            day=current_day,
                            new_shift="G",
                        )