"""
Unit tests for backend/guardrail.py — input filter and tool-call filter.

No DB, no API key, no network needed.
"""
import pytest

from backend.guardrail import (
    REFUSAL_MESSAGE,
    is_destructive_input,
    is_destructive_tool_call,
    log_blocked,
)


# ---------------------------------------------------------------------------
# Layer 1 — is_destructive_input
# ---------------------------------------------------------------------------

class TestInputFilter:

    # ── Should BLOCK ─────────────────────────────────────────────────────────

    def test_sql_drop_table_blocked(self):
        assert is_destructive_input("drop table tickets") is not None

    def test_sql_drop_database_blocked(self):
        assert is_destructive_input("drop database conwo") is not None

    def test_sql_truncate_blocked(self):
        assert is_destructive_input("truncate table jira_tickets") is not None

    def test_sql_truncate_no_table_keyword_blocked(self):
        assert is_destructive_input("truncate tickets") is not None

    def test_sql_delete_from_blocked(self):
        assert is_destructive_input("delete from tickets where id=1") is not None

    def test_sql_update_set_blocked(self):
        assert is_destructive_input("update tickets set status='deleted'") is not None

    def test_sql_alter_table_blocked(self):
        assert is_destructive_input("alter table tickets drop column status") is not None

    def test_wipe_out_blocked(self):
        assert is_destructive_input("wipe out all visitor configs") is not None

    def test_wipe_the_database_blocked(self):
        assert is_destructive_input("wipe the database") is not None

    def test_erase_all_blocked(self):
        assert is_destructive_input("erase all the data") is not None

    def test_clear_all_data_blocked(self):
        assert is_destructive_input("clear all data") is not None

    def test_clear_all_tickets_blocked(self):
        assert is_destructive_input("clear all tickets") is not None

    def test_clear_all_wiki_pages_blocked(self):
        assert is_destructive_input("clear all wiki pages") is not None

    def test_destroy_the_database_blocked(self):
        assert is_destructive_input("destroy the database") is not None

    def test_reset_database_blocked(self):
        assert is_destructive_input("reset the database") is not None

    def test_reset_all_configs_blocked(self):
        assert is_destructive_input("reset all configs") is not None

    def test_purge_all_tickets_blocked(self):
        assert is_destructive_input("purge all tickets") is not None

    def test_delete_all_wiki_pages_blocked(self):
        assert is_destructive_input("delete all wiki pages") is not None

    def test_delete_every_user_blocked(self):
        assert is_destructive_input("delete every user") is not None

    def test_remove_all_users_blocked(self):
        assert is_destructive_input("remove all users") is not None

    def test_case_insensitive_blocked(self):
        assert is_destructive_input("DROP TABLE tickets") is not None

    def test_extra_whitespace_blocked(self):
        assert is_destructive_input("drop  table   tickets") is not None

    # ── Should PASS (legitimate support questions) ───────────────────────────

    def test_legitimate_delete_button_question_passes(self):
        assert is_destructive_input("why does the delete button not work?") is None

    def test_legitimate_delete_meeting_room_passes(self):
        assert is_destructive_input("how does delete meeting room work?") is None

    def test_what_config_removes_nda_passes(self):
        assert is_destructive_input("what config removes the NDA screen?") is None

    def test_how_to_remove_employee_from_visitor_passes(self):
        assert is_destructive_input("how to remove an employee from the visitor list?") is None

    def test_why_is_visitor_record_deleted_passes(self):
        assert is_destructive_input("why does the visitor record get deleted after checkout?") is None

    def test_search_wiki_passes(self):
        assert is_destructive_input("search wiki for kiosk configs") is None

    def test_show_me_config_passes(self):
        assert is_destructive_input("show me the MEETING_ROOM_ENABLED config") is None

    def test_delete_in_feature_context_passes(self):
        assert is_destructive_input("is there a delete option for recurring bookings?") is None

    def test_how_do_i_drop_a_booking_passes(self):
        assert is_destructive_input("how do I drop a booking from the calendar?") is None

    def test_empty_string_passes(self):
        assert is_destructive_input("") is None

    def test_normal_config_question_passes(self):
        assert is_destructive_input("what is kioskRequireOTPBeforeRegister?") is None


# ---------------------------------------------------------------------------
# Layer 2 — is_destructive_tool_call
# ---------------------------------------------------------------------------

class TestToolCallFilter:

    # ── Should BLOCK ─────────────────────────────────────────────────────────

    def test_blocked_tool_name_wiki_create(self):
        assert is_destructive_tool_call("wiki_create_page", {}) is not None

    def test_blocked_tool_name_wiki_edit(self):
        assert is_destructive_tool_call("wiki_edit_page", {"path": "wiki/foo.md"}) is not None

    def test_blocked_tool_name_wiki_append(self):
        assert is_destructive_tool_call("wiki_append_section", {}) is not None

    def test_blocked_tool_name_wiki_rebuild(self):
        assert is_destructive_tool_call("wiki_rebuild_index", {}) is not None

    def test_blocked_tool_name_wiki_update_frontmatter(self):
        assert is_destructive_tool_call("wiki_update_frontmatter", {}) is not None

    def test_write_sql_delete_from_in_input(self):
        assert is_destructive_tool_call(
            "jira_search_ranked",
            {"query": "DELETE FROM tickets WHERE 1=1"},
        ) is not None

    def test_write_sql_drop_table_in_input(self):
        assert is_destructive_tool_call(
            "jira_named_query",
            {"name": "tickets_by_area", "params": {"query": "DROP TABLE tickets"}},
        ) is not None

    def test_write_sql_update_set_in_input(self):
        assert is_destructive_tool_call(
            "config_lookup",
            {"property": "UPDATE configs SET value=1"},
        ) is not None

    def test_write_sql_insert_in_input(self):
        assert is_destructive_tool_call(
            "jira_search_ranked",
            {"query": "INSERT INTO tickets VALUES (1,2,3)"},
        ) is not None

    def test_write_sql_truncate_in_input(self):
        result = is_destructive_tool_call(
            "jira_search_ranked",
            {"query": "TRUNCATE TABLE tickets"},
        )
        assert result is not None

    # ── Should PASS ──────────────────────────────────────────────────────────

    def test_select_sql_passes(self):
        assert is_destructive_tool_call(
            "jira_search_ranked",
            {"query": "SELECT * FROM tickets WHERE status='open'"},
        ) is None

    def test_normal_jira_search_passes(self):
        assert is_destructive_tool_call(
            "jira_search_ranked",
            {"query": "visitor check-in OTP", "limit": 10},
        ) is None

    def test_normal_config_lookup_passes(self):
        assert is_destructive_tool_call(
            "config_lookup",
            {"property": "kioskRequireOTPBeforeRegister", "service": "VISITOR"},
        ) is None

    def test_wiki_search_passes(self):
        assert is_destructive_tool_call(
            "wiki_search",
            {"query": "meeting room recurring bookings"},
        ) is None

    def test_pms_runtime_values_passes(self):
        assert is_destructive_tool_call(
            "pms_runtime_values",
            {"service": "VISITOR", "server": "com", "buid": "acme-corp"},
        ) is None

    def test_wiki_propose_edit_passes(self):
        # Proposals go to admin review — not a direct write
        assert is_destructive_tool_call(
            "wiki_propose_edit",
            {"path": "wiki/modules/visitor.md", "field": "status", "old_value": "draft", "new_value": "published"},
        ) is None

    def test_empty_input_passes(self):
        assert is_destructive_tool_call("wiki_search", {}) is None

    def test_nested_dict_with_safe_sql_passes(self):
        assert is_destructive_tool_call(
            "jira_named_query",
            {"name": "recently_resolved", "params": {"days": 90, "query": "SELECT id FROM t"}},
        ) is None


# ---------------------------------------------------------------------------
# Layer 2 — allow_writes (ingest EXECUTE registry only)
# ---------------------------------------------------------------------------

class TestAllowWrites:

    def test_write_tool_blocked_by_default(self):
        # Default (chat/query, ingest plan) — write tools stay blocked.
        assert is_destructive_tool_call("wiki_create_page", {}) is not None
        assert is_destructive_tool_call("wiki_edit_page", {"path": "x"}) is not None

    def test_write_tool_allowed_when_allow_writes(self):
        # The ingest EXECUTE registry passes allow_writes=True so its write tools run.
        assert is_destructive_tool_call("wiki_create_page", {"path": "x"}, allow_writes=True) is None
        assert is_destructive_tool_call("wiki_edit_page", {}, allow_writes=True) is None
        assert is_destructive_tool_call("wiki_rebuild_index", {}, allow_writes=True) is None

    def test_write_sql_still_blocked_even_when_allow_writes(self):
        # allow_writes only un-gates the wiki write TOOLS — write SQL is never allowed.
        assert is_destructive_tool_call(
            "wiki_create_page", {"content": "DROP TABLE tickets"}, allow_writes=True
        ) is not None


# ---------------------------------------------------------------------------
# Refusal message
# ---------------------------------------------------------------------------

def test_refusal_message_not_empty():
    assert len(REFUSAL_MESSAGE) > 20

def test_refusal_message_mentions_read_only():
    assert "read-only" in REFUSAL_MESSAGE.lower()

def test_refusal_message_mentions_admin():
    assert "admin" in REFUSAL_MESSAGE.lower()


# ---------------------------------------------------------------------------
# log_blocked — smoke test (no side effects needed)
# ---------------------------------------------------------------------------

def test_log_blocked_does_not_raise(caplog):
    import logging
    with caplog.at_level(logging.WARNING, logger="guardrail"):
        log_blocked(
            user_email="test@example.com",
            question="drop table tickets",
            trigger="drop table",
            where="query_input",
        )
    assert any("GUARDRAIL_BLOCKED" in r.message for r in caplog.records)
