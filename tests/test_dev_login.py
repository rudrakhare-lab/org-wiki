"""Dev-only email-login path: flag gating, provisioning, and prod-inert behavior."""
import importlib
import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize("value", ["1", "true", "True", "TRUE", "yes", "on"])
def test_dev_login_enabled_flag_truthy(monkeypatch, value):
    import backend.config as config
    monkeypatch.setenv("CONWO_DEV_LOGIN", value)
    importlib.reload(config)
    assert config.dev_login_enabled() is True


@pytest.mark.parametrize("value", ["0", "false", "no", "off", ""])
def test_dev_login_enabled_flag_falsy(monkeypatch, value):
    import backend.config as config
    monkeypatch.setenv("CONWO_DEV_LOGIN", value)
    importlib.reload(config)
    assert config.dev_login_enabled() is False


def test_dev_login_enabled_flag_unset(monkeypatch):
    import backend.config as config
    monkeypatch.delenv("CONWO_DEV_LOGIN", raising=False)
    importlib.reload(config)
    assert config.dev_login_enabled() is False


@pytest.fixture
def dev_client(clean_db, monkeypatch):
    """TestClient with dev-login ON, against the isolated test DB."""
    monkeypatch.setenv("CONWO_DEV_LOGIN", "true")
    from backend import api as api_module
    from backend import auth_store
    client = TestClient(api_module.app, raise_server_exceptions=False)
    return client, auth_store


def test_auth_config_reports_flag(dev_client):
    client, _ = dev_client
    assert client.get("/auth/config").json() == {"dev_login": True}


def test_dev_login_provisions_general_unapproved(dev_client):
    client, auth = dev_client
    r = client.post("/auth/dev-login", json={"email": "general-test@moveinsync.com"})
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "general-test@moveinsync.com"
    assert body["role"] == "general"
    assert body["approved"] is False
    assert len(body["token"]) == 32
    u = auth.get_user("general-test@moveinsync.com")
    assert u["role"] == "general" and u["approved"] is False


def test_dev_login_rejects_non_domain_email(dev_client):
    client, _ = dev_client
    r = client.post("/auth/dev-login", json={"email": "outsider@gmail.com"})
    assert r.status_code == 403


def test_dev_login_disabled_returns_403(clean_db, monkeypatch):
    monkeypatch.delenv("CONWO_DEV_LOGIN", raising=False)
    from backend import api as api_module
    client = TestClient(api_module.app, raise_server_exceptions=False)
    assert client.get("/auth/config").json() == {"dev_login": False}
    r = client.post("/auth/dev-login", json={"email": "x@moveinsync.com"})
    assert r.status_code == 403
