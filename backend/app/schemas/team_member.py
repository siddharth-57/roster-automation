from pydantic import BaseModel, Field, field_validator


class TeamMemberCreate(BaseModel):
    employee_id: str = Field(
        min_length=1,
        max_length=50
    )

    name: str = Field(
        min_length=1,
        max_length=100
    )

    @field_validator("employee_id")
    @classmethod
    def normalize_employee_id(cls, value: str) -> str:
        return value.strip().upper()


class TeamMemberResponse(BaseModel):
    employee_id: str
    name: str
    active: bool
    display_order: int

    model_config = {
        "from_attributes": True
    }