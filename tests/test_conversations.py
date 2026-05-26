"""
Tests for the conversation_store and the conversation REST endpoints.

These use a temp directory so they never touch the user's real chat DB.
"""
from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def isolated_store(tmp_path, monkeypatch):
    """Point conversation_store at a fresh SQLite under tmp_path and reload modules."""
    fake_root = tmp_path / "raw" / "conversations"
    fake_root.mkdir(parents=True)
    db = fake_root / "conversations.sqlite"

    # Patch the constants the store reads at module load time, then reload it
    from backend import config
    monkeypatch.setattr(config, "CONVERSATIONS_DIR", fake_root, raising=False)
    monkeypatch.setattr(config, "CONVERSATIONS_DB", db, raising=False)

    from backend import conversation_store
    importlib.reload(conversation_store)
    yield conversation_store


def test_create_list_get_delete(isolated_store):
    cs = isolated_store
    c = cs.create_conversation("Hello world")
    assert c["id"]
    assert c["title"] == "Hello world"
    assert c["message_count"] == 0

    cs.add_message(c["id"], "user", "What is X?", mode="api", server="com")
    cs.add_message(
        c["id"],
        "assistant",
        "Answer.",
        mode="api",
        confidence="High",
        sources={"wiki_pages": ["wiki/index.md"], "jira_keys": [], "pms_configs": []},
        tool_trace=[{"round": 1, "tool_name": "wiki_search", "input": {}, "output_summary": ""}],
        missing_context=[],
    )

    listed = cs.list_conversations()
    assert len(listed) == 1
    assert listed[0]["message_count"] == 2

    fetched = cs.get_conversation(c["id"])
    assert len(fetched["messages"]) == 2
    assert fetched["messages"][0]["role"] == "user"
    assert fetched["messages"][1]["sources"]["wiki_pages"] == ["wiki/index.md"]

    assert cs.delete_conversation(c["id"]) is True
    assert cs.get_conversation(c["id"]) is None


def test_messages_cascade_delete(isolated_store):
    cs = isolated_store
    c = cs.create_conversation("To delete")
    cs.add_message(c["id"], "user", "Q")
    cs.add_message(c["id"], "assistant", "A")
    assert cs.delete_conversation(c["id"]) is True
    # underlying rows are gone
    fetched = cs.get_conversation(c["id"])
    assert fetched is None


def test_add_message_rejects_unknown_conversation(isolated_store):
    cs = isolated_store
    with pytest.raises(LookupError):
        cs.add_message("does-not-exist", "user", "Q")


def test_invalid_role(isolated_store):
    cs = isolated_store
    c = cs.create_conversation("R")
    with pytest.raises(ValueError):
        cs.add_message(c["id"], "robot", "?")


def test_auto_title_truncation(isolated_store):
    cs = isolated_store
    short = cs.auto_title_from_question("hi")
    assert short == "hi"
    long = "the quick brown fox jumps over the lazy dog " * 5
    truncated = cs.auto_title_from_question(long, max_len=60)
    assert len(truncated) <= 60
    assert truncated.endswith("…")


def test_trace_sanitization_already_applied():
    """
    Sanity check that the ToolRegistry strips secrets before they ever reach
    the conversation store. The store itself doesn't re-sanitize.
    """
    from backend.tools.registry import ToolRegistry

    registry = ToolRegistry()
    secret = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig"

    def handler(inp: dict) -> dict:
        return {"received": inp.get("token", ""), "status": "ok"}

    schema = {
        "name": "fake",
        "description": "",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    }
    registry.register(schema, handler)
    _result, trace = registry.execute("fake", {"token": secret}, round_num=1)

    assert "Bearer eyJ" not in json.dumps(trace["input"])
    assert "Bearer eyJ" not in trace["output_summary"]


def test_rest_conversation_lifecycle(isolated_store):
    """End-to-end via FastAPI TestClient."""
    from unittest.mock import patch

    # Reload api after patching so its conversation_store binding picks up the temp dir.
    from backend import api as api_module
    importlib.reload(api_module)
    client = TestClient(api_module.app)

    test_user = {"email": "test@example.com", "role": "viewer", "token": "test-token"}
    auth = {"Authorization": "Bearer test-token"}

    with patch("backend.config.lookup_user_by_token", side_effect=lambda t: test_user if t == "test-token" else None):
        # Empty list
        r = client.get("/conversations", headers=auth)
        assert r.status_code == 200
        assert r.json() == {"conversations": []}

        # Create (auth optional — email from token so conversation is owned)
        r = client.post("/conversations", json={"title": "Via REST"}, headers=auth)
        assert r.status_code == 200
        cid = r.json()["id"]

        # List — only sees own conversations
        r = client.get("/conversations", headers=auth)
        assert len(r.json()["conversations"]) == 1

        # Get
        r = client.get(f"/conversations/{cid}", headers=auth)
        assert r.status_code == 200
        assert r.json()["messages"] == []

        # Patch title
        r = client.patch(f"/conversations/{cid}", json={"title": "Renamed"}, headers=auth)
        assert r.status_code == 200
        assert r.json()["title"] == "Renamed"

        # Delete
        r = client.delete(f"/conversations/{cid}", headers=auth)
        assert r.status_code == 200
        assert r.json()["deleted"] is True

        # Now 404
        r = client.get(f"/conversations/{cid}", headers=auth)
        assert r.status_code == 404


def test_user_email_column_added_via_migration(isolated_store):
    """create_conversation with user_email stores the value."""
    cs = isolated_store
    c = cs.create_conversation("Test", user_email="alice@example.com")
    assert c["id"]
    # Verify the value was stored by checking the raw DB
    import sqlite3
    from backend import config
    conn = sqlite3.connect(str(config.CONVERSATIONS_DB))
    row = conn.execute(
        "SELECT user_email FROM conversations WHERE id = ?", (c["id"],)
    ).fetchone()
    conn.close()
    assert row[0] == "alice@example.com"


def test_list_conversations_filters_by_user_email(isolated_store):
    cs = isolated_store
    cs.create_conversation("Alice conv", user_email="alice@example.com")
    cs.create_conversation("Bob conv", user_email="bob@example.com")
    cs.create_conversation("Shared conv", user_email=None)

    alice_convs = cs.list_conversations(user_email="alice@example.com")
    assert len(alice_convs) == 1
    assert alice_convs[0]["title"] == "Alice conv"


def test_list_conversations_admin_sees_all(isolated_store):
    cs = isolated_store
    cs.create_conversation("Alice conv", user_email="alice@example.com")
    cs.create_conversation("Bob conv", user_email="bob@example.com")
    all_convs = cs.list_conversations(user_email=None)
    assert len(all_convs) == 2


# ── G03: compaction migration idempotency + state get/set ─────────────────────

def test_init_schema_is_idempotent_for_g03_columns(isolated_store):
    """Running init_schema() twice must not error and must add the new
    compaction columns exactly once. Mirrors the user_email migration test."""
    cs = isolated_store
    cs.init_schema()
    cs.init_schema()  # second call MUST be a no-op for the migrations

    # Count occurrences of the new columns via PRAGMA — should be 1 each
    import sqlite3
    conn = sqlite3.connect(str(cs.CONVERSATIONS_DB))
    try:
        cols = [row[1] for row in conn.execute("PRAGMA table_info(conversations)")]
    finally:
        conn.close()
    assert cols.count("compacted_summary") == 1
    assert cols.count("compaction_at_turn") == 1
    assert cols.count("user_email") == 1  # earlier migration still intact


def test_compaction_state_starts_none(isolated_store):
    cs = isolated_store
    conv = cs.create_conversation("Test")
    summary, at_turn = cs.get_compaction_state(conv["id"])
    assert summary is None
    assert at_turn is None


def test_set_and_get_compaction_state(isolated_store):
    cs = isolated_store
    conv = cs.create_conversation("Test")
    cs.set_compacted_summary(conv["id"], "- bullet 1\n- bullet 2", at_turn=14)
    summary, at_turn = cs.get_compaction_state(conv["id"])
    assert summary == "- bullet 1\n- bullet 2"
    assert at_turn == 14


def test_get_compaction_state_unknown_conversation_returns_nones(isolated_store):
    cs = isolated_store
    summary, at_turn = cs.get_compaction_state("nonexistent-id")
    assert summary is None
    assert at_turn is None
