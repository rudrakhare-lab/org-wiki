# Triage Classifier Prompt

> **Status**: skeleton — populated in Phase 3, after the editorial policy has been
> stress-tested against ~200 hand-reviewed tickets.

## Versioning

Each prompt revision is committed with a version stamp. The classifier records
the prompt version it used in `tickets.last_triaged_at` notes.

## Current version

_(not yet authored — placeholder for Phase 3)_

## Output schema

The classifier MUST return one JSON object per ticket. Batch calls return an array.

```json
{
  "key": "TS-1234",
  "tier": "wiki" | "evidence" | "ignore",
  "confidence": 0.0,
  "reason": "short justification (one sentence)"
}
```

## Batch optimization

Tickets are sent 5–10 at a time per Claude call. The prompt asks for an array of
verdicts in the same order as the input. Batch reduces token cost ~5x.

## Calibration protocol

1. First run classifies 200 random tickets across all functional areas.
2. Output dumped to `triage_review.csv` for human review.
3. Disagreements are noted; prompt is tuned.
4. Re-run on the same 200; iterate until ≥90% agreement.
5. Only then does the full 35K classification run.

This is the "First run protocol" referenced in the master brief.
