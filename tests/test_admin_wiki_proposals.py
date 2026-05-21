# tests/test_admin_wiki_proposals.py
import importlib
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


@pytest.fixture
def admin_client(tmp_path, monkeypatch):
    """TestClient with admin auth, fresh auth_store, and isolated wiki_proposals store."""
    # Set up isolated auth store
    import backend.auth_store as auth_module
    auth_dir = tmp_path / "raw" / "auth"
    auth_dir.mkdir(parents=True)
    importlib.reload(auth_module)
    monkeypatch.setattr(auth_module, "AUTH_DB", auth_dir / "auth.sqlite", raising=False)
    monkeypatch.setattr(auth_module, "AUTH_DIR", auth_dir, raising=False)

    # Set up isolated wiki_proposals store
    import backend.wiki_proposals as wp_module
    importlib.reload(wp_module)
    feedback_dir = tmp_path / "raw" / "feedback"
    feedback_dir.mkdir(parents=True)
    proposals_file = feedback_dir / "wiki_proposals.jsonl"
    monkeypatch.setattr(wp_module, "PROPOSALS_FILE", proposals_file, raising=False)
    monkeypatch.setattr(wp_module, "FEEDBACK_DIR", feedback_dir, raising=False)

    # Reload api so it picks up the patched modules
    from backend import api as api_module
    importlib.reload(api_module)
    client = TestClient(api_module.app)

    # Patch lookup_user_by_token so admin Bearer token works
    admin_user = {"email": "admin@example.com", "role": "admin", "token": "admin-token"}
    with patch("backend.config.lookup_user_by_token") as mock_lookup:
        mock_lookup.side_effect = lambda t: admin_user if t == "admin-token" else None
        yield client, wp_module


def test_list_proposals_empty(admin_client):
    client, _ = admin_client
    r = client.get(
        "/admin/wiki/proposals",
        headers={"Authorization": "Bearer admin-token"},
    )
    assert r.status_code == 200
    assert r.json() == {"proposals": []}


def test_list_proposals_with_filter(admin_client):
    client, wp = admin_client
    # Create a proposal directly via wiki_proposals module
    pid = wp.create_proposal(
        page_path="modules/visitor-management.md",
        proposed_change="OTP is required",
        submitter_email="alice@example.com",
    )
    r = client.get(
        "/admin/wiki/proposals?status=pending",
        headers={"Authorization": "Bearer admin-token"},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["proposals"]) == 1
    assert data["proposals"][0]["id"] == pid
    assert data["proposals"][0]["status"] == "pending"


def test_apply_proposal_not_found(admin_client):
    client, _ = admin_client
    with patch("backend.admin_api.apply_wiki_proposal") as mock_apply:
        mock_apply.return_value = {"success": False, "error": "Proposal not found: nonexistent-id"}
        r = client.post(
            "/admin/wiki/proposals/nonexistent-id/apply",
            headers={"Authorization": "Bearer admin-token"},
        )
    assert r.status_code == 404
    assert "not found" in r.json()["detail"].lower()


def test_reject_proposal(admin_client):
    client, wp = admin_client
    pid = wp.create_proposal(
        page_path="modules/desk-management.md",
        proposed_change="Incorrect booking slot info",
        submitter_email="bob@example.com",
    )
    r = client.post(
        f"/admin/wiki/proposals/{pid}/reject",
        json={"admin_note": "stale"},
        headers={"Authorization": "Bearer admin-token"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["status"] == "rejected"
    assert data["proposal_id"] == pid

    # Verify the proposal was actually updated in the store
    p = wp.get_proposal(pid)
    assert p["status"] == "rejected"
    assert p["admin_note"] == "stale"


def test_trigger_drive_sync_starts_process(admin_client):
    client, _ = admin_client
    mock_proc = MagicMock()
    mock_proc.pid = 12345
    with patch("backend.admin_api.subprocess.Popen", return_value=mock_proc) as mock_popen:
        r = client.post(
            "/admin/trigger-drive-sync",
            headers={"Authorization": "Bearer admin-token"},
        )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "started"
    assert isinstance(data["pid"], int)
    assert data["pid"] == 12345
    mock_popen.assert_called_once()
