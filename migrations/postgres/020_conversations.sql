-- Conversation store (was raw/conversations/conversations.sqlite). Idempotent.
-- The three columns added by the old hand-rolled _apply_migrations()
-- (user_email, compacted_summary, compaction_at_turn) are folded in here.
CREATE TABLE IF NOT EXISTS conversations (
    id                  TEXT PRIMARY KEY,
    title               TEXT NOT NULL,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    user_email          TEXT,
    compacted_summary   TEXT,
    compaction_at_turn  INTEGER
);

CREATE INDEX IF NOT EXISTS idx_conv_updated_at ON conversations(updated_at DESC);

CREATE TABLE IF NOT EXISTS messages (
    id                    TEXT PRIMARY KEY,
    conversation_id       TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role                  TEXT NOT NULL,
    content               TEXT NOT NULL,
    created_at            TEXT NOT NULL,
    mode                  TEXT,
    server                TEXT,
    buid                  TEXT,
    answer_id             TEXT,
    confidence            TEXT,
    sources_json          TEXT,
    tool_trace_json       TEXT,
    missing_context_json  TEXT
);

CREATE INDEX IF NOT EXISTS idx_msg_conversation_id
    ON messages(conversation_id, created_at ASC);
