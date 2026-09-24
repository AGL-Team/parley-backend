# parley-backend

Backend and supporting infrastructure for Parley.

The repository contains the Python API, PostgreSQL, and Authentik infrastructure.

## Local configuration

1. Copy `.env.example` to `.env`.
2. Replace all `change-me` values with unique random secrets.
3. Start the stack with Docker Compose when ready.

See `docs/infrastructure.md` for the service layout and Authentik setup URL.

The authentication module exposes a headless Authentik integration:

- `POST /api/v1/auth/register` creates and signs in a user with a unique `@tag`;
- `POST /api/v1/auth/login` signs in an existing user by `@tag` or email;
- `POST /api/v1/auth/logout` ends the Authentik session and removes the session cookie;
- `GET /api/v1/auth/me` returns the current Parley user.

The backend executes the configured Authentik flows and stores the resulting
Authentik session in an HttpOnly cookie. Passwords are forwarded to Authentik
for verification and are never stored by the backend.

The MVP intentionally uses server-side sessions only. OAuth2/OIDC and JWT
validation are not configured. Registration opens the Parley database
transaction before creating an Authentik account and compensates a failed
database commit by deleting the newly created Authentik account.

Authentik owns the unique username behind the public `@tag`, email, password,
and session. Parley stores the domain user's `name` in its own `users` table and
links it to Authentik through `external_identities`.
