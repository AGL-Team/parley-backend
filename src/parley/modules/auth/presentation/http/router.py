"""HTTP endpoints exposed by the authentication module."""

import asyncio

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from parley.api.dependencies import (
    AuthenticatedUser,
    AuthentikClientDependency,
    SettingsDependency,
    UserRepositoryDependency,
)
from parley.bootstrap.settings import Settings
from parley.modules.auth.application.identity import IdentityAccessDeniedError
from parley.modules.auth.application.identity_provider import (
    AuthenticationRejectedError,
    IdentityProviderError,
    IdentityProviderUnavailableError,
    RegistrationRejectedError,
)
from parley.modules.auth.application.registration import (
    RegistrationConsistencyError,
    register_user,
)
from parley.modules.auth.application.users import UserRepositoryError, resolve_user
from parley.modules.auth.presentation.http.schemas import (
    LoginRequest,
    RegisterRequest,
    UserResponse,
)


router = APIRouter(prefix="/auth", tags=["auth"])


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


def _delete_session_cookie(*, response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.auth_session_cookie_name,
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
        status.HTTP_403_FORBIDDEN: {"description": "User has no Parley access group"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Authentication or user storage unavailable"
        },
    },
)
async def login(
    credentials: LoginRequest,
    response: Response,
    settings: SettingsDependency,
    identity_provider: AuthentikClientDependency,
    repository: UserRepositoryDependency,
) -> UserResponse:
    """Authenticate through Authentik without exposing the Authentik UI."""

    try:
        session, authentik_user = await asyncio.to_thread(
            identity_provider.login,
            username=credentials.login,
            password=credentials.password,
        )
    except IdentityProviderUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is unavailable",
        ) from error
    except IdentityProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid tag, email, or password",
        ) from error

    try:
        user = await asyncio.to_thread(
            resolve_user,
            issuer=settings.authentik_identity_namespace,
            authentik_user=authentik_user,
            repository=repository,
        )
        response_user = UserResponse.from_domain(user)
    except IdentityAccessDeniedError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no access to Parley",
        ) from error
    except UserRepositoryError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User storage is unavailable",
        ) from error

    _set_session_cookie(response=response, settings=settings, session=session)
    return response_user


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=UserResponse,
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "User has no Parley access group"},
        status.HTTP_409_CONFLICT: {"description": "Registration rejected"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Authentication or user storage unavailable"
        },
    },
)
async def register(
    registration: RegisterRequest,
    response: Response,
    settings: SettingsDependency,
    identity_provider: AuthentikClientDependency,
    repository: UserRepositoryDependency,
) -> UserResponse:
    """Register through Authentik without exposing the Authentik UI."""

    try:
        session, user = await asyncio.to_thread(
            register_user,
            issuer=settings.authentik_identity_namespace,
            username=registration.tag[1:],
            password=registration.password,
            email=registration.email,
            name=registration.name,
            identity_provider=identity_provider,
            repository=repository,
        )
    except IdentityProviderUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is unavailable",
        ) from error
    except (RegistrationRejectedError, AuthenticationRejectedError) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tag or email is already used or invalid",
        ) from error
    except IdentityAccessDeniedError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no access to Parley",
        ) from error
    except RegistrationConsistencyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registration could not be completed or rolled back",
        ) from error
    except UserRepositoryError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User storage is unavailable",
        ) from error

    _set_session_cookie(response=response, settings=settings, session=session)
    return UserResponse.from_domain(user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Authentication service unavailable"
        },
    },
)
async def logout(
    request: Request,
    settings: SettingsDependency,
    identity_provider: AuthentikClientDependency,
) -> Response:
    """Invalidate the Authentik session and remove the Parley session cookie."""

    session = request.cookies.get(settings.auth_session_cookie_name)
    response: Response = Response(status_code=status.HTTP_204_NO_CONTENT)

    if session is not None:
        try:
            await asyncio.to_thread(identity_provider.logout, session=session)
        except IdentityProviderUnavailableError:
            response = JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "Authentication service is unavailable"},
            )
        except IdentityProviderError:
            # An absent or already invalid Authentik session is already logged out.
            pass

    _delete_session_cookie(response=response, settings=settings)
    return response


@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Not authenticated"},
        status.HTTP_403_FORBIDDEN: {"description": "User has no Parley access group"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Authentication or user storage unavailable"
        },
    },
)
async def get_current_user(
    user: AuthenticatedUser,
) -> UserResponse:
    """Return the user resolved by the shared authentication dependency."""

    return UserResponse.from_domain(user)
