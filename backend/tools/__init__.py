"""
Tool layer for the Deep Search agentic query system.

Usage:
    from backend.tools import build_registry, ALL_TOOLS

    registry = build_registry()           # fresh registry
    registry.schemas                      # Anthropic tool definitions list
    registry.execute("wiki_search", {...}, round_num=1)  # dispatch a call

ALL_TOOLS is a module-level singleton built at import time.
"""
from __future__ import annotations

from backend.tools.registry import ToolRegistry
from backend.tools.wiki_tools import (
    WIKI_SEARCH_SCHEMA, WIKI_READ_PAGE_SCHEMA,
    _wiki_search_handler, _wiki_read_page_handler,
    WIKI_GREP_SCHEMA, _wiki_grep_handler,
)
from backend.tools.wiki_propose_tools import (
    WIKI_PROPOSE_NEW_SCHEMA, _wiki_propose_new_handler,
    WIKI_PROPOSE_EDIT_SCHEMA, _wiki_propose_edit_handler,
    WIKI_PROPOSE_APPEND_SCHEMA, _wiki_propose_append_handler,
    WIKI_PROPOSE_MULTI_EDIT_SCHEMA, _wiki_propose_multi_edit_handler,
)
from backend.tools.jira_tools import (
    JIRA_SEARCH_RANKED_SCHEMA, JIRA_GET_TICKET_SCHEMA, JIRA_NAMED_QUERY_SCHEMA,
    _jira_search_ranked_handler, _jira_get_ticket_handler, _jira_named_query_handler,
)
from backend.tools.jira_live_tools import (
    JIRA_LIVE_GET_TICKET_SCHEMA, _jira_live_get_ticket_handler,
)
from backend.tools.pms_tools import (
    PMS_DEFAULT_PROPERTIES_SCHEMA, PMS_RUNTIME_VALUES_SCHEMA,
    PMS_LIST_OFFICES_SCHEMA, PMS_LIST_CRITERIA_SCHEMA,
    PMS_VERIFY_BUID_SCHEMA, PMS_DIAGNOSE_PROPERTY_SCHEMA,
    _pms_default_properties_handler, _pms_runtime_values_handler,
    _pms_list_offices_handler, _pms_list_criteria_handler,
    _pms_verify_buid_handler, _pms_diagnose_property_handler,
)
from backend.tools.config_tools import CONFIG_LOOKUP_SCHEMA, _config_lookup_handler
from backend.tools.feedback_tools import FEEDBACK_RECORD_SCHEMA, _feedback_record_handler


def build_registry(user_role: str = "viewer") -> ToolRegistry:
    """Build a new ToolRegistry with all 19 tools registered."""
    r = ToolRegistry(user_role=user_role)
    r.register(WIKI_SEARCH_SCHEMA, _wiki_search_handler)
    r.register(WIKI_READ_PAGE_SCHEMA, _wiki_read_page_handler)
    r.register(WIKI_GREP_SCHEMA, _wiki_grep_handler)
    r.register(JIRA_SEARCH_RANKED_SCHEMA, _jira_search_ranked_handler)
    r.register(JIRA_GET_TICKET_SCHEMA, _jira_get_ticket_handler)
    r.register(JIRA_NAMED_QUERY_SCHEMA, _jira_named_query_handler)
    r.register(JIRA_LIVE_GET_TICKET_SCHEMA, _jira_live_get_ticket_handler)
    r.register(PMS_DEFAULT_PROPERTIES_SCHEMA, _pms_default_properties_handler)
    r.register(PMS_RUNTIME_VALUES_SCHEMA, _pms_runtime_values_handler)
    r.register(PMS_LIST_OFFICES_SCHEMA, _pms_list_offices_handler)
    r.register(PMS_LIST_CRITERIA_SCHEMA, _pms_list_criteria_handler)
    r.register(PMS_VERIFY_BUID_SCHEMA, _pms_verify_buid_handler)
    r.register(PMS_DIAGNOSE_PROPERTY_SCHEMA, _pms_diagnose_property_handler)
    r.register(CONFIG_LOOKUP_SCHEMA, _config_lookup_handler)
    r.register(FEEDBACK_RECORD_SCHEMA, _feedback_record_handler)
    # Track A: structured propose tools (replaces the old free-text wiki_propose_edit)
    r.register(WIKI_PROPOSE_NEW_SCHEMA, _wiki_propose_new_handler)
    r.register(WIKI_PROPOSE_EDIT_SCHEMA, _wiki_propose_edit_handler)
    r.register(WIKI_PROPOSE_APPEND_SCHEMA, _wiki_propose_append_handler)
    r.register(WIKI_PROPOSE_MULTI_EDIT_SCHEMA, _wiki_propose_multi_edit_handler)
    return r


ALL_TOOLS: ToolRegistry = build_registry()
