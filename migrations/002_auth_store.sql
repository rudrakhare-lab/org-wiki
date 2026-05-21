-- Layer 2: auth store (applied automatically by backend/auth_store.py at startup)
-- This file is a reference copy only — do NOT run it manually.

CREATE TABLE IF NOT EXISTS users (
    email       TEXT PRIMARY KEY,
    role        TEXT NOT NULL DEFAULT 'viewer',
    created_at  TEXT NOT NULL,
    created_by  TEXT
);

CREATE TABLE IF NOT EXISTS tokens (
    token       TEXT PRIMARY KEY,
    user_email  TEXT NOT NULL REFERENCES users(email) ON DELETE CASCADE,
    created_at  TEXT NOT NULL,
    expires_at  TEXT,
    revoked     INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_tokens_email   ON tokens(user_email);
CREATE INDEX IF NOT EXISTS idx_tokens_revoked ON tokens(revoked, expires_at);
