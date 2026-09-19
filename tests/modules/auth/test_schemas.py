"""Tests for authentication HTTP schemas."""

from unittest import TestCase

from pydantic import ValidationError

from parley.modules.auth.presentation.http.schemas import (
    LoginRequest,
    RegisterRequest,
)


class AuthenticationSchemaTests(TestCase):
    def test_registration_normalizes_tag(self) -> None:
        registration = RegisterRequest(
            tag="  @Alice_1  ",
            password="password-123",
            name="Alice",
            email="alice@example.com",
        )

        self.assertEqual(registration.tag, "@alice_1")

    def test_registration_rejects_tag_without_at_sign(self) -> None:
        with self.assertRaises(ValidationError):
            RegisterRequest(
                tag="alice",
                password="password-123",
                name="Alice",
                email="alice@example.com",
            )

    def test_login_converts_tag_to_authentik_username(self) -> None:
        login = LoginRequest(login="@Alice_1", password="password-123")

        self.assertEqual(login.login, "alice_1")

    def test_login_keeps_email(self) -> None:
        login = LoginRequest(login="alice@example.com", password="password-123")

        self.assertEqual(login.login, "alice@example.com")
