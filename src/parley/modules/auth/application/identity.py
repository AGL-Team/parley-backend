"""Mapping Authentik users to the Parley authentication domain."""

from typing import Any
from uuid import NAMESPACE_URL, uuid5

from parley.modules.auth.domain import ExternalIdentity, User, UserRole


def map_authentik_user(
    *,
    issuer: str,
    authentik_user: dict[str, Any],
) -> tuple[User, ExternalIdentity]:
    """Create stable local identities from an Authentik session user."""

    subject = str(authentik_user["uid"])
    user_id = uuid5(NAMESPACE_URL, f"parley:user:{issuer}:{subject}")
    identity_id = uuid5(NAMESPACE_URL, f"parley:identity:{issuer}:{subject}")
    group_names = {
        str(group["name"])
        for group in authentik_user.get("groups", [])
        if isinstance(group, dict) and "name" in group
    }
    role = (
        UserRole.ADMIN
        if "parley-admins" in group_names
        else UserRole.USER
    )

    user = User(
        id=user_id,
        tag=f"@{str(authentik_user['username']).lower()}",
        name="",
        email=str(authentik_user.get("email", "")),
        role=role,
    )
    identity = ExternalIdentity(
        id=identity_id,
        user_id=user_id,
        issuer=issuer,
        subject=subject,
    )
    return user, identity
