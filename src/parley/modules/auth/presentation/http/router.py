"""HTTP endpoints exposed by the authentication module."""

import asyncio
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from parley.bootstrap.dependencies import get_settings
from parley.bootstrap.settings import Settings
from parley.modules.auth.application.users import resolve_user
from parley.modules.auth.infrastructure.authentik import (
    AuthentikAuthenticationError,
    AuthentikClient,
    AuthentikError,
    AuthentikRegistrationError,
    AuthentikUnavailableError,
)
from parley.modules.auth.infrastructure.postgres import (
    PostgresUserRepository,
    UserRepositoryError,
)
from parley.modules.auth.presentation.http.schemas import (
    LoginRequest,
    RegisterRequest,
    UserResponse,
)


router = APIRouter(prefix="/auth", tags=["auth"])


def _client(settings: Settings) -> AuthentikClient:
    return AuthentikClient(api_url=str(settings.authentik_api_url))


def _repository(settings: Settings) -> PostgresUserRepository:
    return PostgresUserRepository(
        host=settings.parley_db_host,
        port=settings.parley_db_port,
        database=settings.parley_db_name,
        user=settings.parley_db_user,
        password=settings.parley_db_password.get_secret_value(),
    )


def _resolve_user_response(
    *,
    settings: Settings,
    authentik_user: dict[str, Any],
    registration_name: str | None = None,
) -> UserResponse:
    user = resolve_user(
        issuer=str(settings.authentik_issuer),
        authentik_user=authentik_user,
        repository=_repository(settings),
        registration_name=registration_name,
    )
    return UserResponse.from_domain(user)


def _set_session_cookie(
    *,
    response: Response,
    settings: Settings,
    session: str,
) -> None:
    response.set_cookie(
        key=settings.auth_session_cookie_name,
        value=session,
        httponly=True,
        secure=settings.auth_session_cookie_secure,
        samesite=settings.auth_session_cookie_samesite,
        path="/",
    )


@router.post(
    "/login",
    response_model=UserResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Invalid credentials"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Authentication or user storage unavailable"
        },
    },
)
async def login(
    credentials: LoginRequest,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserResponse:
    """Authenticate through Authentik without exposing the Authentik UI."""

    try:
        session, authentik_user = await asyncio.to_thread(
            _client(settings).login,
            username=credentials.login,
            password=credentials.password,
        )
    except AuthentikUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is unavailable",
        ) from error
    except AuthentikError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid tag, email, or password",
        ) from error

    try:
        user = await asyncio.to_thread(
            _resolve_user_response,
            settings=settings,
            authentik_user=authentik_user,
        )
    except UserRepositoryError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User storage is unavailable",
        ) from error

    _set_session_cookie(response=response, settings=settings, session=session)
    return user


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=UserResponse,
    responses={
        status.HTTP_409_CONFLICT: {"description": "Registration rejected"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Authentication or user storage unavailable"
        },
    },
)
async def register(
    registration: RegisterRequest,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserResponse:
    """Register through Authentik without exposing the Authentik UI."""

    try:
        session, authentik_user = await asyncio.to_thread(
            _client(settings).register,
            username=registration.tag[1:],
            password=registration.password,
            email=registration.email,
        )
    except AuthentikUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is unavailable",
        ) from error
    except (AuthentikRegistrationError, AuthentikAuthenticationError) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tag or email is already used or invalid",
        ) from error

    try:
        user = await asyncio.to_thread(
            _resolve_user_response,
            settings=settings,
            authentik_user=authentik_user,
            registration_name=registration.name,
        )
    except UserRepositoryError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User storage is unavailable",
        ) from error

    _set_session_cookie(response=response, settings=settings, session=session)
    return user


@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Not authenticated"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Authentication or user storage unavailable"
        },
    },
)
async def get_current_user(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserResponse:
    """Return the Parley user represented by the Authentik session."""

    session = request.cookies.get(settings.auth_session_cookie_name)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        authentik_user = await asyncio.to_thread(
            _client(settings).get_current_user,
            session=session,
        )
    except AuthentikUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is unavailable",
        ) from error
    except AuthentikError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        ) from error

    try:
        return await asyncio.to_thread(
            _resolve_user_response,
            settings=settings,
            authentik_user=authentik_user,
        )
    except UserRepositoryError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User storage is unavailable",
        ) from error
