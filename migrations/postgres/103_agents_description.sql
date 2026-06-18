-- 103_agents_description.sql — idempotent. User-facing one-line description per agent
-- (separate from the system-prompt identity). Shown in the Manage-Agents card grid.
ALTER TABLE agents ADD COLUMN IF NOT EXISTS description TEXT NOT NULL DEFAULT '';

UPDATE agents SET description = 'Product, configuration, and debugging answers for WorkInSync.'
WHERE id = 'conwo' AND description = '';

UPDATE agents SET description = 'Information-security questions from the organization''s security knowledge base.'
WHERE id = 'infosec' AND description = '';
