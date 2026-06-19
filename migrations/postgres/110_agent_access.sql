-- Per-(user, agent) access control. status: pending | granted | rejected | revoked.
-- Access is "granted" only. The default agent (conwo) is open to all and is never
-- stored here. Idempotent; applied at startup by db.init_db().
CREATE TABLE IF NOT EXISTS agent_access (
    user_email   TEXT NOT NULL,
    agent_id     TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending',
    requested_at TEXT,
    decided_at   TEXT,
    decided_by   TEXT,
    PRIMARY KEY (user_email, agent_id)
);
CREATE INDEX IF NOT EXISTS idx_agent_access_status ON agent_access (status);
