ARG POSTGRES_VERSION=17-alpine
FROM postgres:${POSTGRES_VERSION}

COPY infra/postgres/init/ /docker-entrypoint-initdb.d/
