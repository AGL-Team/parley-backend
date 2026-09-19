"""HTTP request and response models for authentication."""

from pydantic import BaseModel, Field

from parley.modules.auth.domain import User, UserRole


class LoginRequest(BaseModel):
    """Credentials accepted by the current Authentik login flow."""

    username: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=1, max_length=1024)


class RegisterRequest(BaseModel):
    """Fields accepted by the current Authentik enrollment flow."""

    username: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=8, max_length=1024)
    name: str = Field(min_length=1, max_length=150)
    email: str = Field(min_length=3, max_length=254)


class UserResponse(BaseModel):
    """Public representation of the authenticated Parley user."""

    id: str
    username: str
    name: str
    email: str
    role: UserRole

    @classmethod
    def from_domain(cls, user: User) -> "UserResponse":
        return cls(
            id=str(user.id),
            username=user.username,
            name=user.name,
            email=user.email,
            role=user.role,
        )
