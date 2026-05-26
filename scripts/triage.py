"""
triage.py — Editorial filter: classifies each ticket as wiki / evidence / ignore.

Phase 3 deliverable. Reads tickets where `last_triaged_at IS NULL OR
updated_at > last_triaged_at`, sends batches of 5–10 to Claude with the prompt
in `docs/classifier-prompt.md`, writes `triage_tier` + `triage_reason` back
to SQLite.

First run protocol (master brief 3.2):
- Classify 200 random tickets
- Dump to triage_review.csv
- Human review and prompt tuning
- Re-run, iterate to ≥90% agreement
- Then full 35K classification

Status: stub. Do not implement until Phase 2 verification + editorial policy
finalized.
"""
