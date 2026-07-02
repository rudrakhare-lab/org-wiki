# Conwo Dashboard — Overview Tab + Quality Judge Pipeline — Design Spec

_Date: 2026-07-02_
_Status: approved (pending implementation plan)_
_Scope: The Overview tab of `/dashboard` only, plus the two backend capabilities it depends on
(LLM-judge quality scoring, trace↔feedback linkage). The other 6 planned tabs (Tool Performance,
Conversations, Tokens & Cost, Quality, Review Queue, Failure Analysis) are each their own
follow-up spec, built one at a time. Existing Traces pages (trace-list, trace-detail),
`/api/traces/sessions*`, and the Admin dashboard (`/admin`) are untouched._

---

## 1. Why we are doing this

Conwo's existing `/dashboard` (`frontend/src/app/features/traces/dashboard.ts` +
`backend/trace_api.py`) shows request-level SRE metrics — latency, cost, tool calls, errors — but
has no notion of *answer quality*. Two sibling org chatbots (MASAI Monitor, Atlas Monitor) have a
richer operational dashboard: conversation volume, an automated quality/accuracy score, an
escalation signal, and a tab structure (Overview / Tool Performance / Conversations / Tokens &
Cost / Quality / Review Queue / Failure Analysis) that separates SRE health from answer quality
and human-review workflows.

We are rebuilding Conwo's dashboard with the same *shape* of information, adapted to what Conwo
actually is (a wiki+Jira retrieval agent, not a customer-support bot with human handoff) rather
than copying the reference dashboards' literal metrics. This spec is the first tab (Overview) plus
the two pieces of new backend infrastructure every later tab will need.

## 2. Goals and non-goals

**Goals:**
1. Give Overview a real answer-quality signal, since none exists today.
2. Reframe "conversations vs requests," "escalation," and "quality" in terms that are true to
   Conwo's actual mechanics (no human agent handoff exists).
3. Lay two foundations the other 6 tabs will reuse: an LLM-judge scoring pipeline, and a
   trace_id↔feedback linkage.
4. Keep the change additive — no existing endpoint, chart, or table is broken; relocated UI
   elements (Cost-by-Day, Mode-Split, Top Tools, Recent Errors) keep their working code for a
   later tab to re-mount.

**Non-goals:**
- Not building Tool Performance, Conversations, Tokens & Cost, Quality, Review Queue, or Failure
  Analysis tab content — each gets its own spec once its reference screenshots are reviewed.
- Not building "Fallback Rate" — no clean Conwo analog exists yet (see §6).
- Not adding a custom date-range picker — existing 24h/7d/30d/All range tabs are kept as-is.
- Not migrating `ANSWER_LOG`/`FEEDBACK_LOG` off flat files onto Postgres — the trace_id linkage
  (§5) is additive to the existing file format.
- Not changing per-tab routing — all 7 tabs live inside the single `/dashboard` route, switched by
  a signal, per the existing reference-dashboard sidebar pattern.

## 3. Navigation shell

`/dashboard` keeps its current URL and route guard (`roleGuard(['admin'])`) but its component
becomes a two-column shell:

```
┌─ global app-sidebar (existing, unchanged) ─┬───────────────────────────────────────┐
│  Ask / Search / Dashboard / Traces / ...   │  ┌─ nested dashboard nav (NEW) ──────┐ │
│                                             │  │ ▣ Overview          (active)      │ │
│                                             │  │ 🔧 Tool Performance  (coming soon)│ │
│                                             │  │ 💬 Conversations     (coming soon)│ │
│                                             │  │ $  Tokens & Cost     (coming soon)│ │
│                                             │  │ ✓  Quality           (coming soon)│ │
│                                             │  │ ✓  Review Queue      (coming soon)│ │
│                                             │  │ ⚠  Failure Analysis  (coming soon)│ │
│                                             │  └────────────────────────────────────┘ │
│                                             │  ┌─ top bar: range tabs + Agent + ↻ ──┐ │
│                                             │  │ 24h 7d 30d All   [All Agents ▾]  ↻ │ │
│                                             │  └────────────────────────────────────┘ │
│                                             │  <active tab content>                   │
└─────────────────────────────────────────────┴───────────────────────────────────────┘
```

- One component (`Dashboard`), `activeTab = signal<TabId>('overview')`. Tab list is a static
  array; `@switch (activeTab())` renders content. Non-Overview tabs render a shared
  `<ComingSoon>` placeholder block — visible in the nav (not hidden), so the full planned surface
  is discoverable, matching your explicit choice to show unbuilt tabs rather than omit them.
- New **"All Agents"** dropdown: `All | Conwo | Infosec | …` populated from the existing
  `AgentService` (already used by the global sidebar's active-agent branding). Selecting one sets
  an `agentFilter` signal that all Overview API calls include.
- Existing range tabs (24h/7d/30d/All) and refresh button are kept as-is, moved into this new top
  bar.

## 4. Overview KPI cards

Six cards, replacing today's 4 cards + the standalone 3-gauge Latency Percentiles section:

| # | Card | Computation | Sub-line |
|---|------|-------------|----------|
| 1 | Conversations | `COUNT(DISTINCT conversation_id)` from `trace_sessions`, range + agent filtered | "in {range}" |
| 2 | Queries | `COUNT(*)` from `trace_sessions` (same as today's "Queries" card) | "{queries ÷ conversations, 1dp} msgs/conversation" |
| 3 | Avg Quality Score | `AVG(overall_score)` from new `quality_judgments`, joined to sessions in range/agent | "{N} judged" |
| 4 | Escalation Rate | (# feedback records with `score <= 3`, joined via `trace_id` to sessions in range/agent) ÷ total queries in range | "{N} feedback received" |
| 5 | Avg Latency | `AVG(duration_ms)` (existing) | "p95 {value}" (existing p95 gauge folds in here) |
| 6 | Est. Cost | `SUM(total_cost_usd)` (existing) | "claude-code billed externally" (existing note) |

**Explicitly dropped from Overview** (code stays, just unmounted from this page): standalone
Success-rate card, standalone Latency Percentiles gauge section (p50/p99 detail — p95 is folded
into card 5; full percentile detail can resurface on a later Tool Performance or Failure Analysis
tab). **Relocated, not deleted**: Cost-by-Day line chart, Mode-Split pie, Top Tools bar/table,
Recent Errors table — all remain working `dashboard.ts`/`trace_api.py` code, simply not rendered
on the new Overview; a later tab (Tokens & Cost, Tool Performance, Failure Analysis) re-mounts
them.

**Escalation Rate coverage caveat**: because user feedback is only ever given when something is
wrong (sparse, negatively-biased sample — the real reason "human feedback" was rejected as the
*quality* metric in §6), the sub-line always shows the raw feedback count received, so the
percentage is never presented as if it had full coverage.

## 5. Overview chart

One chart: **Daily Volume** — two lines (Queries, Conversations), one y-axis (both are counts),
bucketed by day over the selected range. Data from a new endpoint (§8). No overlay lines in v1
(no accuracy/latency dual-axis, unlike the reference dashboards) — kept intentionally simple since
Overview is meant to stay lean; richer combined charts are a candidate for later tabs.

## 6. Quality judge pipeline

**Why not human feedback:** Conwo's existing feedback loop (`log_answer.py` / `record_feedback.py`,
described in `CLAUDE.md` §5 Step 6) only captures a rating when a user *chooses* to give one —
per that workflow, feedback is prompted after every answer but in practice is a sparse,
negative-skewed sample (people rate when something's wrong, rarely to confirm it's right). It
cannot produce a representative "how well is Conwo answering" trend the way MASAI's LLM-judged
score does. Fallback Rate has the same problem and has no other clean analog, so it is dropped
entirely for this pass (§2).

**Design:**
- New Postgres table `quality_judgments` (migration under `migrations/postgres/`):
  ```sql
  CREATE TABLE IF NOT EXISTS quality_judgments (
      trace_id                    TEXT PRIMARY KEY
          REFERENCES trace_sessions(trace_id) ON DELETE CASCADE,
      overall_score               DOUBLE PRECISION NOT NULL,
      groundedness_score          DOUBLE PRECISION,
      completeness_score          DOUBLE PRECISION,
      confidence_calibration_score DOUBLE PRECISION,
      source_usage_score          DOUBLE PRECISION,
      rationale                   TEXT,
      judge_model                 TEXT NOT NULL,
      judged_at                   TEXT NOT NULL
  );
  CREATE INDEX IF NOT EXISTS idx_quality_judgments_judged_at ON quality_judgments(judged_at);
  ```
- New module `backend/quality_judge.py`, following `trace_store.py`'s fail-open discipline (a
  judge failure must never surface to the user or break a request):
  1. `judge_trace(trace_id: str) -> None` — reads the session + events via
     `trace_store.query_session()`.
  2. Extracts: question, final answer text, cited wiki pages / Jira keys, and the answer's stated
     confidence (High/Medium/Low).
  3. Re-fetches the **current** content of the cited sources via the existing
     `wiki_retriever` / `jira_retriever` read paths — no new storage of retrieved context at
     query time. (Trade-off accepted: judge grades against current wiki truth, not a frozen
     snapshot; acceptable since wiki content doesn't change mid-session.)
  4. Calls **Haiku 4.5** with a rubric prompt scoring four 0–100 dimensions: Groundedness (does
     the answer match the cited content, any hallucination), Completeness (did it address the
     actual question), Confidence calibration (does the stated High/Medium/Low match the
     evidence strength), Source usage (did it actually use wiki + Jira per the mandatory answer
     format in CLAUDE.md §5). `overall_score` = average of the four.
  5. Writes one row to `quality_judgments`, fail-open (log + swallow on any error).
- **Trigger, async after response (no added user-facing latency/cost):**
  - `/query` (sync handler): pass a FastAPI `BackgroundTasks` dependency, schedule
    `quality_judge.judge_trace(trace_id)` after `end_session()`.
  - `/query/stream` (async generator): call `asyncio.create_task(quality_judge.judge_trace(trace_id))`
    from the generator's existing `finally` block, after its own `end_session()` call.
  - Applies to both `mode=api` and `mode=claude-code` — quality judging is about answer content,
    not token/cost usage, so it applies even where `trace_metrics` has NULL tokens (claude-code
    mode). The implementation plan will confirm exactly how the final answer text is captured for
    claude-code mode (may need to add a `final_answer` field to an existing trace event's
    metadata if not already present — implementation-plan-level detail, not blocking this spec).

## 7. Trace↔feedback linkage

`ANSWER_LOG` records (written by `log_answer()` in `backend/feedback_service.py`) currently have
no `trace_id` — they're keyed only by `answer_id` (a hash of question+answer+timestamp). This
makes Escalation Rate (§4, card 4) impossible to scope by time range or agent today.

**Change:** `log_answer()` gains a `trace_id: str | None = None` parameter, stored in the
`ANSWER_LOG` record alongside the existing `agent_id`. The call sites already have `trace_id` in
scope (via `request.state.trace_id` or a handler-local variable) and are updated to pass it:
- `backend/api.py`: 3 call sites (~line 783, ~1035, ~1167)
- `backend/orchestrator.py`: 2 call sites (~line 316, ~432)

No change to `record_feedback()`'s signature — feedback records already reference `answer_id`,
and `answer_id → trace_id` is now resolvable via the `ANSWER_LOG` record, so the summary endpoint
(§8) can join feedback → answer log → trace_id → trace_sessions(started_at, agent_id) without
touching the feedback file format.

## 8. New / changed API surface

Both new endpoints follow `trace_api.py`'s existing conventions (admin-gated at router-include
time, fail-soft to a zeroed shape if tracing is disabled):

- **`GET /api/traces/dashboard/summary?time_range=&agent_id=`** — new. Returns the 6 KPI values
  from §4 in one payload: `{conversations, queries, msgs_per_conversation, quality:
  {avg_score, judged_count}, escalation: {rate, feedback_count}, latency_ms: {avg, p95},
  total_cost_usd}`.
- **`GET /api/traces/dashboard/daily-volume?time_range=&agent_id=`** — new. Returns
  `{days: [{day, queries, conversations}, ...]}` for the §5 chart.
- **`agent_id` extension**: both new endpoints accept `agent_id=all` to aggregate across every
  agent (today's `_agent_id()` dependency in `trace_api.py` only ever resolves a single implicit
  agent from request context — `all` is a new literal value meaning "drop the `WHERE agent_id =
  %s` clause entirely").
- **Existing `/api/traces/dashboard/overview`, `/tools`, `/errors`, `/cost` are untouched** —
  still available as-is for whatever later tab wants that data (Tokens & Cost, Tool Performance,
  Failure Analysis).
- Escalation join reads `ANSWER_LOG`/`FEEDBACK_LOG` via the existing `feedback_service` read
  helpers (`_fb_load`, etc.), filtering by the newly-added `trace_id` to resolve time range/agent
  — no new file store, no Postgres migration of the feedback data itself.

## 9. Frontend changes

- `frontend/src/app/features/traces/dashboard.ts`: restructured into the shell (§3) + Overview
  tab content (§4, §5). Existing chart/table template blocks (Cost-by-Day, Mode-Split, Top Tools,
  Recent Errors) are extracted but not deleted — kept as private template fragments or moved into
  the file, ready for a later tab to re-mount without re-writing them.
  - Note: `dashboard.ts` is one Angular file, and after this restructure it will hold shell nav +
    Overview + 6 "coming soon" stubs. This is fine at current size, but as each subsequent tab
    spec lands with real content, the file should be split into per-tab child components
    (`overview-tab.ts`, `tool-performance-tab.ts`, ...) sharing the shell — flagged here so it
    isn't a surprise refactor later, not something to build preemptively now.
- `frontend/src/app/core/api.service.ts`: two new methods (`dashboardSummary`,
  `dashboardDailyVolume`) mirroring the existing `traceOverview`/`traceCost` pattern, plus new
  response-shape interfaces.
- New "All Agents" dropdown reads from `AgentService` (already loaded app-wide for the sidebar
  branding) — no new data source.

## 10. Explicitly deferred

Recorded here so nothing is silently foreclosed by this spec:
- Fallback Rate (no clean Conwo analog — see §6).
- Custom date-range picker (reference dashboards have one; Conwo keeps 24h/7d/30d/All for now).
- The other 6 tabs' content (Tool Performance, Conversations, Tokens & Cost, Quality, Review
  Queue, Failure Analysis) — each is a follow-up spec once its reference screenshots are reviewed.
- Splitting `dashboard.ts` into per-tab components (§9) — do this once a second tab actually needs
  real content, not preemptively.
- Migrating `ANSWER_LOG`/`FEEDBACK_LOG` to Postgres — the trace_id linkage (§7) is additive to the
  current flat-file format; a full migration is a separate concern.
