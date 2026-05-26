"""
synthesize_patterns.py — Tier 2: HDBSCAN clustering + pattern page generation.

Phase 5 deliverable. Partitions tickets by `functional_area`, runs HDBSCAN per
partition (min_cluster_size=8), takes 10 most central tickets per cluster,
sends to Claude with the pattern synthesis prompt. Outputs:

- wiki/patterns/<functional-area>-<auto-named>.md (full frontmatter)
- Updates module page <!-- BEGIN AUTO:RELATED_PATTERNS --> sections

Respects `human_edited: true` flag (only updates frontmatter, preserves body).

Status: stub. CONDITIONAL — requires explicit user approval (Checkpoint 7).
Many teams discover they don't need this layer.
"""
