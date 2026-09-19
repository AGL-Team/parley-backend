"""PostgreSQL persistence for Parley users and external identities."""

from uuid import UUID

import psycopg

from parley.modules.auth.domain import ExternalIdentity, User


class UserRepositoryError(Exception):
    """Parley user persistence is unavailable."""


class PostgresUserRepository:
    """Store Parley-owned user data separately from Authentik."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
    ) -> None:
        self._connection_parameters = {
            "host": host,
            "port": port,
            "dbname": database,
            "user": user,
            "password": password,
        }

    def find_by_identity(self, *, issuer: str, subject: str) -> tuple[UUID, str] | None:
        """Return the local user id and name for an Authentik identity."""

        try:
            with psycopg.connect(**self._connection_parameters) as connection:
                row = connection.execute(
                    """
                    SELECT users.id, users.name
                    FROM external_identities AS identities
                    JOIN users ON users.id = identities.user_id
                    WHERE identities.issuer = %s AND identities.subject = %s
                    """,
                    (issuer, subject),
                ).fetchone()
        except psycopg.Error as error:
            raise UserRepositoryError("Unable to read the Parley user") from error

        if row is None:
            return None
        return UUID(str(row[0])), str(row[1])

    def save(self, *, user: User, identity: ExternalIdentity) -> None:
        """Persist the user and identity in one transaction."""

        try:
            with psycopg.connect(**self._connection_parameters) as connection:
                connection.execute(
                    """
                    INSERT INTO users (id, name)
                    VALUES (%s, %s)
                    ON CONFLICT (id) DO UPDATE
                    SET name = EXCLUDED.name, updated_at = now()
                    """,
                    (user.id, user.name),
                )
                connection.execute(
                    """
                    INSERT INTO external_identities (id, user_id, issuer, subject)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (issuer, subject) DO UPDATE
                    SET user_id = EXCLUDED.user_id
                    """,
                    (
                        identity.id,
                        user.id,
                        identity.issuer,
                        identity.subject,
                    ),
                )
        except psycopg.Error as error:
            raise UserRepositoryError("Unable to save the Parley user") from error
