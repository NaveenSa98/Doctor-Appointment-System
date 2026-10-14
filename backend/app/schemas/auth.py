"""Request and response shapes for authentication and account management."""

import re
import unicodedata
import uuid
from typing import Annotated, Any, Literal, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from app.models import UserRole

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _clean_email(value: str) -> str:
    cleaned = value.strip()
    if not _EMAIL.match(cleaned):
        raise ValueError("must be a valid email address")
    return cleaned


def _clean_full_name(value: str) -> str:
    cleaned = value.strip()
    if not 2 <= len(cleaned) <= 100:
        raise ValueError("must be 2 to 100 characters")
    if any(unicodedata.category(char).startswith("C") for char in cleaned):
        raise ValueError("must not contain control characters")
    return cleaned


Email = Annotated[str, Field(max_length=254), AfterValidator(_clean_email)]
FullName = Annotated[str, AfterValidator(_clean_full_name)]
NewPassword = Annotated[str, Field(min_length=8, max_length=128)]


class LoginRequest(BaseModel):
    """Credentials sent to POST /auth/login."""

    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class RegisterRequest(BaseModel):
    """Body of POST /auth/register. A new account is always a patient: no role field exists."""

    model_config = ConfigDict(extra="forbid")

    full_name: FullName
    email: Email
    password: NewPassword


class ProfileUpdate(BaseModel):
    """Body of PATCH /auth/me. Changing the email or password needs the current password."""

    model_config = ConfigDict(extra="forbid")

    full_name: FullName | None = None
    email: Email | None = None
    new_password: NewPassword | None = None
    current_password: str | None = Field(default=None, max_length=128)

    @model_validator(mode="before")
    @classmethod
    def _no_nulls(cls, data: Any) -> Any:
        if isinstance(data, dict) and any(value is None for value in data.values()):
            raise ValueError("fields may not be null")
        return data

    @model_validator(mode="after")
    def _at_least_one_change(self) -> Self:
        if not ({"full_name", "email", "new_password"} & self.model_fields_set):
            raise ValueError("Provide at least one field to update")
        return self


class DeleteAccountRequest(BaseModel):
    """Body of DELETE /auth/me: the password confirms the person at the keyboard."""

    model_config = ConfigDict(extra="forbid")

    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    """The public view of a user. Never includes the password hash."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str | None
    role: UserRole
    doctor_id: uuid.UUID | None


class LoginResponse(BaseModel):
    """A bearer token and the signed-in user."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserOut
