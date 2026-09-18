"""HTTP endpoints exposed by the authentication module."""

from typing import NoReturn

from fastapi import APIRouter, HTTPException, status


router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def get_current_user() -> NoReturn:
    """Reserve the current-user endpoint for the Authentik integration."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Authentication is not implemented yet",
    )
