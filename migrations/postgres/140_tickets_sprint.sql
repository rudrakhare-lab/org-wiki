-- Add sprint metadata columns to tickets table.
-- customfield_10020 in Jira returns an array of sprint objects; we store
-- the most-recent sprint's name and id for easy filtering.
ALTER TABLE tickets
    ADD COLUMN IF NOT EXISTS sprint_id   TEXT,
    ADD COLUMN IF NOT EXISTS sprint_name TEXT;

CREATE INDEX IF NOT EXISTS idx_sprint ON tickets(sprint_name);
