# roster request schema
# This defines the structure, but it doesn't yet validate whether dates actually exist in the selected month.

from pydantic import BaseModel, Field, field_validator


class MemberRequirements(BaseModel):
    employee_id: str

    a: list[int] = Field(default_factory=list)
    b: list[int] = Field(default_factory=list)
    c: list[int] = Field(default_factory=list)
    g: list[int] = Field(default_factory=list)
    l: list[int] = Field(default_factory=list)
    w: list[int] = Field(default_factory=list)

    @field_validator("employee_id")
    @classmethod
    def normalize_employee_id(cls, value: str) -> str:
        return value.strip().upper()


class RosterGenerationRequest(BaseModel):
    year: int = Field(ge=2000)
    month: int = Field(ge=1, le=12)

    group_number: str = Field(
        min_length=1,
        max_length=20,
    )

    public_holidays: int = Field(
        ge=0,
    )

    requirements: list[MemberRequirements]