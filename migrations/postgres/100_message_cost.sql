-- Per-message query cost (INR), shown as a footer under each assistant answer.
-- Stored in INR directly so the displayed value stays stable even if CONWO_USD_INR
-- changes later. NULL for messages without a cost (e.g. claude-code/agent mode,
-- pre-existing rows). Idempotent.
ALTER TABLE messages ADD COLUMN IF NOT EXISTS cost_inr NUMERIC;
