"""
promote_to_wiki.py — Tier 3: feed wiki-worthy tickets into the ingest workflow.

Phase 3 deliverable. Reads tickets where `triage_tier = 'wiki'` and no
corresponding `wiki/sources/jira/<KEY>.md` exists yet. For each, invokes the
existing Claude Code ingest workflow ONE TICKET AT A TIME (sequential, not
parallel — this is the only place where Jira-derived markdown is created via
the agent rather than templates).

Status: stub. Implemented after Phase 3 classifier is calibrated.
"""
