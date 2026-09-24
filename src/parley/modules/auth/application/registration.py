"""Consistent registration across Authentik and the Parley database."""

from contextlib import AbstractContextManager
from typing import Protocol

from parley.modules.auth.application.identity_provider import (
    AuthenticationRejectedError,
    IdentityProvider,
    IdentityProviderError,
    RegistrationRejectedError,
)
from parley.modules.auth.application.users import UserRepository, resolve_user
from parley.modules.auth.domain import User


class TransactionalUserRepository(Protocol):
    """User storage capable of keeping one transaction around registration."""

    def transaction(self) -> AbstractContextManager[UserRepository]:
        """Open a transaction before Authentik is changed."""


class RegistrationConsistencyError(Exception):
    """Registration failed and its Authentik compensation also failed."""


def register_user(
    *,
    issuer: str,
    username: str,
    password: str,
    email: str,
    name: str,
    identity_provider: IdentityProvider,
    repository: TransactionalUserRepository,
) -> tuple[str, User]:
    """Register a user with compensation and retry-safe recovery."""

    session: str | None = None
    created_in_identity_provider = False

    try:
        # Opening PostgreSQL first prevents creating an Authentik account when
        # the Parley database is already unavailable.
        with repository.transaction() as transaction:
            try:
                session, authentik_user = identity_provider.register(
                    username=username,
                    password=password,
                    email=email,
                )
                created_in_identity_provider = True
            except RegistrationRejectedError as registration_error:
                # A previous request may have created the Authentik account but
                # failed before committing PostgreSQL. Matching credentials and
                # email make that interrupted registration safe to resume.
                try:
                    session, authentik_user = identity_provider.login(
                        username=username,
                        password=password,
                    )
                except AuthenticationRejectedError:
                    raise registration_error

                authentik_email = str(authentik_user.get("email", ""))
                if authentik_email.strip().casefold() != email.strip().casefold():
                    raise registration_error
                if transaction.find_by_identity(
                    issuer=issuer,
                    subject=str(authentik_user["uid"]),
                ) is not None:
                    raise registration_error

            user = resolve_user(
                issuer=issuer,
                authentik_user=authentik_user,
                repository=transaction,
                registration_name=name,
            )
    except Exception:
        if created_in_identity_provider and session is not None:
            try:
                identity_provider.rollback_registration(session=session)
            except IdentityProviderError as rollback_error:
                raise RegistrationConsistencyError(
                    "Unable to roll back the Authentik registration"
                ) from rollback_error
        raise

    return session, user
