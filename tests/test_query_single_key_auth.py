"""Tests for Phase 1.5 — single-key deployment enforcement at /query.

These tests pin the new contract:
  - api-mode /query without a Bearer token → 401
  - claude_api_key in request body → 422 (extra fields forbidden)
  - missing ANTHROPIC_API_KEY → 503 with the user-facing message
  - missing ANTHROPIC_API_KEY at startup → loud warning logged
"""
from __future__ import annotations

import importlib
import logging
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Fresh api app with isolated auth store."""
    import backend.auth_store as auth_module
    auth_dir = tmp_path / "raw" / "auth"
    auth_dir.mkdir(parents=True)
    importlib.reload(auth_module)
    monkeypatch.setattr(auth_module, "AUTH_DB", auth_dir / "auth.sqlite", raising=False)
    monkeypatch.setattr(auth_module, "AUTH_DIR", auth_dir, raising=False)

    from backend import api as api_module
    importlib.reload(api_module)
    return TestClient(api_module.app)


def test_api_mode_query_without_bearer_token_returns_401(client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-server-key")
    r = client.post("/query", json={"question": "What is visitor management?", "mode": "api"})
    assert r.status_code == 401
    assert "Sign in" in r.json()["detail"]


def test_query_rejects_claude_api_key_in_body(client, monkeypatch):
    """Pydantic `extra: forbid` must reject the field at the schema layer —
    no path exists for a request-supplied key to influence the backend."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-server-key")
    user = {"email": "u@example.com", "role": "viewer", "token": "user-tok"}
    with patch("backend.config.lookup_user_by_token",
               side_effect=lambda t: user if t == "user-tok" else None):
        r = client.post(
            "/query",
            json={
                "question": "What is visitor management?",
                "mode": "api",
                "claude_api_key": "sk-attacker-supplied",
            },
            headers={"Authorization": "Bearer user-tok"},
        )
    assert r.status_code == 422
    detail = r.json()["detail"]
    # Pydantic puts the offending field name in the error
    assert any("claude_api_key" in str(d) for d in detail), detail


def test_query_returns_503_when_server_key_unset(client, monkeypatch):
    """When the server has no key, a logged-in user gets a clear 503 with the
    user-facing message — not a stack trace, not a generic 500."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    user = {"email": "u@example.com", "role": "viewer", "token": "user-tok"}
    with patch("backend.config.lookup_user_by_token",
               side_effect=lambda t: user if t == "user-tok" else None):
        r = client.post(
            "/query",
            json={"question": "What is visitor management?", "mode": "api"},
            headers={"Authorization": "Bearer user-tok"},
        )
    assert r.status_code == 503
    assert r.json()["detail"] == "This deployment is missing an API key. Contact your admin."


def test_lifespan_warns_when_anthropic_key_missing(tmp_path, monkeypatch, caplog):
    """Server must come up without ANTHROPIC_API_KEY (so admin endpoints stay
    available), but it must log a loud WARNING so a misdeploy is visible."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    # Reload api so the lifespan runs against the patched env
    from backend import api as api_module
    importlib.reload(api_module)

    caplog.set_level(logging.WARNING, logger="uvicorn.error")
    with TestClient(api_module.app):
        pass  # lifespan startup runs on context entry

    assert any(
        "ANTHROPIC_API_KEY is not set" in rec.message
        for rec in caplog.records
    ), [r.message for r in caplog.records]


def test_lifespan_does_not_warn_when_anthropic_key_set(monkeypatch, caplog):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-server-key")
    from backend import api as api_module
    importlib.reload(api_module)
    caplog.set_level(logging.WARNING, logger="uvicorn.error")
    with TestClient(api_module.app):
        pass
    assert not any(
        "ANTHROPIC_API_KEY is not set" in rec.message
        for rec in caplog.records
    )
