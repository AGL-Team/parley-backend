"""User entity and its authorization role."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class UserRole(StrEnum):
    """Roles available to Parley users."""

    USER = "user"
    ADMIN = "admin"


@dataclass(slots=True, kw_only=True)
class User:
    """A user known to the Parley domain."""

    id: UUID
    username: str
    email: str
    role: UserRole
