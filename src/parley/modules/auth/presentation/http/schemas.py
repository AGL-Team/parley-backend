"""HTTP request and response models for authentication."""

import re

from pydantic import BaseModel, Field, field_validator

from parley.modules.auth.domain import User, UserRole


class LoginRequest(BaseModel):
    """Credentials accepted by the current Authentik login flow."""

    login: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=1024)

    @field_validator("login")
    @classmethod
    def normalize_login(cls, value: str) -> str:
        value = value.strip()
        if value.startswith("@"):
            return normalize_tag(value)[1:]
        return value


class RegisterRequest(BaseModel):
    """Fields accepted by Parley's registration endpoint."""

    tag: str = Field(
        min_length=6,
        max_length=33,
        pattern=r"^@[A-Za-z][A-Za-z0-9_]{4,31}$",
    )
    password: str = Field(min_length=8, max_length=1024)
    name: str = Field(min_length=1, max_length=150)
    email: str = Field(min_length=3, max_length=254)

    @field_validator("tag", mode="before")
    @classmethod
    def validate_tag(cls, value: str) -> str:
        return normalize_tag(value)


class UserResponse(BaseModel):
    """Public representation of the authenticated Parley user."""

    id: str
    tag: str
    name: str
    email: str
    role: UserRole

    @classmethod
    def from_domain(cls, user: User) -> "UserResponse":
        return cls(
            id=str(user.id),
            tag=user.tag,
            name=user.name,
            email=user.email,
            role=user.role,
        )


def normalize_tag(value: str) -> str:
    """Normalize and validate a Telegram-style public tag."""

    normalized = value.strip().lower()
    if not re.fullmatch(r"@[a-z][a-z0-9_]{4,31}", normalized):
        raise ValueError(
            "tag must start with @ and contain 5-32 letters, digits, or underscores"
        )
    return normalized
