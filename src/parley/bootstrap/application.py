"""FastAPI application factory."""

from fastapi import FastAPI

from parley.bootstrap.dependencies import get_settings
from parley.bootstrap.lifecycle import lifespan
from parley.modules.auth.presentation.http.router import router as auth_router


def create_application() -> FastAPI:
    """Create and configure the Parley ASGI application."""
    application = FastAPI(
        title="Parley API",
        lifespan=lifespan,
    )
    application.state.settings = get_settings()
    application.include_router(auth_router, prefix="/api/v1")

    return application
