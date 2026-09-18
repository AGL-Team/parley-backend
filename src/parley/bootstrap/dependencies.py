"""Application-level dependency providers.

Dependencies shared by several modules can be wired here when they appear.
Module-specific dependencies should remain inside their owning modules.
"""

from functools import lru_cache

from parley.bootstrap.settings import Settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load and cache application settings from the environment."""
    return Settings()  # type: ignore[call-arg]
