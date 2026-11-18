# roster request schema
# This defines the structure, but it doesn't yet validate whether dates actually exist in the selected month.

from pydantic import BaseModel, Field, field_validator

from app.scheduler.config import (
    DEFAULT_C_PER_WEEKDAY,
    DEFAULT_C_PER_WEEKEND,
    MAX_C_PER_DAY,
    MIN_C_PER_DAY,
)


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

    # How many people the TL wants on C each day (1 to 3)
    c_per_weekday: int = Field(
        default=DEFAULT_C_PER_WEEKDAY,
        ge=MIN_C_PER_DAY,
        le=MAX_C_PER_DAY,
    )

    c_per_weekend: int = Field(
        default=DEFAULT_C_PER_WEEKEND,
        ge=MIN_C_PER_DAY,
        le=MAX_C_PER_DAY,
    )

    requirements: list[MemberRequirements]

    @field_validator("group_number")
    @classmethod
    def strip_group_number(cls, value: str) -> str:
        return value.strip()