"""
enrich_modules.py — Phase 4: append Recent Activity / Known Issues to module pages.

Template-driven, not creative. Pure SQL → markdown. Runs weekly.

For each functional_area with a corresponding module page (via
`config/functional_area_to_module.toml`):

  Recent Activity (top 5 tickets, last 30 days, ranked by signal):
    signal = priority_weight + (comment_count * 0.5)
           + (has_resolution_text * 2) + recency_bonus

  Known Issues (currently open, P0/P1, sorted by priority then age):
    Up to 10 items.

Both sections written between markers:
  <!-- BEGIN AUTO:RECENT_ACTIVITY --> ... <!-- END AUTO:RECENT_ACTIVITY -->
  <!-- BEGIN AUTO:KNOWN_ISSUES   --> ... <!-- END AUTO:KNOWN_ISSUES   -->

Idempotent — diff before write, skip if no change (preserves git cleanliness).
NEVER touches content outside markers.

Status: stub. Implemented after Phase 2 verification.
"""
