-- 090_agent_id.sql — scope operational data by agent. Idempotent.
-- DEFAULT 'conwo' backfills all existing rows to the original agent.

ALTER TABLE conversations  ADD COLUMN IF NOT EXISTS agent_id TEXT NOT NULL DEFAULT 'conwo';
ALTER TABLE messages       ADD COLUMN IF NOT EXISTS agent_id TEXT NOT NULL DEFAULT 'conwo';
ALTER TABLE trace_sessions ADD COLUMN IF NOT EXISTS agent_id TEXT NOT NULL DEFAULT 'conwo';

CREATE INDEX IF NOT EXISTS idx_conversations_agent_user
    ON conversations (agent_id, user_email);
CREATE INDEX IF NOT EXISTS idx_trace_sessions_agent_started
    ON trace_sessions (agent_id, started_at);
