"""External identity linked to a Parley user."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True, kw_only=True)
class ExternalIdentity:
    """Stable link between an external identity provider and a local user.

    ``subject`` is intentionally stored as text. Authentik can emit an opaque,
    hashed ``sub`` claim, so it must not be treated as the local user UUID.
    The persistence layer must enforce uniqueness for ``(issuer, subject)``.
    """

    id: UUID
    user_id: UUID
    issuer: str
    subject: str
