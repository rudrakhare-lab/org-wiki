# Retrieval-V2 Parity Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close three correctness gaps discovered during Phase 1's final review and a follow-up user-requested code review: (1) `hybrid.py`'s SELECT silently omits `comment_count`, neutering `timeline.assign_bucket`'s substantive-resolution branch on the real SQL path; (2) `_v2_by_module` abandons v1's `ticket_module_tags` confidence-floor guarantee and never enriches rows with date/module fields, degrading `format_module_tagged_for_seed`'s output; (3) v2's `.markdown` field is a bare confidence label instead of a real evidence listing, which matters for `orchestrator.py`'s simpler prompt-building flow.

**Architecture:** Task 1 is a one-line SQL SELECT addition (column already exists — migration 040). Task 2 reuses `jira_retriever.py`'s existing `_fetch_modules_for_keys` helper (already used by `_v1_by_module`) to filter v2's semantic candidates down to genuinely-tagged tickets and enrich them. Task 3 adds a `_render_v2_markdown` helper that mirrors `query_jira_ranked.render_markdown`'s LATEST/HISTORICAL/STALE-OPEN section structure, reusing the existing `format_ticket_line` formatter, keyed off each ticket's own `bucket` tag instead of v1's bucket column.

**Tech Stack:** Python 3.11, psycopg 3, pytest. No new dependencies, no schema changes (comment_count column already exists).

## Global Constraints

- No schema change — `comment_count` already exists on `tickets` (migration 040).
- No new dependencies.
- Task 1 touches `backend/retrieval/v2/hybrid.py` — this file was Phase 1's reviewed, completed work; the change here is additive (one column in a SELECT list) and must not alter any other behavior.
- Tasks 2 and 3 touch `backend/jira_retriever.py` only — do not touch `backend/preflight.py` (correct, reads `buckets` directly) or `backend/tools/jira_tools.py` (correct, reads `buckets` directly — verified in review that its `include_stale` param has been inert since v1, not a v2 regression).
- Reuse existing helpers — do not duplicate `_fetch_modules_for_keys`, `_date_str`, or `format_ticket_line`.
- `_BUCKET_TOP_KEY` mapping (already defined in `jira_retriever.py` at module level from the prior fix) is the single source of truth for lowercase-bucket → uppercase-top-key translation. Reuse it; do not redefine.
- All new callable surfaces have unit tests. Existing tests must not regress.

---

### Task 1: hybrid.py SELECT — add comment_count column

**Files:**
- Modify: `backend/retrieval/v2/hybrid.py:46-49`
- Test: `tests/retrieval/v2/test_hybrid.py` (extend)

**Interfaces:**
- Consumes: `tickets.comment_count` column (exists, migration 040).
- Produces: every candidate dict returned by `hybrid_search()` now includes a `comment_count` key, which `timeline.assign_bucket`'s substantive-resolution branch (`row.get("comment_count")`) can actually read on the real SQL path (previously always `None` → branch was dead code in production).

- [ ] **Step 1: Write the failing test**

Append to `tests/retrieval/v2/test_hybrid.py`:

```python
def test_base_sql_selects_comment_count():
    """comment_count must be selected — timeline.assign_bucket's substantive-
    resolution branch (resolved + comment_count>=2 -> latest) reads it, but
    was silently always None because this column was missing from the SELECT."""
    from backend.retrieval.v2.hybrid import _BASE_SQL
    assert "comment_count" in _BASE_SQL


def test_hybrid_search_passes_through_comment_count():
    """End-to-end: a fake row with comment_count reaches the returned candidate
    dict, and apply_timeline's substantive-resolution override actually fires."""
    from datetime import datetime, timezone, timedelta
    from backend.retrieval.v2 import hybrid

    now = datetime.now(timezone.utc)
    fake_rows = [
        {"key": "TS-old-but-substantive", "fused_score": 0.03,
         "updated_at": now - timedelta(days=800),
         "resolved_at": now - timedelta(days=800),
         "status_category": "done", "comment_count": 5},
    ]

    class FakeCur:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def execute(self, *a, **k): pass
        def fetchall(self): return fake_rows
    class FakeConn:
        def cursor(self, **k): return FakeCur()

    out = hybrid.hybrid_search(FakeConn(), ["q"], [[0.0] * 768], {}, limit=5)
    assert out[0]["comment_count"] == 5
    # Substantive-resolution override: resolved + comment_count>=2 -> latest,
    # even though updated_at/resolved_at are 800 days old.
    assert out[0]["bucket"] == "latest"
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `venv/bin/pytest tests/retrieval/v2/test_hybrid.py -v -k comment_count`
Expected: `test_base_sql_selects_comment_count` fails (`comment_count` not in `_BASE_SQL`). `test_hybrid_search_passes_through_comment_count` fails on the `bucket == "latest"` assertion (would be `"historical"` today, since `comment_count` is silently dropped before reaching `assign_bucket` — actually verify: since the fake row already includes `comment_count` in the dict passed to `fetchall()`, and `hybrid_search`'s code does `{"key": ..., "fused_score": ..., **r}` — it WOULD pass through today already, since this is a fake cursor test, not real Postgres. The real bug only manifests against the live `_BASE_SQL` string used by real Postgres. So this second test is a behavioral characterization test (proves apply_timeline's branch works when the field IS present) — it will actually pass even before Task 1's fix, since the fake cursor bypasses the real SELECT. Only `test_base_sql_selects_comment_count` should fail pre-fix.

- [ ] **Step 3: Add comment_count to the SELECT**

Edit `backend/retrieval/v2/hybrid.py`. Change lines 46-49 from:

```python
SELECT t.key, t.summary, t.description_text, t.comments_text,
       t.status_category, t.priority, t.updated_at, t.resolved_at,
       t.functional_area, t.links_json,
       f.rrf AS fused_score
```

to:

```python
SELECT t.key, t.summary, t.description_text, t.comments_text,
       t.status_category, t.priority, t.updated_at, t.resolved_at,
       t.functional_area, t.links_json, t.comment_count,
       f.rrf AS fused_score
```

- [ ] **Step 4: Run tests, verify both pass**

Run: `venv/bin/pytest tests/retrieval/v2/test_hybrid.py -v`
Expected: all tests pass (existing + 2 new).

- [ ] **Step 5: Run full retrieval-v2 sweep**

Run: `venv/bin/pytest tests/retrieval/v2/ -v --ignore=tests/retrieval/v2/test_e2e_integration.py`
Expected: all pass — no regression from the added column (existing tests never asserted the SELECT list was closed to exactly those columns).

- [ ] **Step 6: Commit**

```bash
git add backend/retrieval/v2/hybrid.py tests/retrieval/v2/test_hybrid.py
git commit -m "$(cat <<'EOF'
fix(retrieval-v2): select comment_count — unblocks substantive-resolution bucket rule

timeline.assign_bucket()'s substantive-resolution override (resolved_at
IS NOT NULL AND comment_count >= 2 -> latest) has been dead code on the
real SQL path since Phase 1 shipped: hybrid.py's SELECT never included
comment_count, so row.get("comment_count") was always None in production
(only unit tests, which construct rows manually, ever exercised this
branch). comment_count already exists on tickets (migration 040) — no
schema change, one column added to an existing SELECT.

Found while investigating a follow-up markdown-rendering fix that also
needs comment_count (format_ticket_line reads it).
EOF
)"
```

---

### Task 2: `_v2_by_module` — confidence-floor filtering + row enrichment

**Files:**
- Modify: `backend/jira_retriever.py:97-99`
- Test: `tests/test_jira_retriever_v2_search.py` (extend — this file already exists from the prior `_v2_search` fix)

**Interfaces:**
- Consumes:
  - `backend.retrieval.v2.pipeline.by_module(module_slug, query, limit) -> list[dict]` (existing, unmodified).
  - `_fetch_modules_for_keys(conn, keys, confidence_floor) -> dict[str, list[dict]]` (existing, defined at `backend/jira_retriever.py:288-312`).
  - `_date_str(value) -> str | None` (existing, defined at `backend/jira_retriever.py:41-47`).
- Produces: `_v2_by_module` now returns only tickets genuinely tagged to `module_slug` at or above `confidence_floor`, each enriched with `modules`, `module_confidence`, `updated`, `resolved` — matching `_v1_by_module`'s output shape.

- [ ] **Step 1: Write the failing tests**

Read the existing test file first to match its style: `cat tests/test_jira_retriever_v2_search.py`.

Append to `tests/test_jira_retriever_v2_search.py`:

```python
"""_v2_by_module tests — confidence-floor parity with _v1_by_module."""
from unittest.mock import patch


def _fake_candidate(key, **overrides):
    base = {
        "key": key, "summary": "s", "status_category": "done",
        "priority": "P2", "bucket": "latest",
        "updated_at": None, "resolved_at": None,
    }
    base.update(overrides)
    return base


def test_v2_by_module_excludes_untagged_tickets(monkeypatch):
    """A semantically-similar but untagged ticket must NOT appear in the
    result — mirrors _v1_by_module's ticket_module_tags JOIN guarantee."""
    from backend import jira_retriever

    candidates = [_fake_candidate("TS-1"), _fake_candidate("TS-2")]
    monkeypatch.setattr(
        "backend.retrieval.v2.pipeline.by_module",
        lambda module_slug, query, limit: candidates,
    )

    class FakeConn:
        def __enter__(self): return self
        def __exit__(self, *a): pass

    with patch.object(jira_retriever.db, "connection", return_value=FakeConn()):
        with patch.object(
            jira_retriever, "_fetch_modules_for_keys",
            return_value={"TS-1": [{"slug": "desk-management", "confidence": 0.8}]},
            # TS-2 absent -> not tagged to any module at the required floor
        ):
            out = jira_retriever._v2_by_module("desk-management", "booking", limit=5)

    keys = [t["key"] for t in out]
    assert keys == ["TS-1"]


def test_v2_by_module_enriches_with_module_confidence_and_modules(monkeypatch):
    from backend import jira_retriever

    candidates = [_fake_candidate("TS-1")]
    monkeypatch.setattr(
        "backend.retrieval.v2.pipeline.by_module",
        lambda module_slug, query, limit: candidates,
    )

    class FakeConn:
        def __enter__(self): return self
        def __exit__(self, *a): pass

    with patch.object(jira_retriever.db, "connection", return_value=FakeConn()):
        with patch.object(
            jira_retriever, "_fetch_modules_for_keys",
            return_value={"TS-1": [{"slug": "desk-management", "confidence": 0.9}]},
        ):
            out = jira_retriever._v2_by_module("desk-management", "booking", limit=5)

    assert out[0]["module_confidence"] == 0.9
    assert out[0]["modules"] == [{"slug": "desk-management", "confidence": 0.9}]
    assert "updated" in out[0]
    assert "resolved" in out[0]


def test_v2_by_module_respects_limit_after_filtering(monkeypatch):
    from backend import jira_retriever

    candidates = [_fake_candidate(f"TS-{i}") for i in range(10)]
    monkeypatch.setattr(
        "backend.retrieval.v2.pipeline.by_module",
        lambda module_slug, query, limit: candidates,
    )

    class FakeConn:
        def __enter__(self): return self
        def __exit__(self, *a): pass

    tagged = {f"TS-{i}": [{"slug": "desk-management", "confidence": 0.7}] for i in range(10)}
    with patch.object(jira_retriever.db, "connection", return_value=FakeConn()):
        with patch.object(jira_retriever, "_fetch_modules_for_keys", return_value=tagged):
            out = jira_retriever._v2_by_module("desk-management", "booking", limit=3)

    assert len(out) == 3


def test_v2_by_module_empty_candidates_returns_empty(monkeypatch):
    from backend import jira_retriever
    monkeypatch.setattr(
        "backend.retrieval.v2.pipeline.by_module",
        lambda module_slug, query, limit: [],
    )
    out = jira_retriever._v2_by_module("desk-management", "booking", limit=5)
    assert out == []
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `venv/bin/pytest tests/test_jira_retriever_v2_search.py -v -k by_module`
Expected: fails — `_v2_by_module` currently returns all candidates unfiltered, un-enriched (`test_v2_by_module_excludes_untagged_tickets` fails because `TS-2` is still present; the enrichment test fails on missing `module_confidence` key).

- [ ] **Step 3: Implement the fix**

Edit `backend/jira_retriever.py`. Replace lines 97-99 (`def _v2_by_module` through its `return`) with:

```python
def _v2_by_module(module_slug: str, query: str, limit: int = 5,
                   confidence_floor: float = 0.5, **kwargs):
    """Query-aware, module-scoped v2 retrieval.

    Mirrors _v1_by_module's guarantee: only tickets genuinely tagged to
    `module_slug` in ticket_module_tags at or above `confidence_floor` are
    returned — v2's underlying pipeline.by_module() does pure semantic
    proximity-to-slug-name matching with no such guarantee on its own, so
    we over-fetch candidates and filter+enrich here using the same
    _fetch_modules_for_keys helper _v1_by_module already relies on.
    """
    from backend.retrieval.v2.pipeline import by_module as _bm
    overfetch = max(limit * 4, 20)
    candidates = _bm(module_slug, query, limit=overfetch)
    if not candidates:
        return []

    with db.connection() as conn:
        modules_map = _fetch_modules_for_keys(
            conn, [c["key"] for c in candidates], confidence_floor=confidence_floor
        )

    out = []
    for c in candidates:
        mods = modules_map.get(c["key"], [])
        match = next((m for m in mods if m["slug"] == module_slug), None)
        if not match:
            continue
        c["modules"] = mods
        c["module_confidence"] = match["confidence"]
        if "updated" not in c:
            c["updated"] = _date_str(c.get("updated_at")) or "?"
        if "resolved" not in c:
            c["resolved"] = _date_str(c.get("resolved_at"))
        out.append(c)
        if len(out) >= limit:
            break
    return out
```

- [ ] **Step 4: Run tests, verify all pass**

Run: `venv/bin/pytest tests/test_jira_retriever_v2_search.py -v`
Expected: all pass (existing 9 from the prior fix + 4 new).

- [ ] **Step 5: Run broader regression check**

Run: `venv/bin/pytest tests/retrieval/v2/ tests/test_jira_retriever_v2_search.py -q`
Expected: all pass, no regressions.

- [ ] **Step 6: Commit**

```bash
git add backend/jira_retriever.py tests/test_jira_retriever_v2_search.py
git commit -m "$(cat <<'EOF'
fix(retrieval-v2): _v2_by_module confidence-floor parity + row enrichment

_v2_by_module previously called pipeline.by_module() and returned its raw
semantic-proximity results unfiltered and unenriched — unlike
_v1_by_module, which JOINs ticket_module_tags with a confidence floor
(only genuinely-tagged tickets qualify) and enriches every row with
modules/module_confidence/updated/resolved.

Fix: over-fetch v2 semantic candidates, then filter+enrich via the same
_fetch_modules_for_keys helper _v1_by_module already uses. A ticket
absent from ticket_module_tags (or below the confidence floor) is now
excluded — matching v1's guarantee that "module-tagged" tickets shown to
the LLM are actually tagged to that module.

Without this fix, preflight.format_module_tagged_for_seed() rendered
every v2 module-scoped row as "updated ?" (missing updated/resolved
fields) and could surface semantically-similar-but-unrelated tickets
under a module heading.
EOF
)"
```

---

### Task 3: v2 markdown rendering — `_render_v2_markdown`

**Files:**
- Modify: `backend/jira_retriever.py` (add `_render_v2_markdown`, wire into `_v2_search`)
- Test: `tests/test_jira_retriever_v2_search.py` (extend)

**Interfaces:**
- Consumes:
  - `query_jira_ranked.format_ticket_line(row) -> str` (existing, already imported by `jira_retriever.py`; needs `row["comment_count"]`, available after Task 1).
  - `_BUCKET_TOP_KEY` (existing module-level dict in `jira_retriever.py`).
- Produces: `_v2_search`'s `"markdown"` field is now a real bucketed evidence listing (mirrors `query_jira_ranked.render_markdown`'s structure) instead of a bare gate confidence label. This is consumed by `orchestrator.py:390,481` (`jira_context = jira_result["markdown"]`) — the only place `.markdown` content reaches the LLM as prose.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_jira_retriever_v2_search.py`:

```python
def _md_ticket(key, bucket, **overrides):
    base = {
        "key": key, "bucket": bucket, "summary": "does a thing",
        "status_category": "done", "priority": "P2",
        "updated": "2026-06-01", "resolved": None, "comment_count": 1,
    }
    base.update(overrides)
    return base


def test_render_v2_markdown_always_shows_latest_and_historical():
    from backend.jira_retriever import _render_v2_markdown
    tickets = [_md_ticket("TS-1", "latest"), _md_ticket("TS-2", "historical")]
    md = _render_v2_markdown(tickets, confidence="High", message="strong evidence")
    assert "**Latest evidence**" in md
    assert "**Historical evidence**" in md
    assert "TS-1" in md
    assert "TS-2" in md


def test_render_v2_markdown_omits_stale_section_by_default():
    from backend.jira_retriever import _render_v2_markdown
    tickets = [_md_ticket("TS-3", "stale_open")]
    md = _render_v2_markdown(tickets, confidence="Low", message="weak")
    assert "Stale-open" not in md


def test_render_v2_markdown_includes_stale_section_when_requested():
    from backend.jira_retriever import _render_v2_markdown
    tickets = [_md_ticket("TS-3", "stale_open")]
    md = _render_v2_markdown(tickets, confidence="Low", message="weak", include_stale=True)
    assert "**Stale-open**" in md
    assert "TS-3" in md


def test_render_v2_markdown_includes_confidence_header():
    from backend.jira_retriever import _render_v2_markdown
    md = _render_v2_markdown([], confidence="Medium", message="moderate evidence")
    assert "Medium" in md
    assert "moderate evidence" in md


def test_v2_search_markdown_field_uses_renderer(monkeypatch):
    """_v2_search's returned dict must use _render_v2_markdown, not the bare
    gate message, for its 'markdown' field."""
    from backend import jira_retriever
    from dataclasses import dataclass, field

    @dataclass
    class _FakeResult:
        tickets: list
        confidence: str = "High"
        abstain: bool = False
        message: str = "strong evidence"
        diagnostics: dict = field(default_factory=dict)

    fake_result = _FakeResult(tickets=[
        {"key": "TS-1", "summary": "s", "status_category": "done", "priority": "P1",
         "bucket": "latest", "updated_at": None, "resolved_at": None, "comment_count": 0},
    ])
    monkeypatch.setattr(
        "backend.retrieval.v2.pipeline.search",
        lambda question, **kw: fake_result,
    )
    out = jira_retriever._v2_search("some question")
    assert "**Latest evidence**" in out["markdown"]
    assert out["markdown"] != fake_result.message
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `venv/bin/pytest tests/test_jira_retriever_v2_search.py -v -k render_v2_markdown or markdown_field`
Expected: fails — `_render_v2_markdown` doesn't exist yet; `_v2_search`'s markdown field is still `result.message`.

- [ ] **Step 3: Implement `_render_v2_markdown` and wire it into `_v2_search`**

Edit `backend/jira_retriever.py`. Add the import for `format_ticket_line` — extend the existing import line near the top:

```python
from query_jira_ranked import fetch_ranked, render_markdown, format_ticket_line  # noqa: E402
```

Add the new function, placed just above `_v2_search`:

```python
def _render_v2_markdown(tickets: list[dict], *, confidence: str, message: str,
                         include_stale: bool = False) -> str:
    """Mirror query_jira_ranked.render_markdown()'s LATEST/HISTORICAL/
    STALE-OPEN section structure for v2 tickets, keyed off each ticket's own
    lowercase `bucket` tag (set by timeline.apply_timeline() upstream)
    instead of v1's bucket column. This is the only place v2's evidence
    reaches the LLM as prose — orchestrator.py's jira_context = jira_result
    reads this field directly.
    """
    grouped: dict[str, list[dict]] = {"LATEST": [], "HISTORICAL": [], "STALE-OPEN": []}
    for t in tickets:
        top_key = _BUCKET_TOP_KEY.get(t.get("bucket") or "latest", "LATEST")
        grouped[top_key].append(t)

    out = [
        f"### V2 ranked Jira evidence (confidence: {confidence})",
        f"_{message}_",
        "",
        f"_Buckets: LATEST={len(grouped['LATEST'])} · "
        f"HISTORICAL={len(grouped['HISTORICAL'])} · "
        f"STALE-OPEN={len(grouped['STALE-OPEN'])}_",
        "",
        "**Latest evidence** (current behavior, last ~6 months):",
    ]
    if grouped["LATEST"]:
        out.extend(format_ticket_line(r) for r in grouped["LATEST"])
    else:
        out.append("- —")
    out.append("")

    out.append("**Historical evidence** (older context, may be stale):")
    if grouped["HISTORICAL"]:
        out.extend(format_ticket_line(r) for r in grouped["HISTORICAL"])
    else:
        out.append("- —")
    out.append("")

    if include_stale:
        out.append("**Stale-open** (open but no activity >180 days — usually noise):")
        if grouped["STALE-OPEN"]:
            out.extend(format_ticket_line(r) for r in grouped["STALE-OPEN"])
        else:
            out.append("- —")
        out.append("")

    return "\n".join(out)
```

Then edit `_v2_search`'s signature and return statement. Change the signature from:

```python
def _v2_search(question: str, *, functional_area: str | None = None,
               limit: int = 10, **kwargs):
```

to:

```python
def _v2_search(question: str, *, functional_area: str | None = None,
               limit: int = 10, include_stale: bool = False, **kwargs):
```

And change the final `return` statement from:

```python
    return {
        "keywords": extract_keywords(question),
        "markdown": result.message,
        "rows": tickets,
        "buckets": buckets,
    }
```

to:

```python
    return {
        "keywords": extract_keywords(question),
        "markdown": _render_v2_markdown(
            tickets, confidence=result.confidence, message=result.message,
            include_stale=include_stale,
        ),
        "rows": tickets,
        "buckets": buckets,
    }
```

- [ ] **Step 4: Run tests, verify all pass**

Run: `venv/bin/pytest tests/test_jira_retriever_v2_search.py -v`
Expected: all pass (existing 13 from Tasks prior + 5 new = 18).

- [ ] **Step 5: Run full regression sweep**

Run: `venv/bin/pytest tests/retrieval/v2/ tests/test_jira_retriever_v2_search.py -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/jira_retriever.py tests/test_jira_retriever_v2_search.py
git commit -m "$(cat <<'EOF'
fix(retrieval-v2): render real evidence markdown for v2 (was bare confidence label)

_v2_search's "markdown" field was gate.py's short confidence message
("strong, agreeing evidence") — the only consumer that reads this field
as prose, orchestrator.py's jira_context = jira_result["markdown"] flow,
showed zero ticket-level evidence in v2 mode.

New _render_v2_markdown() mirrors query_jira_ranked.render_markdown()'s
LATEST/HISTORICAL/STALE-OPEN section structure, reusing the existing
format_ticket_line() formatter, keyed off each ticket's own `bucket` tag.
STALE-OPEN section is included only when include_stale=True, matching
v1's semantics. (Note: include_stale has no effect on jira_tools.py's
_jira_search_ranked_handler or preflight's seed path — both already read
`buckets` directly, unaffected by this markdown-only field. That handler's
include_stale parameter has been inert since v1 for the same reason.)

Requires Task 1 (comment_count in hybrid.py's SELECT) since
format_ticket_line() reads row["comment_count"].
EOF
)"
```

---

## Post-implementation

- Run the full test suite once more: `venv/bin/pytest tests/ -q` and confirm no regressions beyond the known pre-existing environmental failures.
- This plan's 3 tasks are a follow-up to the `feat/retrieval-v2-timeline` branch (already pushed as PR #38-candidate). Commit these on the same branch, or open as a small separate PR — controller's call at execution time based on whether the original PR is still open for review.
