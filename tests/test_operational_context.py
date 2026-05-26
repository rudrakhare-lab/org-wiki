"""Tests for backend.operational_context — the per-query freshness block.

Mocks admin_api.get_sync_status to control the scenario and asserts the
rendered block shape. Includes realistic-shape fixtures (JSON-encoded log
lines, matching what jira_sync.py actually emits) so we know the parser
handles the real format, not a fictionalized one.

G31 closure added the `most_recent_successful_sync` field (authoritative
for stale detection) plus tests for the recent-error / old-success and
recent-success / old-error scenarios that motivated G31.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import backend.operational_context as oc


def _set_status(monkeypatch, status: dict) -> None:
    monkeypatch.setattr(oc, "_compute_status", lambda: status)
    oc._reset_cache_for_testing()


def _iso(ts: datetime) -> str:
    return ts.isoformat().replace("+00:00", "Z")


def _json_log_line(ts: datetime, msg: str = "ALL DONE: fetched=15 new=0 updated=0") -> str:
    """Return a log line shaped like jira_sync.py emits (default = success line)."""
    return json.dumps({
        "ts": _iso(ts),
        "level": "INFO",
        "logger": "jira_sync",
        "msg": msg,
    })


def test_fresh_mirror_and_no_pending_returns_empty(monkeypatch):
    """Mirror fresh (1h old via most_recent_successful_sync), zero pending → no block."""
    fresh_ts = datetime.now(timezone.utc) - timedelta(hours=1)
    _set_status(monkeypatch, {
        "jira": {
            "last_log_line": _json_log_line(fresh_ts),
            "last_sync_line": _json_log_line(fresh_ts),
            "most_recent_successful_sync": _iso(fresh_ts),
            "ticket_count": 37131,
        },
        "drive": {"last_sync": "", "file_count": 0},
        "feedback": {"pending_count": 0},
    })
    assert oc.get_context_block() == ""


def test_stale_mirror_emits_stale_warning(monkeypatch):
    """most_recent_successful_sync >36h old → ⚠️ stale warning."""
    stale_ts = datetime.now(timezone.utc) - timedelta(hours=72)
    _set_status(monkeypatch, {
        "jira": {
            "last_log_line": _json_log_line(stale_ts),
            "last_sync_line": _json_log_line(stale_ts),
            "most_recent_successful_sync": _iso(stale_ts),
            "ticket_count": 37131,
        },
        "drive": {"last_sync": "", "file_count": 0},
        "feedback": {"pending_count": 0},
    })
    block = oc.get_context_block()
    assert block.startswith("**Operational context:**\n")
    assert "⚠️" in block
    assert "last successful sync is" in block
    assert any(s in block for s in ("71h", "72h", "73h"))
    assert "Pending feedback" not in block


def test_pending_feedback_emits_pending_line(monkeypatch):
    """pending_count > 0 → block contains pending count, no stale warning."""
    fresh_ts = datetime.now(timezone.utc) - timedelta(hours=2)
    _set_status(monkeypatch, {
        "jira": {
            "last_log_line": _json_log_line(fresh_ts),
            "last_sync_line": _json_log_line(fresh_ts),
            "most_recent_successful_sync": _iso(fresh_ts),
            "ticket_count": 37131,
        },
        "drive": {"last_sync": "", "file_count": 0},
        "feedback": {"pending_count": 5},
    })
    block = oc.get_context_block()
    assert block.startswith("**Operational context:**\n")
    assert "Pending feedback awaiting admin review: 5 items." in block
    assert "⚠️" not in block


# ── G31 honesty tests: warning fires on actual sync success, not noise ────────

def test_recent_error_old_success_fires_stale_warning(monkeypatch):
    """The previously-broken scenario from G31: log file has a RECENT ERROR
    line but the last SUCCESSFUL sync was 72h ago. Mirror IS stale; warning
    must fire. Pre-G31 the old code grabbed the recent error line and treated
    it as 'fresh' — silent false-negative."""
    recent_error_ts = datetime.now(timezone.utc) - timedelta(hours=1)
    old_success_ts = datetime.now(timezone.utc) - timedelta(hours=72)
    _set_status(monkeypatch, {
        "jira": {
            "last_log_line": json.dumps({
                "ts": _iso(recent_error_ts),
                "level": "ERROR",
                "logger": "jira_sync",
                "msg": "normalize/upsert failed for TB-40308",
            }),
            "last_sync_line": json.dumps({
                "ts": _iso(recent_error_ts),
                "level": "ERROR",
                "logger": "jira_sync",
                "msg": "normalize/upsert failed for TB-40308",
            }),
            "most_recent_successful_sync": _iso(old_success_ts),
            "ticket_count": 37131,
        },
        "drive": {"last_sync": "", "file_count": 0},
        "feedback": {"pending_count": 0},
    })
    block = oc.get_context_block()
    assert "⚠️" in block
    assert "last successful sync is" in block
    assert any(s in block for s in ("71h", "72h", "73h"))


def test_recent_success_old_error_no_warning(monkeypatch):
    """Inverse: log file's most recent line is an OLD error, but a fresh
    success exists at 1h ago. Mirror IS fresh; no warning."""
    fresh_success_ts = datetime.now(timezone.utc) - timedelta(hours=1)
    old_error_ts = datetime.now(timezone.utc) - timedelta(hours=72)
    _set_status(monkeypatch, {
        "jira": {
            "last_log_line": json.dumps({
                "ts": _iso(old_error_ts),
                "level": "ERROR",
                "logger": "jira_sync",
                "msg": "something failed",
            }),
            "last_sync_line": json.dumps({
                "ts": _iso(old_error_ts),
                "level": "ERROR",
                "logger": "jira_sync",
                "msg": "something failed",
            }),
            "most_recent_successful_sync": _iso(fresh_success_ts),
            "ticket_count": 37131,
        },
        "drive": {"last_sync": "", "file_count": 0},
        "feedback": {"pending_count": 0},
    })
    block = oc.get_context_block()
    assert block == "", f"expected no block (fresh successful sync), got: {block!r}"


def test_no_successful_sync_ever_logged_emits_harder_warning(monkeypatch):
    """If logs exist but no 'ALL DONE:' line is ever found, surface a
    harder warning — the sync may never have completed successfully."""
    old_error_ts = datetime.now(timezone.utc) - timedelta(hours=2)
    _set_status(monkeypatch, {
        "jira": {
            "last_log_line": json.dumps({
                "ts": _iso(old_error_ts),
                "level": "ERROR",
                "logger": "jira_sync",
                "msg": "something failed",
            }),
            "last_sync_line": json.dumps({
                "ts": _iso(old_error_ts),
                "level": "ERROR",
                "logger": "jira_sync",
                "msg": "something failed",
            }),
            "most_recent_successful_sync": "",
            "ticket_count": 37131,
        },
        "drive": {"last_sync": "", "file_count": 0},
        "feedback": {"pending_count": 0},
    })
    block = oc.get_context_block()
    assert "⚠️" in block
    assert "no successful sync" in block.lower()
