"""Tests that wiki-read and graph endpoints are gated by agent access.

Covers the read-path bypass fix: before this patch, GET /wiki/{path} and
GET /api/wiki/graph resolved the agent from X-Agent-Id but never checked
whether the user actually had access to that agent.
"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.fixture
def client(clean_db):
    from backend import api, auth_store, db, agent_registry

    # Seed a restricted "infosec" agent (same as test_agent_access_api.py).
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO agents (id, display_name, wiki_dir, raw_dir, claude_md, status) "
            "VALUES ('infosec', 'Infosec', 'wiki/', 'raw/', 'CLAUDE.md', 'active') "
            "ON CONFLICT (id) DO NOTHING"
        )
    agent_registry.invalidate_cache()
    yield TestClient(api.app, raise_server_exceptions=False), auth_store
    agent_registry.invalidate_cache()


def _bearer(tok):
    return {"Authorization": f"Bearer {tok}"}


# ---------------------------------------------------------------------------
# GET /wiki/{path} — agent-access gate
# ---------------------------------------------------------------------------


def test_wiki_read_blocked_for_restricted_agent(client):
    """A general user with no grant should get 403 on wiki read for a restricted agent."""
    c, auth = client
    auth.create_user("u1@x.com", role="general", approved=True)
    tok = auth.create_token("u1@x.com")
    r = c.get("/wiki/modules/test", headers={**_bearer(tok), "X-Agent-Id": "infosec"})
    assert r.status_code == 403
    assert "access" in r.json()["detail"].lower()


def test_wiki_read_allowed_for_default_agent(client):
    """Default agent (conwo) is open to all users — gate must not fire."""
    c, auth = client
    auth.create_user("u2@x.com", role="general", approved=True)
    tok = auth.create_token("u2@x.com")
    # We don't care about 404 (page probably doesn't exist in test env);
    # we only care it is NOT 403 from the access gate.
    r = c.get("/wiki/modules/test", headers={**_bearer(tok), "X-Agent-Id": "conwo"})
    assert r.status_code != 403


def test_wiki_read_allowed_after_grant(client):
    """After granting access, the gate must let the user through."""
    c, auth = client
    from backend import agent_access

    auth.create_user("u3@x.com", role="general", approved=True)
    tok = auth.create_token("u3@x.com")
    agent_access.set_status("u3@x.com", "infosec", "granted", "admin@x.com")
    r = c.get("/wiki/modules/test", headers={**_bearer(tok), "X-Agent-Id": "infosec"})
    assert r.status_code != 403


# ---------------------------------------------------------------------------
# GET /api/wiki/graph — agent-access gate
# ---------------------------------------------------------------------------


def test_graph_blocked_for_restricted_agent(client):
    """A general user with no grant should get 403 on graph for a restricted agent."""
    c, auth = client
    auth.create_user("u4@x.com", role="general", approved=True)
    tok = auth.create_token("u4@x.com")
    r = c.get("/api/wiki/graph", headers={**_bearer(tok), "X-Agent-Id": "infosec"})
    assert r.status_code == 403
    assert "access" in r.json()["detail"].lower()


def test_graph_allowed_for_default_agent(client):
    """Default agent (conwo) must not be blocked by the access gate."""
    c, auth = client
    auth.create_user("u5@x.com", role="general", approved=True)
    tok = auth.create_token("u5@x.com")
    r = c.get("/api/wiki/graph", headers={**_bearer(tok), "X-Agent-Id": "conwo"})
    assert r.status_code != 403


def test_graph_allowed_after_grant(client):
    """After granting access, the gate must let the user reach the graph endpoint."""
    c, auth = client
    from backend import agent_access

    auth.create_user("u6@x.com", role="general", approved=True)
    tok = auth.create_token("u6@x.com")
    agent_access.set_status("u6@x.com", "infosec", "granted", "admin@x.com")
    r = c.get("/api/wiki/graph", headers={**_bearer(tok), "X-Agent-Id": "infosec"})
    assert r.status_code != 403
