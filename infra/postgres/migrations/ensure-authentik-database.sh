#!/bin/sh
set -eu

# This runs against an existing cluster after PostgreSQL is healthy.  It does
# not mount or create a volume and does not apply application migrations.
# It only reconciles the Authentik login role and its database.
psql \
    --host "$POSTGRES_HOST" \
    --username "$POSTGRES_ADMIN_USER" \
    --dbname "$POSTGRES_ADMIN_DB" \
    --set authentik_db_name="$AUTHENTIK_DB_NAME" \
    --set authentik_db_user="$AUTHENTIK_DB_USER" \
    --set authentik_db_password="$AUTHENTIK_DB_PASSWORD" <<-'SQL'
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'authentik_db_user', :'authentik_db_password')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = :'authentik_db_user') \gexec

SELECT format('ALTER ROLE %I LOGIN PASSWORD %L', :'authentik_db_user', :'authentik_db_password') \gexec

SELECT format('CREATE DATABASE %I OWNER %I', :'authentik_db_name', :'authentik_db_user')
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = :'authentik_db_name') \gexec

SELECT format('ALTER DATABASE %I OWNER TO %I', :'authentik_db_name', :'authentik_db_user') \gexec
SQL
