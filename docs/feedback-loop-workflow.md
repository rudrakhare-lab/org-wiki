# Feedback Loop Workflow

The feedback loop turns answer review into durable wiki improvements. The goal
is not only to score an answer, but to capture what was wrong, update the
knowledge graph, and prevent the same failure pattern from repeating.

> **Important:** The model is not fine-tuned. "Learning" here means updating
> the knowledge base — wiki pages, config docs, guardrails in CLAUDE.md, and
> the failure-pattern registry — so the *next* query reads better sources.

## Architecture — 4 layers

| # | Layer | What it does | Where it lives |
|---|-------|-------------|----------------|
| 1 | Capture (at answer time) | Every answer gets a stable `answer_id`, full text, confidence, and cited sources logged | `raw/feedback/answer_log.jsonl` (gitignored) |
| 2 | Validate (user review) | User scores 1–5; on score ≤3 records correction | `raw/feedback/answer_feedback.jsonl` (gitignored) |
| 3 | Learn (apply to repo) | Patches the right wiki page(s); flags systematic patterns | `wiki/configs/`, `wiki/modules/`, `wiki/log.md`, optionally `CLAUDE.md` |
| 4 | Prevent repeat failures | Failure patterns registered for in-session reference | `wiki/known-answer-patterns.md` (committed, PII-sanitized) |

## What Feedback Captures

Every tested answer should have a feedback record with:

- original question
- answer id or run id
- score from 1 to 5
- issue label, for example `outdated`, `missing_jira`, `wrong_config`,
  `missing_pms_runtime`, or `incomplete`
- user's correction or expected answer
- cited sources used in the answer
- affected wiki pages/configs/Jira tickets, if known

Feedback records may contain customer context, so local raw feedback is stored
under `raw/feedback/` and ignored from git.

## Rating Scale

| Score | Meaning | Action |
|---:|---|---|
| 5 | Correct and well sourced | No action, optionally save as a good example |
| 4 | Mostly correct, minor missing context | Add small wiki/Jira/PMS evidence note |
| 3 | Partially correct | Triage and update affected page(s) |
| 2 | Wrong or misleading | Fix wiki/prompt/evidence retrieval before reuse |
| 1 | Dangerous/confidently wrong | Block as known failure pattern and patch immediately |

## Issue Labels

Use one primary label first:

- `correct`
- `partially_correct`
- `wrong`
- `incomplete`
- `outdated`
- `conflicting_evidence`
- `wrong_config`
- `wrong_scope`
- `missing_jira`
- `missing_pms_runtime`
- `missing_runtime_context`
- `unclear`

## Layer 1 — Capture: `log_answer.py`

Every product/config/architecture answer must be logged. The answer_id is the
12-char sha1 prefix of `question + answer_text + created_at`.

```bash
venv/bin/python scripts/log_answer.py log \
  --question "Why is visitor kiosk OTP not working at office Z for client Y?" \
  --answer-text "<full answer text from response>" \
  --confidence Medium \
  --wiki "wiki/configs/visitor-management.md" \
  --jira "TS-36471,PB-66727" \
  --pms "VISITOR:kioskRequireOTPBeforeRegister" \
  --retrieval-notes "ranked Jira: 1 Latest / 2 Historical; PMS BUID-level checked only" \
  --quiet
# → prints answer_id (e.g. 9f2c1ad03b81)
```

The agent prints this id alongside its answer so the user can score it.

### `answer_log.jsonl` schema

```json
{
  "answer_id": "9f2c1ad03b81",
  "created_at": "2026-05-18T12:34:56+00:00",
  "question": "...",
  "answer_text": "...",
  "confidence": "Medium",
  "sources": {
    "wiki": ["wiki/configs/visitor-management.md"],
    "jira": ["TS-36471", "PB-66727"],
    "pms": ["VISITOR:kioskRequireOTPBeforeRegister"]
  },
  "retrieval_notes": "ranked Jira: 1 Latest / 2 Historical; PMS BUID-level only"
}
```

## Layer 2 — Validate: `record_feedback.py`

```bash
venv/bin/python scripts/record_feedback.py record \
  --question "Why is visitor kiosk OTP not working for this office?" \
  --answer-id "9f2c1ad03b81" \
  --score 2 \
  --label missing_pms_runtime \
  --correction "The answer should have checked VISITOR properties at OFFICEID level before recommending a BUID change." \
  --affected "wiki/configs/visitor-management.md,VISITOR:kioskRequireOTPBeforeRegister"
# answer_id is auto-linked from answer_log.jsonl (if present)
```

List / filter / summary:

```bash
venv/bin/python scripts/record_feedback.py list --status pending
venv/bin/python scripts/record_feedback.py list --label missing_pms_runtime
venv/bin/python scripts/record_feedback.py summary
```

Resolve manually (the script `apply_feedback.py` calls this for you):

```bash
venv/bin/python scripts/record_feedback.py resolve \
  --feedback-id abc123def456 \
  --resolution "Updated wiki/configs/visitor-management.md; added OFFICEID precedence note" \
  --wiki-commit-ref "wiki/configs/visitor-management.md"
```

## Layer 3 — Learn: `apply_feedback.py`

The default is `--dry-run` — it prints the patch plan but writes nothing.
`--apply` enables writes.

```bash
# Plan one specific feedback
venv/bin/python scripts/apply_feedback.py --feedback-id abc123def456

# Plan all pending (score 1-3)
venv/bin/python scripts/apply_feedback.py --all-pending

# Actually patch the wiki
venv/bin/python scripts/apply_feedback.py --feedback-id abc123def456 --apply
```

**What apply does:**

1. Loads the feedback record + linked answer_log entry
2. Resolves patch targets in this order:
   - explicit `--affected` paths from the feedback
   - `wiki` sources from the linked answer_log
   - PMS service tokens in `correction` (e.g. `VISITOR:propName` → `wiki/configs/visitor-management.md`)
   - label hint (e.g. `wrong_config` → `wiki/configs/`)
3. Inserts a `## Feedback Notes` block at the bottom of each target page,
   guarded by an HTML marker comment `<!-- feedback:<id> -->` for idempotency
4. Appends an entry to `wiki/log.md`
5. Calls `record_feedback.py resolve` to mark the feedback as applied
6. If the label appears ≥3 times across pending+resolved feedback, prints a
   CLAUDE.md guardrail recommendation (it does NOT auto-write CLAUDE.md)

### Label → patch routing table

| Label | Patch location | Strategy |
|-------|----------------|----------|
| `wrong_config` | `wiki/configs/<module>.md` | Add the correct behavior, scope, default to the config page |
| `missing_jira` | Module or config page | Re-run `query_jira_ranked.py`; cite the missing ticket keys |
| `outdated` | Affected page | Update the wiki page and add a "supersedes older behavior (pre-YYYY)" note |
| `missing_pms_runtime` | Config page or `docs/live-config-debug.md` | Add runtime-criteria note (which hierarchy level, when to check) |
| `wrong_scope` | Config page | Clarify BUID / OFFICEID / ROOM_ID / ROLE precedence |
| `conflicting_evidence` | Wiki page | Add a conflict block (current vs legacy) |
| `missing_runtime_context` | `docs/live-config-debug.md` | Add the missing runtime step |
| `incomplete` / `unclear` | Affected page | Additive clarification only |
| Systematic (label seen 3+ times) | `CLAUDE.md` Section 5 or 12 | Recommend a guardrail; human edits manually |

## Layer 4 — Prevent: `wiki/known-answer-patterns.md`

This file is committed to the repo (PII-sanitized). It contains two sections:

- **Failure patterns** — sourced from score 1–2 feedback; describes question
  shapes the agent must handle carefully
- **Good examples** — sourced from score 5 feedback; describes answer shapes
  the agent should emulate

The agent reads this file at session start (Section 8 checklist) and before
answering config questions that involve a specific BUID/office/role
(CLAUDE.md Section 5 Step 6).

When `apply_feedback.py` detects a systematic pattern (label ≥3 times), it
recommends adding an entry here. The entry is added manually after PII review.

## Recommended workflow — dry-run → review → apply

The agent should always run apply in two passes:

1. `apply_feedback.py --feedback-id X` — prints the patch plan
2. Show the plan to the user, ask for confirmation
3. `apply_feedback.py --feedback-id X --apply` — writes the changes

Never silently auto-apply without a dry-run review, even for batch operations
on score-1 feedback. The patch may target the wrong file if `affected` was
not specified precisely.

## Answer-Time Feedback Hook (mandatory)

Every answer for a product/config/architecture query MUST end with:

```text
---
**Review this answer:** Score 1–5 (5 = fully correct).
**Answer ID:** `<answer_id>`
If score ≤3, tell me what was wrong or what the answer should have said.
```

The answer_id is the value returned by `log_answer.py log`. See CLAUDE.md
Section 5 Step 6 for the full agent-side workflow.

## Success Metrics

Track weekly:

- average answer score
- percentage of answers scoring 4 or 5
- count of score 1-2 failures
- top failure labels
- time from feedback to wiki patch
- repeated failure count by config/module
- number of feedback items converted into wiki improvements

