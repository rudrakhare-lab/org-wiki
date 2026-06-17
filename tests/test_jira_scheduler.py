"""In-app Jira scheduler: env gating, leader (pod-0) detection, hour parsing,
next-run math, and the disabled/non-leader fast return."""
import asyncio
from datetime import datetime, timezone

from backend import jira_scheduler as js


def test_enabled_flag(monkeypatch):
    monkeypatch.delenv("CONWO_ENABLE_JIRA_CRON", raising=False)
    assert js.enabled() is False
    monkeypatch.setenv("CONWO_ENABLE_JIRA_CRON", "true")
    assert js.enabled() is True
    monkeypatch.setenv("CONWO_ENABLE_JIRA_CRON", "off")
    assert js.enabled() is False


def test_leader_detection(monkeypatch):
    monkeypatch.setattr(js.socket, "gethostname", lambda: "conwo-0")
    assert js._is_leader() is True
    monkeypatch.setattr(js.socket, "gethostname", lambda: "conwo-1")
    assert js._is_leader() is False
    monkeypatch.setattr(js.socket, "gethostname", lambda: "conwo-2")
    assert js._is_leader() is False
    # No StatefulSet ordinal (local dev / plain Deployment) → treated as leader.
    monkeypatch.setattr(js.socket, "gethostname", lambda: "Rudras-MacBook")
    assert js._is_leader() is True


def test_hour_utc_parsing(monkeypatch):
    monkeypatch.delenv("CONWO_JIRA_CRON_HOUR_UTC", raising=False)
    assert js._hour_utc() == 2
    monkeypatch.setenv("CONWO_JIRA_CRON_HOUR_UTC", "5")
    assert js._hour_utc() == 5
    monkeypatch.setenv("CONWO_JIRA_CRON_HOUR_UTC", "99")   # clamped to 23
    assert js._hour_utc() == 23
    monkeypatch.setenv("CONWO_JIRA_CRON_HOUR_UTC", "bad")  # falls back to 2
    assert js._hour_utc() == 2


def test_seconds_until_is_within_a_day():
    secs = js._seconds_until(2)
    assert 0 < secs <= 24 * 3600


def test_run_forever_returns_immediately_when_disabled(monkeypatch):
    monkeypatch.delenv("CONWO_ENABLE_JIRA_CRON", raising=False)
    # Should return at once (not loop) — completes well under the timeout.
    asyncio.run(asyncio.wait_for(js.run_forever(), timeout=2))


def test_run_forever_returns_when_not_leader(monkeypatch):
    monkeypatch.setenv("CONWO_ENABLE_JIRA_CRON", "true")
    monkeypatch.setattr(js.socket, "gethostname", lambda: "conwo-1")
    asyncio.run(asyncio.wait_for(js.run_forever(), timeout=2))
