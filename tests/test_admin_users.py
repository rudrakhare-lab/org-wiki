# tests/test_admin_users.py
import importlib
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch


@pytest.fixture
def admin_client(tmp_path, monkeypatch):
    """TestClient with admin auth and fresh auth_store."""
    import backend.auth_store as auth_module
    auth_dir = tmp_path / "raw" / "auth"
    auth_dir.mkdir(parents=True)
    importlib.reload(auth_module)
    monkeypatch.setattr(auth_module, "AUTH_DB", auth_dir / "auth.sqlite", raising=False)
    monkeypatch.setattr(auth_module, "AUTH_DIR", auth_dir, raising=False)

    # Reload api so it picks up the patched auth_store
    from backend import api as api_module
    importlib.reload(api_module)
    client = TestClient(api_module.app)

    # Patch lookup_user_by_token so admin Bearer token works
    admin_user = {"email": "admin@example.com", "role": "admin", "token": "admin-token"}
    with patch("backend.config.lookup_user_by_token") as mock_lookup:
        mock_lookup.side_effect = lambda t: admin_user if t == "admin-token" else None
        yield client, auth_module


def test_create_user_and_token(admin_client):
    client, _ = admin_client
    r = client.post(
        "/admin/users",
        json={"email": "newuser@example.com", "role": "contributor"},
        headers={"Authorization": "Bearer admin-token"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == "newuser@example.com"
    assert "token" in data


def test_list_users(admin_client):
    client, as_ = admin_client
    as_.create_user("user1@example.com", role="viewer")
    r = client.get("/admin/users", headers={"Authorization": "Bearer admin-token"})
    assert r.status_code == 200
    assert any(u["email"] == "user1@example.com" for u in r.json()["users"])


def test_delete_user(admin_client):
    client, as_ = admin_client
    as_.create_user("todelete@example.com", role="viewer")
    r = client.delete(
        "/admin/users/todelete@example.com",
        headers={"Authorization": "Bearer admin-token"},
    )
    assert r.status_code == 200
    assert r.json()["deleted"] is True


def test_revoke_token(admin_client):
    client, as_ = admin_client
    as_.create_user("trevoke@example.com", role="viewer")
    token = as_.create_token("trevoke@example.com")
    r = client.delete(
        f"/admin/tokens/{token}",
        headers={"Authorization": "Bearer admin-token"},
    )
    assert r.status_code == 200
    assert as_.lookup_token(token) is None
