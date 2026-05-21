"""
Focused security and correctness tests for the Deep Search tool layer.

These tests don't require a live Anthropic API key or running database.
They check the trust boundary — ToolRegistry dispatch, path traversal protection,
SQL injection protection, credential handling, and secret sanitization.
"""
import os
import pytest

from backend.tools import build_registry
from backend.tools.wiki_tools import _wiki_read_page_handler
from backend.tools.jira_tools import _jira_get_ticket_handler, _jira_named_query_handler
from backend.tools.pms_tools import _pms_runtime_values_handler
from backend.tools.registry import ToolRegistry


# ── 1. Registry loads all 9 tools ─────────────────────────────────────────────

def test_registry_loads_all_tools():
    registry = build_registry()
    names = {s["name"] for s in registry.schemas}
    expected = {
        "wiki_search", "wiki_read_page",
        "jira_search_ranked", "jira_get_ticket", "jira_named_query",
        "pms_default_properties", "pms_runtime_values",
        "config_lookup",
        "feedback_record",
    }
    assert names == expected, f"Missing tools: {expected - names}"


# ── 2–4. Path traversal protection ────────────────────────────────────────────

def test_wiki_read_page_blocks_traversal():
    result = _wiki_read_page_handler({"path": "../backend/config.py"})
    assert result.get("code") == "path_traversal"
    assert "error" in result


def test_wiki_read_page_blocks_absolute():
    result = _wiki_read_page_handler({"path": "/etc/passwd"})
    assert result.get("code") == "path_traversal"
    assert "error" in result


def test_wiki_read_page_blocks_nested_traversal():
    result = _wiki_read_page_handler({"path": "modules/../../.env"})
    assert result.get("code") == "path_traversal"
    assert "error" in result


# ── 5. Jira key format validation ─────────────────────────────────────────────

def test_jira_get_ticket_invalid_key():
    result = _jira_get_ticket_handler({"key": "not-a-key"})
    assert result.get("code") == "invalid_key_format"
    assert "error" in result


# ── 6. Named query whitelist ──────────────────────────────────────────────────

def test_jira_named_query_unknown_name():
    result = _jira_named_query_handler({"query_name": "DROP TABLE tickets; --", "params": {}})
    assert "error" in result
    assert "allowed_names" in result


# ── 7. PMS no credentials → credentials_required, no exception ────────────────

def test_pms_runtime_values_no_credentials(clear_pms_env):
    result = _pms_runtime_values_handler({"service": "VISITOR", "server": "com", "buid": "test-buid"})
    assert result.get("status") == "credentials_required"
    assert "needed_env_vars" in result
    # must not raise or return an exception traceback
    assert "error" not in result


# ── 8. Secret sanitizer strips Bearer tokens ──────────────────────────────────

def test_sanitizer_strips_secrets():
    registry = ToolRegistry()

    def fake_handler(inp: dict) -> dict:
        return {"echo": inp.get("token", ""), "status": "ok"}

    fake_schema = {
        "name": "fake_tool",
        "description": "test",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    }
    registry.register(fake_schema, fake_handler)

    secret = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig"
    _result_json, trace = registry.execute(
        name="fake_tool",
        tool_input={"token": secret},
        round_num=1,
    )
    # Neither the input nor the output_summary should contain the raw secret
    import json
    input_str = json.dumps(trace["input"])
    assert "Bearer eyJ" not in input_str
    assert "[REDACTED]" in input_str or "eyJ" not in input_str
    assert "Bearer eyJ" not in trace["output_summary"]


# ── 9. Role-scoped registry ───────────────────────────────────────────────

def test_registry_accepts_user_role_param():
    """build_registry should accept user_role without error."""
    registry = build_registry(user_role="contributor")
    assert registry is not None


def test_permission_denied_for_unknown_tool_with_role():
    """A missing tool still returns unknown_tool code regardless of role."""
    registry = build_registry(user_role="admin")
    result_json, trace = registry.execute("nonexistent_tool", {}, round_num=1)
    import json
    result = json.loads(result_json)
    assert result["code"] == "unknown_tool"


def test_role_order_viewer_lt_contributor():
    from backend.tools.registry import _ROLE_ORDER
    assert _ROLE_ORDER["viewer"] < _ROLE_ORDER["contributor"]
    assert _ROLE_ORDER["contributor"] < _ROLE_ORDER["admin"]
