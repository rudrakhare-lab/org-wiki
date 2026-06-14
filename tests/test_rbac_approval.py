"""
RBAC + user-approval flow tests.

Covers the three-role model (admin / developer / general) and the approval gate:
  (a) an unapproved user is blocked from querying (/query → 403, gate before LLM)
  (b) a developer can reach the ingest endpoints but NOT the admin endpoints
  (c) a general user can ask/search but NOT ingest or browse the graph

Plus auth_store defaults (general + unapproved) and the admin approve / role-change
endpoints.

These run against the isolated `wis_conwo_test` Postgres DB (see conftest.py), which
is migrated with 070_roles_and_approval.sql (the `approved` column) at session start.
Tokens are minted with the real auth_store and resolved through the real auth chain
(_get_user → config.lookup_user_by_token → auth_store.lookup_token) — no auth mocking,
so the approval plumbing is exercised end to end. The orchestrator is mocked only so
the /query gate tests never spawn an LLM call.
"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.fixture
def rbac(clean_db):
    """Truncated test DB + a TestClient + the live auth_store.

    NOTE: TestClient is NOT used as a context manager on purpose — that skips
    lifespan startup (the test DB is already migrated by conftest), matching the
    existing auth tests. raise_server_exceptions=False so a mocked-orchestrator
    failure surfaces as a 500 response instead of bubbling into the test.
    """
    from backend import api as api_module
    from backend import auth_store
    client = TestClient(api_module.app, raise_server_exceptions=False)
    return client, auth_store


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── auth_store defaults (migration behaviour) ─────────────────────────────────
def test_create_user_defaults_to_general_unapproved(rbac):
    _client, auth = rbac
    created = auth.create_user("x@moveinsync.com")
    assert created["role"] == "general"
    assert created["approved"] is False
    fetched = auth.get_user("x@moveinsync.com")
    assert fetched["role"] == "general"
    assert fetched["approved"] is False


def test_lookup_token_carries_approved(rbac):
    _client, auth = rbac
    auth.create_user("look@moveinsync.com", role="general", approved=True)
    tok = auth.create_token("look@moveinsync.com")
    u = auth.lookup_token(tok)
    assert u is not None
    assert u["approved"] is True
    assert u["role"] == "general"


# ── (a) unapproved user blocked from querying ─────────────────────────────────
def test_unapproved_user_blocked_from_query(rbac):
    client, auth = rbac
    auth.create_user("pending@moveinsync.com", role="general", approved=False)
    tok = auth.create_token("pending@moveinsync.com")
    with patch("backend.api.orchestrator.run") as mrun:
        r = client.post("/query", json={"question": "what is desk booking?"},
                        headers=_bearer(tok))
    assert r.status_code == 403
    assert "pending admin approval" in r.json()["detail"].lower()
    mrun.assert_not_called()  # gate fired before any LLM work


def test_approved_user_passes_query_gate(rbac):
    client, auth = rbac
    auth.create_user("ok@moveinsync.com", role="general", approved=True)
    tok = auth.create_token("ok@moveinsync.com")
    # Mock the orchestrator so we never hit an LLM; reaching it proves the gate passed.
    with patch("backend.api.orchestrator.run", side_effect=RuntimeError("reached")) as mrun:
        r = client.post("/query", json={"question": "what is desk booking?"},
                        headers=_bearer(tok))
    assert mrun.called
    assert r.status_code != 403


# ── (b) developer: ingest yes, admin no ───────────────────────────────────────
def test_developer_can_access_ingest(rbac):
    client, auth = rbac
    auth.create_user("dev@moveinsync.com", role="developer", approved=True)
    tok = auth.create_token("dev@moveinsync.com")
    # Empty body → the dev-or-admin guard passes, so we get past 403 (422 for the
    # missing body is fine — it proves the guard let us through).
    r = client.post("/api/ingest/plan", json={}, headers=_bearer(tok))
    assert r.status_code != 403


def test_developer_cannot_access_admin(rbac):
    client, auth = rbac
    auth.create_user("dev2@moveinsync.com", role="developer", approved=True)
    tok = auth.create_token("dev2@moveinsync.com")
    r = client.post("/admin/trigger-sync", headers=_bearer(tok))
    assert r.status_code == 403


def test_developer_can_access_graph(rbac):
    client, auth = rbac
    auth.create_user("dev3@moveinsync.com", role="developer", approved=True)
    tok = auth.create_token("dev3@moveinsync.com")
    r = client.get("/api/wiki/graph", headers=_bearer(tok))
    assert r.status_code != 403


# ── (c) general: ask/search yes, ingest/graph no ──────────────────────────────
def test_general_cannot_access_ingest(rbac):
    client, auth = rbac
    auth.create_user("gen@moveinsync.com", role="general", approved=True)
    tok = auth.create_token("gen@moveinsync.com")
    r = client.post("/api/ingest/plan", json={}, headers=_bearer(tok))
    assert r.status_code == 403


def test_general_cannot_access_graph(rbac):
    client, auth = rbac
    auth.create_user("gen2@moveinsync.com", role="general", approved=True)
    tok = auth.create_token("gen2@moveinsync.com")
    r = client.get("/api/wiki/graph", headers=_bearer(tok))
    assert r.status_code == 403


def test_general_can_access_search(rbac):
    client, auth = rbac
    auth.create_user("gen3@moveinsync.com", role="general", approved=True)
    tok = auth.create_token("gen3@moveinsync.com")
    # /search is open to all; mock the retrieval so the test stays hermetic.
    with patch("backend.api.orchestrator.search_only", return_value={
        "wiki_pages": [], "jira_markdown": "",
        "jira_buckets": {"LATEST": [], "HISTORICAL": [], "STALE-OPEN": []},
        "jira_keywords": [],
    }):
        r = client.post("/search", json={"question": "desk booking", "server": "com"},
                        headers=_bearer(tok))
    assert r.status_code != 403


# ── admin approve + role-change endpoints ─────────────────────────────────────
def test_admin_approve_endpoint_flips_flag(rbac):
    client, auth = rbac
    auth.create_user("admin@moveinsync.com", role="admin", approved=True)
    admin_tok = auth.create_token("admin@moveinsync.com")
    auth.create_user("topromote@moveinsync.com", role="general", approved=False)

    r = client.post("/admin/users/topromote@moveinsync.com/approve",
                    headers=_bearer(admin_tok))
    assert r.status_code == 200
    assert r.json()["approved"] is True
    assert auth.get_user("topromote@moveinsync.com")["approved"] is True


def test_admin_change_role_endpoint(rbac):
    client, auth = rbac
    auth.create_user("admin2@moveinsync.com", role="admin", approved=True)
    admin_tok = auth.create_token("admin2@moveinsync.com")
    auth.create_user("rolee@moveinsync.com", role="general", approved=True)

    r = client.patch("/admin/users/rolee@moveinsync.com/role",
                     json={"role": "developer"}, headers=_bearer(admin_tok))
    assert r.status_code == 200
    assert auth.get_user("rolee@moveinsync.com")["role"] == "developer"


def test_non_admin_cannot_approve(rbac):
    client, auth = rbac
    auth.create_user("dev4@moveinsync.com", role="developer", approved=True)
    dev_tok = auth.create_token("dev4@moveinsync.com")
    auth.create_user("victim@moveinsync.com", role="general", approved=False)
    r = client.post("/admin/users/victim@moveinsync.com/approve", headers=_bearer(dev_tok))
    assert r.status_code == 403
    assert auth.get_user("victim@moveinsync.com")["approved"] is False


def test_approve_with_role_sets_both(rbac):
    client, auth = rbac
    auth.create_user("admin@moveinsync.com", role="admin", approved=True)
    admin_tok = auth.create_token("admin@moveinsync.com")
    auth.create_user("p@moveinsync.com", role="general", approved=False)
    r = client.post("/admin/users/p@moveinsync.com/approve",
                    json={"role": "developer"}, headers=_bearer(admin_tok))
    assert r.status_code == 200
    u = auth.get_user("p@moveinsync.com")
    assert u["approved"] is True
    assert u["role"] == "developer"


def test_approve_without_role_keeps_role(rbac):
    client, auth = rbac
    auth.create_user("admin2@moveinsync.com", role="admin", approved=True)
    admin_tok = auth.create_token("admin2@moveinsync.com")
    auth.create_user("q@moveinsync.com", role="general", approved=False)
    r = client.post("/admin/users/q@moveinsync.com/approve",
                    json={}, headers=_bearer(admin_tok))
    assert r.status_code == 200
    u = auth.get_user("q@moveinsync.com")
    assert u["approved"] is True
    assert u["role"] == "general"
