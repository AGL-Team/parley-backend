# Infrastructure

The local infrastructure consists of:

- the Parley FastAPI backend;
- one PostgreSQL cluster with isolated `parley` and `authentik` databases and roles;
- an Authentik server;
- an Authentik background worker.

Persistent data is stored in named Docker volumes. Authentik blueprints intended
for version control belong in `infra/authentik/blueprints`, and custom templates
belong in `infra/authentik/templates`.

## Configuration

Copy `.env.example` to `.env` and replace every `change-me` value before starting
the containers. The `.env` file is intentionally excluded from Git.

The database initialization script is executed only when the PostgreSQL data
volume is created for the first time. `postgres-migrations` then idempotently
ensures both database roles and databases exist, then applies the idempotent
Parley schema migration before the backend and Authentik start. This supports
an existing local PostgreSQL volume that predates either application role.
Changing database names or users still requires a dedicated migration or
recreation of the development volume.

## Authentik setup

After the containers have started, open the initial setup URL:

`http://localhost:9000/if/flow/initial-setup/`

The trailing slash is required by Authentik.
