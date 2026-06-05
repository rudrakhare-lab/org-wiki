import importlib
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Fresh TestClient with isolated auth_store and GOOGLE_CLIENT_ID configured."""
    import backend.auth_store as auth_module
    auth_dir = tmp_path / "raw" / "auth"
    auth_dir.mkdir(parents=True)
    monkeypatch.setattr(auth_module, "AUTH_DB", auth_dir / "auth.sqlite", raising=False)
    monkeypatch.setattr(auth_module, "AUTH_DIR", auth_dir, raising=False)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
    from backend import api as api_module
    importlib.reload(api_module)
    return TestClient(api_module.app), auth_module


def _mock_verify(email="rudra.khare@moveinsync.com", name="Rudra Khare"):
    return {"email": email, "name": name, "picture": "https://example.com/pic.jpg"}


def test_google_login_provisions_new_user_and_returns_token(client):
    test_client, auth_module = client
    with patch("backend.api.verify_google_credential", return_value=_mock_verify()):
        resp = test_client.post("/auth/google", json={"credential": "fake-id-token"})
    assert resp.status_code == 200
    body = resp.json()
    assert "token" in body
    assert body["email"] == "rudra.khare@moveinsync.com"
    assert body["name"] == "Rudra Khare"
    assert len(body["token"]) == 32
    user = auth_module.get_user("rudra.khare@moveinsync.com")
    assert user is not None
    assert user["role"] == "viewer"


def test_google_login_returns_token_for_existing_user(client):
    test_client, auth_module = client
    auth_module.create_user("existing@moveinsync.com", role="viewer")
    with patch("backend.api.verify_google_credential",
               return_value=_mock_verify(email="existing@moveinsync.com", name="Existing")):
        resp = test_client.post("/auth/google", json={"credential": "fake-id-token"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "existing@moveinsync.com"


def test_google_login_rejects_wrong_domain(client):
    test_client, _ = client
    with patch("backend.api.verify_google_credential",
               side_effect=ValueError("Domain 'gmail.com' not allowed")):
        resp = test_client.post("/auth/google", json={"credential": "outsider-token"})
    assert resp.status_code == 403
    assert "not allowed" in resp.json()["detail"]


def test_google_login_rejects_invalid_token(client):
    test_client, _ = client
    with patch("backend.api.verify_google_credential",
               side_effect=ValueError("Token signature invalid")):
        resp = test_client.post("/auth/google", json={"credential": "garbage"})
    assert resp.status_code == 403


def test_google_login_returns_500_when_client_id_not_configured(tmp_path, monkeypatch):
    import backend.auth_store as auth_module
    auth_dir = tmp_path / "raw" / "auth"
    auth_dir.mkdir(parents=True)
    monkeypatch.setattr(auth_module, "AUTH_DB", auth_dir / "auth.sqlite", raising=False)
    monkeypatch.setattr(auth_module, "AUTH_DIR", auth_dir, raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    from backend import api as api_module
    importlib.reload(api_module)
    test_client = TestClient(api_module.app)
    resp = test_client.post("/auth/google", json={"credential": "any"})
    assert resp.status_code == 500
    assert "GOOGLE_CLIENT_ID" in resp.json()["detail"]
