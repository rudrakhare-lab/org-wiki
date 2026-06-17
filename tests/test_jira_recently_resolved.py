"""Determinism fix for 'recently resolved in <area>' named query:
- recently_resolved accepts an optional functional_area (passed twice for the
  `%s = '' OR functional_area = %s` guard)
- the SQL orders by resolved_at DESC then key ASC (stable tiebreaker)
"""
from backend.tools import jira_tools


def test_recently_resolved_params_with_area():
    params = jira_tools._recently_resolved_params(
        {"functional_area": "WP-admin", "days": 90, "limit": 3}
    )
    # (cutoff_date, area, area, limit) — area duplicated for the two placeholders.
    assert len(params) == 4
    assert params[1] == "WP-admin"
    assert params[2] == "WP-admin"
    assert params[3] == 3


def test_recently_resolved_params_without_area_matches_all():
    params = jira_tools._recently_resolved_params({"days": 90})
    # Empty area string → the `%s = ''` guard short-circuits to "all areas".
    assert params[1] == ""
    assert params[2] == ""


def test_recently_resolved_sql_is_deterministic_and_area_scoped():
    sql, _ = jira_tools._NAMED_QUERIES["recently_resolved"]
    assert "ORDER BY resolved_at DESC, key ASC" in sql
    assert "(%s = '' OR functional_area = %s)" in sql


def test_other_named_queries_have_key_tiebreaker():
    for name in ("tickets_by_area", "open_by_priority", "tickets_linking_key"):
        sql, _ = jira_tools._NAMED_QUERIES[name]
        assert ", key ASC" in sql, f"{name} missing deterministic key tiebreaker"
