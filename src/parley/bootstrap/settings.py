"""Environment-backed application settings."""

from typing import Literal

from pydantic import AnyHttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration required by the Parley application."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    authentik_api_url: AnyHttpUrl = AnyHttpUrl("http://localhost:9000/api/v3/")
    authentik_identity_namespace: str = "authentik:parley"
    auth_session_cookie_name: str = "parley_session"
    auth_session_cookie_secure: bool = False
    auth_session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    parley_db_host: str = "localhost"
    parley_db_port: int = 5432
    parley_db_name: str = "parley"
    parley_db_user: str = "parley"
    parley_db_password: SecretStr
