-- Per-token daily request counter (replaces the in-memory dict in
-- backend/rate_limit.py). Shared across replicas so the daily limit is global,
-- not N× per replica. Idempotent.
CREATE TABLE IF NOT EXISTS rate_limits (
    token  TEXT NOT NULL,
    day    TEXT NOT NULL,        -- 'YYYY-MM-DD' (UTC). TEXT, consistent with our timestamp policy.
    count  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (token, day)
);

CREATE INDEX IF NOT EXISTS idx_rate_limits_day ON rate_limits(day);
