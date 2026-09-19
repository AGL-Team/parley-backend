"""Environment-backed application settings."""

from typing import Literal

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration required by the Parley application."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    authentik_issuer: AnyHttpUrl
    authentik_jwks_url: AnyHttpUrl
    authentik_client_id: str
    authentik_api_url: AnyHttpUrl = AnyHttpUrl("http://localhost:9000/api/v3/")
    auth_session_cookie_name: str = "parley_session"
    auth_session_cookie_secure: bool = False
    auth_session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
