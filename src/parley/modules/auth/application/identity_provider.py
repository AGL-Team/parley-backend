"""Identity-provider contracts used by the authentication application layer."""

from typing import Any, Protocol


class IdentityProviderError(Exception):
    """Base error raised while communicating with the identity provider."""


class AuthenticationRejectedError(IdentityProviderError):
    """The supplied credentials or session were not accepted."""


class RegistrationRejectedError(IdentityProviderError):
    """The supplied registration data was not accepted."""


class IdentityProviderUnavailableError(IdentityProviderError):
    """The identity provider could not serve the request."""


class IdentityProvider(Protocol):
    """Authentication operations required by the Parley application."""

    def login(self, *, username: str, password: str) -> tuple[str, dict[str, Any]]:
        """Authenticate a user and return their session and profile."""

    def register(
        self,
        *,
        username: str,
        password: str,
        email: str,
    ) -> tuple[str, dict[str, Any]]:
        """Create and authenticate a user."""

    def get_current_user(self, *, session: str) -> dict[str, Any]:
        """Return the profile represented by a session."""

    def logout(self, *, session: str) -> None:
        """Invalidate a session."""

    def rollback_registration(self, *, session: str) -> None:
        """Delete the user created by an uncommitted registration."""
