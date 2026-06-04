"""Tests for ingest_service — mutex, session state, tool registry builders."""
import time
import pytest
from unittest.mock import patch


def test_acquire_and_release_lock():
    from backend.ingest_service import acquire_lock, release_lock, is_locked

    assert not is_locked()
    assert acquire_lock() is True
    assert is_locked()
    release_lock()
    assert not is_locked()


def test_acquire_lock_fails_when_held():
    from backend.ingest_service import acquire_lock, release_lock

    acquire_lock()
    try:
        assert acquire_lock() is False
    finally:
        release_lock()


def test_store_and_get_session():
    from backend.ingest_service import store_session, get_session, IngestSession

    s = IngestSession(
        session_id="abc123",
        upload_id="up-1",
        plan={"operations": []},
        created_at=time.time(),
        slug="visitor-management",
        filename="test.pdf",
        original_path="raw/modules/_uploads/up-1/test.pdf",
    )
    store_session(s)
    retrieved = get_session("abc123")
    assert retrieved is not None
    assert retrieved.slug == "visitor-management"


def test_session_expires():
    from backend.ingest_service import store_session, get_session, IngestSession

    old_time = time.time() - 700  # 700 seconds ago > 600s TTL
    s = IngestSession(
        session_id="expired-session",
        upload_id="up-2",
        plan={},
        created_at=old_time,
        slug="test",
        filename="test.pdf",
        original_path="raw/modules/_uploads/up-2/test.pdf",
    )
    store_session(s)
    assert get_session("expired-session") is None


def test_get_nonexistent_session():
    from backend.ingest_service import get_session

    assert get_session("does-not-exist") is None


def test_build_plan_registry_has_no_write_tools():
    from backend.ingest_service import build_plan_registry

    registry = build_plan_registry()
    tool_names = {s["name"] for s in registry.schemas}
    assert "wiki_create_page" not in tool_names
    assert "wiki_edit_page" not in tool_names
    assert "wiki_search" in tool_names
    assert "extract_pdf" in tool_names
    assert "wiki_list_pages" in tool_names


def test_build_execute_registry_has_write_tools():
    from backend.ingest_service import build_execute_registry

    registry = build_execute_registry()
    tool_names = {s["name"] for s in registry.schemas}
    assert "wiki_create_page" in tool_names
    assert "wiki_edit_page" in tool_names
    assert "wiki_rebuild_index" in tool_names
    # Execute registry should NOT have extraction tools (not needed)
    assert "extract_pdf" not in tool_names
