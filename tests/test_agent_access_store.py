"""agent_access store: grant/request/revoke lifecycle + has_access policy."""
import pytest
from backend import agent_access


@pytest.fixture(autouse=True)
def clean(clean_db):
    # clean_db (conftest) truncates the test DB between tests.
    yield


ADMIN = {"email": "admin@x.com", "role": "admin"}
GEN = {"email": "gen@x.com", "role": "general"}


def test_default_agent_open_to_everyone():
    assert agent_access.has_access(GEN, "conwo") is True
    assert agent_access.has_access(None, "conwo") is True


def test_admin_bypasses_for_any_agent():
    assert agent_access.has_access(ADMIN, "infosec") is True


def test_general_denied_without_grant():
    assert agent_access.has_access(GEN, "infosec") is False


def test_request_then_approve_grants_access():
    r = agent_access.request_access("gen@x.com", "infosec")
    assert r == {"agent_id": "infosec", "status": "pending"}
    assert agent_access.has_access(GEN, "infosec") is False        # still pending
    assert agent_access.set_status("gen@x.com", "infosec", "granted", "admin@x.com") is True
    assert agent_access.has_access(GEN, "infosec") is True


def test_revoke_removes_access():
    agent_access.set_status("gen@x.com", "infosec", "granted", "admin@x.com")
    assert agent_access.has_access(GEN, "infosec") is True
    agent_access.set_status("gen@x.com", "infosec", "revoked", "admin@x.com")
    assert agent_access.has_access(GEN, "infosec") is False


def test_request_does_not_downgrade_existing_grant():
    agent_access.set_status("gen@x.com", "infosec", "granted", "admin@x.com")
    agent_access.request_access("gen@x.com", "infosec")            # no-op
    assert agent_access.has_access(GEN, "infosec") is True


def test_list_pending_and_grants_and_for_user():
    agent_access.request_access("gen@x.com", "infosec")
    agent_access.set_status("g2@x.com", "infosec", "granted", "admin@x.com")
    pending = agent_access.list_pending()
    assert any(p["user_email"] == "gen@x.com" and p["agent_id"] == "infosec" for p in pending)
    grants = agent_access.list_grants()
    assert any(g["user_email"] == "g2@x.com" for g in grants)
    assert agent_access.list_for_user("gen@x.com")["infosec"] == "pending"
