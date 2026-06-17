-- 100_agents.sql — dynamic agent registry. Idempotent. Seeds the two built-ins.
CREATE TABLE IF NOT EXISTS agents (
    id           TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    identity     TEXT NOT NULL DEFAULT '',
    accent       TEXT NOT NULL DEFAULT '#a78bfa',
    theme_base   TEXT NOT NULL DEFAULT 'dark',
    schema_kind  TEXT NOT NULL DEFAULT 'generic',
    modes        TEXT[] NOT NULL DEFAULT '{api}',
    tools        TEXT[] NOT NULL DEFAULT '{wiki_search,wiki_read_page,wiki_grep,wiki_list_pages,wiki_check_duplicate,wiki_propose_new,wiki_propose_edit,wiki_propose_append,wiki_propose_multi_edit,feedback_record}',
    has_jira     BOOLEAN NOT NULL DEFAULT false,
    has_pms      BOOLEAN NOT NULL DEFAULT false,
    wiki_dir     TEXT NOT NULL,
    raw_dir      TEXT NOT NULL,
    claude_md    TEXT NOT NULL,
    prompt_sections INT[] NOT NULL DEFAULT '{}',
    status       TEXT NOT NULL DEFAULT 'active',
    created_by   TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO agents (id, display_name, identity, accent, theme_base, schema_kind, modes, tools,
                    has_jira, has_pms, wiki_dir, raw_dir, claude_md, prompt_sections, created_by)
VALUES
  ('conwo', 'Conwo',
   'You are Conwo, an AI assistant that answers product, config, and debugging questions about WorkInSync.',
   '#1e293b', 'light', 'workinsync', '{api,agent}', '{*}',
   true, true, 'wiki', 'raw', 'CLAUDE.md', '{5,9,12}', 'system'),
  ('infosec', 'Infosec',
   'You are the Infosec assistant, answering information-security questions from the organization''s security knowledge base.',
   '#a78bfa', 'dark', 'generic', '{api}',
   '{wiki_search,wiki_read_page,wiki_grep,wiki_list_pages,wiki_check_duplicate,wiki_propose_new,wiki_propose_edit,wiki_propose_append,wiki_propose_multi_edit,feedback_record}',
   false, false, 'agents/infosec/wiki', 'agents/infosec/raw', 'agents/infosec/CLAUDE.md', '{}', 'system')
ON CONFLICT (id) DO NOTHING;
