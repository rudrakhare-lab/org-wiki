# tests/test_auth_store.py
import importlib
import pytest
from pathlib import Path


@pytest.fixture
def isolated_auth(tmp_path, monkeypatch):
    """Point auth_store at a fresh SQLite under tmp_path."""
    auth_dir = tmp_path / "raw" / "auth"
    auth_dir.mkdir(parents=True)
    db = auth_dir / "auth.sqlite"

    import backend.auth_store as auth_module
    importlib.reload(auth_module)
    monkeypatch.setattr(auth_module, "AUTH_DB", db, raising=False)
    monkeypatch.setattr(auth_module, "AUTH_DIR", auth_dir, raising=False)
    yield auth_module


def test_create_and_get_user(isolated_auth):
    as_ = isolated_auth
    as_.create_user("alice@example.com", role="contributor", created_by="admin@example.com")
    user = as_.get_user("alice@example.com")
    assert user is not None
    assert user["role"] == "contributor"
    assert user["email"] == "alice@example.com"


def test_create_and_lookup_token(isolated_auth):
    as_ = isolated_auth
    as_.create_user("bob@example.com", role="viewer")
    token = as_.create_token("bob@example.com", expires_at="2099-01-01")
    assert len(token) == 32

    result = as_.lookup_token(token)
    assert result is not None
    assert result["email"] == "bob@example.com"
    assert result["role"] == "viewer"


def test_revoked_token_not_found(isolated_auth):
    as_ = isolated_auth
    as_.create_user("carol@example.com", role="viewer")
    token = as_.create_token("carol@example.com")
    as_.revoke_token(token)
    assert as_.lookup_token(token) is None


def test_expired_token_not_found(isolated_auth):
    as_ = isolated_auth
    as_.create_user("dave@example.com", role="viewer")
    token = as_.create_token("dave@example.com", expires_at="2020-01-01")
    assert as_.lookup_token(token) is None


def test_list_tokens_for_user(isolated_auth):
    as_ = isolated_auth
    as_.create_user("eve@example.com", role="viewer")
    t1 = as_.create_token("eve@example.com")
    t2 = as_.create_token("eve@example.com")
    tokens = as_.list_tokens("eve@example.com")
    assert len(tokens) == 2


def test_delete_user_cascades_tokens(isolated_auth):
    as_ = isolated_auth
    as_.create_user("frank@example.com", role="viewer")
    token = as_.create_token("frank@example.com")
    as_.delete_user("frank@example.com")
    assert as_.get_user("frank@example.com") is None
    assert as_.lookup_token(token) is None
