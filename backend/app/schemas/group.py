import re

from pydantic import BaseModel, Field, field_validator


# Group numbers are two-digit numbers: 01, 02, ... 99.
# A single digit is padded ("1" -> "01", "8" -> "08").
# They appear in URLs, roster names ("2026-09-Group-08")
# and Excel cell A1 ("Group = 08"), so the format must stay fixed.
GROUP_NUMBER_ERROR = "Group number must be a number from 01 to 99."


def normalize_group_number(value: str) -> str:
    value = value.strip()

    if not re.fullmatch(r"\d{1,2}", value):
        raise ValueError(GROUP_NUMBER_ERROR)

    value = value.zfill(2)

    if value == "00":
        raise ValueError(GROUP_NUMBER_ERROR)

    return value


class GroupCreate(BaseModel):
    group_number: str

    name: str | None = Field(
        default=None,
        max_length=100,
    )

    @field_validator("group_number", mode="before")
    @classmethod
    def validate_group_number(cls, value):
        if not isinstance(value, str):
            value = str(value)

        return normalize_group_number(value)

    @field_validator("name")
    @classmethod
    def blank_name_is_none(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()
        return value or None


class GroupUpdate(BaseModel):
    # Only the display name can change; group_number is fixed.
    name: str | None = Field(
        default=None,
        max_length=100,
    )

    @field_validator("name")
    @classmethod
    def blank_name_is_none(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()
        return value or None


class GroupResponse(BaseModel):
    group_id: int
    group_number: str
    name: str | None
    active: bool
    active_member_count: int