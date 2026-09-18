# parley-backend

Backend and supporting infrastructure for Parley.

The repository currently contains the PostgreSQL and Authentik infrastructure.
The Python backend will be added separately.

## Local configuration

1. Copy `.env.example` to `.env`.
2. Replace all `change-me` values with unique random secrets.
3. Start the stack with Docker Compose when ready.

See `docs/infrastructure.md` for the service layout and Authentik setup URL.
