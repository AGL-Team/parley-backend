"""Tests for resolving external identities to Parley users."""

from unittest import TestCase
from uuid import UUID

from parley.modules.auth.application.users import resolve_user
from parley.modules.auth.domain import ExternalIdentity, User


class FakeUserRepository:
    def __init__(self) -> None:
        self.stored: tuple[User, ExternalIdentity] | None = None

    def find_by_identity(self, *, issuer: str, subject: str) -> tuple[UUID, str] | None:
        if self.stored is None:
            return None
        user, identity = self.stored
        if (identity.issuer, identity.subject) != (issuer, subject):
            return None
        return user.id, user.name

    def save(self, *, user: User, identity: ExternalIdentity) -> None:
        self.stored = user, identity


class UserResolutionTests(TestCase):
    def test_registration_name_is_owned_by_parley(self) -> None:
        repository = FakeUserRepository()

        user = resolve_user(
            issuer="authentik:parley",
            authentik_user={
                "uid": "external-id",
                "username": "alice_1",
                "name": "Name from Authentik must be ignored",
                "email": "alice@example.com",
                "groups": [{"name": "parley-users"}],
            },
            repository=repository,
            registration_name="Alice from Parley",
        )

        self.assertEqual(user.name, "Alice from Parley")
        self.assertIsNotNone(repository.stored)

    def test_existing_parley_name_wins_over_authentik(self) -> None:
        repository = FakeUserRepository()
        first = resolve_user(
            issuer="authentik:parley",
            authentik_user={
                "uid": "external-id",
                "username": "alice_1",
                "name": "Ignored",
                "email": "alice@example.com",
                "groups": [{"name": "parley-users"}],
            },
            repository=repository,
            registration_name="Parley Name",
        )

        second = resolve_user(
            issuer="authentik:parley",
            authentik_user={
                "uid": "external-id",
                "username": "alice_1",
                "name": "Changed in Authentik",
                "email": "alice@example.com",
                "groups": [{"name": "parley-users"}],
            },
            repository=repository,
        )

        self.assertEqual(second.id, first.id)
        self.assertEqual(second.name, "Parley Name")
