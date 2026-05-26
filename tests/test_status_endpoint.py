"""Tests for the public /status endpoint — Pass 3 of the frontend operational
context banner work. The endpoint surfaces Jira mirror age + wiki page count to
any authenticated user, plus pending-review count for admins."""
from __future__ import annotations

import importlib
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_with_users(tmp_path, monkeypatch):
    """TestClient with the api app reloaded against a fresh auth store, plus a
    parametrizable lookup_user_by_token patch so each test can configure roles."""
    import backend.auth_store as auth_module
    auth_dir = tmp_path / "raw" / "auth"
    auth_dir.mkdir(parents=True)
    importlib.reload(auth_module)
    monkeypatch.setattr(auth_module, "AUTH_DB", auth_dir / "auth.sqlite", raising=False)
    monkeypatch.setattr(auth_module, "AUTH_DIR", auth_dir, raising=False)

    from backend import api as api_module
    importlib.reload(api_module)
    client = TestClient(api_module.app)
    yield client, api_module


def _fake_sync_status(success_ts: str = "", ticket_count: int = 5):
    """Returns a sync-status payload shaped like admin_api.get_sync_status."""
    return {
        "jira": {
            "last_log_line": "{}",
            "most_recent_successful_sync": success_ts,
            "last_sync_line": "{}",
            "ticket_count": ticket_count,
        },
        "drive": {"last_sync": "", "file_count": 0},
        "feedback": {"pending_count": 0},
    }


def test_status_requires_authentication(client_with_users):
    client, _ = client_with_users
    r = client.get("/status")
    assert r.status_code == 401


def test_status_viewer_sees_freshness_no_admin_field(client_with_users):
    """A viewer-role user gets freshness fields but pending_admin_review_count
    stays at 0 even when proposals exist (the count is admin-gated)."""
    client, api_module = client_with_users
    viewer = {"email": "v@example.com", "role": "viewer", "token": "viewer-tok"}
    fresh_ts = "2026-05-25T10:00:00+00:00"

    with patch("backend.config.lookup_user_by_token",
               side_effect=lambda t: viewer if t == "viewer-tok" else None), \
         patch("backend.admin_api.get_sync_status",
               return_value=_fake_sync_status(success_ts=fresh_ts)), \
         patch("backend.wiki_retriever.page_count", return_value=42), \
         patch("backend.wiki_proposals.list_proposals", return_value=[{"id": "p1"}, {"id": "p2"}]):
        r = client.get("/status", headers={"Authorization": "Bearer viewer-tok"})

    assert r.status_code == 200
    body = r.json()
    assert body["wiki_page_count"] == 42
    assert body["last_successful_sync"] == fresh_ts
    assert body["jira_mirror_age_hours"] is not None  # actual age — varies
    assert body["pending_admin_review_count"] == 0, "viewer must not see the proposal queue size"


def test_status_admin_includes_pending_review_count(client_with_users):
    client, _ = client_with_users
    admin = {"email": "a@example.com", "role": "admin", "token": "admin-tok"}

    with patch("backend.config.lookup_user_by_token",
               side_effect=lambda t: admin if t == "admin-tok" else None), \
         patch("backend.admin_api.get_sync_status",
               return_value=_fake_sync_status(success_ts="2026-05-25T10:00:00+00:00")), \
         patch("backend.wiki_retriever.page_count", return_value=10), \
         patch("backend.wiki_proposals.list_proposals", return_value=[{"id": "p1"}, {"id": "p2"}, {"id": "p3"}]):
        r = client.get("/status", headers={"Authorization": "Bearer admin-tok"})

    assert r.status_code == 200
    body = r.json()
    assert body["pending_admin_review_count"] == 3


def test_status_handles_missing_sync_timestamp(client_with_users):
    """When no successful sync has ever been logged, age_hours is null and
    last_successful_sync is null — the frontend banner should render an
    'unknown' state rather than a misleading number."""
    client, _ = client_with_users
    viewer = {"email": "v@example.com", "role": "viewer", "token": "viewer-tok"}

    with patch("backend.config.lookup_user_by_token",
               side_effect=lambda t: viewer if t == "viewer-tok" else None), \
         patch("backend.admin_api.get_sync_status",
               return_value=_fake_sync_status(success_ts="")), \
         patch("backend.wiki_retriever.page_count", return_value=10):
        r = client.get("/status", headers={"Authorization": "Bearer viewer-tok"})

    assert r.status_code == 200
    body = r.json()
    assert body["last_successful_sync"] is None
    assert body["jira_mirror_age_hours"] is None
