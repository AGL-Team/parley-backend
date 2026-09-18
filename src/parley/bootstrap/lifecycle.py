"""Application startup and shutdown lifecycle."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(_application: FastAPI) -> AsyncIterator[None]:
    """Manage resources owned by the application process."""
    yield
