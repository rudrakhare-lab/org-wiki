"""
Auth tests for the Claude Code endpoints:
  - default: Bearer token required (401 without)
  - CONWO_LOCAL_CLAUDE_CODE=true: bypass allowed (no token needed)

We don't actually spawn `claude` here — we monkeypatch the streamer to
yield a single event so the request returns 200 quickly. The point is the
auth gate, not the subprocess.
"""
from __future__ import annotations

import importlib
import os
from typing import AsyncIterator

import pytest
from fastapi.testclient import TestClient


def _reload_api() -> "module":
    """Reload backend.api so it re-reads the env var at module import time."""
    from backend import config
    importlib.reload(config)
    from backend import api as api_module
    importlib.reload(api_module)
    return api_module


def _patch_streamer(api_module, monkeypatch) -> None:
    """Replace stream_claude_code with a stub that yields one event."""
    async def _stub(question: str, timeout_seconds: int = 600) -> AsyncIterator[dict]:
        yield {"type": "result", "subtype": "success", "result": "ok"}

    monkeypatch.setattr(api_module, "stream_claude_code", _stub)
    monkeypatch.setattr(api_module, "claude_available", lambda: True)


# ── Default: token required ─────────────────────────────────────────────────

def test_default_query_stream_requires_admin(monkeypatch):
    """Without a valid admin token, /query/stream rejects with 401 (no token) or 403 (wrong role)."""
    monkeypatch.delenv("CONWO_LOCAL_CLAUDE_CODE", raising=False)
    api_module = _reload_api()
    _patch_streamer(api_module, monkeypatch)
    client = TestClient(api_module.app)

    r = client.post("/query/stream", json={"question": "hello world"})
    assert r.status_code in (401, 403), r.text


def test_default_health_says_token_required(monkeypatch):
    monkeypatch.delenv("CONWO_LOCAL_CLAUDE_CODE", raising=False)
    api_module = _reload_api()
    monkeypatch.setattr(api_module, "claude_available", lambda: True)
    client = TestClient(api_module.app)

    r = client.get("/health/claude-code")
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is True
    assert body["local_dev_unauthenticated"] is False
    assert "Bearer token is required" in body["note"]


# ── Local dev: bypass active ────────────────────────────────────────────────

def test_local_dev_bypass_does_not_apply_to_query_stream(monkeypatch):
    """CONWO_LOCAL_CLAUDE_CODE bypass does NOT grant access to /query/stream — admin is required."""
    monkeypatch.setenv("CONWO_LOCAL_CLAUDE_CODE", "true")
    api_module = _reload_api()
    _patch_streamer(api_module, monkeypatch)
    client = TestClient(api_module.app)

    r = client.post("/query/stream", json={"question": "hello world"})
    # Admin is required now; local-dev bypass is not sufficient
    assert r.status_code == 403, r.text


def test_local_dev_health_flag(monkeypatch):
    monkeypatch.setenv("CONWO_LOCAL_CLAUDE_CODE", "1")
    api_module = _reload_api()
    monkeypatch.setattr(api_module, "claude_available", lambda: True)
    client = TestClient(api_module.app)

    r = client.get("/health/claude-code")
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is True
    assert body["local_dev_unauthenticated"] is True
    assert "LOCAL-DEV" in body["note"]


def test_local_dev_does_not_bypass_admin_endpoints(monkeypatch):
    """The bypass is scoped to Claude Code endpoints only — /admin/* must stay locked."""
    monkeypatch.setenv("CONWO_LOCAL_CLAUDE_CODE", "true")
    api_module = _reload_api()
    client = TestClient(api_module.app)

    r = client.get("/admin/sync-status")
    assert r.status_code == 403, r.text


# ── Various env-var truthy spellings ────────────────────────────────────────

@pytest.mark.parametrize("value", ["true", "True", "TRUE", "1", "yes", "on"])
def test_env_var_truthy_spellings(monkeypatch, value):
    monkeypatch.setenv("CONWO_LOCAL_CLAUDE_CODE", value)
    from backend import config
    importlib.reload(config)
    assert config.local_claude_code_enabled() is True


@pytest.mark.parametrize("value", ["false", "0", "no", "off", ""])
def test_env_var_falsy_spellings(monkeypatch, value):
    monkeypatch.setenv("CONWO_LOCAL_CLAUDE_CODE", value)
    from backend import config
    importlib.reload(config)
    assert config.local_claude_code_enabled() is False
