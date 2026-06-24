-- Add image storage columns to messages.
-- Both are nullable — existing rows remain unaffected.
ALTER TABLE messages
    ADD COLUMN IF NOT EXISTS image_data       BYTEA,
    ADD COLUMN IF NOT EXISTS image_media_type TEXT;
