"""Tests for registration consistency across Authentik and PostgreSQL."""

from contextlib import contextmanager
from unittest import TestCase
from unittest.mock import Mock

from parley.modules.auth.application.identity_provider import (
    IdentityProviderUnavailableError,
    RegistrationRejectedError,
)
from parley.modules.auth.application.registration import (
    RegistrationConsistencyError,
    register_user,
)
from parley.modules.auth.application.users import UserRepositoryError
from tests.modules.auth.test_users import FakeUserRepository


AUTHENTIK_USER = {
    "uid": "external-id",
    "username": "alice_1",
    "email": "alice@example.com",
    "groups": [{"name": "parley-users"}],
}


class TransactionalRepository:
    def __init__(self, transaction: FakeUserRepository | None = None) -> None:
        self.storage = transaction or FakeUserRepository()
        self.fail_before_yield = False

    @contextmanager
    def transaction(self):
        if self.fail_before_yield:
            raise UserRepositoryError("database unavailable")
        yield self.storage


class FailingSaveRepository(FakeUserRepository):
    def save(self, **_values) -> None:
        raise UserRepositoryError("commit failed")


class RegistrationTests(TestCase):
    def test_checks_postgres_before_creating_authentik_user(self) -> None:
        provider = Mock()
        repository = TransactionalRepository()
        repository.fail_before_yield = True

        with self.assertRaises(UserRepositoryError):
            register_user(
                issuer="authentik:parley",
                username="alice_1",
                password="password",
                email="alice@example.com",
                name="Alice",
                identity_provider=provider,
                repository=repository,
            )

        provider.register.assert_not_called()

    def test_rolls_back_authentik_when_postgres_save_fails(self) -> None:
        provider = Mock()
        provider.register.return_value = "session", AUTHENTIK_USER
        repository = TransactionalRepository(FailingSaveRepository())

        with self.assertRaises(UserRepositoryError):
            register_user(
                issuer="authentik:parley",
                username="alice_1",
                password="password",
                email="alice@example.com",
                name="Alice",
                identity_provider=provider,
                repository=repository,
            )

        provider.rollback_registration.assert_called_once_with(session="session")

    def test_resumes_interrupted_registration_with_matching_credentials(self) -> None:
        provider = Mock()
        provider.register.side_effect = RegistrationRejectedError("already exists")
        provider.login.return_value = "session", AUTHENTIK_USER
        repository = TransactionalRepository()

        session, user = register_user(
            issuer="authentik:parley",
            username="alice_1",
            password="password",
            email="ALICE@example.com",
            name="Alice",
            identity_provider=provider,
            repository=repository,
        )

        self.assertEqual(session, "session")
        self.assertEqual(user.name, "Alice")
        provider.rollback_registration.assert_not_called()

    def test_does_not_treat_existing_parley_user_as_interrupted(self) -> None:
        provider = Mock()
        provider.register.return_value = "session", AUTHENTIK_USER
        repository = TransactionalRepository()
        register_user(
            issuer="authentik:parley",
            username="alice_1",
            password="password",
            email="alice@example.com",
            name="Alice",
            identity_provider=provider,
            repository=repository,
        )
        provider.register.side_effect = RegistrationRejectedError("already exists")
        provider.login.return_value = "session", AUTHENTIK_USER

        with self.assertRaises(RegistrationRejectedError):
            register_user(
                issuer="authentik:parley",
                username="alice_1",
                password="password",
                email="alice@example.com",
                name="Changed name",
                identity_provider=provider,
                repository=repository,
            )

    def test_reports_inconsistent_state_when_rollback_fails(self) -> None:
        provider = Mock()
        provider.register.return_value = "session", AUTHENTIK_USER
        provider.rollback_registration.side_effect = IdentityProviderUnavailableError(
            "unavailable"
        )
        repository = TransactionalRepository(FailingSaveRepository())

        with self.assertRaises(RegistrationConsistencyError):
            register_user(
                issuer="authentik:parley",
                username="alice_1",
                password="password",
                email="alice@example.com",
                name="Alice",
                identity_provider=provider,
                repository=repository,
            )
