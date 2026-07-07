# Wiki Retrieval V2 — Phase A (Foundation + Core Pipeline) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Working hybrid semantic + graph wiki retrieval end-to-end: chunked+embedded wiki in pgvector, in-memory typed graph, leashed expansion, calibrated rerank, wired into preflight and the `wiki_search` tool behind a default-on flag with instant kill switch.

**Architecture:** Section-level chunks (row-group table splitting) in a new `wiki_chunks` pgvector table; hybrid tsvector+dense search fused with RRF; a single `wiki_graph` module consumed by retrieval, the UI graph API, and preflight; shared MiniLM rerank with sigmoid calibration; intent/temporal boosts as soft multipliers. Spec: `docs/superpowers/specs/2026-07-07-wiki-retrieval-v2-design.md`.

**Tech Stack:** Postgres + pgvector (HNSW), psycopg 3, Gemini `gemini-embedding-001` via existing `backend/retrieval/v2/embed.py`, MiniLM cross-encoder via existing `backend/retrieval/v2/rerank.py`. No new dependencies.

## Global Constraints

- **Zero new infrastructure / dependencies.** pgvector + in-process Python only.
- **Flag `CONWO_WIKI_RETRIEVAL_V2` domain `"on" | "off"`, default `"on"` in code**, read at call time (never import time). `off` reverts to `WikiIndex.search()` instantly.
- **Empty `wiki_chunks` table (pre-backfill) auto-degrades to the keyword path** with a visible seed note. Every failure fails open, never crashes a query.
- **Prod-realistic test fixtures mandatory** (July-outage policy): ISO-**string** dates, `decimal.Decimal` for any SQL numeric, minimal-column row shapes for every consumer. Never hand-build fixtures with datetime/float where a SQL row is simulated.
- **Soft routing invariant:** intent/temporal adjustments are score multipliers in [0.6, 1.4] — never filters, never zero.
- **Graph leash:** expansion depth ≤ 2 (2 only for ARCHITECTURAL), neighbor cap 6 pages, edge-priority curated → structural → wikilink, expanded chunks always tagged `related_via`.
- **Multi-agent:** every `wiki_chunks` query filters `agent_id`; graph and index registries are per-agent.
- CLAUDE.md §1: never edit `.py` files while a backend runs with `--reload`.
- All timestamps/dates stored as TEXT (repo convention — see migration 040).

---

### Task 1: Migration 170 — `wiki_chunks` table

**Files:**
- Create: `migrations/postgres/170_wiki_chunks.sql`
- Test: `tests/test_migration_170.py`

**Interfaces:**
- Produces: table `wiki_chunks` with columns exactly as below — Tasks 5, 6, 7 depend on these names/types.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_migration_170.py` (pattern: `tests/test_migration_151.py` — per-function skipif so content assertions always run):

```python
"""Migration 170 — wiki_chunks table for wiki retrieval v2."""
import os
import pathlib
import pytest

PG_DSN = os.getenv("CONWO_TEST_DSN")
MIGRATION = pathlib.Path("migrations/postgres/170_wiki_chunks.sql")


def test_migration_170_file_exists():
    assert MIGRATION.is_file()


def test_migration_170_is_idempotent_sql():
    sql = MIGRATION.read_text()
    assert "CREATE TABLE IF NOT EXISTS wiki_chunks" in sql
    assert sql.count("IF NOT EXISTS") >= 4  # table + 3 indexes


def test_migration_170_has_required_columns_and_indexes():
    sql = MIGRATION.read_text()
    for col in ("agent_id", "page_path", "section_anchor", "section_title",
                "page_type", "chunk_index", "chunk_text", "last_updated",
                "content_hash", "embedding", "search_tsv"):
        assert col in sql, f"missing column {col}"
    assert "vector(768)" in sql
    assert "hnsw" in sql and "vector_cosine_ops" in sql
    assert "GENERATED ALWAYS" in sql  # search_tsv is generated (repo convention)


@pytest.mark.skipif(not PG_DSN, reason="requires CONWO_TEST_DSN")
def test_migration_170_applies_idempotently():
    import psycopg
    sql = MIGRATION.read_text()
    with psycopg.connect(PG_DSN, autocommit=True) as conn:
        conn.execute(sql)
        conn.execute(sql)  # second run must be a no-op
        cur = conn.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'wiki_chunks'")
        cols = {r[0] for r in cur.fetchall()}
        assert {"agent_id", "page_path", "section_anchor", "embedding",
                "content_hash", "search_tsv"} <= cols
```

- [ ] **Step 2: Run tests, verify content tests fail**

Run: `venv/bin/pytest tests/test_migration_170.py -v`
Expected: 3 content tests FAIL (file missing); PG test skipped without DSN.

- [ ] **Step 3: Write the migration**

Create `migrations/postgres/170_wiki_chunks.sql`:

```sql
-- 170: wiki_chunks — section-level wiki chunks for hybrid retrieval (wiki v2).
-- Nullable embedding: rows are inserted by scripts/embed_wiki.py with vectors;
-- an all-NULL/empty table means "backfill pending" and the retriever degrades
-- to the keyword path. Safe to deploy ahead of application code.

CREATE TABLE IF NOT EXISTS wiki_chunks (
  id             BIGSERIAL PRIMARY KEY,
  agent_id       TEXT NOT NULL,
  page_path      TEXT NOT NULL,
  section_anchor TEXT NOT NULL DEFAULT '',
  section_title  TEXT NOT NULL DEFAULT '',
  page_type      TEXT NOT NULL DEFAULT '',
  chunk_index    INT  NOT NULL DEFAULT 0,
  chunk_text     TEXT NOT NULL,
  last_updated   TEXT,
  content_hash   TEXT NOT NULL,
  embedding      vector(768),
  search_tsv     tsvector GENERATED ALWAYS AS (to_tsvector('english', chunk_text)) STORED
);

CREATE INDEX IF NOT EXISTS idx_wiki_chunks_embedding ON wiki_chunks
  USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS idx_wiki_chunks_tsv  ON wiki_chunks USING gin (search_tsv);
CREATE INDEX IF NOT EXISTS idx_wiki_chunks_page ON wiki_chunks (agent_id, page_path);
```

- [ ] **Step 4: Run tests, verify pass**

Run: `venv/bin/pytest tests/test_migration_170.py -v`
Expected: 3 pass, 1 skip (or 4 pass with `CONWO_TEST_DSN` exported).

- [ ] **Step 5: Commit**

```bash
git add migrations/postgres/170_wiki_chunks.sql tests/test_migration_170.py
git commit -m "feat(wiki-v2): migration 170 — wiki_chunks table + HNSW (spec §5.1)"
```

---

### Task 2: Chunker — pure functions

**Files:**
- Create: `backend/retrieval/wiki_v2/__init__.py` (empty)
- Create: `backend/retrieval/wiki_v2/chunker.py`
- Test: `tests/retrieval/wiki_v2/__init__.py` (empty), `tests/retrieval/wiki_v2/test_chunker.py`

**Interfaces:**
- Produces:
  - `@dataclass Chunk: page_path: str; section_anchor: str; section_title: str; page_type: str; chunk_index: int; chunk_text: str; last_updated: str | None` with property `embed_text -> str` (returns `f"{page_title} — {section_title}\n{chunk_text}"` where page_title is stored on the chunk as `page_title: str`).
  - `split_page(page_path: str, text: str, page_type: str = "", last_updated: str | None = None) -> list[Chunk]`
  - `slugify(heading: str) -> str` (GitHub-style: lowercase, spaces→`-`, strip non `[a-z0-9-]`)
  - `page_type_from_path(page_path: str) -> str` (first path segment singularized: `modules/x.md` → `"module"`, `configs/…` → `"config"`, `runbooks/…` → `"runbook"`, `decisions/…` → `"decision"`, `history/…` → `"history"`, `cross-module/…` → `"cross-module"`, root files → `""`)
- Constants Tasks 5/6/7 rely on: `MAX_PROSE_CHARS = 1200`, `TABLE_ROWS_PER_CHUNK = 15`.

- [ ] **Step 1: Write the failing tests**

Create `tests/retrieval/wiki_v2/test_chunker.py`:

```python
"""Chunker tests — section splits, anchors, row-group tables, prose caps."""
from backend.retrieval.wiki_v2 import chunker

MODULE_PAGE = """---
type: module
status: active
last_updated: 2026-06-01
---

# Desk Management

Handles desk booking end to end.

## Overview

Desk booking for employees across offices.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
""" + "\n".join(
    f"| GET | /desks/{i} | endpoint {i} |" for i in range(40)
) + """

## Open Questions

- Who owns rate limits?
"""


def test_split_page_creates_preamble_and_section_chunks():
    chunks = chunker.split_page("modules/desk-management.md", MODULE_PAGE,
                                page_type="module", last_updated="2026-06-01")
    anchors = [c.section_anchor for c in chunks]
    assert "" in anchors                      # preamble (title + intro)
    assert "overview" in anchors
    assert "open-questions" in anchors
    pre = next(c for c in chunks if c.section_anchor == "")
    assert "Desk booking" not in pre.chunk_text  # preamble stops at first ##
    assert "type: module" not in pre.chunk_text  # frontmatter stripped


def test_big_table_splits_into_row_groups_with_repeated_header():
    chunks = chunker.split_page("modules/desk-management.md", MODULE_PAGE,
                                page_type="module")
    api = [c for c in chunks if c.section_anchor == "api-endpoints"]
    assert len(api) >= 3          # 40 rows / 15 per chunk
    for c in api:
        assert "| Method | Path | Description |" in c.chunk_text  # header repeated
    assert [c.chunk_index for c in api] == list(range(len(api)))


def test_long_prose_splits_at_paragraph_boundaries():
    long_section = "## Notes\n\n" + "\n\n".join(f"Paragraph {i}. " + "x" * 300
                                                for i in range(8))
    text = "# T\n\nintro\n\n" + long_section
    chunks = chunker.split_page("concepts/t.md", text)
    notes = [c for c in chunks if c.section_anchor == "notes"]
    assert len(notes) >= 2
    assert all(len(c.chunk_text) <= chunker.MAX_PROSE_CHARS + 400 for c in notes)


def test_embed_text_carries_page_and_section_titles():
    chunks = chunker.split_page("modules/desk-management.md", MODULE_PAGE)
    ov = next(c for c in chunks if c.section_anchor == "overview")
    assert ov.embed_text.startswith("Desk Management — Overview\n")


def test_slugify_matches_github_style():
    assert chunker.slugify("API Endpoints") == "api-endpoints"
    assert chunker.slugify("Config Comparison (.in vs .com)") == "config-comparison-in-vs-com"


def test_page_type_from_path():
    assert chunker.page_type_from_path("modules/x.md") == "module"
    assert chunker.page_type_from_path("configs/x.md") == "config"
    assert chunker.page_type_from_path("history/release-notes-2026.md") == "history"
    assert chunker.page_type_from_path("overview.md") == ""


def test_empty_sections_are_skipped():
    text = "# T\n\n## Empty\n\n## Real\n\ncontent here"
    chunks = chunker.split_page("concepts/t.md", text)
    anchors = [c.section_anchor for c in chunks]
    assert "real" in anchors and "empty" not in anchors
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `venv/bin/pytest tests/retrieval/wiki_v2/test_chunker.py -v`
Expected: FAIL — `ModuleNotFoundError: backend.retrieval.wiki_v2`.

- [ ] **Step 3: Implement the chunker**

Create `backend/retrieval/wiki_v2/__init__.py` (empty) and `backend/retrieval/wiki_v2/chunker.py`:

```python
"""Section-level chunking for wiki pages (spec §5.2).

Pure functions — no I/O, no DB. Pages split at `##` headings; markdown
tables split into row-groups of TABLE_ROWS_PER_CHUNK with the header
repeated per group; long prose split at paragraph boundaries near
MAX_PROSE_CHARS. Anchors are GitHub-style heading slugs, stable across
re-embeds.
"""
from __future__ import annotations
import re
from dataclasses import dataclass

MAX_PROSE_CHARS = 1200
TABLE_ROWS_PER_CHUNK = 15

_FM_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
_H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


@dataclass
class Chunk:
    page_path: str
    page_title: str
    section_anchor: str
    section_title: str
    page_type: str
    chunk_index: int
    chunk_text: str
    last_updated: str | None = None

    @property
    def embed_text(self) -> str:
        head = self.page_title
        if self.section_title:
            head = f"{self.page_title} — {self.section_title}"
        return f"{head}\n{self.chunk_text}"


def slugify(heading: str) -> str:
    s = heading.strip().lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s]+", "-", s).strip("-")
    return re.sub(r"-{2,}", "-", s)


_TYPE_MAP = {
    "modules": "module", "configs": "config", "runbooks": "runbook",
    "decisions": "decision", "concepts": "concept", "entities": "entity",
    "integrations": "integration", "cross-module": "cross-module",
    "history": "history", "sources": "source", "persons": "person",
    "patterns": "pattern", "epics": "epic",
}


def page_type_from_path(page_path: str) -> str:
    first = page_path.split("/", 1)[0]
    return _TYPE_MAP.get(first, "") if "/" in page_path else ""


def _is_table_line(line: str) -> bool:
    return line.lstrip().startswith("|")


def _split_table(lines: list[str]) -> list[str]:
    """Row-group split: header (first 2 lines) repeated per group."""
    if len(lines) <= 2 + TABLE_ROWS_PER_CHUNK:
        return ["\n".join(lines)]
    header, rows = lines[:2], lines[2:]
    out = []
    for i in range(0, len(rows), TABLE_ROWS_PER_CHUNK):
        out.append("\n".join(header + rows[i:i + TABLE_ROWS_PER_CHUNK]))
    return out


def _split_prose(text: str) -> list[str]:
    if len(text) <= MAX_PROSE_CHARS:
        return [text]
    paras, out, cur = text.split("\n\n"), [], ""
    for p in paras:
        cand = f"{cur}\n\n{p}".strip() if cur else p
        if len(cand) > MAX_PROSE_CHARS and cur:
            out.append(cur)
            cur = p
        else:
            cur = cand
    if cur:
        out.append(cur)
    return out


def _split_section_body(body: str) -> list[str]:
    """Split a section into pieces: tables by row-group, prose by paragraph."""
    lines = body.splitlines()
    blocks: list[tuple[bool, list[str]]] = []  # (is_table, lines)
    for line in lines:
        t = _is_table_line(line)
        if blocks and blocks[-1][0] == t:
            blocks[-1][1].append(line)
        else:
            blocks.append((t, [line]))
    pieces: list[str] = []
    for is_table, blk in blocks:
        text = "\n".join(blk).strip()
        if not text:
            continue
        pieces.extend(_split_table(blk) if is_table else _split_prose(text))
    return pieces


def split_page(page_path: str, text: str, page_type: str = "",
               last_updated: str | None = None) -> list[Chunk]:
    body = _FM_RE.sub("", text)
    m = _H1_RE.search(body)
    page_title = m.group(1).strip() if m else page_path.rsplit("/", 1)[-1].removesuffix(".md")
    ptype = page_type or page_type_from_path(page_path)

    # Split into (section_title, section_body) at ## headings.
    sections: list[tuple[str, str]] = []
    cur_title, cur_lines = "", []
    for line in body.splitlines():
        if line.startswith("## "):
            sections.append((cur_title, "\n".join(cur_lines)))
            cur_title, cur_lines = line[3:].strip(), []
        else:
            cur_lines.append(line)
    sections.append((cur_title, "\n".join(cur_lines)))

    chunks: list[Chunk] = []
    for title, sec_body in sections:
        sec_body = sec_body.strip()
        if title == "" and sec_body:
            sec_body = _H1_RE.sub("", sec_body).strip()  # drop the H1 line itself
        if not sec_body:
            continue
        anchor = slugify(title) if title else ""
        for idx, piece in enumerate(_split_section_body(sec_body)):
            chunks.append(Chunk(
                page_path=page_path, page_title=page_title,
                section_anchor=anchor, section_title=title,
                page_type=ptype, chunk_index=idx, chunk_text=piece,
                last_updated=last_updated,
            ))
    return chunks
```

- [ ] **Step 4: Run tests, verify pass**

Run: `venv/bin/pytest tests/retrieval/wiki_v2/test_chunker.py -v`
Expected: all pass. If the prose-cap test fails on boundary size, adjust the test tolerance, not the splitter contract.

- [ ] **Step 5: Commit**

```bash
git add backend/retrieval/wiki_v2/ tests/retrieval/wiki_v2/
git commit -m "feat(wiki-v2): section chunker — anchors, row-group tables, prose caps (spec §5.2)"
```

---

### Task 3: `backend/wiki_graph.py` — one graph, three consumers

**Files:**
- Create: `backend/wiki_graph.py`
- Modify: `backend/wiki_retriever.py` (add `WikiIndex.pages()` accessor; invalidate graph on `build_index`)
- Modify: `backend/wiki_graph_api.py` (consume `wiki_graph` instead of re-extracting)
- Modify: `backend/preflight.py:163-198` region (related-module discovery via `wiki_graph.neighbors`)
- Test: `tests/test_wiki_graph.py`

**Interfaces:**
- Consumes: `wiki_retriever.get_index(agent_id)` pages (`WikiPage.path`, `.full_text`, `.frontmatter`).
- Produces:
  - `EDGE_PRIORITY: dict[str, int]` = `{"config_of": 0, "runbook_of": 0, "decision_for": 0, "depends_on": 1, "used_by": 1, "wikilink": 2}`
  - `@dataclass(frozen=True) Edge: src: str; dst: str; type: str` (src/dst are page paths)
  - `class WikiGraph:` with `.edges: list[Edge]`, `.neighbors(page_path: str, types: tuple[str, ...] | None = None, limit: int | None = None) -> list[tuple[str, str]]` (returns `(neighbor_page_path, edge_type)`, both directions, deduped, ordered by `EDGE_PRIORITY` then path), `.node_count: int`
  - `get_graph(agent_id: str | None = None) -> WikiGraph` (per-agent cache), `invalidate(agent_id: str | None = None)`
- Tasks 7 and Phase B rely on `neighbors()` exactly as above.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_wiki_graph.py`:

```python
"""wiki_graph — typed edge extraction + neighbors API."""
from backend import wiki_graph
from backend.wiki_retriever import WikiPage


def _page(path, text, fm=None):
    return WikiPage(path=path, title=path, full_text=text,
                    tokens=[], frontmatter=fm or {})


PAGES = {
    "modules/desk-management.md": _page(
        "modules/desk-management.md",
        "# Desk\n\nSee [[modules/parking-management]] and [[concepts/booking]].",
        fm={"depends_on": ["sso"], "used_by": ["employee-experience"]}),
    "modules/sso.md": _page("modules/sso.md", "# SSO"),
    "modules/employee-experience.md": _page("modules/employee-experience.md", "# EE"),
    "modules/parking-management.md": _page("modules/parking-management.md", "# P"),
    "concepts/booking.md": _page("concepts/booking.md", "# B"),
    "configs/desk-management.md": _page(
        "configs/desk-management.md", "# Cfg", fm={"module": "desk-management"}),
    "runbooks/desk-setup.md": _page(
        "runbooks/desk-setup.md", "# RB", fm={"module": "desk-management"}),
    "decisions/2026-01-01-desk-policy.md": _page(
        "decisions/2026-01-01-desk-policy.md", "# D",
        fm={"modules": ["desk-management"]}),
}


def _graph():
    return wiki_graph.build_graph(PAGES)


def test_frontmatter_dependency_edges():
    g = _graph()
    types = {(d, t) for d, t in g.neighbors("modules/desk-management.md")}
    assert ("modules/sso.md", "depends_on") in types
    assert ("modules/employee-experience.md", "used_by") in types


def test_structural_edges_config_runbook_decision():
    g = _graph()
    n = dict(g.neighbors("modules/desk-management.md"))
    assert n.get("configs/desk-management.md") == "config_of"
    assert n.get("runbooks/desk-setup.md") == "runbook_of"
    assert n.get("decisions/2026-01-01-desk-policy.md") == "decision_for"


def test_wikilink_edges_resolve_paths():
    g = _graph()
    n = dict(g.neighbors("modules/desk-management.md"))
    assert n.get("modules/parking-management.md") == "wikilink"
    assert n.get("concepts/booking.md") == "wikilink"


def test_neighbors_ordered_by_edge_priority_and_limited():
    g = _graph()
    ordered = g.neighbors("modules/desk-management.md", limit=3)
    assert len(ordered) == 3
    prios = [wiki_graph.EDGE_PRIORITY[t] for _, t in ordered]
    assert prios == sorted(prios)  # curated/structural before wikilink


def test_neighbors_bidirectional():
    g = _graph()
    back = dict(g.neighbors("modules/sso.md"))
    assert back.get("modules/desk-management.md") == "depends_on"


def test_type_filter():
    g = _graph()
    only = g.neighbors("modules/desk-management.md", types=("depends_on", "used_by"))
    assert all(t in ("depends_on", "used_by") for _, t in only)
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `venv/bin/pytest tests/test_wiki_graph.py -v`
Expected: FAIL — no module `backend.wiki_graph`.

- [ ] **Step 3: Implement `backend/wiki_graph.py`**

```python
"""One wiki knowledge graph, three consumers (spec §5.3).

Built from what already exists in the markdown: frontmatter relations
(depends_on / used_by / module / modules), structural pairs
(configs/X ↔ modules/X etc.), and [[wikilinks]]. In-memory, per-agent,
rebuilt whenever the wiki index rebuilds. Consumers: retrieval expansion
(wiki_v2), the UI force-graph API, and preflight's related-module fetch.
"""
from __future__ import annotations
import re
import threading
from dataclasses import dataclass

EDGE_PRIORITY: dict[str, int] = {
    "config_of": 0, "runbook_of": 0, "decision_for": 0,
    "depends_on": 1, "used_by": 1,
    "wikilink": 2,
}

_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)")


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    type: str


def _resolve(target: str, paths: set[str]) -> str | None:
    """Resolve a wikilink target to an existing page path."""
    t = target.strip().removesuffix(".md")
    for cand in (f"{t}.md", f"modules/{t}.md"):
        if cand in paths:
            return cand
    stem = t.rsplit("/", 1)[-1]
    matches = [p for p in paths if p.removesuffix(".md").rsplit("/", 1)[-1] == stem]
    return matches[0] if len(matches) == 1 else None


def _module_path(slug: str, paths: set[str]) -> str | None:
    p = f"modules/{slug}.md"
    return p if p in paths else None


def _listify(v) -> list[str]:
    if isinstance(v, list):
        return [str(x) for x in v]
    if isinstance(v, str) and v.strip():
        return [v.strip()]
    return []


class WikiGraph:
    def __init__(self, edges: list[Edge], node_count: int) -> None:
        self.edges = edges
        self.node_count = node_count
        self._adj: dict[str, list[tuple[str, str]]] = {}
        for e in edges:
            self._adj.setdefault(e.src, []).append((e.dst, e.type))
            self._adj.setdefault(e.dst, []).append((e.src, e.type))

    def neighbors(self, page_path: str, types: tuple[str, ...] | None = None,
                  limit: int | None = None) -> list[tuple[str, str]]:
        seen: dict[str, str] = {}
        for dst, t in self._adj.get(page_path, []):
            if types and t not in types:
                continue
            # keep the highest-priority edge type per neighbor
            if dst not in seen or EDGE_PRIORITY[t] < EDGE_PRIORITY[seen[dst]]:
                seen[dst] = t
        out = sorted(seen.items(), key=lambda kv: (EDGE_PRIORITY[kv[1]], kv[0]))
        return out[:limit] if limit else out


def build_graph(pages: dict) -> WikiGraph:
    """pages: {path: WikiPage} — the wiki_retriever index's page map."""
    paths = set(pages)
    edges: set[Edge] = set()

    for path, page in pages.items():
        fm = page.frontmatter or {}

        for slug in _listify(fm.get("depends_on")):
            dst = _module_path(slug, paths)
            if dst:
                edges.add(Edge(path, dst, "depends_on"))
        for slug in _listify(fm.get("used_by")):
            dst = _module_path(slug, paths)
            if dst:
                edges.add(Edge(path, dst, "used_by"))

        if path.startswith("configs/"):
            slug = path.removeprefix("configs/").removesuffix(".md")
            for s in _listify(fm.get("module")) or [slug]:
                dst = _module_path(s, paths)
                if dst:
                    edges.add(Edge(path, dst, "config_of"))
        if path.startswith("runbooks/"):
            for s in _listify(fm.get("module")) + _listify(fm.get("modules")):
                dst = _module_path(s, paths)
                if dst:
                    edges.add(Edge(path, dst, "runbook_of"))
        if path.startswith("decisions/"):
            for s in _listify(fm.get("modules")):
                dst = _module_path(s, paths)
                if dst:
                    edges.add(Edge(path, dst, "decision_for"))

        for m in _WIKILINK_RE.finditer(page.full_text):
            dst = _resolve(m.group(1), paths)
            if dst and dst != path:
                edges.add(Edge(path, dst, "wikilink"))

    return WikiGraph(sorted(edges, key=lambda e: (e.src, e.dst, e.type)),
                     node_count=len(paths))


# ── Per-agent cache (mirrors wiki_retriever._INDICES) ────────────────────────
_GRAPHS: dict[str, WikiGraph] = {}
_lock = threading.RLock()


def get_graph(agent_id: str | None = None) -> WikiGraph:
    from backend import agent_context, wiki_retriever
    aid = agent_id or agent_context.get_current_agent_id()
    with _lock:
        g = _GRAPHS.get(aid)
    if g is None:
        idx = wiki_retriever.get_index(aid)
        g = build_graph(idx.pages())
        with _lock:
            _GRAPHS[aid] = g
    return g


def invalidate(agent_id: str | None = None) -> None:
    from backend import agent_context
    aid = agent_id or agent_context.get_current_agent_id()
    with _lock:
        _GRAPHS.pop(aid, None)
```

- [ ] **Step 4: Add the `pages()` accessor + invalidation hook**

In `backend/wiki_retriever.py`, add inside `class WikiIndex` (after `all_paths`):

```python
    def pages(self) -> dict[str, WikiPage]:
        with self._lock:
            return dict(self._pages)
```

At the end of `build_index(...)` (just before `return idx`):

```python
    from backend import wiki_graph as _wg
    _wg.invalidate(aid)
```

- [ ] **Step 5: Run tests + regression, verify pass**

Run: `venv/bin/pytest tests/test_wiki_graph.py tests/ -q -k "wiki"`
Expected: new tests pass; existing wiki tests unaffected.

- [ ] **Step 6: Rewire `wiki_graph_api.py`**

Replace its edge-extraction internals: where it currently regex-extracts `[[links]]` per page to build `{nodes, links}`, build from `wiki_graph.get_graph()`:

```python
from backend import wiki_graph

def _build_graph_payload():
    g = wiki_graph.get_graph()
    from backend import wiki_retriever
    pages = wiki_retriever.get_index().pages()
    degree: dict[str, int] = {}
    for e in g.edges:
        degree[e.src] = degree.get(e.src, 0) + 1
        degree[e.dst] = degree.get(e.dst, 0) + 1
    nodes = [{"id": p, "label": pg.title, "type": _page_type(pg.full_text),
              "path": p, "val": degree.get(p, 1)} for p, pg in pages.items()]
    links = [{"source": e.src, "target": e.dst, "type": e.type} for e in g.edges]
    return {"nodes": nodes, "links": links}
```

Keep the endpoint contract `{nodes, links}` identical (UI unchanged; `type` on links is additive). Read the existing file first and adapt names — the payload shape in its docstring is the contract.

- [ ] **Step 7: Rewire preflight related-module discovery**

In `backend/preflight.py`, the block at ~163-198 currently reads `deps["depends_on"] + deps["used_by"]` from `_module_relations(page)` frontmatter parsing. Replace the relation source with the graph (keep caps/dedup/ticket-fetch logic identical):

```python
from backend import wiki_graph
# inside the loop over module pages:
related = wiki_graph.get_graph().neighbors(
    page.path, types=("depends_on", "used_by"))
for related_path, _edge in related:
    related_slug = extract_slug_from_path(related_path)
    ...  # existing dedup/cap/fetch logic unchanged
```

Delete the now-unused `_module_relations` helper **only if** nothing else imports it (grep first; if used elsewhere, leave it).

- [ ] **Step 8: Run the full affected sweep**

Run: `venv/bin/pytest tests/ -q -k "wiki or preflight or graph"`
Expected: all pass, no regressions.

- [ ] **Step 9: Commit**

```bash
git add backend/wiki_graph.py backend/wiki_retriever.py backend/wiki_graph_api.py backend/preflight.py tests/test_wiki_graph.py
git commit -m "feat(wiki-v2): wiki_graph module — one typed graph, three consumers (spec §5.3)"
```

---

### Task 4: Reranker sigmoid calibration (shared fix — changes Jira gate behavior too)

**Files:**
- Modify: `backend/retrieval/v2/rerank.py` (`score()` — apply sigmoid to logits)
- Test: `tests/retrieval/v2/test_rerank.py` (extend)

**Interfaces:**
- Produces: `rerank.score(query, candidates) -> list[tuple[dict, float]]` where the float is now **in [0, 1]** (sigmoid of the raw logit). `gate.py` thresholds (`ABSTAIN=0.5`, `HIGH=0.7`, env-tunable) become meaningful. Task 7 and the Jira pipeline both consume this.
- ⚠️ **Deliberate prod behavior change:** the Jira gate will abstain more often (currently it almost never does, because raw logits vastly exceed 0.7). This is audit fix #1 — intended. Thresholds remain env-tunable (`CONWO_RETRIEVAL_V2_ABSTAIN_THRESHOLD`, `CONWO_RETRIEVAL_V2_HIGH_THRESHOLD`) as the rollback lever.

- [ ] **Step 1: Write the failing tests**

Append to `tests/retrieval/v2/test_rerank.py`:

```python
def test_score_returns_probabilities_not_logits(monkeypatch):
    """ms-marco MiniLM predict() returns raw logits (≈ -11..+11). score()
    must sigmoid them into [0,1] so gate thresholds (0.5/0.7) mean what
    they say. Regression for audit Critical #1."""
    from backend.retrieval.v2 import rerank

    class FakeModel:
        def predict(self, pairs):
            return [7.3, -4.1, 0.0]  # raw logits

    monkeypatch.setattr(rerank, "_model", FakeModel())
    cands = [{"summary": f"c{i}", "description_text": "", "comments_text": ""}
             for i in range(3)]
    out = rerank.score("q", cands)
    scores = sorted((s for _, s in out), reverse=True)
    assert all(0.0 <= s <= 1.0 for s in scores)
    assert scores[0] > 0.99      # sigmoid(7.3)
    assert 0.49 < scores[1] < 0.51  # sigmoid(0.0)
    assert scores[2] < 0.02      # sigmoid(-4.1)


def test_score_ordering_preserved_after_sigmoid(monkeypatch):
    from backend.retrieval.v2 import rerank

    class FakeModel:
        def predict(self, pairs):
            return [2.0, 5.0, -1.0]

    monkeypatch.setattr(rerank, "_model", FakeModel())
    cands = [{"summary": s, "description_text": "", "comments_text": ""}
             for s in ("a", "b", "c")]
    out = rerank.score("q", cands)
    assert [c["summary"] for c, _ in out] == ["b", "a", "c"]
```

- [ ] **Step 2: Run tests, verify the first fails**

Run: `venv/bin/pytest tests/retrieval/v2/test_rerank.py -v -k sigmoid or probabilities`
Expected: `test_score_returns_probabilities_not_logits` FAILS (scores are raw logits today). Ordering test may already pass.

- [ ] **Step 3: Implement**

In `backend/retrieval/v2/rerank.py`, modify `score()`:

```python
import math

def _sigmoid(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    e = math.exp(x)
    return e / (1.0 + e)


def score(query: str, candidates: list[dict]) -> list[tuple[dict, float]]:
    if not candidates:
        return []
    pairs = [(query, _doc_text(c)) for c in candidates]
    m = _model_or_load() if _model is None else _model
    # ms-marco cross-encoders emit raw logits (no activation declared in
    # their config). Sigmoid to [0,1] so gate.py's ABSTAIN/HIGH thresholds
    # compare against probabilities, not an unbounded logit scale.
    scores = m.predict(pairs)
    out = list(zip(candidates, (_sigmoid(float(s)) for s in scores)))
    out.sort(key=lambda x: x[1], reverse=True)
    return out
```

- [ ] **Step 4: Run the full v2 suite**

Run: `venv/bin/pytest tests/retrieval/ -q`
Expected: all pass. If any existing gate test hand-fed logit-scale scores, update its fixture scores to the [0,1] scale (flag this in the report — it's an intended contract change).

- [ ] **Step 5: Commit**

```bash
git add backend/retrieval/v2/rerank.py tests/retrieval/v2/test_rerank.py
git commit -m "fix(retrieval-v2): sigmoid-calibrate reranker scores — gate thresholds now meaningful (audit C1)"
```

---

### Task 5: `scripts/embed_wiki.py` — chunk + embed backfill (full/delta, resumable)

**Files:**
- Create: `scripts/embed_wiki.py`
- Test: `tests/scripts/test_embed_wiki.py`

**Interfaces:**
- Consumes: `chunker.split_page`, `chunker.page_type_from_path`, `backend.retrieval.v2.embed.embed_documents(texts: list[str]) -> list[list[float]]`, `backend.db.connection()`, `wiki_retriever` page discovery conventions (`WIKI_INDEX_EXCLUDE`, Obsidian-artifact filtering).
- Produces: CLI `venv/bin/python scripts/embed_wiki.py --mode full|delta [--agent conwo]`. Delta = only pages whose sha1 `content_hash` differs from DB (or absent). Page-level atomicity: DELETE page's chunks + INSERT new ones in one transaction.

- [ ] **Step 1: Write the failing tests**

Create `tests/scripts/test_embed_wiki.py`:

```python
"""embed_wiki — hash-driven delta, page-level atomic replace, skip-empty."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import embed_wiki


def test_page_hash_stable():
    h1 = embed_wiki.page_hash("# Title\n\ncontent")
    h2 = embed_wiki.page_hash("# Title\n\ncontent")
    assert h1 == h2 and len(h1) == 40  # sha1 hex


def test_pages_needing_embed_delta_filters_by_hash():
    disk = {"modules/a.md": "# A\n\nnew", "modules/b.md": "# B\n\nsame"}
    db_hashes = {"modules/b.md": embed_wiki.page_hash("# B\n\nsame"),
                 "modules/a.md": "stale-hash"}
    todo = embed_wiki.pages_needing_embed(disk, db_hashes, mode="delta")
    assert set(todo) == {"modules/a.md"}


def test_pages_needing_embed_full_takes_all():
    disk = {"modules/a.md": "# A", "modules/b.md": "# B"}
    todo = embed_wiki.pages_needing_embed(disk, {"modules/a.md": "x"}, mode="full")
    assert set(todo) == set(disk)


def test_replace_page_chunks_deletes_then_inserts(monkeypatch):
    executed = []

    class FakeCur:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def execute(self, sql, params=None):
            executed.append((" ".join(sql.split()), params))
    class FakeConn:
        def cursor(self): return FakeCur()
        def commit(self): executed.append(("COMMIT", None))

    from backend.retrieval.wiki_v2.chunker import Chunk
    chunks = [Chunk(page_path="modules/a.md", page_title="A",
                    section_anchor="overview", section_title="Overview",
                    page_type="module", chunk_index=0, chunk_text="text",
                    last_updated="2026-06-01")]
    embed_wiki.replace_page_chunks(FakeConn(), "conwo", "modules/a.md",
                                   "hash123", chunks, [[0.0] * 768])
    sqls = [s for s, _ in executed]
    assert any(s.startswith("DELETE FROM wiki_chunks") for s in sqls)
    assert any(s.startswith("INSERT INTO wiki_chunks") for s in sqls)
    assert sqls[-1] == "COMMIT"
    delete_idx = next(i for i, s in enumerate(sqls) if s.startswith("DELETE"))
    insert_idx = next(i for i, s in enumerate(sqls) if s.startswith("INSERT"))
    assert delete_idx < insert_idx


def test_empty_chunks_are_not_embedded(monkeypatch):
    calls = []
    monkeypatch.setattr(embed_wiki, "embed_documents",
                        lambda texts: calls.append(texts) or [[0.0] * 768] * len(texts))
    from backend.retrieval.wiki_v2.chunker import Chunk
    good = Chunk(page_path="p", page_title="T", section_anchor="s",
                 section_title="S", page_type="", chunk_index=0,
                 chunk_text="real content")
    vecs = embed_wiki.embed_chunks([good])
    assert len(vecs) == 1 and calls
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `venv/bin/pytest tests/scripts/test_embed_wiki.py -v`
Expected: FAIL — `embed_wiki` not found.

- [ ] **Step 3: Implement `scripts/embed_wiki.py`**

```python
"""Chunk + embed wiki pages into wiki_chunks (spec §5.2).

Modes:
  --mode full   re-chunk + re-embed every page (hash updated).
  --mode delta  only pages whose content hash differs from DB / missing.

Page-level atomic: each page's chunks are DELETEd + INSERTed in one
transaction, so an interruption never leaves a page half-indexed —
re-running picks up cleanly (resumable by construction).
"""
from __future__ import annotations
import argparse
import hashlib
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend import db  # noqa: E402
from backend.retrieval.v2.embed import embed_documents  # noqa: E402
from backend.retrieval.wiki_v2.chunker import split_page, page_type_from_path, Chunk  # noqa: E402

BATCH = 32

INSERT_SQL = """
    INSERT INTO wiki_chunks (agent_id, page_path, section_anchor, section_title,
        page_type, chunk_index, chunk_text, last_updated, content_hash, embedding)
    VALUES (%(agent_id)s, %(page_path)s, %(section_anchor)s, %(section_title)s,
        %(page_type)s, %(chunk_index)s, %(chunk_text)s, %(last_updated)s,
        %(content_hash)s, %(embedding)s::vector)
"""


def page_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def discover_pages(wiki_dir: Path) -> dict[str, str]:
    """{rel_path: text} for every indexable page (reuses retriever filters)."""
    from backend.config import WIKI_INDEX_EXCLUDE
    from backend.wiki_retriever import _is_obsidian_artifact_at_root
    out: dict[str, str] = {}
    for f in sorted(wiki_dir.rglob("*.md")):
        rel = f.relative_to(wiki_dir)
        if rel.name in WIKI_INDEX_EXCLUDE or _is_obsidian_artifact_at_root(rel):
            continue
        out[str(rel)] = f.read_text(encoding="utf-8", errors="replace")
    return out


def db_hashes(conn, agent_id: str) -> dict[str, str]:
    cur = conn.execute(
        "SELECT DISTINCT page_path, content_hash FROM wiki_chunks WHERE agent_id = %s",
        (agent_id,))
    return {r[0]: r[1] for r in cur.fetchall()}


def pages_needing_embed(disk: dict[str, str], hashes: dict[str, str],
                        mode: str) -> list[str]:
    if mode == "full":
        return list(disk)
    return [p for p, text in disk.items() if hashes.get(p) != page_hash(text)]


def embed_chunks(chunks: list[Chunk]) -> list[list[float]]:
    texts = [c.embed_text for c in chunks]
    vecs: list[list[float]] = []
    for i in range(0, len(texts), BATCH):
        vecs.extend(embed_documents(texts[i:i + BATCH]))
    return vecs


def replace_page_chunks(conn, agent_id: str, page_path: str, content_hash: str,
                        chunks: list[Chunk], vecs: list[list[float]]) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM wiki_chunks WHERE agent_id = %s AND page_path = %s",
                    (agent_id, page_path))
        for c, v in zip(chunks, vecs):
            cur.execute(INSERT_SQL, {
                "agent_id": agent_id, "page_path": c.page_path,
                "section_anchor": c.section_anchor, "section_title": c.section_title,
                "page_type": c.page_type, "chunk_index": c.chunk_index,
                "chunk_text": c.chunk_text, "last_updated": c.last_updated,
                "content_hash": content_hash,
                "embedding": "[" + ",".join(f"{x:.7f}" for x in v) + "]",
            })
    conn.commit()


def _frontmatter_last_updated(text: str) -> str | None:
    from backend.wiki_retriever import _parse_frontmatter
    v = _parse_frontmatter(text).get("last_updated")
    return str(v) if v else None


def run(mode: str, agent_id: str, wiki_dir: Path) -> int:
    disk = discover_pages(wiki_dir)
    with db.connection() as conn:
        todo = pages_needing_embed(disk, db_hashes(conn, agent_id), mode)
        print(f"embed_wiki: {len(todo)}/{len(disk)} pages to (re)embed "
              f"(mode={mode}, agent={agent_id})", flush=True)
        done = 0
        for path in todo:
            text = disk[path]
            chunks = split_page(path, text,
                                page_type=page_type_from_path(path),
                                last_updated=_frontmatter_last_updated(text))
            chunks = [c for c in chunks if c.chunk_text.strip()]
            if not chunks:
                continue
            t0 = time.perf_counter()
            vecs = embed_chunks(chunks)
            replace_page_chunks(conn, agent_id, path, page_hash(text), chunks, vecs)
            done += 1
            print(f"  [{done}/{len(todo)}] {path}: {len(chunks)} chunks "
                  f"({time.perf_counter() - t0:.1f}s)", flush=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("full", "delta"), default="delta")
    ap.add_argument("--agent", default="conwo")
    ap.add_argument("--wiki-dir", default=str(ROOT / "wiki"))
    args = ap.parse_args()
    return run(args.mode, args.agent, Path(args.wiki_dir))


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests, verify pass**

Run: `venv/bin/pytest tests/scripts/test_embed_wiki.py -v`
Expected: all pass (tests are DB-free; `tests/scripts/conftest.py` already no-ops the PG fixture).

- [ ] **Step 5: Commit**

```bash
git add scripts/embed_wiki.py tests/scripts/test_embed_wiki.py
git commit -m "feat(wiki-v2): embed_wiki backfill — hash-driven delta, page-atomic, resumable (spec §5.2)"
```

---

### Task 6: Hybrid chunk search + RRF

**Files:**
- Create: `backend/retrieval/wiki_v2/search.py`
- Test: `tests/retrieval/wiki_v2/test_search.py`

**Interfaces:**
- Consumes: `wiki_chunks` schema (Task 1).
- Produces: `hybrid_chunks(conn, sub_queries: list[str], query_vecs: list[list[float]], agent_id: str, expansions: dict[str, list[str]] | None = None, limit: int = 24) -> list[dict]` — each dict: `id, page_path, section_anchor, section_title, page_type, chunk_index, chunk_text, last_updated, fused_score (float)`. Task 7 consumes this exactly.

- [ ] **Step 1: Write the failing tests**

Create `tests/retrieval/wiki_v2/test_search.py`:

```python
"""Hybrid chunk search — SQL shape, RRF fusion, prod-realistic types."""
from decimal import Decimal
from backend.retrieval.wiki_v2 import search as ws


def test_chunk_sql_has_lex_dense_and_agent_filter():
    assert "search_tsv @@" in ws._CHUNK_SQL
    assert "embedding <=>" in ws._CHUNK_SQL
    assert "agent_id = %(agent_id)s" in ws._CHUNK_SQL
    assert "embedding IS NOT NULL" in ws._CHUNK_SQL


def test_expand_terms_appended_to_lex_query():
    q = ws._lex_query("kiosk OTP", {"OTP": ["one-time password"]})
    assert "kiosk OTP" in q and "one-time password" in q and " OR " in q


def _fake_conn(rows_per_call):
    calls = {"n": 0}
    class FakeCur:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def execute(self, *a, **k): pass
        def fetchall(self):
            rows = rows_per_call[min(calls["n"], len(rows_per_call) - 1)]
            calls["n"] += 1
            return rows
    class FakeConn:
        def cursor(self, **k): return FakeCur()
    return FakeConn()


def _row(cid, path, score):
    # prod-realistic: Decimal fused score, ISO-string date
    return {"id": cid, "page_path": path, "section_anchor": "s",
            "section_title": "S", "page_type": "module", "chunk_index": 0,
            "chunk_text": "t", "last_updated": "2026-06-01",
            "fused_score": Decimal(str(score))}


def test_rrf_fuses_across_sub_queries_and_casts_float():
    conn = _fake_conn([
        [_row(1, "modules/a.md", 0.03), _row(2, "modules/b.md", 0.02)],
        [_row(2, "modules/b.md", 0.04), _row(3, "modules/c.md", 0.01)],
    ])
    out = ws.hybrid_chunks(conn, ["q1", "q2"], [[0.0] * 768] * 2, "conwo")
    ids = [r["id"] for r in out]
    assert ids[0] == 2                      # appears in both sub-queries → fused highest
    assert all(isinstance(r["fused_score"], float) for r in out)


def test_empty_results_return_empty_list():
    conn = _fake_conn([[]])
    assert ws.hybrid_chunks(conn, ["q"], [[0.0] * 768], "conwo") == []
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `venv/bin/pytest tests/retrieval/wiki_v2/test_search.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement `backend/retrieval/wiki_v2/search.py`**

```python
"""Hybrid chunk retrieval: tsvector + pgvector fused by RRF (spec §5.4 step 1).

Mirrors backend/retrieval/v2/hybrid.py conventions: named params, per-sub-query
SQL call, Python-side RRF across sub-queries, explicit float() casts at the
SQL boundary (numeric SUM returns decimal.Decimal — July outage class).
"""
from __future__ import annotations

RRF_K = 60

_CHUNK_SQL = """
WITH lex AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY ts_rank_cd(search_tsv, q) DESC) AS rnk
    FROM wiki_chunks, websearch_to_tsquery('english', %(q_text)s) q
    WHERE search_tsv @@ q AND agent_id = %(agent_id)s
    LIMIT 50
),
dense AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY embedding <=> %(q_vec)s::vector) AS rnk
    FROM wiki_chunks
    WHERE embedding IS NOT NULL AND agent_id = %(agent_id)s
    ORDER BY embedding <=> %(q_vec)s::vector
    LIMIT 50
),
fused AS (
    SELECT id, SUM(1.0 / (%(k)s + rnk)) AS rrf
    FROM (SELECT id, rnk FROM lex UNION ALL SELECT id, rnk FROM dense) u
    GROUP BY id
)
SELECT c.id, c.page_path, c.section_anchor, c.section_title, c.page_type,
       c.chunk_index, c.chunk_text, c.last_updated, f.rrf AS fused_score
FROM fused f JOIN wiki_chunks c USING (id)
ORDER BY f.rrf DESC
LIMIT %(limit)s
"""


def _lex_query(sub_query: str, expansions: dict[str, list[str]] | None) -> str:
    """Append synonym expansions as OR-terms (websearch syntax)."""
    terms = [sub_query]
    for syns in (expansions or {}).values():
        terms.extend(syns)
    return " OR ".join(t for t in terms if t and t.strip())


def hybrid_chunks(conn, sub_queries: list[str], query_vecs: list[list[float]],
                  agent_id: str, expansions: dict[str, list[str]] | None = None,
                  limit: int = 24) -> list[dict]:
    from psycopg.rows import dict_row
    per_sub: list[list[dict]] = []
    with conn.cursor(row_factory=dict_row) as cur:
        for q_text, q_vec in zip(sub_queries, query_vecs):
            cur.execute(_CHUNK_SQL, {
                "q_text": _lex_query(q_text, expansions),
                "q_vec": q_vec, "k": RRF_K,
                "agent_id": agent_id, "limit": limit,
            })
            rows = list(cur.fetchall())
            per_sub.append(
                [{**r, "fused_score": float(r["fused_score"])} for r in rows])

    if len(per_sub) == 1:
        return per_sub[0]

    # RRF across sub-queries, keyed by chunk id.
    scores: dict = {}
    rowmap: dict = {}
    for rows in per_sub:
        for rank, r in enumerate(rows, start=1):
            scores[r["id"]] = scores.get(r["id"], 0.0) + 1.0 / (RRF_K + rank)
            rowmap[r["id"]] = r
    fused = sorted(rowmap.values(),
                   key=lambda r: scores[r["id"]], reverse=True)
    for r in fused:
        r["fused_score"] = float(scores[r["id"]])
    return fused[:limit]
```

- [ ] **Step 4: Run tests, verify pass**

Run: `venv/bin/pytest tests/retrieval/wiki_v2/test_search.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/retrieval/wiki_v2/search.py tests/retrieval/wiki_v2/test_search.py
git commit -m "feat(wiki-v2): hybrid chunk search — tsvector+pgvector RRF, expansion OR-terms (spec §5.4)"
```

---

### Task 7: Pipeline — graph expansion (leashed) + rerank + intent/temporal selection

**Files:**
- Create: `backend/retrieval/wiki_v2/pipeline.py`
- Test: `tests/retrieval/wiki_v2/test_pipeline.py`

**Interfaces:**
- Consumes: `search.hybrid_chunks` (Task 6), `wiki_graph.get_graph().neighbors` (Task 3), `rerank.score` (Task 4, [0,1] scores), `embed.embed_query`.
- Produces:
  - `class WikiV2Unavailable(Exception)` — raised when embedding fails or chunk table is empty; callers fall back to keyword path.
  - `@dataclass ChunkHit: page_path: str; section_anchor: str; section_title: str; page_type: str; chunk_text: str; last_updated: str | None; score: float; related_via: str | None` with property `anchor -> str` returning `f"{page_path}#{section_anchor}"` (or bare `page_path` when anchor is `""`).
  - `search(question: str, *, sub_queries: list[str] | None = None, expansions: dict | None = None, intent: str = "GENERAL", agent_id: str | None = None, top_k: int = 10) -> list[ChunkHit]`
- Constants: `NEIGHBOR_CAP = 6`, `EXPAND_DEPTH = {"ARCHITECTURAL": 2}` (default 1), `TYPE_BOOSTS` per intent, `TEMPORAL_INTENTS = {"HISTORY"}` handled via boost table. Soft-routing invariant: all multipliers within [0.6, 1.4].

- [ ] **Step 1: Write the failing tests**

Create `tests/retrieval/wiki_v2/test_pipeline.py`:

```python
"""wiki_v2 pipeline — expansion leash, tags, soft boosts, degradation."""
import pytest
from backend.retrieval.wiki_v2 import pipeline as wp


def _chunk_row(path, anchor="overview", ptype="module", score=0.02):
    return {"id": hash((path, anchor)) % 10_000, "page_path": path,
            "section_anchor": anchor, "section_title": anchor.title(),
            "page_type": ptype, "chunk_index": 0,
            "chunk_text": f"text of {path}#{anchor}",
            "last_updated": "2026-06-01", "fused_score": score}


@pytest.fixture
def wired(monkeypatch):
    """Wire pipeline internals to fakes; returns dict of knobs tests mutate."""
    knobs = {
        "hybrid": [_chunk_row("modules/desk-management.md")],
        "neighbors": [("configs/desk-management.md", "config_of"),
                      ("modules/sso.md", "depends_on"),
                      ("concepts/booking.md", "wikilink")],
        "best_chunks": {"configs/desk-management.md":
                        _chunk_row("configs/desk-management.md", "config-comparison", "config"),
                        "modules/sso.md":
                        _chunk_row("modules/sso.md", "overview", "module"),
                        "concepts/booking.md":
                        _chunk_row("concepts/booking.md", "definition", "concept")},
    }
    monkeypatch.setattr(wp, "embed_query", lambda q: [0.0] * 768)
    monkeypatch.setattr(wp, "hybrid_chunks",
                        lambda conn, sq, qv, aid, expansions=None, limit=24: knobs["hybrid"])

    class FakeGraph:
        def neighbors(self, path, types=None, limit=None):
            n = knobs["neighbors"]
            return n[:limit] if limit else n
    monkeypatch.setattr(wp, "_graph_for", lambda aid: FakeGraph())
    monkeypatch.setattr(wp, "_best_chunk_for_page",
                        lambda conn, aid, page, qvec: knobs["best_chunks"].get(page))
    # rerank: score by inverse text length (deterministic, [0,1])
    monkeypatch.setattr(
        wp, "rerank_score",
        lambda q, cands: sorted(((c, 0.9) for c in cands),
                                key=lambda x: x[0]["page_path"]))

    class FakeConn:
        def __enter__(self): return self
        def __exit__(self, *a): pass
    monkeypatch.setattr(wp, "_connection", lambda: FakeConn())
    return knobs


def test_expanded_chunks_are_tagged_never_direct(wired):
    hits = wp.search("desk booking", agent_id="conwo")
    direct = [h for h in hits if h.related_via is None]
    related = [h for h in hits if h.related_via is not None]
    assert direct and related
    assert any("config_of" in h.related_via for h in related)


def test_neighbor_cap_respected(wired):
    wired["neighbors"] = [(f"modules/m{i}.md", "wikilink") for i in range(20)]
    wired["best_chunks"] = {f"modules/m{i}.md": _chunk_row(f"modules/m{i}.md")
                            for i in range(20)}
    hits = wp.search("q", agent_id="conwo", top_k=50)
    related = [h for h in hits if h.related_via]
    assert len({h.page_path for h in related}) <= wp.NEIGHBOR_CAP


def test_intent_boost_is_soft_never_zero(wired):
    for intent, mults in wp.TYPE_BOOSTS.items():
        for v in mults.values():
            assert 0.6 <= v <= 1.4, f"{intent} multiplier {v} breaks soft-routing"


def test_configuration_intent_ranks_config_chunk_higher(wired, monkeypatch):
    monkeypatch.setattr(
        wp, "rerank_score",
        lambda q, cands: [(c, 0.8) for c in cands])  # equal base scores
    hits = wp.search("q", agent_id="conwo", intent="CONFIGURATION")
    types = [h.page_type for h in hits]
    assert types.index("config") < types.index("concept")


def test_history_downranked_for_current_state_intent(wired, monkeypatch):
    wired["hybrid"] = [_chunk_row("history/release-notes-2026.md", "rn-1", "history"),
                       _chunk_row("modules/desk-management.md")]
    monkeypatch.setattr(wp, "rerank_score", lambda q, c: [(x, 0.8) for x in c])
    hits = wp.search("q", agent_id="conwo", intent="CONFIGURATION")
    paths = [h.page_path for h in hits]
    assert paths.index("modules/desk-management.md") < paths.index(
        "history/release-notes-2026.md")


def test_temporal_question_boosts_history_even_with_other_intent(wired, monkeypatch):
    wired["hybrid"] = [_chunk_row("history/release-notes-2026.md", "rn-1", "history"),
                       _chunk_row("modules/desk-management.md")]
    monkeypatch.setattr(wp, "rerank_score", lambda q, c: [(x, 0.8) for x in c])
    hits = wp.search("when did desk booking change?", agent_id="conwo",
                     intent="CONFIGURATION")
    paths = [h.page_path for h in hits]
    assert paths.index("history/release-notes-2026.md") < paths.index(
        "modules/desk-management.md")


def test_empty_chunk_table_raises_unavailable(wired):
    wired["hybrid"] = []
    with pytest.raises(wp.WikiV2Unavailable):
        wp.search("q", agent_id="conwo")


def test_embed_failure_raises_unavailable(wired, monkeypatch):
    def boom(q):
        raise RuntimeError("gemini down")
    monkeypatch.setattr(wp, "embed_query", boom)
    with pytest.raises(wp.WikiV2Unavailable):
        wp.search("q", agent_id="conwo")


def test_anchor_property():
    h = wp.ChunkHit(page_path="modules/a.md", section_anchor="overview",
                    section_title="Overview", page_type="module",
                    chunk_text="t", last_updated=None, score=0.5,
                    related_via=None)
    assert h.anchor == "modules/a.md#overview"
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `venv/bin/pytest tests/retrieval/wiki_v2/test_pipeline.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement `backend/retrieval/wiki_v2/pipeline.py`**

```python
"""Wiki v2 retrieval pipeline (spec §5.4): hybrid → leashed graph expansion
→ shared rerank → soft intent/temporal selection.

Raises WikiV2Unavailable on any dependency failure (embedding API, empty
chunk table) — the caller (preflight / wiki_search tool) falls back to the
keyword path and notes the degradation. Never crash a query from here.
"""
from __future__ import annotations
import os
import re
from dataclasses import dataclass

from backend.db import connection as _connection
from backend.retrieval.v2.embed import embed_query
from backend.retrieval.v2.rerank import score as rerank_score
from backend.retrieval.wiki_v2.search import hybrid_chunks

NEIGHBOR_CAP = 6
EXPAND_DEPTH = {"ARCHITECTURAL": 2}  # every other intent: 1

# Temporal detection (spec §5.10): QueryIntent has no HISTORY member — the
# temporal signal is detected from the question text and switches the boost
# table to "HISTORY" (history/decision pages boosted). Requires `import re`
# at module top alongside `import os`.
_TEMPORAL_RE = re.compile(
    r"\b(when did|when was|what changed|changelog|release note|history of|"
    r"used to|previously|before 20\d\d|since 20\d\d|evolved|timeline)\b",
    re.IGNORECASE)

# Soft multipliers only — [0.6, 1.4]. NEVER 0 (soft-routing invariant, spec §5.5).
TYPE_BOOSTS: dict[str, dict[str, float]] = {
    "CONFIGURATION": {"config": 1.3, "module": 1.1, "history": 0.7},
    "DEBUGGING":     {"config": 1.25, "module": 1.1, "history": 0.7},
    "HOW_TO":        {"runbook": 1.3, "module": 1.1, "history": 0.8},
    "DEFINITION":    {"concept": 1.2, "module": 1.15, "history": 0.7},
    "ARCHITECTURAL": {"cross-module": 1.3, "module": 1.2, "history": 0.8},
    "COMPARISON":    {"config": 1.2, "module": 1.1},
    "STATUS":        {"history": 0.8},
    "GENERAL":       {},
    "HISTORY":       {"history": 1.4, "decision": 1.2},  # temporal intent
}


class WikiV2Unavailable(Exception):
    """Wiki v2 cannot serve (embed API down / chunks not backfilled)."""


@dataclass
class ChunkHit:
    page_path: str
    section_anchor: str
    section_title: str
    page_type: str
    chunk_text: str
    last_updated: str | None
    score: float
    related_via: str | None = None

    @property
    def anchor(self) -> str:
        return (f"{self.page_path}#{self.section_anchor}"
                if self.section_anchor else self.page_path)


def _graph_for(agent_id: str | None):
    from backend import wiki_graph
    return wiki_graph.get_graph(agent_id)


_BEST_CHUNK_SQL = """
    SELECT id, page_path, section_anchor, section_title, page_type,
           chunk_index, chunk_text, last_updated, 0.0 AS fused_score
    FROM wiki_chunks
    WHERE agent_id = %(agent_id)s AND page_path = %(page_path)s
          AND embedding IS NOT NULL
    ORDER BY embedding <=> %(q_vec)s::vector
    LIMIT 1
"""


def _best_chunk_for_page(conn, agent_id: str, page_path: str,
                         q_vec: list[float]) -> dict | None:
    from psycopg.rows import dict_row
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(_BEST_CHUNK_SQL, {"agent_id": agent_id,
                                      "page_path": page_path, "q_vec": q_vec})
        rows = cur.fetchall()
    return dict(rows[0]) if rows else None


def _to_rerank_shape(row: dict) -> dict:
    """Map a chunk row onto rerank._doc_text's expected keys."""
    title = f"{row['page_path']} {row.get('section_title', '')}".strip()
    return {**row, "summary": title, "description_text": row["chunk_text"],
            "comments_text": ""}


def search(question: str, *, sub_queries: list[str] | None = None,
           expansions: dict | None = None, intent: str = "GENERAL",
           agent_id: str | None = None, top_k: int = 10) -> list[ChunkHit]:
    from backend import agent_context
    aid = agent_id or agent_context.get_current_agent_id()
    subs = [q for q in (sub_queries or [question]) if q and q.strip()] or [question]

    try:
        q_vecs = [embed_query(q) for q in subs]
    except Exception as exc:
        raise WikiV2Unavailable(f"query embedding failed: {exc}") from exc

    with _connection() as conn:
        direct = hybrid_chunks(conn, subs, q_vecs, aid,
                               expansions=expansions, limit=24)
        if not direct:
            raise WikiV2Unavailable("wiki_chunks empty or no match "
                                    "(backfill pending?)")

        # ── Graph expansion (the leash: depth, priority, cap, tags) ──────
        depth = EXPAND_DEPTH.get(intent, 1)
        graph = _graph_for(aid)
        hit_pages = list(dict.fromkeys(r["page_path"] for r in direct[:10]))
        expanded: dict[str, tuple[dict, str]] = {}
        frontier = hit_pages
        for _hop in range(depth):
            nxt: list[str] = []
            for page in frontier:
                for npath, etype in graph.neighbors(page, limit=NEIGHBOR_CAP):
                    if npath in hit_pages or npath in expanded:
                        continue
                    if len(expanded) >= NEIGHBOR_CAP:
                        break
                    row = _best_chunk_for_page(conn, aid, npath, q_vecs[0])
                    if row:
                        expanded[npath] = (row, f"{page} —{etype}→ {npath}")
                        nxt.append(npath)
            frontier = nxt
            if len(expanded) >= NEIGHBOR_CAP:
                break

    # ── Rerank direct + expanded together ─────────────────────────────────
    tagged: list[tuple[dict, str | None]] = [(r, None) for r in direct]
    tagged += [(row, via) for row, via in expanded.values()]
    shapes = [_to_rerank_shape(r) for r, _ in tagged]
    via_by_id = {id(s): via for s, (_, via) in zip(shapes, tagged)}
    scored = rerank_score(question, shapes)

    # Temporal questions use the HISTORY boost table regardless of the
    # classified intent (spec §5.10) — still soft multipliers only.
    boost_key = "HISTORY" if _TEMPORAL_RE.search(question) else intent
    boosts = TYPE_BOOSTS.get(boost_key, {})
    hits: list[ChunkHit] = []
    for shape, base in scored:
        mult = boosts.get(shape.get("page_type", ""), 1.0)
        hits.append(ChunkHit(
            page_path=shape["page_path"],
            section_anchor=shape.get("section_anchor", ""),
            section_title=shape.get("section_title", ""),
            page_type=shape.get("page_type", ""),
            chunk_text=shape["chunk_text"],
            last_updated=shape.get("last_updated"),
            score=float(base) * mult,
            related_via=via_by_id.get(id(shape)),
        ))
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:top_k]
```

- [ ] **Step 4: Run tests, verify pass**

Run: `venv/bin/pytest tests/retrieval/wiki_v2/ -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/retrieval/wiki_v2/pipeline.py tests/retrieval/wiki_v2/test_pipeline.py
git commit -m "feat(wiki-v2): pipeline — leashed graph expansion, rerank, soft intent/temporal boosts (spec §5.4-5.5, 5.10)"
```

---

### Task 8: Wiring — preflight seed, `wiki_search` tool, kill switch, degradation notes

**Files:**
- Modify: `backend/preflight.py` (seed_wiki fetch + `format_wiki_for_seed`; add `bundle.degradations: list[str]` rendered into the seed)
- Modify: `backend/tools/wiki_tools.py` (`_wiki_search_handler`)
- Test: `tests/test_preflight_wiki_v2.py`, extend `tests/` wiki tool tests

**Interfaces:**
- Consumes: `pipeline.search`, `WikiV2Unavailable`, `ChunkHit` (Task 7).
- Produces:
  - `wiki_v2_enabled() -> bool` in `backend/retrieval/wiki_v2/pipeline.py`: `os.getenv("CONWO_WIKI_RETRIEVAL_V2", "on").lower() == "on"` — read at **call time**.
  - Preflight: `bundle.seed_wiki_chunks: list[ChunkHit]` (new field; old `seed_wiki` kept for fallback path), `bundle.degradations: list[str]`.
  - Seed formatter `format_wiki_chunks_for_seed(hits) -> str`: heading per chunk `### {page_title-ish} — \`{anchor}\``, related chunks get a `(related via: X —depends_on→ Y)` suffix line, headings preserved inside text.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_preflight_wiki_v2.py`:

```python
"""Preflight wiki v2 wiring — flag dispatch, fallback + visible degradation."""
from backend.retrieval.wiki_v2.pipeline import ChunkHit, WikiV2Unavailable


def _hit(path="modules/a.md", anchor="overview", via=None):
    return ChunkHit(page_path=path, section_anchor=anchor,
                    section_title=anchor.title(), page_type="module",
                    chunk_text="Section content here.", last_updated="2026-06-01",
                    score=0.9, related_via=via)


def test_flag_off_uses_keyword_path(monkeypatch):
    monkeypatch.setenv("CONWO_WIKI_RETRIEVAL_V2", "off")
    from backend.retrieval.wiki_v2 import pipeline
    assert pipeline.wiki_v2_enabled() is False


def test_flag_default_on(monkeypatch):
    monkeypatch.delenv("CONWO_WIKI_RETRIEVAL_V2", raising=False)
    from backend.retrieval.wiki_v2 import pipeline
    assert pipeline.wiki_v2_enabled() is True


def test_format_wiki_chunks_for_seed_carries_anchors_and_tags():
    from backend import preflight
    text = preflight.format_wiki_chunks_for_seed(
        [_hit(), _hit("configs/a.md", "config-comparison",
                      via="modules/a.md —config_of→ configs/a.md")])
    assert "`modules/a.md#overview`" in text
    assert "`configs/a.md#config-comparison`" in text
    assert "related via" in text


def test_unavailable_falls_back_and_notes_degradation(monkeypatch):
    from backend import preflight

    def boom(question, **kw):
        raise WikiV2Unavailable("backfill pending")
    monkeypatch.setattr(preflight, "_wiki_v2_search", boom)

    class FakePage:
        path, title, full_text = "modules/a.md", "A", "text"
        def excerpt(self, n): return "kw excerpt"
    monkeypatch.setattr(preflight.wiki_retriever, "search",
                        lambda q, top_n=3: [FakePage()])

    pages, chunks, note = preflight._fetch_seed_wiki("q", 3, intent="GENERAL",
                                                     rewrite=None)
    assert chunks == [] and pages and note and "keyword" in note.lower()
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `venv/bin/pytest tests/test_preflight_wiki_v2.py -v`
Expected: FAIL — `wiki_v2_enabled` / `format_wiki_chunks_for_seed` / `_fetch_seed_wiki` missing.

- [ ] **Step 3: Implement**

(a) In `backend/retrieval/wiki_v2/pipeline.py`, add:

```python
def wiki_v2_enabled() -> bool:
    # Default ON in code (no devops env change needed); env var is the ops
    # kill switch — CONWO_WIKI_RETRIEVAL_V2=off reverts to the keyword index.
    return os.getenv("CONWO_WIKI_RETRIEVAL_V2", "on").lower() == "on"
```

(b) In `backend/preflight.py`:

```python
from backend.retrieval.wiki_v2 import pipeline as _wiki_v2
from backend.retrieval.wiki_v2.pipeline import WikiV2Unavailable

_wiki_v2_search = _wiki_v2.search  # test seam


def _fetch_seed_wiki(question: str, top_n: int, intent: str, rewrite):
    """Returns (pages, chunk_hits, degradation_note). Exactly one of
    pages/chunk_hits is populated. Fail-open: v2 failure → keyword path."""
    if _wiki_v2.wiki_v2_enabled():
        try:
            hits = _wiki_v2_search(
                question,
                sub_queries=getattr(rewrite, "sub_queries", None),
                expansions=getattr(rewrite, "expansions", None),
                intent=intent, top_k=top_n * 3)
            return [], hits, None
        except WikiV2Unavailable as exc:
            note = (f"wiki semantic search unavailable ({exc}) — "
                    f"fell back to keyword search; results may be less complete.")
            return wiki_retriever.search(question, top_n=top_n), [], note
    return wiki_retriever.search(question, top_n=top_n), [], None


def format_wiki_chunks_for_seed(hits) -> str:
    if not hits:
        return "No relevant wiki sections found in preflight."
    parts = []
    for h in hits:
        head = f"### `{h.anchor}` — {h.section_title or h.page_path}"
        if h.related_via:
            head += f"\n_(related via: {h.related_via})_"
        parts.append(f"{head}\n\n{h.chunk_text}")
    return "\n\n---\n\n".join(parts)
```

In `PreflightBundle`, add fields:

```python
    seed_wiki_chunks: list = field(default_factory=list)  # list[ChunkHit]
    degradations: list = field(default_factory=list)      # visible seed notes
```

In `run_preflight`, replace the `bundle.seed_wiki = wiki_retriever.search(...)` line (~136):

```python
        pages, chunk_hits, note = _fetch_seed_wiki(
            _search_query, _wiki_top_n_eff,
            intent=bundle.intent_result.intent.value if bundle.intent_result else "GENERAL",
            rewrite=None)  # Phase B passes the shared RewriteResult here
        bundle.seed_wiki = pages
        bundle.seed_wiki_chunks = chunk_hits
        if note:
            bundle.degradations.append(note)
```

**Note:** the module-page loop at ~167 (`for page in bundle.seed_wiki: if page.path.startswith("modules/")`) must also consider chunk hits when the v2 path served: derive module pages as `{h.page_path for h in bundle.seed_wiki_chunks if h.page_path.startswith("modules/")}` and iterate slugs from that union so module-tagged ticket fetch keeps working on both paths.

In `build_seed_message` (~439): render `format_wiki_chunks_for_seed(bundle.seed_wiki_chunks)` when chunks are present, else the existing `format_wiki_for_seed(bundle.seed_wiki)`; and append a degradations block when non-empty:

```python
    if bundle.degradations:
        degradation_block = ("## Degradation notes\n\n"
                             + "\n".join(f"- ⚠️ {d}" for d in bundle.degradations)
                             + "\n\n---\n\n")
```

(c) In `backend/tools/wiki_tools.py`, `_wiki_search_handler` (~92):

```python
def _wiki_search_handler(inp: dict) -> dict:
    query = str(inp.get("query", "")).strip()
    if not query:
        return {"error": "query is required", "code": "missing_input"}
    top_n = min(int(inp.get("top_n", 5)), 10)

    from backend.retrieval.wiki_v2 import pipeline as _wv2
    if _wv2.wiki_v2_enabled():
        try:
            hits = _wv2.search(query, top_k=top_n)
            return {"results": [{
                "path": h.page_path, "anchor": h.anchor,
                "section": h.section_title, "type": h.page_type,
                "excerpt": h.chunk_text[:300],
                "related_via": h.related_via,
                "score": round(h.score, 4),
            } for h in hits], "engine": "v2"}
        except _wv2.WikiV2Unavailable:
            pass  # fall through to keyword engine
    pages = wiki_retriever.search(query, top_n=top_n)
    ...  # existing keyword rendering unchanged, plus "engine": "keyword-fallback"
```

- [ ] **Step 4: Run tests + full regression**

Run: `venv/bin/pytest tests/test_preflight_wiki_v2.py tests/ -q -k "preflight or wiki"`
Expected: new tests pass; existing preflight/wiki-tool tests pass (they run with the fake/keyword path since test DB has no chunks → `WikiV2Unavailable` → fallback; assert no test breaks on the added degradation note text).

- [ ] **Step 5: Commit**

```bash
git add backend/preflight.py backend/tools/wiki_tools.py backend/retrieval/wiki_v2/pipeline.py tests/test_preflight_wiki_v2.py
git commit -m "feat(wiki-v2): wire preflight + wiki_search tool — default-on flag, keyword fallback, visible degradation (spec §5.4, 5.7-5.8)"
```

---

### Task 9: Phase A regression sweep + push

**Files:** none new.

- [ ] **Step 1: Full test suite**

Run: `venv/bin/pytest tests/ -q`
Expected: no regressions beyond the 5 documented pre-existing environmental failures (PMS creds, .env reload, ingest order — see project memory).

- [ ] **Step 2: Optional live smoke (if local PG has migrations)**

```bash
CONWO_TEST_DSN="postgresql://wis_conwo@localhost:5432/wis_conwo_test" \
  venv/bin/pytest tests/test_migration_170.py -v
```

- [ ] **Step 3: Push**

```bash
git push -u bitbucket feat/wiki-retrieval-v2
```

Phase B (intelligence + verification + eval) continues on this branch — see `2026-07-07-wiki-retrieval-v2-phase-b.md`. The PR opens at the end of Phase B with eval results attached.
