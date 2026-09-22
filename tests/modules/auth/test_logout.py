"""Tests for logging out of Authentik through the Parley HTTP endpoint."""

import asyncio
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import ANY, Mock, patch

from fastapi import status
from starlette.requests import Request

# Load the bootstrap modules in the same order as the ASGI entry point.
from parley.bootstrap.application import create_application as _create_application
from parley.modules.auth.infrastructure.authentik import (
    AUTHENTIK_SESSION_COOKIE,
    AuthentikClient,
    AuthentikUnavailableError,
)
from parley.modules.auth.presentation.http.router import logout


def _request(cookie: str | None = None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if cookie is not None:
        headers.append((b"cookie", f"parley_session={cookie}".encode()))
    return Request({"type": "http", "headers": headers})


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        authentik_api_url="http://authentik:9000/api/v3/",
        auth_session_cookie_name="parley_session",
        auth_session_cookie_secure=False,
        auth_session_cookie_samesite="lax",
    )


class AuthentikClientLogoutTests(TestCase):
    def test_logout_executes_default_invalidation_flow_with_session(self) -> None:
        client = AuthentikClient(api_url="http://authentik:9000/api/v3/")

        with patch.object(
            client,
            "_request",
            return_value={
                "component": "xak-flow-redirect",
                "final_redirect": "/",
            },
        ) as request:
            client.logout(session="session-value")

        request.assert_called_once_with(
            ANY,
            "http://authentik:9000/api/v3/flows/executor/"
            "default-invalidation-flow/?query=",
            headers={
                "Cookie": f"{AUTHENTIK_SESSION_COOKIE}=session-value",
            },
        )


class LogoutEndpointTests(TestCase):
    def test_logout_invalidates_remote_session_and_deletes_cookie(self) -> None:
        client = Mock()

        with patch(
            "parley.modules.auth.presentation.http.router._client",
            return_value=client,
        ):
            response = asyncio.run(logout(_request("session-value"), _settings()))

        client.logout.assert_called_once_with(session="session-value")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIn("parley_session=", response.headers["set-cookie"])
        self.assertIn("Max-Age=0", response.headers["set-cookie"])

    def test_logout_without_cookie_is_idempotent(self) -> None:
        with patch(
            "parley.modules.auth.presentation.http.router._client"
        ) as client_factory:
            response = asyncio.run(logout(_request(), _settings()))

        client_factory.assert_not_called()
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIn("Max-Age=0", response.headers["set-cookie"])

    def test_logout_deletes_cookie_when_authentik_is_unavailable(self) -> None:
        client = Mock()
        client.logout.side_effect = AuthentikUnavailableError("unavailable")

        with patch(
            "parley.modules.auth.presentation.http.router._client",
            return_value=client,
        ):
            response = asyncio.run(logout(_request("session-value"), _settings()))

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn("Max-Age=0", response.headers["set-cookie"])
