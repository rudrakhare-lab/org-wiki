-- 101_generic_agents_extract_tools.sql — idempotent.
-- Ingest extraction is tool-driven: the planner is handed a file path and must
-- call extract_pdf/extract_docx/extract_xlsx/extract_text_file to read the doc.
-- Generic agents (infosec + any self-service agent) were seeded WITHOUT these
-- tools, so they could not ingest anything. Grant them to every generic agent
-- that is missing them. The WHERE guard keys on extract_pdf so re-running is a
-- no-op once applied. Conwo (schema_kind='workinsync', tools='{*}') is untouched.
UPDATE agents
SET tools = ARRAY['extract_pdf', 'extract_docx', 'extract_xlsx', 'extract_text_file'] || tools
WHERE schema_kind = 'generic'
  AND NOT ('extract_pdf' = ANY(tools));
