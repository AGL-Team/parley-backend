# Authentik configuration

`blueprints/parley.yaml` is the portable, version-controlled Authentik configuration for Parley.
It creates:

- the `parley-users` and `parley-admins` groups;
- the two-step enrollment flow;
- automatic membership of newly registered users in `parley-users`;
- the Parley OAuth2/OIDC provider and application.

The blueprint intentionally does not contain users, passwords, database contents, private keys,
or the Authentik secret key. Those values must not be committed to Git.

## Start on another machine

1. Copy `.env.example` to `.env` and replace all `change-me-*` values.
2. Generate a new, long `AUTHENTIK_SECRET_KEY` for that installation.
3. Run `docker compose up -d` from the repository root.
4. Complete Authentik's initial setup and create the administrator account.

The worker mounts `infra/authentik/blueprints` at `/blueprints/custom` and applies the Parley
blueprint automatically. Application users are not migrated; they register again or must be
migrated separately with a database backup.

For non-local environments, add their callback URLs to `redirect_uris` in the blueprint and
change the public issuer URL in `.env`.
