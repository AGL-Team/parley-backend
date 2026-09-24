"""Tests for shared API authentication and authorization dependencies."""

import asyncio
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock

from fastapi import HTTPException, status
from starlette.requests import Request

# Load bootstrap in the same order as the ASGI entry point.
from parley.bootstrap.application import create_application as _create_application
from parley.api.dependencies import get_authenticated_user, require_admin
from parley.modules.auth.domain import UserRole
from tests.modules.auth.test_users import FakeUserRepository


def _request(cookie: str | None = None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if cookie is not None:
        headers.append((b"cookie", f"parley_session={cookie}".encode()))
    return Request({"type": "http", "headers": headers})


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        auth_session_cookie_name="parley_session",
        authentik_identity_namespace="authentik:parley",
    )


class AuthenticationDependencyTests(TestCase):
    def test_resolves_authenticated_user_without_me_endpoint(self) -> None:
        provider = Mock()
        provider.get_current_user.return_value = {
            "uid": "external-id",
            "username": "alice_1",
            "email": "alice@example.com",
            "groups": [{"name": "parley-users"}],
        }

        user = asyncio.run(
            get_authenticated_user(
                _request("session"),
                _settings(),
                provider,
                FakeUserRepository(),
            )
        )

        self.assertEqual(user.tag, "@alice_1")
        self.assertEqual(user.role, UserRole.USER)

    def test_requires_session_cookie(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            asyncio.run(
                get_authenticated_user(
                    _request(),
                    _settings(),
                    Mock(),
                    FakeUserRepository(),
                )
            )

        self.assertEqual(raised.exception.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_dependency_rejects_regular_user(self) -> None:
        provider = Mock()
        provider.get_current_user.return_value = {
            "uid": "external-id",
            "username": "alice_1",
            "email": "alice@example.com",
            "groups": [{"name": "parley-users"}],
        }
        user = asyncio.run(
            get_authenticated_user(
                _request("session"),
                _settings(),
                provider,
                FakeUserRepository(),
            )
        )

        with self.assertRaises(HTTPException) as raised:
            asyncio.run(require_admin(user))

        self.assertEqual(raised.exception.status_code, status.HTTP_403_FORBIDDEN)
