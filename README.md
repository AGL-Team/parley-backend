# parley-backend

Backend and supporting infrastructure for Parley.

The repository contains the Python API, PostgreSQL, and Authentik infrastructure.

## Local configuration

1. Copy `.env.example` to `.env`.
2. Replace all `change-me` values with unique random secrets.
3. Start the stack with Docker Compose when ready.

See `docs/infrastructure.md` for the service layout and Authentik setup URL.

The authentication module currently exposes a placeholder endpoint at
`GET /api/v1/auth/me`. It returns `501 Not Implemented` until the Authentik OIDC
integration is designed.
