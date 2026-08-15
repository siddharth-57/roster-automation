from fastapi import APIRouter

from app.schemas.roster import RosterGenerationRequest
from app.services.roster_validation import validate_roster_request


router = APIRouter(
    prefix="/rosters",
    tags=["Rosters"],
)

# This is deliberately a validation endpoint only. Nothing is being generated yet.
@router.post("/validate")
def validate_roster(
    request: RosterGenerationRequest,
):
    validated_request = validate_roster_request(request)

    return {
        "message": "Roster requirements are valid",
        "request": validated_request,
    }