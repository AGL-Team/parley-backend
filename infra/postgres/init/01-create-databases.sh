#!/bin/sh
set -eu

create_database_and_role() {
    database_name="$1"
    database_user="$2"
    database_password="$3"

    psql \
        --username "$POSTGRES_USER" \
        --dbname "$POSTGRES_DB" \
        --set database_name="$database_name" \
        --set database_user="$database_user" \
        --set database_password="$database_password" <<-'SQL'
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'database_user', :'database_password')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = :'database_user') \gexec

SELECT format('CREATE DATABASE %I OWNER %I', :'database_name', :'database_user')
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = :'database_name') \gexec
SQL
}

create_database_and_role "$PARLEY_DB_NAME" "$PARLEY_DB_USER" "$PARLEY_DB_PASSWORD"
create_database_and_role "$AUTHENTIK_DB_NAME" "$AUTHENTIK_DB_USER" "$AUTHENTIK_DB_PASSWORD"
