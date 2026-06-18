-- 102_generic_agents_write_tools.sql — idempotent.
-- The ingest EXECUTE phase writes pages via direct-write tools (build_execute_registry
-- registers only wiki_create_page/edit/append/update_frontmatter/rebuild_index, gated by
-- the agent's allowlist). Generic agents (infosec + self-service) were seeded WITHOUT these,
-- so their ingest executor had only wiki_read_page and could not create any page — ingest
-- produced zero output. Grant the five direct-write tools to every generic agent missing them.
-- The WHERE guard keys on wiki_create_page so re-running is a no-op once applied.
-- Conwo (schema_kind='workinsync', tools='{*}') is untouched. The chat path is unaffected:
-- build_registry never registers these write tools regardless of allowlist.
UPDATE agents
SET tools = ARRAY['wiki_create_page', 'wiki_edit_page', 'wiki_append_section',
                  'wiki_update_frontmatter', 'wiki_rebuild_index'] || tools
WHERE schema_kind = 'generic'
  AND NOT ('wiki_create_page' = ANY(tools));
