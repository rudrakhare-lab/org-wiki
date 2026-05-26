# API Conwo vs Claude Code — Parity Eval

Thirty questions that probe every capability documented in CLAUDE.md. Each one
produces a binary PASS/FAIL signal, observable from the response — not "is the
answer good?" but "did the system do X concrete thing?"

See `../../docs/superpowers/audits/` (when committed) for the full audit that
generated this set. Each FAIL maps back to a specific Phase 3 gap ID.

## Files

- `questions.json` — the 30 questions, each with pass criteria and predicted
  CC/API results. Edit-in-place is fine; the runner re-reads on every run.
- `runner.py` — the runner. Two drivers (`api` and `cc`). Outputs CSV.

## How to run

### Prerequisites

- Both drivers: the project's `venv/` activated (only Python stdlib is used,
  but the script lives in the project tree).
- **API driver**: a running FastAPI backend (default `start.sh` → port 8000)
  and a Bearer token. Generate one with:
  ```bash
  venv/bin/python -c "from backend import auth_store; \
    auth_store.create_user('eval@conwo.local', role='admin'); \
    print(auth_store.create_token('eval@conwo.local'))"
  ```
  (The eval needs admin to exercise the curator questions Q16–Q18; viewer
  works for everything else.)
- **CC driver**: `claude` CLI on PATH and the repo's `.claude/`, `.mcp.json`,
  and `CLAUDE.md` intact in the project root.
- **PMS-dependent questions** (Q12, Q13, Q14, Q15, Q27): export
  `PMS_TOKEN_COM` / `PMS_TOKEN_IN` / `PMS_COOKIE_COM` / `PMS_COOKIE_IN` per
  CLAUDE.md §12. Without these, those questions are SKIPPED automatically.
- **Q3p (live ticket)**: edit `questions.json` and replace `TS-99999` in Q3p's
  `question` field with a real ticket key updated since the last mirror sync.
  Verify with `sqlite3 raw/jira/tickets.sqlite "SELECT updated_at FROM tickets WHERE key='TS-XXXXX';"`.
- **Q25 (long comment thread)**: similarly, replace `TS-XXXXX` with a real
  ticket having 15+ comments. Find one with:
  ```bash
  sqlite3 raw/jira/tickets.sqlite \
    "SELECT key, comment_count FROM tickets WHERE comment_count >= 15 ORDER BY updated_at DESC LIMIT 5;"
  ```
- **Q17 (INGEST PDF)**: requires `raw/modules/safe-reach/PRD-v2.pdf` to exist.
  If it doesn't, Q17 SKIPS.

### Running

```bash
# API only
venv/bin/python eval/parity/runner.py \
  --system api \
  --api-url http://localhost:8000 \
  --token "$CONWO_TOKEN" \
  --out eval_runs/parity_api_$(date +%F).csv

# Claude Code only
venv/bin/python eval/parity/runner.py \
  --system cc \
  --out eval_runs/parity_cc_$(date +%F).csv

# Both side-by-side (writes one CSV with rows for both systems per question)
venv/bin/python eval/parity/runner.py \
  --system both \
  --api-url http://localhost:8000 \
  --token "$CONWO_TOKEN" \
  --out eval_runs/parity_both_$(date +%F).csv
```

Output goes to the CSV path you specify. Console shows per-question status as
it runs.

## CSV columns

| Column | Meaning |
|--------|---------|
| `question_id` | `Q1`, `Q2`, ..., `Q30` (Q3p is the live-Jira variant inserted between Q3 and Q4) |
| `system` | `api` or `cc` |
| `category` | One of: `query-fidelity`, `live-config-debug`, `curator`, `feedback-loop`, `session-posture`, `coherence`, `power-user`, `streaming`, `safety`, `mcp-live` |
| `status` | `PASS` / `FAIL` / `PARTIAL` / `SKIPPED` / `MANUAL_REVIEW` / `ERROR` |
| `gap` | Phase 3 gap ID if a FAIL is predicted (e.g., `G01`, `G05`) — empty otherwise |
| `latency_s` | Wall-clock seconds for the question |
| `notes` | Auto-score detail (which patterns matched/didn't, or human checklist) |
| `response_snippet` | First 300 chars of the response for at-a-glance review |

## Status values explained

- **PASS** — auto-scored, all pass criteria met.
- **FAIL** — auto-scored, criteria not met. If the question's `gap` column is
  set, this confirms a known gap is still open.
- **PARTIAL** — partial pass per the question's criteria (used sparingly; most
  graded questions are PASS/FAIL).
- **SKIPPED** — setup prerequisite not satisfied (no PMS credentials, ticket
  placeholder not edited, etc.). Not counted in the headline parity score.
- **MANUAL_REVIEW** — the question has a `human` checklist or observation-only
  criterion (e.g., Q28 streaming latency). Read `response_snippet` and score
  the row yourself; the runner just captures the response.
- **ERROR** — the driver failed (HTTP error, timeout, missing binary). Investigate
  before scoring.

## Headline parity number

After running:

```bash
# Total auto-scored PASSes per system
awk -F',' 'NR>1 && $4=="PASS" {print $2}' eval_runs/parity_both_*.csv | sort | uniq -c
```

The expected baseline (today, with all Phase 4 work still pending):

- **CC**: ~28–30 / 30
- **API Conwo**: ~14–17 / 30

Expected post-Batch-1 (P1 closures shipped):

- **API Conwo**: ~24–27 / 30 (residual ~3 = intentional curator-workflow gaps)

## Adding new questions

1. Edit `questions.json`. Each question needs: `id`, `category`, `capability`,
   `question` (or `multi_turn`), `pass_criteria`, `predicted_cc`,
   `predicted_api`, optional `gap_if_failure`, optional `requires`.
2. Pass criteria types supported by the runner:
   - `regex_all` — every pattern must match
   - `regex_any` — any pattern matches
   - `any_of_n` — N of M patterns match (threshold field)
   - `regex_all_and_none` — `must_match` all present, `must_not_match` none present
   - `file_exists` — listed files exist on disk after the run (optional `cleanup_after`)
   - `shell_check` — runs `command`, optionally checks `expect_regex` against response or `expect_response_contains_command_output`
   - `latency_first_token` — observation-only; routed to MANUAL_REVIEW
   - `human` — checklist routed to MANUAL_REVIEW
3. If `pass_criteria.type` is unknown the runner emits `ERROR`. To add a new
   type, extend `score()` in `runner.py`.

## Caveats

- **Multi-turn for CC**: the `claude -p` interface doesn't expose session
  reuse, so multi-turn questions (Q23, Q24) are sent to CC as a single
  concatenated prompt with explicit "respond only to the LAST turn"
  instructions. Imperfect but it's the only API CC offers headless. The API
  driver uses real `conversation_id` threading.
- **Q28 (streaming)** is observation-only — the runner does not measure
  first-token latency for non-streaming APIs. Run this one interactively
  against both systems and judge yourself.
- **No determinism guarantees**. LLM responses vary run-to-run. For a stable
  number, average across 3+ runs.
