"""Resolve Authentik identities to persisted Parley users."""

from dataclasses import replace
from typing import Any, Protocol
from uuid import UUID

from parley.modules.auth.application.identity import map_authentik_user
from parley.modules.auth.domain import ExternalIdentity, User


class UserRepository(Protocol):
    """Persistence required by the authentication application service."""

    def find_by_identity(self, *, issuer: str, subject: str) -> tuple[UUID, str] | None:
        """Return the local user id and name linked to an external identity."""

    def save(self, *, user: User, identity: ExternalIdentity) -> None:
        """Persist a user and their external identity atomically."""


def resolve_user(
    *,
    issuer: str,
    authentik_user: dict[str, Any],
    repository: UserRepository,
    registration_name: str | None = None,
) -> User:
    """Resolve an Authentik session user to the Parley source of truth."""

    user, identity = map_authentik_user(
        issuer=issuer,
        authentik_user=authentik_user,
    )
    stored = repository.find_by_identity(
        issuer=identity.issuer,
        subject=identity.subject,
    )
    if stored is not None:
        stored_user_id, stored_name = stored
        user = replace(
            user,
            id=stored_user_id,
            name=registration_name or stored_name,
        )
        if registration_name is not None:
            repository.save(
                user=user,
                identity=replace(identity, user_id=stored_user_id),
            )
        return user

    user = replace(
        user,
        name=registration_name or user.name or user.tag,
    )
    repository.save(user=user, identity=identity)
    return user
