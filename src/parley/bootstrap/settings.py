"""Environment-backed application settings."""

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
