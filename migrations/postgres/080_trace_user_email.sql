-- 080: per-trace user email for the Traces dashboard "User" column. Idempotent.
--
-- NOTE — deliberate PII trade-off: trace_store otherwise stores only a salted
-- hash_user_email() (see trace_store.py). This column stores the raw email so the
-- admin-only Traces UI can attribute each query to a user. The hashed value in the
-- request_start event metadata is retained unchanged. The Traces surface is
-- admin-gated (api.py registers trace_api.router behind _require_admin).
ALTER TABLE trace_sessions ADD COLUMN IF NOT EXISTS user_email TEXT;
