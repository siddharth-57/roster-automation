from pydantic import BaseModel, Field, field_validator


# Used when a request doesn't say which group, so the current
# screens keep working until they send a group themselves.
DEFAULT_GROUP_NUMBER = "08"


class TeamMemberCreate(BaseModel):
    employee_id: str = Field(
        min_length=1,
        max_length=50
    )

    name: str = Field(
        min_length=1,
        max_length=100
    )

    group_number: str = Field(
        default=DEFAULT_GROUP_NUMBER,
        min_length=1,
        max_length=20,
    )

    @field_validator("employee_id")
    @classmethod
    def normalize_employee_id(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("name", "group_number")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class TeamMemberMove(BaseModel):
    group_number: str = Field(
        min_length=1,
        max_length=20,
    )

    @field_validator("group_number")
    @classmethod
    def strip_group_number(cls, value: str) -> str:
        return value.strip()


class TeamMemberResponse(BaseModel):
    employee_id: str
    name: str
    active: bool
    display_order: int
    group_id: int
    group_number: str

    model_config = {
        "from_attributes": True
    }