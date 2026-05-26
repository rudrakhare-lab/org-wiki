"""Mocked unit tests for backend.tools.jira_live_tools — no live Jira calls.

The smoke test in tests/manual/g01_smoke.py covers the happy path against
real Jira; this file covers all error envelopes and the input-validation
boundary without network or credentials.
"""
from __future__ import annotations

import io
import json
import urllib.error
from unittest.mock import patch, MagicMock


# ──────────────────────────────────────────────────────────────────────────────
# Fixture: a stable mock response shape matching what Atlassian returns

_HAPPY_PATH_RESPONSE = {
    "key": "TS-12345",
    "fields": {
        "summary": "OTP not appearing for visitor kiosk users",
        "status": {"name": "Done", "statusCategory": {"key": "done"}},
        "priority": {"name": "P1"},
        "resolution": {"name": "Fixed"},
        "created": "2026-04-01T10:00:00.000+0000",
        "updated": "2026-04-12T15:30:00.000+0000",
        "assignee": {"displayName": "Alice Engineer"},
        "reporter": {"displayName": "Bob PM"},
    },
}


def _mock_urlopen_ok(payload: dict, headers: dict | None = None):
    """Return a mock context-manager whose .read() yields JSON bytes."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(payload).encode("utf-8")
    mock_resp.headers = headers or {}
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def _mock_urlopen_http_error(code: int, msg: str = "Error"):
    """Raise a real HTTPError when called."""
    return urllib.error.HTTPError(
        url="https://example.com",
        code=code,
        msg=msg,
        hdrs={},
        fp=io.BytesIO(b""),
    )


# ──────────────────────────────────────────────────────────────────────────────
# Tests

def test_happy_path_returns_structured_ticket(monkeypatch):
    """Mocked Atlassian response → structured dict with the expected fields."""
    monkeypatch.setenv("JIRA_EMAIL", "test@example.com")
    monkeypatch.setenv("JIRA_API_TOKEN", "fake-token-1234")
    monkeypatch.setattr(
        "backend.tools.jira_live_tools.JIRA_BASE_URL",
        "https://moveinsync.atlassian.net",
    )

    from backend.tools.jira_live_tools import _jira_live_get_ticket_handler

    with patch("urllib.request.urlopen") as mock_open:
        mock_open.return_value = _mock_urlopen_ok(
            _HAPPY_PATH_RESPONSE,
            headers={"X-RateLimit-Remaining": "499"},
        )
        result = _jira_live_get_ticket_handler({"key": "TS-12345"})

    assert "error" not in result
    assert result["key"] == "TS-12345"
    assert result["summary"] == "OTP not appearing for visitor kiosk users"
    assert result["status"] == "Done"
    assert result["status_category"] == "done"
    assert result["priority"] == "P1"
    assert result["resolution"] == "Fixed"
    assert result["updated"] == "2026-04-12T15:30:00.000+0000"
    assert result["assignee"] == "Alice Engineer"
    assert result["source"] == "live"
    assert result["_rate_limit_remaining"] == "499"


def test_404_returns_not_found_code(monkeypatch):
    monkeypatch.setenv("JIRA_EMAIL", "test@example.com")
    monkeypatch.setenv("JIRA_API_TOKEN", "fake-token-1234")
    monkeypatch.setattr(
        "backend.tools.jira_live_tools.JIRA_BASE_URL",
        "https://moveinsync.atlassian.net",
    )

    from backend.tools.jira_live_tools import _jira_live_get_ticket_handler

    with patch("urllib.request.urlopen", side_effect=_mock_urlopen_http_error(404)):
        result = _jira_live_get_ticket_handler({"key": "TS-99999"})

    assert result["code"] == "not_found"
    assert "TS-99999" in result["error"]


def test_missing_credentials_returns_credentials_required(monkeypatch):
    """If JIRA_EMAIL or JIRA_API_TOKEN is unset, return credentials_required
    WITHOUT making a network call."""
    monkeypatch.delenv("JIRA_EMAIL", raising=False)
    monkeypatch.delenv("JIRA_API_TOKEN", raising=False)
    monkeypatch.setattr(
        "backend.tools.jira_live_tools.JIRA_BASE_URL",
        "https://moveinsync.atlassian.net",
    )

    from backend.tools.jira_live_tools import _jira_live_get_ticket_handler

    with patch("urllib.request.urlopen") as mock_open:
        result = _jira_live_get_ticket_handler({"key": "TS-12345"})

    assert result["code"] == "credentials_required"
    # No network call should have been made
    assert mock_open.call_count == 0


def test_invalid_key_format_short_circuits(monkeypatch):
    """A malformed key never touches the network."""
    monkeypatch.setenv("JIRA_EMAIL", "test@example.com")
    monkeypatch.setenv("JIRA_API_TOKEN", "fake-token-1234")
    monkeypatch.setattr(
        "backend.tools.jira_live_tools.JIRA_BASE_URL",
        "https://moveinsync.atlassian.net",
    )

    from backend.tools.jira_live_tools import _jira_live_get_ticket_handler

    bad_keys = ["", "lowercase-1", "TS_123", "12-TS", "TS-", "TS-abc", "not-a-key"]
    for k in bad_keys:
        with patch("urllib.request.urlopen") as mock_open:
            result = _jira_live_get_ticket_handler({"key": k})
        assert result["code"] == "invalid_key_format", f"key={k!r} should have been rejected"
        assert mock_open.call_count == 0, f"key={k!r} reached the network"


def test_network_error_returns_network_error_code(monkeypatch):
    """URLError / timeout / OSError → network_error envelope."""
    monkeypatch.setenv("JIRA_EMAIL", "test@example.com")
    monkeypatch.setenv("JIRA_API_TOKEN", "fake-token-1234")
    monkeypatch.setattr(
        "backend.tools.jira_live_tools.JIRA_BASE_URL",
        "https://moveinsync.atlassian.net",
    )

    from backend.tools.jira_live_tools import _jira_live_get_ticket_handler

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused")):
        result = _jira_live_get_ticket_handler({"key": "TS-12345"})

    assert result["code"] == "network_error"
    assert "connection refused" in result["error"]
