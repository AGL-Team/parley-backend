"""Tests for mapping Authentik identities to Parley users."""

from unittest import TestCase

from parley.modules.auth.application.identity import map_authentik_user
from parley.modules.auth.domain import UserRole


class IdentityMappingTests(TestCase):
    def test_keeps_external_subject_separate_from_local_user_id(self) -> None:
        user, identity = map_authentik_user(
            issuer="http://localhost:9000/application/o/parley/",
            authentik_user={
                "uid": "authentik-subject",
                "username": "alice",
                "name": "Alice",
                "email": "alice@example.com",
                "groups": [{"name": "parley-users"}],
            },
        )

        self.assertEqual(identity.subject, "authentik-subject")
        self.assertEqual(identity.user_id, user.id)
        self.assertNotEqual(str(user.id), identity.subject)
        self.assertEqual(user.tag, "@alice")
        self.assertEqual(user.role, UserRole.USER)

    def test_maps_admin_group_to_admin_role(self) -> None:
        user, _identity = map_authentik_user(
            issuer="http://localhost:9000/application/o/parley/",
            authentik_user={
                "uid": "admin-subject",
                "username": "admin",
                "name": "Admin",
                "email": "admin@example.com",
                "groups": [{"name": "parley-admins"}],
            },
        )

        self.assertEqual(user.role, UserRole.ADMIN)
