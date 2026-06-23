"""Admin agent-access endpoints: inbox, approve/reject/grant/revoke, grants."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(clean_db):
    from backend import api, auth_store
    c = TestClient(api.app, raise_server_exceptions=False)
    auth_store.create_user("admin@moveinsync.com", role="admin", approved=True)
    tok = auth_store.create_token("admin@moveinsync.com")
    return c, {"Authorization": f"Bearer {tok}"}


def test_inbox_lists_pending(client):
    c, h = client
    from backend import agent_access
    agent_access.request_access("g@moveinsync.com", "infosec")
    rows = c.get("/admin/agent-access/requests", headers=h).json()
    assert any(r["user_email"] == "g@moveinsync.com" and r["agent_id"] == "infosec" for r in rows)


def test_approve_then_grants_list(client):
    c, h = client
    from backend import agent_access
    agent_access.request_access("g@moveinsync.com", "infosec")
    assert c.post("/admin/agent-access/g@moveinsync.com/infosec/approve", headers=h).status_code == 200
    grants = c.get("/admin/agent-access/grants", headers=h).json()
    assert any(g["user_email"] == "g@moveinsync.com" for g in grants)


def test_grant_then_revoke(client):
    c, h = client
    from backend import agent_access
    assert c.post("/admin/agent-access/g@moveinsync.com/infosec/grant", headers=h).status_code == 200
    assert agent_access.has_access({"email": "g@moveinsync.com", "role": "general"}, "infosec") is True
    assert c.request("DELETE", "/admin/agent-access/g@moveinsync.com/infosec", headers=h).status_code == 200
    assert agent_access.has_access({"email": "g@moveinsync.com", "role": "general"}, "infosec") is False


def test_reject(client):
    c, h = client
    from backend import agent_access
    agent_access.request_access("g@moveinsync.com", "infosec")
    assert c.post("/admin/agent-access/g@moveinsync.com/infosec/reject", headers=h).status_code == 200
    assert agent_access.list_for_user("g@moveinsync.com")["infosec"] == "rejected"


def test_non_admin_denied(client):
    c, _ = client
    from backend import auth_store
    auth_store.create_user("g@moveinsync.com", role="general", approved=True)
    tok = auth_store.create_token("g@moveinsync.com")
    r = c.get("/admin/agent-access/requests", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 403
