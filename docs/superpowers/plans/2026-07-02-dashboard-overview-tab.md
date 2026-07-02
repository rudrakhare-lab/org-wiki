# Dashboard Overview Tab + Quality Judge Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild Conwo's `/dashboard` as a tabbed shell (Overview built now, 6 tabs stubbed), add an async LLM-judge quality-scoring pipeline, and link the existing human-feedback loop to `trace_id` so Escalation Rate can be computed per time range/agent.

**Architecture:** Two new backend capabilities (a `quality_judgments` Postgres table + `backend/quality_judge.py` scored by Haiku 4.5, fired via FastAPI `BackgroundTasks` after each successful query) feed two new read-only endpoints in `backend/trace_api.py`, consumed by a restructured `frontend/src/app/features/traces/dashboard.ts`. A small trace_id↔feedback linkage (`backend/feedback_service.py` + 5 call sites) makes Escalation Rate computable for the first time.

**Tech Stack:** FastAPI, Postgres (psycopg, existing `backend.db` pool), Anthropic SDK (`claude-haiku-4-5-20251001`), Angular 17 (standalone components, signals), ng2-charts.

## Global Constraints

- Every new Postgres migration must be idempotent (`CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`) per `backend/db.py`'s `init_db()` contract — it re-runs all migrations on every startup.
- All new `trace_store`/`quality_judge` code must be **fail-open**: a failure must never raise out to the caller or affect the user-facing response. Match `backend/trace_store.py`'s existing try/except-and-log discipline.
- DB-touching tests run against the `wis_conwo_test` database via the session-scoped `_pg_test_db` fixture in `tests/conftest.py` — never assume a fresh empty DB without using the `clean_db` fixture for isolation.
- No new endpoint may break `frontend/src/app/features/traces/dashboard.ts`'s **existing** four API calls (`traceOverview`, `traceTools`, `traceErrors`, `traceCost`) or their backing `trace_api.py` routes — this plan is additive only.
- Existing chart/table code being relocated off the Overview tab (Cost-by-Day, Mode-Split, Top Tools, Recent Errors) must **not be deleted** — kept in `dashboard.ts` as inert (still-fetched, not-yet-rendered) code for a later tab to re-mount, per the approved design spec §9.

---

### Task 1: `quality_judgments` table migration

**Files:**
- Create: `migrations/postgres/160_quality_judgments.sql`
- Modify: `tests/conftest.py:16-27` (add `quality_judgments` to `_APP_TABLES`)
- Test: `tests/test_migration_160.py`

**Interfaces:**
- Produces: table `quality_judgments(trace_id PK/FK, overall_score, groundedness_score, completeness_score, confidence_calibration_score, source_usage_score, rationale, judge_model, judged_at)` — consumed by Task 5 (`quality_judge.py` writes) and Task 7 (`trace_api.py` reads).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_migration_160.py
"""Verifies the 160_quality_judgments migration created the expected schema."""
from backend import db


def test_quality_judgments_table_exists(clean_db):
    with db.connection() as conn:
        row = conn.execute("SELECT to_regclass('quality_judgments')").fetchone()
    assert row[0] is not None


def test_quality_judgments_columns(clean_db):
    with db.connection() as conn:
        cols = {
            r[0]
            for r in conn.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'quality_judgments'"
            ).fetchall()
        }
    assert cols == {
        "trace_id", "overall_score", "groundedness_score", "completeness_score",
        "confidence_calibration_score", "source_usage_score", "rationale",
        "judge_model", "judged_at",
    }


def test_quality_judgments_fk_cascades_on_session_delete(clean_db):
    from backend import trace_store
    trace_store.start_session("t-mig-160", mode="api")
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO quality_judgments "
            "(trace_id, overall_score, judge_model, judged_at) "
            "VALUES (%s, %s, %s, %s)",
            ("t-mig-160", 80.0, "claude-haiku-4-5-20251001", "2026-07-02T00:00:00Z"),
        )
        conn.execute("DELETE FROM trace_sessions WHERE trace_id = %s", ("t-mig-160",))
        row = conn.execute(
            "SELECT 1 FROM quality_judgments WHERE trace_id = %s", ("t-mig-160",)
        ).fetchone()
    assert row is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/pytest tests/test_migration_160.py -v`
Expected: FAIL — `to_regclass('quality_judgments')` returns `None` (table doesn't exist yet).

- [ ] **Step 3: Write the migration**

```sql
-- migrations/postgres/160_quality_judgments.sql
-- LLM-judge quality scores for completed query traces (Dashboard Overview,
-- design spec 2026-07-02-dashboard-overview-tab-design.md §6). One row per
-- trace, written async after end_session by backend/quality_judge.py.
CREATE TABLE IF NOT EXISTS quality_judgments (
    trace_id                     TEXT PRIMARY KEY
        REFERENCES trace_sessions(trace_id) ON DELETE CASCADE,
    overall_score                DOUBLE PRECISION NOT NULL,
    groundedness_score           DOUBLE PRECISION,
    completeness_score           DOUBLE PRECISION,
    confidence_calibration_score DOUBLE PRECISION,
    source_usage_score           DOUBLE PRECISION,
    rationale                    TEXT,
    judge_model                  TEXT NOT NULL,
    judged_at                    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_quality_judgments_judged_at ON quality_judgments(judged_at);
```

- [ ] **Step 4: Add the table to the test-isolation truncate list**

In `tests/conftest.py`, the `_APP_TABLES` list (lines 16-27):

```python
_APP_TABLES = [
    "tokens", "users",
    "messages", "conversations",
    "quality_judgments", "trace_events", "trace_metrics", "trace_sessions",
    "ticket_module_tags", "ticket_classifications", "sync_runs",
    "custom_field_map", "tickets",
    "jira_links", "module_links", "dependencies", "configs",
    "rate_limits",
    "agent_access",
    "ingest_batch_items",
    "ingest_batches",
]
```

(Only change: `"quality_judgments",` added before `"trace_events"` — must precede `trace_sessions` in the TRUNCATE statement's table list since it has an FK to it, though `TRUNCATE ... CASCADE` would also catch it transitively; listing it explicitly matches the file's existing style of listing every FK-child table.)

- [ ] **Step 5: Run test to verify it passes**

Run: `venv/bin/pytest tests/test_migration_160.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add migrations/postgres/160_quality_judgments.sql tests/conftest.py tests/test_migration_160.py
git commit -m "feat(dashboard): add quality_judgments table migration"
```

---

### Task 2: Trace↔feedback linkage in `feedback_service.py` + `scripts/log_answer.py`

**Files:**
- Modify: `backend/feedback_service.py:15,42-78` (import + `log_answer()` signature; add `find_answer_by_trace_id()` and `load_all_feedback()`)
- Modify: `scripts/log_answer.py:111-132` (`cmd_log()` gains `--trace-id`)
- Test: `tests/test_feedback_service_trace_linkage.py`

**Interfaces:**
- Produces: `feedback_service.log_answer(..., trace_id: str | None = None) -> str` (new optional kwarg, backward compatible — every existing call site keeps working unchanged until Tasks 3/4 add the kwarg).
- Produces: `feedback_service.find_answer_by_trace_id(trace_id: str) -> dict | None`.
- Produces: `feedback_service.load_all_feedback() -> list[dict]` (every feedback record, any status, most-recent-first).
- Consumes (Task 7): `find_answer_by_trace_id` is used inside `quality_judge.py` (Task 5); `load_all_feedback` is used inside `trace_api.py`'s new summary endpoint (Task 7).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_feedback_service_trace_linkage.py
"""trace_id linkage between ANSWER_LOG records and trace_sessions (design spec
2026-07-02-dashboard-overview-tab-design.md §7) — enables Escalation Rate and
the quality judge to resolve a trace's answer text/sources."""
import json


def test_log_answer_stores_trace_id(tmp_path, monkeypatch):
    from backend import feedback_service
    answer_log = tmp_path / "answer_log.jsonl"
    monkeypatch.setattr(feedback_service, "ANSWER_LOG", answer_log)

    answer_id = feedback_service.log_answer(
        question="q", answer_text="a", confidence="High", trace_id="trace-abc",
    )

    lines = answer_log.read_text().strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["answer_id"] == answer_id
    assert record["trace_id"] == "trace-abc"


def test_log_answer_trace_id_defaults_to_none(tmp_path, monkeypatch):
    from backend import feedback_service
    answer_log = tmp_path / "answer_log.jsonl"
    monkeypatch.setattr(feedback_service, "ANSWER_LOG", answer_log)

    feedback_service.log_answer(question="q", answer_text="a", confidence="High")

    record = json.loads(answer_log.read_text().strip())
    assert record["trace_id"] is None


def test_find_answer_by_trace_id_returns_matching_record(tmp_path, monkeypatch):
    from backend import feedback_service
    answer_log = tmp_path / "answer_log.jsonl"
    monkeypatch.setattr(feedback_service, "ANSWER_LOG", answer_log)
    feedback_service.log_answer(question="q1", answer_text="a1", confidence="Low", trace_id="t1")
    feedback_service.log_answer(question="q2", answer_text="a2", confidence="High", trace_id="t2")

    found = feedback_service.find_answer_by_trace_id("t2")

    assert found is not None
    assert found["question"] == "q2"
    assert found["trace_id"] == "t2"


def test_find_answer_by_trace_id_returns_none_when_missing(tmp_path, monkeypatch):
    from backend import feedback_service
    answer_log = tmp_path / "answer_log.jsonl"
    monkeypatch.setattr(feedback_service, "ANSWER_LOG", answer_log)
    feedback_service.log_answer(question="q1", answer_text="a1", confidence="Low", trace_id="t1")

    assert feedback_service.find_answer_by_trace_id("does-not-exist") is None


def test_load_all_feedback_returns_every_status(tmp_path, monkeypatch):
    from backend import feedback_service
    # Isolate BOTH stores: record_feedback() reads feedback_service.ANSWER_LOG
    # at call time to auto-link the answer_log record — leaving it unpatched
    # would read the real (possibly huge) production file.
    monkeypatch.setattr(feedback_service, "ANSWER_LOG", tmp_path / "answer_log.jsonl")
    monkeypatch.setattr(feedback_service, "FEEDBACK_LOG", tmp_path / "answer_feedback.jsonl")
    feedback_service.record_feedback(
        answer_id="a1", question="q1", score=2, label="wrong",
    )
    feedback_service.record_feedback(
        answer_id="a2", question="q2", score=5, label="correct",
    )

    records = feedback_service.load_all_feedback()

    assert len(records) == 2
    assert {r["answer_id"] for r in records} == {"a1", "a2"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/test_feedback_service_trace_linkage.py -v`
Expected: FAIL — `log_answer() got an unexpected keyword argument 'trace_id'`, and `AttributeError: module 'feedback_service' has no attribute 'find_answer_by_trace_id'`.

- [ ] **Step 3: Implement in `backend/feedback_service.py`**

Change the import line (currently line 15):

```python
from log_answer import cmd_log, make_answer_id, utc_now as _la_utc_now, append_record as _la_append
```

to:

```python
from log_answer import (
    cmd_log,
    make_answer_id,
    utc_now as _la_utc_now,
    append_record as _la_append,
    load_records as _la_load,
)
```

Change `log_answer()` (currently lines 42-78) to add the `trace_id` parameter and store it:

```python
def log_answer(
    question: str,
    answer_text: str,
    confidence: str,
    wiki_pages: list[str] | None = None,
    jira_keys: list[str] | None = None,
    pms_configs: list[str] | None = None,
    retrieval_notes: str = "",
    answer_id: str | None = None,
    created_at: str | None = None,
    agent_id: str = "conwo",
    trace_id: str | None = None,
) -> str:
    """Log an answer record and return the answer_id.

    If `answer_id` and `created_at` are provided (e.g. from prepare_answer_id),
    use them verbatim — useful when the answer_text was post-processed after
    id computation. Otherwise compute fresh.

    trace_id links this record back to trace_sessions (design spec
    2026-07-02-dashboard-overview-tab-design.md §7) so Escalation Rate and the
    quality judge can resolve a trace's answer text/sources. None for records
    logged outside a traced request (e.g. the CLI wiki-maintainer workflow).
    """
    if answer_id is None or created_at is None:
        answer_id, created_at = prepare_answer_id(question, answer_text)
    record = {
        "answer_id": answer_id,
        "created_at": created_at,
        "question": question,
        "answer_text": answer_text,
        "confidence": confidence,
        "sources": {
            "wiki": list(wiki_pages or []),
            "jira": list(jira_keys or []),
            "pms": list(pms_configs or []),
        },
        "retrieval_notes": retrieval_notes,
        "agent_id": agent_id,
        "trace_id": trace_id,
    }
    ANSWER_LOG.parent.mkdir(parents=True, exist_ok=True)
    _la_append(ANSWER_LOG, record)
    return answer_id


def find_answer_by_trace_id(trace_id: str) -> dict[str, Any] | None:
    """Return the most recent ANSWER_LOG record linked to trace_id, or None.

    Used by quality_judge.judge_trace() (Task 5) to resolve the answer text
    and cited sources for a completed trace. O(n) linear scan of the JSONL
    file — matches record_feedback.py's existing lookup_answer_log() pattern;
    acceptable since this runs async in the background, never on the request
    path.
    """
    for record in reversed(_la_load(ANSWER_LOG)):
        if record.get("trace_id") == trace_id:
            return record
    return None


def load_all_feedback() -> list[dict[str, Any]]:
    """Return every feedback record (all statuses), most recent first.

    Used by trace_api.py's dashboard summary endpoint (Task 7) to compute
    Escalation Rate — unlike list_feedback(), this is not filtered to
    status='pending' and has no limit.
    """
    return sorted(_fb_load(FEEDBACK_LOG), key=lambda r: r.get("created_at", ""), reverse=True)
```

Add the `Any` import at the top of the file if not already present — check the existing `from typing import Any` import; `feedback_service.py` currently has no typing import beyond what's inline, so add:

```python
from typing import Any
```

right after the existing `from types import SimpleNamespace` import.

- [ ] **Step 4: Add `--trace-id` to `scripts/log_answer.py`'s CLI path (schema parity)**

In `scripts/log_answer.py`, the `log_cmd` argument block (currently lines 40-68), add after `--retrieval-notes`:

```python
    log_cmd.add_argument(
        "--trace-id",
        default="",
        help="Optional: trace_id linking this answer to a traced /query request",
    )
```

In `cmd_log()` (currently lines 111-132), add `trace_id` to the record dict:

```python
def cmd_log(args: argparse.Namespace) -> int:
    created_at = utc_now()
    answer_id = make_answer_id(args.question, args.answer_text, created_at)
    record = {
        "answer_id": answer_id,
        "created_at": created_at,
        "question": args.question,
        "answer_text": args.answer_text,
        "confidence": args.confidence,
        "sources": {
            "wiki": split_csv(args.wiki),
            "jira": split_csv(args.jira),
            "pms": split_csv(args.pms),
        },
        "retrieval_notes": args.retrieval_notes,
        "trace_id": args.trace_id or None,
    }
    append_record(args.store, record)
    if args.quiet:
        print(answer_id)
    else:
        print(f"Logged answer {answer_id} → {args.store}")
    return 0
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_feedback_service_trace_linkage.py -v`
Expected: PASS (5 tests)

- [ ] **Step 6: Run the full existing feedback/orchestrator suite to check for regressions**

Run: `venv/bin/pytest tests/test_orchestrator.py tests/test_agent_scoping.py -v`
Expected: PASS — `log_answer` is called positionally/by-kwarg everywhere else without `trace_id`, and it now defaults to `None`, so no existing call site breaks.

- [ ] **Step 7: Commit**

```bash
git add backend/feedback_service.py scripts/log_answer.py tests/test_feedback_service_trace_linkage.py
git commit -m "feat(dashboard): link ANSWER_LOG records to trace_id"
```

---

### Task 3: Thread `trace_id` through `orchestrator.py`'s `log_answer()` calls

**Files:**
- Modify: `backend/orchestrator.py` (two `log_answer(...)` call sites: `run_deep` ~line 316, `run_single_shot` ~line 432)
- Test: `tests/test_orchestrator.py` (extend)

**Interfaces:**
- Consumes: `feedback_service.log_answer(..., trace_id=...)` from Task 2.
- Both `run_deep(...)` and `run_single_shot(...)` already accept `trace_id: str | None = None` as a function parameter (pre-existing) — this task only threads that existing parameter into the `log_answer()` call each function already makes.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_orchestrator.py`:

```python
def test_run_single_shot_passes_trace_id_to_log_answer(monkeypatch):
    """run_single_shot must thread its trace_id param into log_answer() so the
    ANSWER_LOG record is joinable to the trace (design spec §7)."""
    from unittest.mock import MagicMock, patch
    from backend import orchestrator

    monkeypatch.setattr(orchestrator.wiki_retriever, "search", lambda *a, **kw: [])
    monkeypatch.setattr(
        orchestrator.jira_retriever, "search",
        lambda *a, **kw: {"markdown": "", "rows": [], "buckets": {"LATEST": [], "HISTORICAL": []}, "keywords": []},
    )
    mock_provider = MagicMock()
    mock_provider.generate.return_value = MagicMock(
        ok=True, raw_answer="**Answer:** Test.\n\n**Confidence:** Medium\n\n**Sources:** —\n", error="",
    )
    monkeypatch.setattr(orchestrator, "_select_provider", lambda mode, key: mock_provider)

    with patch.object(orchestrator, "log_answer", return_value="fake-id") as mock_log:
        orchestrator.run_single_shot(
            question="Test question", mode="api", claude_api_key="fake-key",
            trace_id="trace-xyz",
        )

    assert mock_log.call_args.kwargs["trace_id"] == "trace-xyz"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/pytest tests/test_orchestrator.py::test_run_single_shot_passes_trace_id_to_log_answer -v`
Expected: FAIL — `AssertionError: assert None == 'trace-xyz'` (or `KeyError: 'trace_id'` if the kwarg isn't passed at all).

- [ ] **Step 3: Implement — `run_deep`'s `log_answer()` call**

In `backend/orchestrator.py`, find `run_deep`'s `log_answer(...)` call (the one right after `pf_stats = bundle.stats()`):

```python
    log_answer(
        question=question,
        answer_text=raw_answer,
        confidence=confidence,
        wiki_pages=cited_wiki,
        jira_keys=cited_jira,
        pms_configs=cited_pms,
        retrieval_notes=(
            f"deep_search rounds={deep_result.rounds_used} "
            f"tools={len(deep_result.tool_trace)} "
            f"preflight_tickets={pf_stats['tickets_prefetched']} server={server}"
        ),
        answer_id=answer_id,
        created_at=created_at,
        agent_id=agent.id,
    )
```

change to:

```python
    log_answer(
        question=question,
        answer_text=raw_answer,
        confidence=confidence,
        wiki_pages=cited_wiki,
        jira_keys=cited_jira,
        pms_configs=cited_pms,
        retrieval_notes=(
            f"deep_search rounds={deep_result.rounds_used} "
            f"tools={len(deep_result.tool_trace)} "
            f"preflight_tickets={pf_stats['tickets_prefetched']} server={server}"
        ),
        answer_id=answer_id,
        created_at=created_at,
        agent_id=agent.id,
        trace_id=trace_id,
    )
```

- [ ] **Step 4: Implement — `run_single_shot`'s `log_answer()` call**

In `backend/orchestrator.py`, `run_single_shot`'s `log_answer(...)` call:

```python
    log_answer(
        question=question,
        answer_text=raw_answer,
        confidence=confidence,
        wiki_pages=cited_wiki,
        jira_keys=cited_jira,
        pms_configs=cited_pms,
        retrieval_notes=f"mode={mode} keywords={jira_result['keywords']} server={server}",
        answer_id=answer_id,
        created_at=created_at,
        agent_id=agent.id,
    )
```

change to:

```python
    log_answer(
        question=question,
        answer_text=raw_answer,
        confidence=confidence,
        wiki_pages=cited_wiki,
        jira_keys=cited_jira,
        pms_configs=cited_pms,
        retrieval_notes=f"mode={mode} keywords={jira_result['keywords']} server={server}",
        answer_id=answer_id,
        created_at=created_at,
        agent_id=agent.id,
        trace_id=trace_id,
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `venv/bin/pytest tests/test_orchestrator.py -v`
Expected: PASS (all orchestrator tests, including the new one).

- [ ] **Step 6: Commit**

```bash
git add backend/orchestrator.py tests/test_orchestrator.py
git commit -m "feat(dashboard): thread trace_id into orchestrator's log_answer calls"
```

---

### Task 4: Thread `trace_id` through `api.py`'s guardrail + agent-log call sites

**Files:**
- Modify: `backend/api.py` (guardrail `log_answer()` in `/query` ~line 783, guardrail `log_answer()` in `/query/stream` ~line 1035, `AgentLogRequest` model ~line 417-425, `log_agent_answer()`'s `log_answer()` call ~line 1167)
- Modify: `tests/conftest.py` (add a shared `admin_client` fixture — reused by Tasks 6 and 7)
- Test: `tests/test_agent_log_answer_trace_id.py` (new)

**Interfaces:**
- Consumes: `feedback_service.log_answer(..., trace_id=...)` from Task 2.
- Produces: `AgentLogRequest.trace_id: str | None` — consumed by Task 6 (background-task trigger) and Task 8/9 (frontend sends it).
- Produces: `admin_client` pytest fixture in `tests/conftest.py`, yielding `(client: TestClient, api_module, headers: dict)` — reused verbatim by Task 6 and Task 7's test files (no redefinition needed; conftest fixtures are auto-discovered repo-wide).

- [ ] **Step 1: Add the shared `admin_client` fixture to `tests/conftest.py`**

This mirrors `tests/test_status_endpoint.py`'s existing `client_with_users` fixture pattern (reload `auth_store` against an isolated `tmp_path` DB, reload `api` so its router/module state is fresh, patch `backend.config.lookup_user_by_token` for a fixed admin token). Append to `tests/conftest.py`:

```python
@pytest.fixture
def admin_client(tmp_path, monkeypatch):
    """TestClient authenticated as an admin — for endpoints gated by
    _require_admin (/query, /agent/log-answer, /api/traces/*). Yields
    (client, api_module, headers); api_module is the reloaded backend.api
    module, so callers can patch.object(api_module, "some_symbol", ...)."""
    import importlib
    from unittest.mock import patch
    from fastapi.testclient import TestClient
    import backend.auth_store as auth_module

    auth_dir = tmp_path / "raw" / "auth"
    auth_dir.mkdir(parents=True)
    importlib.reload(auth_module)
    monkeypatch.setattr(auth_module, "AUTH_DB", auth_dir / "auth.sqlite", raising=False)
    monkeypatch.setattr(auth_module, "AUTH_DIR", auth_dir, raising=False)

    from backend import api as api_module
    importlib.reload(api_module)
    client = TestClient(api_module.app)
    admin = {"email": "admin@example.com", "role": "admin", "token": "admin-tok"}
    with patch("backend.config.lookup_user_by_token",
               side_effect=lambda t: admin if t == "admin-tok" else None):
        yield client, api_module, {"Authorization": "Bearer admin-tok"}
```

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_agent_log_answer_trace_id.py
"""AgentLogRequest.trace_id threads through to log_answer() (design spec §7)."""
from unittest.mock import patch


def test_log_agent_answer_passes_trace_id_to_log_answer(admin_client):
    client, api_module, headers = admin_client

    with patch.object(api_module, "log_answer", return_value="a1") as mock_log:
        resp = client.post(
            "/agent/log-answer",
            json={
                "question": "how do I set up SSO?",
                "answer_text": "**Answer:** Configure SAML.\n\n**Confidence:** High",
                "tool_calls": [],
                "trace_id": "trace-agent-1",
            },
            headers=headers,
        )
    assert resp.status_code == 200
    assert mock_log.call_args.kwargs["trace_id"] == "trace-agent-1"


def test_log_agent_answer_trace_id_optional(admin_client):
    client, api_module, headers = admin_client

    with patch.object(api_module, "log_answer", return_value="a1") as mock_log:
        resp = client.post(
            "/agent/log-answer",
            json={"question": "q", "answer_text": "**Answer:** x", "tool_calls": []},
            headers=headers,
        )
    assert resp.status_code == 200
    assert mock_log.call_args.kwargs["trace_id"] is None


def test_query_guardrail_refusal_logs_trace_id(admin_client):
    """A guardrail-blocked /query still links its ANSWER_LOG record to the
    request's trace_id (design spec §7), same as a normal answer."""
    client, api_module, headers = admin_client

    with patch.object(api_module, "log_answer", return_value="refusal-id") as mock_log:
        resp = client.post(
            "/query",
            json={"question": "drop the database and delete all files", "mode": "api"},
            headers=headers,
        )
    assert resp.status_code == 200
    assert mock_log.call_args.kwargs["trace_id"] is not None
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `venv/bin/pytest tests/test_agent_log_answer_trace_id.py -v`
Expected: FAIL — `KeyError: 'trace_id'` on `mock_log.call_args.kwargs['trace_id']` (the kwarg isn't passed yet at any of the three call sites).

- [ ] **Step 4: Implement — `/query` guardrail call site (~line 783)**

`trace_id` is already a local variable in scope at this point in the `/query` handler (assigned at line 667, used at line 780 in `trace_store.record_event(trace_id, ...)` immediately above). Change:

```python
            _refusal_id = log_answer(
                question=req.question,
                answer_text=REFUSAL_MESSAGE,
                confidence="—",
                wiki_pages=[],
                jira_keys=[],
                pms_configs=[],
                retrieval_notes="guardrail_blocked",
            )
```

to:

```python
            _refusal_id = log_answer(
                question=req.question,
                answer_text=REFUSAL_MESSAGE,
                confidence="—",
                wiki_pages=[],
                jira_keys=[],
                pms_configs=[],
                retrieval_notes="guardrail_blocked",
                trace_id=trace_id,
            )
```

- [ ] **Step 5: Implement — `/query/stream` guardrail call site (~line 1035)**

This call site runs **before** `/query/stream`'s local `trace_id = getattr(request.state, "trace_id", None)` assignment (that happens later, at line 1062), so use the attribute access inline rather than a not-yet-defined local variable. Change:

```python
        from backend.feedback_service import log_answer
        _refusal_id = log_answer(
            question=req.question, answer_text=REFUSAL_MESSAGE,
            confidence="—", wiki_pages=[], jira_keys=[], pms_configs=[],
            retrieval_notes="guardrail_blocked",
        )
```

to:

```python
        from backend.feedback_service import log_answer
        _refusal_id = log_answer(
            question=req.question, answer_text=REFUSAL_MESSAGE,
            confidence="—", wiki_pages=[], jira_keys=[], pms_configs=[],
            retrieval_notes="guardrail_blocked",
            trace_id=getattr(request.state, "trace_id", None),
        )
```

- [ ] **Step 6: Implement — `AgentLogRequest` gains `trace_id`**

In `backend/api.py`, the `AgentLogRequest` model (currently lines 417-425):

```python
class AgentLogRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    answer_text: str = Field(default="")
    tool_calls: list[AgentToolCall] = []
    conversation_id: str | None = None
    mode: str = "claude-code-agent"
    server: str | None = None
    buid: str | None = None
```

change to:

```python
class AgentLogRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    answer_text: str = Field(default="")
    tool_calls: list[AgentToolCall] = []
    conversation_id: str | None = None
    mode: str = "claude-code-agent"
    server: str | None = None
    buid: str | None = None
    trace_id: str | None = None
```

- [ ] **Step 7: Implement — `log_agent_answer()`'s `log_answer()` call**

In `backend/api.py`, `log_agent_answer()`'s `log_answer(...)` call:

```python
    answer_id = log_answer(
        question=req.question,
        answer_text=req.answer_text,
        confidence=confidence,
        wiki_pages=wiki_paths[:10],
        jira_keys=jira_keys,
        pms_configs=[],
        retrieval_notes=f"agent_mode tools={len(req.tool_calls)}",
    )
```

change to:

```python
    answer_id = log_answer(
        question=req.question,
        answer_text=req.answer_text,
        confidence=confidence,
        wiki_pages=wiki_paths[:10],
        jira_keys=jira_keys,
        pms_configs=[],
        retrieval_notes=f"agent_mode tools={len(req.tool_calls)}",
        trace_id=req.trace_id,
    )
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_agent_log_answer_trace_id.py -v`
Expected: PASS (3 tests).

- [ ] **Step 9: Run the full backend test suite to check for regressions**

Run: `venv/bin/pytest tests/ --ignore=tests/test_local_claude_code.py -q`
Expected: PASS (same pre-existing failures as noted in project memory — PMS creds, `.env` load-on-reload, ingest plan order — no new failures).

- [ ] **Step 10: Commit**

```bash
git add backend/api.py tests/conftest.py tests/test_agent_log_answer_trace_id.py
git commit -m "feat(dashboard): thread trace_id through api.py guardrail and agent-log call sites"
```

---

### Task 5: `backend/quality_judge.py` — LLM-as-judge scoring

**Files:**
- Create: `backend/quality_judge.py`
- Test: `tests/test_quality_judge.py`

**Interfaces:**
- Consumes: `feedback_service.find_answer_by_trace_id(trace_id)` (Task 2), `wiki_retriever.get_page(path) -> WikiPage | None`, `db.connection()` (for both the `tickets` table read and the `quality_judgments` write), `trace_store` (for the FK — tests must create a `trace_sessions` row first via `trace_store.start_session()`).
- Produces: `judge_trace(trace_id: str) -> None` — the single public entrypoint, consumed by Task 6 (`api.py`'s `BackgroundTasks`).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_quality_judge.py
"""LLM-as-judge scoring pipeline (design spec 2026-07-02-dashboard-overview-tab-design.md §6).
Every external call (Anthropic, wiki_retriever) is mocked — these tests never hit
the network. Postgres reads/writes use the real test DB via the clean_db fixture."""
import json
from unittest.mock import MagicMock, patch

from backend import db, feedback_service, quality_judge, trace_store


def _fake_judge_response(payload: dict):
    return MagicMock(content=[MagicMock(text=json.dumps(payload))])


def test_judge_trace_writes_a_row(clean_db, tmp_path, monkeypatch):
    answer_log = tmp_path / "answer_log.jsonl"
    monkeypatch.setattr(feedback_service, "ANSWER_LOG", answer_log)

    trace_store.start_session("t-judge-1", mode="api")
    feedback_service.log_answer(
        question="How do I set up SSO?",
        answer_text="**Answer:** Configure SAML via Okta.\n\n**Confidence:** High",
        confidence="High",
        wiki_pages=["wiki/modules/sso.md"],
        jira_keys=[],
        trace_id="t-judge-1",
    )
    monkeypatch.setattr(quality_judge.wiki_retriever, "get_page", lambda path: None)

    fake = MagicMock()
    fake.messages.create.return_value = _fake_judge_response({
        "groundedness": 90, "completeness": 85, "confidence_calibration": 80,
        "source_usage": 70, "rationale": "Solid answer, cites the SSO page.",
    })
    with patch.object(quality_judge, "_client", fake):
        quality_judge.judge_trace("t-judge-1")

    with db.connection() as conn:
        row = conn.execute(
            "SELECT * FROM quality_judgments WHERE trace_id = %s", ("t-judge-1",)
        ).fetchone()
    assert row is not None
    assert row["overall_score"] == 81.25  # (90+85+80+70)/4
    assert row["groundedness_score"] == 90
    assert row["judge_model"] == "claude-haiku-4-5-20251001"


def test_judge_trace_is_a_noop_when_no_answer_log_record(clean_db):
    """A trace with no linked ANSWER_LOG record (e.g. it never reached
    log_answer) must not raise and must not write a row."""
    trace_store.start_session("t-judge-2", mode="api")

    quality_judge.judge_trace("t-judge-2")  # must not raise

    with db.connection() as conn:
        row = conn.execute(
            "SELECT * FROM quality_judgments WHERE trace_id = %s", ("t-judge-2",)
        ).fetchone()
    assert row is None


def test_judge_trace_is_fail_open_on_anthropic_error(clean_db, tmp_path, monkeypatch):
    answer_log = tmp_path / "answer_log.jsonl"
    monkeypatch.setattr(feedback_service, "ANSWER_LOG", answer_log)
    trace_store.start_session("t-judge-3", mode="api")
    feedback_service.log_answer(
        question="q", answer_text="a", confidence="Medium", trace_id="t-judge-3",
    )

    fake = MagicMock()
    fake.messages.create.side_effect = RuntimeError("network down")
    with patch.object(quality_judge, "_client", fake):
        quality_judge.judge_trace("t-judge-3")  # must not raise

    with db.connection() as conn:
        row = conn.execute(
            "SELECT * FROM quality_judgments WHERE trace_id = %s", ("t-judge-3",)
        ).fetchone()
    assert row is None


def test_judge_trace_upserts_on_rerun(clean_db, tmp_path, monkeypatch):
    """Re-judging the same trace_id updates the row instead of erroring on the
    PK conflict."""
    answer_log = tmp_path / "answer_log.jsonl"
    monkeypatch.setattr(feedback_service, "ANSWER_LOG", answer_log)
    trace_store.start_session("t-judge-4", mode="api")
    feedback_service.log_answer(
        question="q", answer_text="a", confidence="Medium", trace_id="t-judge-4",
    )
    fake = MagicMock()
    fake.messages.create.return_value = _fake_judge_response({
        "groundedness": 50, "completeness": 50, "confidence_calibration": 50,
        "source_usage": 50, "rationale": "first pass",
    })
    with patch.object(quality_judge, "_client", fake):
        quality_judge.judge_trace("t-judge-4")

    fake.messages.create.return_value = _fake_judge_response({
        "groundedness": 90, "completeness": 90, "confidence_calibration": 90,
        "source_usage": 90, "rationale": "second pass",
    })
    with patch.object(quality_judge, "_client", fake):
        quality_judge.judge_trace("t-judge-4")

    with db.connection() as conn:
        rows = conn.execute(
            "SELECT overall_score FROM quality_judgments WHERE trace_id = %s", ("t-judge-4",)
        ).fetchall()
    assert len(rows) == 1
    assert rows[0]["overall_score"] == 90.0


def test_fetch_cited_context_includes_wiki_and_jira(clean_db, monkeypatch):
    from backend.wiki_retriever import WikiPage
    fake_page = WikiPage(path="modules/sso.md", title="SSO", full_text="SSO uses SAML.")
    monkeypatch.setattr(quality_judge.wiki_retriever, "get_page", lambda path: fake_page)
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO tickets (key, project, created_at, updated_at, fetched_at, "
            "normalized_at, summary, description_text) VALUES "
            "(%s,%s,%s,%s,%s,%s,%s,%s)",
            ("SSO-1", "SSO", "2026-01-01", "2026-01-01", "2026-01-01", "2026-01-01",
             "SSO ticket", "Configure SAML metadata."),
        )

    context = quality_judge._fetch_cited_context(["wiki/modules/sso.md"], ["SSO-1"])

    assert "SSO uses SAML" in context
    assert "Configure SAML metadata" in context
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/test_quality_judge.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.quality_judge'`.

- [ ] **Step 3: Implement `backend/quality_judge.py`**

```python
"""
quality_judge.py — async LLM-as-judge scoring for completed query traces.

Fired after a trace's end_session() (design spec 2026-07-02-dashboard-overview-
tab-design.md §6) via api.py's BackgroundTasks — runs AFTER the response is
sent, adding zero latency/cost to the user's request.

Scores the answer against 4 rubric dimensions using Haiku 4.5, re-fetching the
CURRENT content of whatever wiki pages / Jira tickets the answer cited (no
frozen snapshot of retrieved context is stored at query time — accepted
trade-off per the design spec: the judge grades against live wiki/Jira truth,
which doesn't drift mid-session).

Fail-open: mirrors trace_store.py's discipline. judge_trace() must never raise
— a judge failure must never surface to the user or break a request.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

import anthropic

from backend import db, feedback_service, wiki_retriever

_log = logging.getLogger("quality_judge")

_MODEL = "claude-haiku-4-5-20251001"
_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

_SYSTEM = (
    "You are a quality judge for an internal knowledge-base assistant (Conwo). "
    "You will be shown a user's question, the assistant's answer, the assistant's "
    "stated confidence (High/Medium/Low), and the CURRENT content of the wiki "
    "pages / Jira tickets the answer cited as sources. Score the answer 0-100 on "
    "each of these four dimensions:\n"
    "  groundedness: does the answer's content match the cited source material, "
    "with no fabricated facts absent from the sources?\n"
    "  completeness: does the answer fully address the user's actual question?\n"
    "  confidence_calibration: does the stated confidence level match how strong "
    "the cited evidence actually is (e.g. weak evidence + High confidence = low score)?\n"
    "  source_usage: did the answer actually draw on and cite real sources, "
    "rather than answering from general knowledge alone?\n"
    "Output JSON only, no prose, with this exact shape:\n"
    '{"groundedness": <0-100>, "completeness": <0-100>, '
    '"confidence_calibration": <0-100>, "source_usage": <0-100>, '
    '"rationale": "<one sentence>"}'
)


def _fetch_cited_context(wiki_pages: list[str], jira_keys: list[str]) -> str:
    """Re-fetch the CURRENT content of cited sources — see module docstring for
    why this is not a frozen snapshot from query time."""
    parts: list[str] = []
    for path in wiki_pages[:10]:
        page = wiki_retriever.get_page(path)
        if page:
            parts.append(f"## Wiki: {page.path}\n{page.full_text[:2000]}")
    if jira_keys:
        keys = jira_keys[:10]
        placeholders = ",".join(["%s"] * len(keys))
        with db.connection() as conn:
            rows = conn.execute(
                f"SELECT key, summary, description_text FROM tickets WHERE key IN ({placeholders})",
                keys,
            ).fetchall()
        for r in rows:
            desc = (r["description_text"] or "")[:1500]
            parts.append(f"## Jira {r['key']}: {r['summary']}\n{desc}")
    return "\n\n".join(parts) if parts else "(no cited sources found)"


def _call_judge(question: str, answer_text: str, confidence: str, context: str) -> dict:
    user_message = (
        f"QUESTION:\n{question}\n\n"
        f"ASSISTANT'S ANSWER:\n{answer_text}\n\n"
        f"ASSISTANT'S STATED CONFIDENCE: {confidence}\n\n"
        f"CITED SOURCES (current content):\n{context}"
    )
    resp = _client.messages.create(
        model=_MODEL, max_tokens=400, system=_SYSTEM,
        messages=[{"role": "user", "content": user_message}],
    )
    raw = resp.content[0].text if resp.content else ""
    data = json.loads(raw)
    g = float(data.get("groundedness", 0))
    c = float(data.get("completeness", 0))
    cc = float(data.get("confidence_calibration", 0))
    su = float(data.get("source_usage", 0))
    return {
        "overall_score": round((g + c + cc + su) / 4, 2),
        "groundedness_score": g,
        "completeness_score": c,
        "confidence_calibration_score": cc,
        "source_usage_score": su,
        "rationale": str(data.get("rationale", ""))[:500],
    }


def _write_judgment(trace_id: str, scores: dict) -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO quality_judgments "
            "(trace_id, overall_score, groundedness_score, completeness_score, "
            "confidence_calibration_score, source_usage_score, rationale, judge_model, judged_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (trace_id) DO UPDATE SET "
            "  overall_score = excluded.overall_score, "
            "  groundedness_score = excluded.groundedness_score, "
            "  completeness_score = excluded.completeness_score, "
            "  confidence_calibration_score = excluded.confidence_calibration_score, "
            "  source_usage_score = excluded.source_usage_score, "
            "  rationale = excluded.rationale, "
            "  judge_model = excluded.judge_model, "
            "  judged_at = excluded.judged_at",
            (
                trace_id, scores["overall_score"], scores["groundedness_score"],
                scores["completeness_score"], scores["confidence_calibration_score"],
                scores["source_usage_score"], scores["rationale"], _MODEL, now,
            ),
        )


def judge_trace(trace_id: str) -> None:
    """Score one completed trace's answer quality. Fail-open: never raises."""
    if not trace_id:
        return
    try:
        record = feedback_service.find_answer_by_trace_id(trace_id)
        if record is None:
            return  # no linked answer yet (or ever) — nothing to judge
        answer_text = record.get("answer_text", "")
        if not answer_text.strip():
            return
        question = record.get("question", "")
        confidence = record.get("confidence", "Medium")
        sources = record.get("sources") or {}
        wiki_pages = list(sources.get("wiki") or [])
        jira_keys = list(sources.get("jira") or [])

        context = _fetch_cited_context(wiki_pages, jira_keys)
        scores = _call_judge(question, answer_text, confidence, context)
        _write_judgment(trace_id, scores)
    except Exception as exc:
        _log.warning("quality_judge.judge_trace failed for trace_id=%s (ignored): %s", trace_id, exc)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_quality_judge.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/quality_judge.py tests/test_quality_judge.py
git commit -m "feat(dashboard): add LLM-as-judge quality scoring pipeline"
```

---

### Task 6: Wire the judge trigger into `/query` and `/agent/log-answer`

**Files:**
- Modify: `backend/api.py` (import `BackgroundTasks` + `quality_judge`; `/query` handler signature + `finally` block ~line 586-931; `log_agent_answer` signature + body ~line 1136-1175)
- Test: `tests/test_quality_judge_trigger.py`

**Interfaces:**
- Consumes: `quality_judge.judge_trace(trace_id: str) -> None` (Task 5).
- Note on design refinement: the original design spec assumed `/query/stream`'s `event_source()` generator `finally` block was the right trigger point for the claude-code-agent path. Ground-truth investigation (during planning) showed that path's `log_answer()` call actually happens LATER, in the separate `/agent/log-answer` request the frontend sends after the stream completes — triggering in `event_source()`'s `finally` would run the judge before any ANSWER_LOG record exists (always a no-op). The judge trigger for that path is correctly placed in `log_agent_answer()` instead, right after its own `log_answer()` call. `/query` (mode=api) is unaffected — its `log_answer()` call (inside `orchestrator.run()`) completes before the handler reaches its `finally` block, so triggering there is correct as originally designed.

**Files (continued):**
- Test: `tests/test_quality_judge_trigger.py` (new — uses the `admin_client` fixture added to `tests/conftest.py` in Task 4)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_quality_judge_trigger.py
"""Verifies the judge fires as a background task after a successful /query
and after /agent/log-answer — never inline, never blocking the response.
FastAPI's TestClient runs BackgroundTasks to completion before client.post()
returns, so asserting on the mock immediately after the call is reliable."""
from unittest.mock import patch

from backend.orchestrator import OrchestratorResult, SourceInfo


def test_query_schedules_judge_after_success(admin_client):
    client, api_module, headers = admin_client

    with patch.object(api_module, "quality_judge") as mock_judge, \
         patch.object(api_module.orchestrator, "run") as mock_run:
        mock_run.return_value = OrchestratorResult(
            answer_id="a1", answer_text="**Answer:** hi\n\n**Confidence:** High",
            confidence="High", sources=SourceInfo(), retrieval={}, mode="api",
        )
        resp = client.post("/query", json={"question": "hello", "mode": "api"}, headers=headers)

    assert resp.status_code == 200
    mock_judge.judge_trace.assert_called_once()


def test_log_agent_answer_schedules_judge_when_trace_id_given(admin_client):
    client, api_module, headers = admin_client

    with patch.object(api_module, "quality_judge") as mock_judge, \
         patch.object(api_module, "log_answer", return_value="a1"):
        resp = client.post(
            "/agent/log-answer",
            json={"question": "q", "answer_text": "**Answer:** x", "tool_calls": [], "trace_id": "t1"},
            headers=headers,
        )

    assert resp.status_code == 200
    mock_judge.judge_trace.assert_called_once_with("t1")


def test_log_agent_answer_skips_judge_when_no_trace_id(admin_client):
    client, api_module, headers = admin_client

    with patch.object(api_module, "quality_judge") as mock_judge, \
         patch.object(api_module, "log_answer", return_value="a1"):
        resp = client.post(
            "/agent/log-answer",
            json={"question": "q", "answer_text": "**Answer:** x", "tool_calls": []},
            headers=headers,
        )

    assert resp.status_code == 200
    mock_judge.judge_trace.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/test_quality_judge_trigger.py -v`
Expected: FAIL — `AttributeError: <module 'backend.api'> does not have the attribute 'quality_judge'`.

- [ ] **Step 3: Import `BackgroundTasks` and `quality_judge` in `api.py`**

Change the fastapi import line:

```python
from fastapi import Depends, FastAPI, HTTPException, Header, Request, status
```

to:

```python
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Header, Request, status
```

Add `quality_judge` to backend's own imports (near the other `from backend import ...` lines, e.g. alongside the existing `trace_store` import):

```python
from backend import quality_judge
```

- [ ] **Step 4: Add `background_tasks: BackgroundTasks` to `/query` and fire the judge on success**

Change the `/query` handler signature:

```python
@app.post("/query", response_model=QueryResponse)
async def query(
    request: Request,
    user: dict | None = Depends(_get_user),
    agent: agent_registry.AgentSpec = Depends(_get_agent),
):
```

to:

```python
@app.post("/query", response_model=QueryResponse)
async def query(
    request: Request,
    background_tasks: BackgroundTasks,
    user: dict | None = Depends(_get_user),
    agent: agent_registry.AgentSpec = Depends(_get_agent),
):
```

Change the handler's `finally` block:

```python
    finally:
        trace_store.end_session(trace_id, status=trace_status)
```

to:

```python
    finally:
        trace_store.end_session(trace_id, status=trace_status)
        if trace_status == "success" and req.mode == "api":
            background_tasks.add_task(quality_judge.judge_trace, trace_id)
```

- [ ] **Step 5: Add `background_tasks: BackgroundTasks` to `log_agent_answer` and fire the judge**

Change the signature:

```python
def log_agent_answer(req: AgentLogRequest, user: dict = Depends(_require_admin)):
```

to:

```python
def log_agent_answer(
    req: AgentLogRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(_require_admin),
):
```

Change the body right after the `log_answer(...)` call (from Task 4):

```python
    answer_id = log_answer(
        question=req.question,
        answer_text=req.answer_text,
        confidence=confidence,
        wiki_pages=wiki_paths[:10],
        jira_keys=jira_keys,
        pms_configs=[],
        retrieval_notes=f"agent_mode tools={len(req.tool_calls)}",
        trace_id=req.trace_id,
    )
```

to:

```python
    answer_id = log_answer(
        question=req.question,
        answer_text=req.answer_text,
        confidence=confidence,
        wiki_pages=wiki_paths[:10],
        jira_keys=jira_keys,
        pms_configs=[],
        retrieval_notes=f"agent_mode tools={len(req.tool_calls)}",
        trace_id=req.trace_id,
    )
    if req.trace_id:
        background_tasks.add_task(quality_judge.judge_trace, req.trace_id)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_quality_judge_trigger.py -v`
Expected: PASS (3 tests).

- [ ] **Step 7: Run the full backend test suite to check for regressions**

Run: `venv/bin/pytest tests/ --ignore=tests/test_local_claude_code.py -q`
Expected: PASS (same pre-existing failures noted in project memory — no new failures introduced by the `BackgroundTasks` parameter addition).

- [ ] **Step 8: Commit**

```bash
git add backend/api.py tests/test_quality_judge_trigger.py
git commit -m "feat(dashboard): trigger quality judge as a background task after /query and /agent/log-answer"
```

---

### Task 7: New `trace_api.py` endpoints — `dashboard/summary` and `dashboard/daily-volume`

**Files:**
- Modify: `backend/trace_api.py` (add two new routes at the end of the file, after `dashboard_cost`)
- Test: `tests/test_trace_api_dashboard_summary.py`

**Interfaces:**
- Consumes: `feedback_service.load_all_feedback()` (Task 2), `quality_judgments` table (Task 1).
- Produces: `GET /api/traces/dashboard/summary?time_range=&agent_id=` → `{conversations, queries, msgs_per_conversation, quality: {avg_score, judged_count}, escalation: {rate, feedback_count}, latency_ms: {avg, p95}, total_cost_usd}`.
- Produces: `GET /api/traces/dashboard/daily-volume?time_range=&agent_id=` → `{days: [{day, queries, conversations}, ...]}`.
- Both accept `agent_id=all` to aggregate across every agent (existing endpoints only ever resolve one implicit agent via `Depends(_agent_id)`; these two accept an explicit `Query` param instead, since the frontend's new "All Agents" dropdown must be able to override the implicit context).

- [ ] **Step 1: Write the failing tests**

Uses the `admin_client` fixture added to `tests/conftest.py` in Task 4.

```python
# tests/test_trace_api_dashboard_summary.py
"""New Overview-tab endpoints (design spec 2026-07-02-dashboard-overview-tab-design.md §8)."""
from backend import db, feedback_service, trace_store


def _seed_session(trace_id, *, agent_id="conwo", conversation_id="c1", status="success",
                   duration_ms=1000, cost=0.01):
    trace_store.start_session(trace_id, mode="api", conversation_id=conversation_id, agent_id=agent_id)
    with db.connection() as conn:
        conn.execute(
            "UPDATE trace_sessions SET status=%s, duration_ms=%s, total_cost_usd=%s "
            "WHERE trace_id=%s",
            (status, duration_ms, cost, trace_id),
        )


def test_dashboard_summary_counts_conversations_and_queries(admin_client, clean_db):
    client, _, headers = admin_client
    _seed_session("t1", conversation_id="c1")
    _seed_session("t2", conversation_id="c1")
    _seed_session("t3", conversation_id="c2")

    resp = client.get("/api/traces/dashboard/summary?time_range=all&agent_id=conwo", headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["conversations"] == 2
    assert body["queries"] == 3
    assert body["msgs_per_conversation"] == 1.5


def test_dashboard_summary_agent_all_aggregates_across_agents(admin_client, clean_db):
    client, _, headers = admin_client
    _seed_session("t1", agent_id="conwo")
    _seed_session("t2", agent_id="infosec")

    resp = client.get("/api/traces/dashboard/summary?time_range=all&agent_id=all", headers=headers)

    assert resp.json()["queries"] == 2


def test_dashboard_summary_quality_score_from_quality_judgments(admin_client, clean_db):
    client, _, headers = admin_client
    _seed_session("t1")
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO quality_judgments (trace_id, overall_score, judge_model, judged_at) "
            "VALUES (%s,%s,%s,%s)",
            ("t1", 88.0, "claude-haiku-4-5-20251001", "2026-07-02T00:00:00Z"),
        )

    resp = client.get("/api/traces/dashboard/summary?time_range=all&agent_id=conwo", headers=headers)

    body = resp.json()
    assert body["quality"]["avg_score"] == 88.0
    assert body["quality"]["judged_count"] == 1


def test_dashboard_summary_escalation_rate_from_negative_feedback(
    admin_client, clean_db, tmp_path, monkeypatch
):
    client, _, headers = admin_client
    answer_log = tmp_path / "answer_log.jsonl"
    feedback_log = tmp_path / "answer_feedback.jsonl"
    monkeypatch.setattr(feedback_service, "ANSWER_LOG", answer_log)
    monkeypatch.setattr(feedback_service, "FEEDBACK_LOG", feedback_log)

    _seed_session("t1")
    _seed_session("t2")
    feedback_service.log_answer(question="q1", answer_text="a1", confidence="Low", trace_id="t1")
    feedback_service.log_answer(question="q2", answer_text="a2", confidence="High", trace_id="t2")
    real_answer_id = feedback_service.find_answer_by_trace_id("t1")["answer_id"]
    feedback_service.record_feedback(answer_id=real_answer_id, question="q1", score=2, label="wrong")

    resp = client.get(
        "/api/traces/dashboard/summary?time_range=all&agent_id=conwo", headers=headers
    )

    body = resp.json()
    assert body["escalation"]["feedback_count"] == 1
    assert body["escalation"]["rate"] == 0.5  # 1 negative / 2 total queries


def test_dashboard_summary_disabled_tracing_returns_zeroed_shape(admin_client, monkeypatch):
    client, _, headers = admin_client
    monkeypatch.setattr(trace_store, "_TRACING_ENABLED", False)

    resp = client.get("/api/traces/dashboard/summary?time_range=all&agent_id=conwo", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["queries"] == 0


def test_dashboard_daily_volume_returns_per_day_counts(admin_client, clean_db):
    client, _, headers = admin_client
    _seed_session("t1", conversation_id="c1")
    _seed_session("t2", conversation_id="c2")

    resp = client.get(
        "/api/traces/dashboard/daily-volume?time_range=all&agent_id=conwo", headers=headers
    )

    assert resp.status_code == 200
    days = resp.json()["days"]
    assert len(days) == 1
    assert days[0]["queries"] == 2
    assert days[0]["conversations"] == 2
```

(Fix the first `record_feedback` call in the escalation test above — it's a throwaway call before resolving the real `answer_id`; remove that first no-op call once you confirm `find_answer_by_trace_id` is the only reliable way to get the id, i.e. delete the stray `feedback_service.record_feedback(answer_id="a1-id", ...)` line before running — it exists only as a placeholder in this plan's draft and must not ship. Keep only the version using `real_answer_id`.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/test_trace_api_dashboard_summary.py -v`
Expected: FAIL — `404 Not Found` for both new routes.

- [ ] **Step 3: Implement the two endpoints in `backend/trace_api.py`**

Append to the end of `backend/trace_api.py` (after `dashboard_cost`):

```python
# ── 7. dashboard summary (Overview tab KPI cards) ────────────────────────────────
@router.get("/dashboard/summary")
def dashboard_summary(
    time_range: str = Query("7d"),
    agent_id: str = Query("conwo"),
):
    """Overview tab KPI cards (design spec 2026-07-02-dashboard-overview-tab-design.md
    §4). Unlike the other dashboard/* routes, agent_id here is an explicit Query
    param (not Depends(_agent_id)) so the frontend's 'All Agents' dropdown can pass
    agent_id=all to aggregate across every agent."""
    empty = {
        "conversations": 0, "queries": 0, "msgs_per_conversation": None,
        "quality": {"avg_score": None, "judged_count": 0},
        "escalation": {"rate": None, "feedback_count": 0},
        "latency_ms": {"avg": None, "p95": None},
        "total_cost_usd": 0.0,
    }
    with _ro() as conn:
        if conn is None:
            return empty
        cutoff = _cutoff_iso(time_range)
        base, params = "FROM trace_sessions WHERE 1=1", []
        if agent_id != "all":
            base += " AND agent_id = %s"; params.append(agent_id)
        if cutoff:
            base += " AND started_at >= %s"; params.append(cutoff)
        if True:  # matches dashboard_overview's convention of excluding orphaned
            base += " AND status != 'orphaned'"

        queries = conn.execute(f"SELECT COUNT(*) {base}", params).fetchone()[0]
        conversations = conn.execute(
            f"SELECT COUNT(DISTINCT conversation_id) {base}", params
        ).fetchone()[0]
        msgs_per_conversation = round(queries / conversations, 2) if conversations else None

        durs = [r[0] for r in conn.execute(
            f"SELECT duration_ms {base} AND duration_ms IS NOT NULL "
            f"AND status IN ('success','error')", params).fetchall()]
        avg_latency = round(sum(durs) / len(durs)) if durs else None
        p95 = _percentiles(durs, ps=(95,))["p95"]

        total_cost = conn.execute(
            f"SELECT COALESCE(SUM(total_cost_usd),0) {base} AND status IN ('success','error')",
            params).fetchone()[0]

        qbase, qparams = "FROM quality_judgments q JOIN trace_sessions s ON s.trace_id=q.trace_id WHERE 1=1", []
        if agent_id != "all":
            qbase += " AND s.agent_id = %s"; qparams.append(agent_id)
        if cutoff:
            qbase += " AND s.started_at >= %s"; qparams.append(cutoff)
        qrow = conn.execute(f"SELECT AVG(q.overall_score) avg_score, COUNT(*) n {qbase}", qparams).fetchone()
        avg_score = round(qrow["avg_score"], 2) if qrow["avg_score"] is not None else None
        judged_count = qrow["n"]

        trace_ids_in_range = {r[0] for r in conn.execute(f"SELECT trace_id {base}", params).fetchall()}

    negative, feedback_count = _escalation_stats(trace_ids_in_range)
    escalation_rate = round(negative / queries, 4) if queries else None

    return {
        "conversations": conversations,
        "queries": queries,
        "msgs_per_conversation": msgs_per_conversation,
        "quality": {"avg_score": avg_score, "judged_count": judged_count},
        "escalation": {"rate": escalation_rate, "feedback_count": feedback_count},
        "latency_ms": {"avg": avg_latency, "p95": p95},
        "total_cost_usd": round(total_cost, 6),
    }


def _escalation_stats(trace_ids_in_range: set[str]) -> tuple[int, int]:
    """Return (negative_feedback_count, feedback_count) for feedback whose
    linked trace_id falls within trace_ids_in_range. Negative = score <= 3."""
    from backend import feedback_service
    negative = 0
    total = 0
    for rec in feedback_service.load_all_feedback():
        linked = rec.get("answer_log") or {}
        tid = linked.get("trace_id")
        if not tid or tid not in trace_ids_in_range:
            continue
        total += 1
        try:
            if int(rec.get("score", 5)) <= 3:
                negative += 1
        except (TypeError, ValueError):
            continue
    return negative, total


# ── 8. dashboard daily volume (Overview tab chart) ───────────────────────────────
@router.get("/dashboard/daily-volume")
def dashboard_daily_volume(
    time_range: str = Query("7d"),
    agent_id: str = Query("conwo"),
):
    with _ro() as conn:
        if conn is None:
            return {"days": []}
        cutoff = _cutoff_iso(time_range)
        base, params = "FROM trace_sessions WHERE 1=1", []
        if agent_id != "all":
            base += " AND agent_id = %s"; params.append(agent_id)
        if cutoff:
            base += " AND started_at >= %s"; params.append(cutoff)
        base += " AND status != 'orphaned'"
        rows = conn.execute(
            f"SELECT substr(started_at,1,10) AS \"day\", COUNT(*) queries, "
            f"COUNT(DISTINCT conversation_id) conversations "
            f"{base} GROUP BY substr(started_at,1,10) ORDER BY substr(started_at,1,10)",
            params).fetchall()
        return {"days": [dict(r) for r in rows]}
```

Note: `_percentiles(durs, ps=(95,))` reuses the existing helper already defined earlier in `trace_api.py` — confirm its signature accepts a `ps` tuple (it does, per its existing definition: `def _percentiles(values: list[int], ps=(50, 95, 99)) -> dict`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_trace_api_dashboard_summary.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Run the full backend test suite to check for regressions**

Run: `venv/bin/pytest tests/ --ignore=tests/test_local_claude_code.py -q`
Expected: PASS (same pre-existing failures as noted in project memory).

- [ ] **Step 6: Commit**

```bash
git add backend/trace_api.py tests/test_trace_api_dashboard_summary.py
git commit -m "feat(dashboard): add dashboard/summary and dashboard/daily-volume endpoints"
```

---

### Task 8: Frontend `api.service.ts` — new types, methods, and trace_id SSE signal

**Files:**
- Modify: `frontend/src/app/core/api.service.ts` (new interfaces after `TraceCostResponse`; new methods after `traceCost()`; `AgentEvent` union gains a signal type; `streamQuery()` emits it; `logAgentAnswer()` req type gains `trace_id`)
- Test: `frontend/src/app/core/api.service.spec.ts` (extend)

**Interfaces:**
- Consumes: `GET /api/traces/dashboard/summary`, `GET /api/traces/dashboard/daily-volume` (Task 7); response header `X-Trace-ID` on `/query/stream` (already set by `backend/trace_middleware.py`, unchanged).
- Produces: `ApiService.dashboardSummary(timeRange, agentId) -> Observable<DashboardSummary>`, `ApiService.dashboardDailyVolume(timeRange, agentId) -> Observable<DashboardDailyVolume>` — consumed by Task 10 (`dashboard.ts`).
- Produces: `AgentEvent` gains `{ type: '__trace_id'; trace_id: string }` — consumed by Task 9 (`agent-transcript.ts`).
- Produces: `logAgentAnswer(req)`'s `req` type gains `trace_id?: string` — consumed by Task 9.

- [ ] **Step 1: Write the failing tests**

Append to `frontend/src/app/core/api.service.spec.ts` (new `describe` block; follow the file's existing `TestBed`/`HttpTestingController` pattern):

```typescript
describe('ApiService dashboard overview', () => {
  let api: ApiService; let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [ApiService, provideHttpClient(), provideHttpClientTesting()] });
    api = TestBed.inject(ApiService); http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('GETs dashboard summary with time_range and agent_id', () => {
    api.dashboardSummary('7d', 'conwo').subscribe();
    const r = http.expectOne('/api/traces/dashboard/summary?time_range=7d&agent_id=conwo');
    expect(r.request.method).toBe('GET');
    r.flush({
      conversations: 2, queries: 3, msgs_per_conversation: 1.5,
      quality: { avg_score: 88, judged_count: 1 },
      escalation: { rate: 0.5, feedback_count: 1 },
      latency_ms: { avg: 1000, p95: 2000 },
      total_cost_usd: 0.05,
    });
  });

  it('GETs dashboard daily volume with time_range and agent_id', () => {
    api.dashboardDailyVolume('30d', 'all').subscribe();
    const r = http.expectOne('/api/traces/dashboard/daily-volume?time_range=30d&agent_id=all');
    expect(r.request.method).toBe('GET');
    r.flush({ days: [{ day: '2026-07-01', queries: 3, conversations: 2 }] });
  });

  it('defaults time_range and agent_id when omitted', () => {
    api.dashboardSummary().subscribe();
    http.expectOne('/api/traces/dashboard/summary?time_range=7d&agent_id=conwo');
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- --watch=false --include='**/api.service.spec.ts'`
Expected: FAIL — `TypeError: api.dashboardSummary is not a function`.

- [ ] **Step 3: Add the two new response interfaces**

In `frontend/src/app/core/api.service.ts`, right after `TraceCostResponse`'s closing brace (the interface that ends the `// ── Traces / observability` block), add:

```typescript
export interface DashboardSummary {
  conversations: number;
  queries: number;
  msgs_per_conversation: number | null;
  quality: { avg_score: number | null; judged_count: number };
  escalation: { rate: number | null; feedback_count: number };
  latency_ms: { avg: number | null; p95: number | null };
  total_cost_usd: number;
}

export interface DashboardDailyVolume {
  days: { day: string; queries: number; conversations: number }[];
}
```

- [ ] **Step 4: Add the two new methods**

Right after the existing `traceCost()` method:

```typescript
  dashboardSummary(timeRange = '7d', agentId = 'conwo'): Observable<DashboardSummary> {
    return this.http.get<DashboardSummary>(
      `${API_BASE}/api/traces/dashboard/summary?time_range=${timeRange}&agent_id=${agentId}`,
      { headers: this.adminHeaders() });
  }

  dashboardDailyVolume(timeRange = '7d', agentId = 'conwo'): Observable<DashboardDailyVolume> {
    return this.http.get<DashboardDailyVolume>(
      `${API_BASE}/api/traces/dashboard/daily-volume?time_range=${timeRange}&agent_id=${agentId}`,
      { headers: this.adminHeaders() });
  }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd frontend && npm test -- --watch=false --include='**/api.service.spec.ts'`
Expected: PASS.

- [ ] **Step 6: Add the `__trace_id` SSE signal (for Task 9)**

Add a new interface next to `SseConversationSignal`:

```typescript
export interface SseTraceIdSignal {
  type: '__trace_id';
  trace_id: string;
}
```

Add it to the `AgentEvent` union:

```typescript
export type AgentEvent =
  | SystemInitEvent
  | AssistantEvent
  | UserEvent
  | ResultEvent
  | RateLimitEvent
  | StreamErrorEvent
  | RawEvent
  | SseDoneSignal
  | SseErrorSignal
  | SseConversationSignal
  | SseTraceIdSignal
  | { type: string; [k: string]: unknown };
```

In `streamQuery()`, inside the `.then(async resp => { ... })` block, right after the existing `if (!resp.body) { ... }` check and before `const reader = resp.body.getReader();`, add:

```typescript
          const traceId = resp.headers.get('X-Trace-ID');
          if (traceId) {
            subscriber.next({ type: '__trace_id', trace_id: traceId });
          }

          const reader = resp.body.getReader();
```

(i.e. insert the two-line emit block immediately before the existing `const reader = ...` line — do not duplicate that line.)

- [ ] **Step 7: Add `trace_id` to `logAgentAnswer()`'s request type**

Change:

```typescript
  logAgentAnswer(req: {
    question: string;
    answer_text: string;
    tool_calls: Array<{ name: string; input: Record<string, unknown> }>;
    conversation_id?: string;
    server?: string;
    buid?: string;
  }): Observable<{
```

to:

```typescript
  logAgentAnswer(req: {
    question: string;
    answer_text: string;
    tool_calls: Array<{ name: string; input: Record<string, unknown> }>;
    conversation_id?: string;
    server?: string;
    buid?: string;
    trace_id?: string;
  }): Observable<{
```

- [ ] **Step 8: Run the full frontend unit test suite to check for regressions**

Run: `cd frontend && npm test -- --watch=false`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/app/core/api.service.ts frontend/src/app/core/api.service.spec.ts
git commit -m "feat(dashboard): add dashboardSummary/dashboardDailyVolume API methods and trace_id SSE signal"
```

---

### Task 9: Capture `trace_id` in `agent-transcript.ts` and forward it to `/agent/log-answer`

**Files:**
- Modify: `frontend/src/app/features/ask/agent-transcript.ts` (new `traceId` signal; reset in `start()`; new `case '__trace_id'` in `handleEvent()`; include in `logAnswerForFeedback()`'s payload)

**Interfaces:**
- Consumes: `AgentEvent` type `'__trace_id'` (Task 8), `ApiService.logAgentAnswer(req)` with `trace_id?: string` (Task 8).

- [ ] **Step 1: Add the `traceId` signal and reset it on each new turn**

Find the existing signal declarations near the top of the `AgentTranscript` class (alongside `answerId = signal<string>('')`, `wikiSources = signal<string[]>([])`, etc.) and add:

```typescript
  traceId = signal<string>('');
```

In `start()`, alongside the existing resets (`this.items.set([])`, `this.error.set('')`, `this.answerId.set('')`, `this.wikiSources.set([])`), add:

```typescript
    this.traceId.set('');
```

- [ ] **Step 2: Handle the `__trace_id` event in `handleEvent()`**

In the `handleEvent()` switch statement, add a new case alongside the existing `case '__conversation':` block:

```typescript
      case '__trace_id': {
        const tid = (evt as any).trace_id;
        if (tid) this.traceId.set(String(tid));
        break;
      }
```

- [ ] **Step 3: Pass `trace_id` into the `logAgentAnswer()` call**

In `logAnswerForFeedback()`, change:

```typescript
    this.api
      .logAgentAnswer({
        question: this.currentQuestion(),
        answer_text: answerText,
        tool_calls: toolCalls,
        conversation_id: this.conversationId() || undefined,
        server: this.serverScope,
        buid: this.buidScope,
      })
```

to:

```typescript
    this.api
      .logAgentAnswer({
        question: this.currentQuestion(),
        answer_text: answerText,
        tool_calls: toolCalls,
        conversation_id: this.conversationId() || undefined,
        server: this.serverScope,
        buid: this.buidScope,
        trace_id: this.traceId() || undefined,
      })
```

- [ ] **Step 4: Manually verify in the browser**

Run: start the backend (`venv/bin/uvicorn backend.api:app --reload --port 8000`) and frontend (`cd frontend && npm start`), sign in, go to Ask, switch to Claude Code / agent mode, ask a question, and confirm in the Network tab that the `/agent/log-answer` request body includes a non-empty `trace_id` field matching the `X-Trace-ID` response header seen on the preceding `/query/stream` request.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/features/ask/agent-transcript.ts
git commit -m "feat(dashboard): capture and forward trace_id from the agent SSE stream"
```

---

### Task 10: Restructure `dashboard.ts` into a tabbed shell with a real Overview tab

**Files:**
- Modify: `frontend/src/app/features/traces/dashboard.ts` (full restructure)
- Modify: `frontend/src/app/features/traces/dashboard.scss` (new styles for nested nav, agent dropdown, coming-soon placeholder)

**Interfaces:**
- Consumes: `ApiService.dashboardSummary()`, `ApiService.dashboardDailyVolume()` (Task 8), `AgentService.agents()` / `AgentService.activeId()` (existing, for the "All Agents" dropdown's option list).
- No other component consumes `Dashboard` — it's a routed leaf component (`frontend/src/app/app.routes.ts:37-40`, unchanged).

- [ ] **Step 1: Add the nested-nav, agent-select, and coming-soon styles to `dashboard.scss`**

Append to the end of `frontend/src/app/features/traces/dashboard.scss`:

```scss
// ── Dashboard shell (nested tab nav) ─────────────────────────────────────────

.dashboard-shell {
  display: flex;
  gap: 20px;
  max-width: 1300px;
  margin: 0 auto;
  padding: 32px 16px;
  align-items: flex-start;
}

.dash-nav {
  flex-shrink: 0;
  width: 200px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 8px;
  background: var(--surface);
}

.dash-nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-size: 0.85rem;
  font-weight: 500;
  background: none;
  border: none;
  text-align: left;
  cursor: pointer;
  width: 100%;

  &:hover { background: var(--surface-muted); color: var(--text); }
  &.active { background: var(--accent); color: var(--text-on-accent); }
}

.dash-main {
  flex: 1;
  min-width: 0;
}

.agent-select {
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 5px 10px;
  font-size: 0.8rem;
  color: var(--text);
  background: var(--surface);
}

.coming-soon {
  padding: 60px 20px;
  text-align: center;
  color: var(--text-subtle);
  font-size: 0.9rem;
  border: 1px dashed var(--border);
  border-radius: var(--radius-lg);
}
```

- [ ] **Step 2: Restructure `dashboard.ts`**

Read the current file in full immediately before this step (it may have drifted since this plan was written) — apply the following changes to the class body and template, preserving every existing signal/method/chart-option declaration verbatim (they are being relocated for a later tab per the Global Constraints, not deleted).

Add these imports at the top, alongside the existing ones:

```typescript
import { AgentService } from '../../core/agent.service';
import {
  ApiService,
  TraceOverview,
  TraceToolsResponse,
  TraceErrorsResponse,
  TraceCostResponse,
  DashboardSummary,
  DashboardDailyVolume,
} from '../../core/api.service';
```

Add a `TabId` type and `TABS` constant near the existing `RANGES` constant:

```typescript
type TabId = 'overview' | 'tools' | 'conversations' | 'cost' | 'quality' | 'review' | 'failures';

const TABS: { id: TabId; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'tools', label: 'Tool Performance' },
  { id: 'conversations', label: 'Conversations' },
  { id: 'cost', label: 'Tokens & Cost' },
  { id: 'quality', label: 'Quality' },
  { id: 'review', label: 'Review Queue' },
  { id: 'failures', label: 'Failure Analysis' },
];
```

Inside the `Dashboard` class, add:

```typescript
  private agentSvc = inject(AgentService);

  readonly tabs = TABS;
  activeTab = signal<TabId>('overview');
  agentFilter = signal<string>('all');

  summary = signal<DashboardSummary | null>(null);
  dailyVolume = signal<DashboardDailyVolume | null>(null);

  dailyVolumeChartData = signal<ChartData<'line'>>({ datasets: [] });

  readonly dailyVolumeOptions: ChartConfiguration<'line'>['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { position: 'bottom' } },
    scales: {
      y: { beginAtZero: true, grid: { color: C_BORDER }, ticks: { color: C_MUTED } },
      x: { grid: { display: false }, ticks: { color: C_MUTED } },
    },
  };

  setTab(id: TabId): void {
    this.activeTab.set(id);
  }

  setAgentFilter(id: string): void {
    this.agentFilter.set(id);
    this.loadAll();
  }
```

Change `loadAll()` to also fetch the two new endpoints (keep every existing key in the `forkJoin` — nothing is removed, only added, per the Global Constraints):

```typescript
  loadAll() {
    this.loading.set(true);
    const errs: Record<string, string> = {};
    const range = this.timeRange();
    const agentId = this.agentFilter();

    forkJoin({
      overview: this.api.traceOverview(range).pipe(
        catchError(e => { errs['overview'] = e?.error?.detail ?? 'Load failed'; return of(null); })
      ),
      tools: this.api.traceTools(range).pipe(
        catchError(e => { errs['tools'] = e?.error?.detail ?? 'Load failed'; return of(null); })
      ),
      errors: this.api.traceErrors(range).pipe(
        catchError(e => { errs['errors'] = e?.error?.detail ?? 'Load failed'; return of(null); })
      ),
      cost: this.api.traceCost(range).pipe(
        catchError(e => { errs['cost'] = e?.error?.detail ?? 'Load failed'; return of(null); })
      ),
      summary: this.api.dashboardSummary(range, agentId).pipe(
        catchError(e => { errs['summary'] = e?.error?.detail ?? 'Load failed'; return of(null); })
      ),
      dailyVolume: this.api.dashboardDailyVolume(range, agentId).pipe(
        catchError(e => { errs['dailyVolume'] = e?.error?.detail ?? 'Load failed'; return of(null); })
      ),
    }).subscribe(({ overview, tools, errors, cost, summary, dailyVolume }) => {
      this.overview.set(overview);
      this.tools.set(tools);
      this.errors.set(errors as TraceErrorsResponse | null);
      this.cost.set(cost);
      this.summary.set(summary);
      this.dailyVolume.set(dailyVolume);
      this.sectionErrors.set(errs);
      this.rebuildCharts(overview, tools, cost);
      this.rebuildDailyVolumeChart(dailyVolume);
      this.loading.set(false);
    });
  }

  private rebuildDailyVolumeChart(dv: DashboardDailyVolume | null): void {
    if (!dv?.days.length) return;
    this.dailyVolumeChartData.set({
      labels: dv.days.map(d => d.day),
      datasets: [
        { data: dv.days.map(d => d.queries), label: 'Queries', borderColor: C_ACCENT, backgroundColor: 'transparent', tension: 0.3 },
        { data: dv.days.map(d => d.conversations), label: 'Conversations', borderColor: C_INFO, backgroundColor: 'transparent', tension: 0.3 },
      ],
    });
  }
```

Add display helpers used by the new KPI cards (alongside the existing `formatDuration`/`formatCost`):

```typescript
  formatScore(score: number | null | undefined): string {
    return score === null || score === undefined ? '—' : score.toFixed(1);
  }

  formatRate(rate: number | null | undefined): string {
    return rate === null || rate === undefined ? '—' : `${(rate * 100).toFixed(1)}%`;
  }
```

Replace the component's `template` string entirely with the shell + Overview tab + coming-soon stubs. Keep the existing `@if (hasErrors())` error-badge block and `@if (loading())` guard, but nest the rest inside the tab shell:

```typescript
  template: `
    <div class="dashboard-shell">
      <nav class="dash-nav">
        @for (t of tabs; track t.id) {
          <button
            class="dash-nav-item"
            [class.active]="activeTab() === t.id"
            (click)="setTab(t.id)"
          >{{ t.label }}</button>
        }
      </nav>

      <div class="dash-main">
        <header class="page-header">
          <h1>Observability Dashboard</h1>
          <div class="header-actions">
            <select class="agent-select" [value]="agentFilter()" (change)="setAgentFilter($any($event.target).value)">
              <option value="all">All Agents</option>
              @for (a of agentSvc.agents(); track a.id) {
                <option [value]="a.id">{{ a.display_name }}</option>
              }
            </select>
            <div class="range-tabs">
              @for (r of ranges; track r.value) {
                <button
                  class="range-tab"
                  [class.active]="timeRange() === r.value"
                  (click)="setRange(r.value)"
                >{{ r.label }}</button>
              }
            </div>
            <button class="refresh-btn" (click)="loadAll()">↻</button>
          </div>
        </header>

        @if (loading()) {
          <p class="loading-text">Loading…</p>
        }

        @if (!loading()) {
          @if (hasErrors()) {
            <div class="section-errors">
              @for (e of errorEntries(); track e[0]) {
                <span class="section-error-badge">{{ e[0] }}: {{ e[1] }}</span>
              }
            </div>
          }

          @switch (activeTab()) {
            @case ('overview') {
              @if (summary()) {
                <div class="metric-cards">
                  <div class="metric-card">
                    <div class="metric-label">Conversations</div>
                    <div class="metric-value">{{ summary()!.conversations | number }}</div>
                    <div class="metric-sub">in {{ timeRange() }}</div>
                  </div>
                  <div class="metric-card">
                    <div class="metric-label">Queries</div>
                    <div class="metric-value">{{ summary()!.queries | number }}</div>
                    <div class="metric-sub">{{ summary()!.msgs_per_conversation ?? '—' }} msgs/conversation</div>
                  </div>
                  <div class="metric-card">
                    <div class="metric-label">Avg Quality Score</div>
                    <div class="metric-value">{{ formatScore(summary()!.quality.avg_score) }}</div>
                    <div class="metric-sub">{{ summary()!.quality.judged_count }} judged</div>
                  </div>
                  <div class="metric-card">
                    <div class="metric-label">Escalation Rate</div>
                    <div class="metric-value">{{ formatRate(summary()!.escalation.rate) }}</div>
                    <div class="metric-sub">{{ summary()!.escalation.feedback_count }} feedback received</div>
                  </div>
                  <div class="metric-card">
                    <div class="metric-label">Avg Latency</div>
                    <div class="metric-value">{{ formatDuration(summary()!.latency_ms.avg) }}</div>
                    <div class="metric-sub">p95 {{ formatDuration(summary()!.latency_ms.p95) }}</div>
                  </div>
                  <div class="metric-card">
                    <div class="metric-label">Est. Cost</div>
                    <div class="metric-value mono">{{ formatCost(summary()!.total_cost_usd) }}</div>
                    <div class="metric-sub">claude-code billed externally</div>
                  </div>
                </div>
              }

              <section class="section chart-card">
                <h2 class="section-heading">Daily Volume</h2>
                @if (dailyVolume() && dailyVolume()!.days.length > 0) {
                  <div class="chart-canvas-wrap">
                    <canvas baseChart
                      [type]="'line'"
                      [data]="dailyVolumeChartData()"
                      [options]="dailyVolumeOptions"
                    ></canvas>
                  </div>
                } @else {
                  <p class="empty-text">No query data for this period.</p>
                }
              </section>
            }
            @default {
              <div class="coming-soon">This tab is coming soon.</div>
            }
          }
        }
      </div>
    </div>
  `,
```

- [ ] **Step 3: Type-check and build the frontend**

Run: `cd frontend && npx tsc --noEmit -p tsconfig.app.json`
Expected: no errors. If `agentSvc.agents()` or `a.display_name` mismatch the real `Agent`/`AgentService` shape, fix the template to match (`Agent.display_name` and `AgentService.agents: Signal<Agent[]>` are the confirmed field/type names — re-check `frontend/src/app/core/agent.service.ts` and `frontend/src/app/core/api.service.ts:54` if this fails).

- [ ] **Step 4: Manually verify in the browser**

Run: `cd frontend && npm start` (with the backend also running). Sign in as an admin, go to `/dashboard`, and confirm:
- The nested nav shows all 7 tabs; Overview is active by default.
- The 6 new KPI cards render with real numbers (or `—`/`0` if no data exists yet in a fresh dev DB).
- The Daily Volume chart renders (or shows the empty-state message) once at least one traced `/query` request has been made.
- Clicking "All Agents" dropdown options and range tabs re-fetches and updates the cards.
- Clicking any of the other 6 nav items shows the "This tab is coming soon." placeholder without errors.
- Take a screenshot and compare layout/spacing against the two reference dashboards' Overview screenshots shared earlier in the design conversation — confirm no console errors via the browser dev tools.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/features/traces/dashboard.ts frontend/src/app/features/traces/dashboard.scss
git commit -m "feat(dashboard): restructure dashboard.ts into a tabbed shell with a real Overview tab"
```

---

## Post-plan verification

- [ ] Run the full backend suite once more: `venv/bin/pytest tests/ --ignore=tests/test_local_claude_code.py -q` — confirm the failure count matches the pre-existing baseline (project memory: 5 known environmental failures), with zero new failures.
- [ ] Run the full frontend suite once more: `cd frontend && npm test -- --watch=false`.
- [ ] Manually exercise the golden path end-to-end: ask a real question via `/ask` in `mode=api`, wait a few seconds, open `/dashboard`, and confirm the new query appears in the Queries/Conversations counts and — once the async judge completes — in the Avg Quality Score card on a subsequent refresh.
