import pytest
from unittest.mock import patch

from backend.config import resolve_api_key, lookup_user_by_token


def test_resolve_api_key_prefers_server_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-server-key")
    assert resolve_api_key("sk-caller-key") == "sk-server-key"


def test_resolve_api_key_falls_back_to_caller(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert resolve_api_key("sk-caller-key") == "sk-caller-key"


def test_resolve_api_key_raises_when_neither(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ValueError, match="No Anthropic API key"):
        resolve_api_key(None)


def test_lookup_user_by_token_rejects_expired_token():
    fake_users = {
        "alice": {
            "email": "alice@moveinsync.com",
            "role": "contributor",
            "token": "abc123",
            "expires_at": "2020-01-01",  # past date
        }
    }
    with patch("backend.config._load_users", return_value=fake_users):
        result = lookup_user_by_token("abc123")
    assert result is None


def test_lookup_user_by_token_accepts_valid_token():
    fake_users = {
        "alice": {
            "email": "alice@moveinsync.com",
            "role": "contributor",
            "token": "abc123",
            "expires_at": "2099-01-01",
        }
    }
    with patch("backend.config._load_users", return_value=fake_users):
        result = lookup_user_by_token("abc123")
    assert result is not None
    assert result["email"] == "alice@moveinsync.com"


def test_lookup_user_by_token_no_expiry_always_valid():
    fake_users = {
        "admin": {
            "email": "admin@moveinsync.com",
            "role": "admin",
            "token": "admintoken",
        }
    }
    with patch("backend.config._load_users", return_value=fake_users):
        result = lookup_user_by_token("admintoken")
    assert result is not None


def test_lookup_prefers_auth_store_over_toml(tmp_path, monkeypatch):
    """When auth.sqlite has a valid token, TOML is not consulted."""
    import importlib
    import backend.auth_store as auth_module
    auth_dir = tmp_path / "raw" / "auth"
    auth_dir.mkdir(parents=True)
    db = auth_dir / "auth.sqlite"
    importlib.reload(auth_module)
    monkeypatch.setattr(auth_module, "AUTH_DB", db, raising=False)
    monkeypatch.setattr(auth_module, "AUTH_DIR", auth_dir, raising=False)

    auth_module.create_user("store_user@example.com", role="viewer")
    token = auth_module.create_token("store_user@example.com")

    # TOML has no such token
    with patch("backend.config._load_users", return_value={}):
        result = lookup_user_by_token(token)

    assert result is not None
    assert result["email"] == "store_user@example.com"
