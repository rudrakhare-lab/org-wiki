-- 070: three-role model (admin / developer / general) + user approval flow. Idempotent.
--
-- Approval column strategy (re-runs on EVERY startup via db.init_db(), so it MUST
-- be idempotent AND must never re-approve a pending user on restart):
--   1. ADD COLUMN with NO default  → existing rows become NULL.
--   2. Backfill WHERE approved IS NULL → only ever touches rows that predate the
--      column (pre-existing users), marking them approved. New sign-ups always get
--      an explicit value (default FALSE below), so they are NOT NULL and are never
--      caught by this backfill on a later restart.
--   3. SET DEFAULT FALSE  → new Google sign-ups default to unapproved.
--   4. SET NOT NULL       → integrity; all rows now have an explicit value.
-- init_db() runs once in lifespan startup (advisory-locked), before the app serves
-- requests, so there are no concurrent create_user() inserts racing the backfill.
ALTER TABLE users ADD COLUMN IF NOT EXISTS approved BOOLEAN;
UPDATE users SET approved = TRUE WHERE approved IS NULL;
ALTER TABLE users ALTER COLUMN approved SET DEFAULT FALSE;
ALTER TABLE users ALTER COLUMN approved SET NOT NULL;

-- Rename the legacy 'viewer' role → 'general'. Idempotent: after the first run no
-- rows have role='viewer', so this is a no-op on subsequent startups. Admins and
-- any other roles are untouched.
UPDATE users SET role = 'general' WHERE role = 'viewer';

-- New default role for the column (was 'viewer').
ALTER TABLE users ALTER COLUMN role SET DEFAULT 'general';
