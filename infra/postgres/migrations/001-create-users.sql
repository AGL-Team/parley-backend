CREATE TABLE IF NOT EXISTS users (
    id uuid PRIMARY KEY,
    name varchar(150) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS external_identities (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    issuer text NOT NULL,
    subject text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (issuer, subject)
);
