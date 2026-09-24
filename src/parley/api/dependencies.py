"""Reusable API dependencies for authentication and authorization."""

import asyncio
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from parley.bootstrap.dependencies import get_settings
from parley.bootstrap.settings import Settings
from parley.modules.auth.application.identity import IdentityAccessDeniedError
from parley.modules.auth.application.identity_provider import (
    IdentityProviderError,
    IdentityProviderUnavailableError,
)
from parley.modules.auth.application.users import UserRepositoryError, resolve_user
from parley.modules.auth.domain import User, UserRole
from parley.modules.auth.infrastructure.authentik import AuthentikClient
from parley.modules.auth.infrastructure.postgres import PostgresUserRepository


SettingsDependency = Annotated[Settings, Depends(get_settings)]


def get_authentik_client(settings: SettingsDependency) -> AuthentikClient:
    return AuthentikClient(api_url=str(settings.authentik_api_url))


def get_user_repository(settings: SettingsDependency) -> PostgresUserRepository:
    return PostgresUserRepository(
        host=settings.parley_db_host,
        port=settings.parley_db_port,
        database=settings.parley_db_name,
        user=settings.parley_db_user,
        password=settings.parley_db_password.get_secret_value(),
    )


AuthentikClientDependency = Annotated[AuthentikClient, Depends(get_authentik_client)]
UserRepositoryDependency = Annotated[
    PostgresUserRepository,
    Depends(get_user_repository),
]


async def get_authenticated_user(
    request: Request,
    settings: SettingsDependency,
    identity_provider: AuthentikClientDependency,
    repository: UserRepositoryDependency,
) -> User:
    """Resolve the current session independently of any concrete endpoint."""

    session = request.cookies.get(settings.auth_session_cookie_name)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        authentik_user = await asyncio.to_thread(
            identity_provider.get_current_user,
            session=session,
        )
        return await asyncio.to_thread(
            resolve_user,
            issuer=settings.authentik_identity_namespace,
            authentik_user=authentik_user,
            repository=repository,
        )
    except IdentityProviderUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is unavailable",
        ) from error
    except IdentityProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        ) from error
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


AuthenticatedUser = Annotated[User, Depends(get_authenticated_user)]


async def require_admin(user: AuthenticatedUser) -> User:
    """Require the authenticated user to have the Parley admin role."""

    if user.role is not UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator role required",
        )
    return user


AdminUser = Annotated[User, Depends(require_admin)]
