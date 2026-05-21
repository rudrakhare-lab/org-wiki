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
)
from backend.tools.jira_tools import (
    JIRA_SEARCH_RANKED_SCHEMA, JIRA_GET_TICKET_SCHEMA, JIRA_NAMED_QUERY_SCHEMA,
    _jira_search_ranked_handler, _jira_get_ticket_handler, _jira_named_query_handler,
)
from backend.tools.pms_tools import (
    PMS_DEFAULT_PROPERTIES_SCHEMA, PMS_RUNTIME_VALUES_SCHEMA,
    _pms_default_properties_handler, _pms_runtime_values_handler,
)
from backend.tools.config_tools import CONFIG_LOOKUP_SCHEMA, _config_lookup_handler
from backend.tools.feedback_tools import FEEDBACK_RECORD_SCHEMA, _feedback_record_handler


def build_registry(user_role: str = "viewer") -> ToolRegistry:
    """Build a new ToolRegistry with all 9 tools registered."""
    r = ToolRegistry(user_role=user_role)
    r.register(WIKI_SEARCH_SCHEMA, _wiki_search_handler)
    r.register(WIKI_READ_PAGE_SCHEMA, _wiki_read_page_handler)
    r.register(JIRA_SEARCH_RANKED_SCHEMA, _jira_search_ranked_handler)
    r.register(JIRA_GET_TICKET_SCHEMA, _jira_get_ticket_handler)
    r.register(JIRA_NAMED_QUERY_SCHEMA, _jira_named_query_handler)
    r.register(PMS_DEFAULT_PROPERTIES_SCHEMA, _pms_default_properties_handler)
    r.register(PMS_RUNTIME_VALUES_SCHEMA, _pms_runtime_values_handler)
    r.register(CONFIG_LOOKUP_SCHEMA, _config_lookup_handler)
    r.register(FEEDBACK_RECORD_SCHEMA, _feedback_record_handler)
    return r


ALL_TOOLS: ToolRegistry = build_registry()
