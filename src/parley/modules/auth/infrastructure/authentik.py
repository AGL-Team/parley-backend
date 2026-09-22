"""Small client for the Authentik Flow Executor and session APIs."""

from __future__ import annotations

from http.cookiejar import CookieJar
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import HTTPCookieProcessor, Request, build_opener


AUTHENTIK_SESSION_COOKIE = "authentik_session"


class AuthentikError(Exception):
    """Base error raised while communicating with Authentik."""


class AuthentikAuthenticationError(AuthentikError):
    """The supplied credentials were not accepted."""


class AuthentikRegistrationError(AuthentikError):
    """The supplied registration data was not accepted."""


class AuthentikUnavailableError(AuthentikError):
    """Authentik could not serve the request."""


class AuthentikClient:
    """Execute the fixed authentication and enrollment flows used by Parley."""

    def __init__(self, *, api_url: str, timeout: float = 10.0) -> None:
        self._api_url = api_url.rstrip("/") + "/"
        self._timeout = timeout

    def login(self, *, username: str, password: str) -> tuple[str, dict[str, Any]]:
        """Authenticate a user and return their Authentik session and profile."""

        cookies = CookieJar()
        opener = build_opener(HTTPCookieProcessor(cookies))
        flow_url = self._flow_url("default-authentication-flow")

        challenge = self._request(opener, flow_url)
        self._require_component(
            challenge,
            "ak-stage-identification",
            AuthentikAuthenticationError,
        )
        challenge = self._request(
            opener,
            flow_url,
            payload={
                "component": "ak-stage-identification",
                "uid_field": username,
            },
        )
        self._require_component(
            challenge,
            "ak-stage-password",
            AuthentikAuthenticationError,
        )
        challenge = self._request(
            opener,
            flow_url,
            payload={
                "component": "ak-stage-password",
                "password": password,
            },
        )
        self._require_success(challenge, AuthentikAuthenticationError)

        return self._session_and_user(opener, cookies)

    def register(
        self,
        *,
        username: str,
        password: str,
        email: str,
    ) -> tuple[str, dict[str, Any]]:
        """Create and authenticate a user through the fixed enrollment flow."""

        cookies = CookieJar()
        opener = build_opener(HTTPCookieProcessor(cookies))
        flow_url = self._flow_url("default-enrollment-flow")

        challenge = self._request(opener, flow_url)
        self._require_component(
            challenge,
            "ak-stage-prompt",
            AuthentikRegistrationError,
        )
        challenge = self._request(
            opener,
            flow_url,
            payload={
                "component": "ak-stage-prompt",
                "username": username,
                "password": password,
                "password_repeat": password,
            },
        )
        self._require_component(
            challenge,
            "ak-stage-prompt",
            AuthentikRegistrationError,
        )
        challenge = self._request(
            opener,
            flow_url,
            payload={
                "component": "ak-stage-prompt",
                "email": email,
            },
        )
        self._require_success(challenge, AuthentikRegistrationError)

        return self._session_and_user(opener, cookies)

    def get_current_user(self, *, session: str) -> dict[str, Any]:
        """Return the Authentik user represented by a session cookie."""

        opener = build_opener()
        response = self._request(
            opener,
            urljoin(self._api_url, "core/users/me/"),
            headers={"Cookie": f"{AUTHENTIK_SESSION_COOKIE}={session}"},
        )
        user = response.get("user")
        if not isinstance(user, dict) or not user.get("is_current"):
            raise AuthentikAuthenticationError("Session is not authenticated")
        return user

    def logout(self, *, session: str) -> None:
        """Invalidate an Authentik session through its default logout flow."""

        opener = build_opener()
        challenge = self._request(
            opener,
            self._flow_url("default-invalidation-flow"),
            headers={"Cookie": f"{AUTHENTIK_SESSION_COOKIE}={session}"},
        )
        self._require_success(challenge, AuthentikAuthenticationError)

    def _session_and_user(
        self,
        opener: Any,
        cookies: CookieJar,
    ) -> tuple[str, dict[str, Any]]:
        response = self._request(opener, urljoin(self._api_url, "core/users/me/"))
        user = response.get("user")
        if not isinstance(user, dict) or not user.get("is_current"):
            raise AuthentikAuthenticationError("Flow did not create a user session")

        session = next(
            (cookie.value for cookie in cookies if cookie.name == AUTHENTIK_SESSION_COOKIE),
            None,
        )
        if session is None:
            raise AuthentikAuthenticationError("Flow did not return a session cookie")
        return session, user

    def _flow_url(self, slug: str) -> str:
        endpoint = urljoin(self._api_url, f"flows/executor/{slug}/")
        return f"{endpoint}?{urlencode({'query': ''})}"

    def _request(
        self,
        opener: Any,
        url: str,
        *,
        payload: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        request_headers = {"Accept": "application/json", **(headers or {})}
        data = None
        if payload is not None:
            request_headers["Content-Type"] = "application/json"
            data = json.dumps(payload).encode("utf-8")

        request = Request(url, data=data, headers=request_headers)
        try:
            with opener.open(request, timeout=self._timeout) as response:
                result = json.load(response)
        except HTTPError as error:
            if error.code in {400, 401, 403}:
                raise AuthentikAuthenticationError(
                    "Authentik rejected the request"
                ) from error
            raise AuthentikUnavailableError(
                f"Authentik returned HTTP {error.code}"
            ) from error
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            raise AuthentikUnavailableError("Authentik is unavailable") from error

        if not isinstance(result, dict):
            raise AuthentikUnavailableError("Authentik returned an invalid response")
        return result

    @staticmethod
    def _require_component(
        challenge: dict[str, Any],
        expected: str,
        error_type: type[AuthentikError],
    ) -> None:
        if challenge.get("component") != expected or challenge.get("response_errors"):
            raise error_type("Authentik flow rejected the submitted data")

    @staticmethod
    def _require_success(
        challenge: dict[str, Any],
        error_type: type[AuthentikError],
    ) -> None:
        if (
            challenge.get("component") != "xak-flow-redirect"
            or not challenge.get("final_redirect")
        ):
            raise error_type("Authentik flow did not complete")
