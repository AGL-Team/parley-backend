"""PostgreSQL persistence for Parley users and external identities."""

from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

import psycopg

from parley.modules.auth.application.users import UserRepositoryError
from parley.modules.auth.domain import ExternalIdentity, User


class PostgresUserTransaction:
    """User repository operations executed on one PostgreSQL transaction."""

    def __init__(self, connection: psycopg.Connection) -> None:
        self._connection = connection

    def find_by_identity(self, *, issuer: str, subject: str) -> tuple[UUID, str] | None:
        try:
            row = self._connection.execute(
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
        try:
            self._connection.execute(
                """
                INSERT INTO users (id, name)
                VALUES (%s, %s)
                ON CONFLICT (id) DO UPDATE
                SET name = EXCLUDED.name, updated_at = now()
                """,
                (user.id, user.name),
            )
            self._connection.execute(
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

        with self.transaction() as transaction:
            return transaction.find_by_identity(issuer=issuer, subject=subject)

    def save(self, *, user: User, identity: ExternalIdentity) -> None:
        """Persist the user and identity in one transaction."""

        with self.transaction() as transaction:
            transaction.save(user=user, identity=identity)

    @contextmanager
    def transaction(self) -> Iterator[PostgresUserTransaction]:
        """Open a transaction before any external registration side effect."""

        try:
            with psycopg.connect(**self._connection_parameters) as connection:
                yield PostgresUserTransaction(connection)
        except UserRepositoryError:
            raise
        except psycopg.Error as error:
            raise UserRepositoryError("Unable to commit the Parley user") from error
