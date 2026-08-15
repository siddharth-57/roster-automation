import calendar

from fastapi import HTTPException

from app.schemas.roster import RosterGenerationRequest


SHIFTS = ("a", "b", "c", "g", "l", "w")


def validate_roster_request(
    request: RosterGenerationRequest,
) -> RosterGenerationRequest:

    days_in_month = calendar.monthrange(
        request.year,
        request.month,
    )[1]

    seen_employee_ids = set()

    for member in request.requirements:

        employee_id = member.employee_id

        if employee_id in seen_employee_ids:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Duplicate requirements found for "
                    f"employee {employee_id}."
                ),
            )

        seen_employee_ids.add(employee_id)

        dates_by_shift = {}

        for shift in SHIFTS:
            dates = getattr(member, shift)

            # Remove duplicates while preserving order.
            unique_dates = list(dict.fromkeys(dates))

            setattr(
                member,
                shift,
                unique_dates,
            )

            for day in unique_dates:

                if day < 1 or day > days_in_month:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Invalid date {day} for employee "
                            f"{employee_id} in "
                            f"{request.year}-{request.month:02d}. "
                            f"The month has only "
                            f"{days_in_month} days."
                        ),
                    )

                if day in dates_by_shift:
                    previous_shift = dates_by_shift[day]

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Employee {employee_id} has conflicting "
                            f"requirements on day {day}: "
                            f"{previous_shift.upper()} and "
                            f"{shift.upper()}."
                        ),
                    )

                dates_by_shift[day] = shift

    return request