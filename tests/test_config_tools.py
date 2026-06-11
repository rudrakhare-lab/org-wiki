"""
Tests for config_tools._config_lookup_handler — now backed by the Postgres
test DB. Seeds a config row + links, asserts the enriched lookup, and the
fuzzy/fall-through behavior. (Was SQLite + FTS5; now config_db + pg_trgm.)
"""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

import backend.tools.config_tools as ct
from backend.tools.config_tools import _config_lookup_handler, CONFIG_LOOKUP_SCHEMA
from backend import db


def _seed(conn):
    conn.execute(
        "INSERT INTO configs (property_name, service, server, description, data_type, "
        "default_value, criteria_priority_list) VALUES "
        "(%s, %s, %s, %s, %s, %s, %s)",
        ("kioskRequireOTPBeforeRegister", "VISITOR", "both",
         "Requires OTP verification before kiosk self-registration.", "Boolean", "false",
         '["BUID","OFFICEID"]'),
    )
    conn.execute(
        "INSERT INTO jira_links (property_name, jira_key, relevance) VALUES (%s, %s, %s)",
        ("kioskRequireOTPBeforeRegister", "VIS-1234", 1.0),
    )
    conn.execute(
        "INSERT INTO module_links (property_name, module_slug, link_type) VALUES (%s, %s, %s)",
        ("kioskRequireOTPBeforeRegister", "modules/visitor-management", "service_match"),
    )


@pytest.fixture
def seeded(clean_db):
    """Truncated test DB seeded with one config + its jira/module links."""
    with db.connection() as conn:
        _seed(conn)
    yield


def test_exact_match(seeded):
    result = _config_lookup_handler({"property_name": "kioskRequireOTPBeforeRegister"})
    assert result["found"]
    assert result["source"] == "config_db"
    assert result["service"] == "VISITOR"
    assert "OTP" in result["description"]
    assert result["criteria_priority_list"] == ["BUID", "OFFICEID"]


def test_jira_tickets_returned(seeded):
    result = _config_lookup_handler({"property_name": "kioskRequireOTPBeforeRegister"})
    assert len(result["jira_tickets"]) == 1
    assert result["jira_tickets"][0]["key"] == "VIS-1234"


def test_module_pages_returned(seeded):
    result = _config_lookup_handler({"property_name": "kioskRequireOTPBeforeRegister"})
    assert "modules/visitor-management" in result["module_pages"]


def test_empty_property_name_returns_error():
    result = _config_lookup_handler({"property_name": ""})
    assert "error" in result
    assert result["code"] == "missing_input"


def test_missing_property_falls_through(clean_db):
    """When the property isn't in the config catalog, fall through to wiki TF-IDF."""
    mock_page = MagicMock()
    mock_page.path = "wiki/modules/visitor-management.md"
    mock_page.title = "Visitor Management"
    mock_page.excerpt.return_value = "Some excerpt"

    with patch.object(ct.wiki_retriever, "search", return_value=[mock_page]):
        result = _config_lookup_handler({"property_name": "nonExistentXYZ999"})

    assert result["source"] == "wiki_tfidf"
    assert result["property_name"] == "nonExistentXYZ999"
    assert "wiki_matches" in result


def test_fuzzy_match_via_trigram(seeded):
    """pg_trgm fuzzy fallback: a near-miss spelling still finds the property."""
    result = _config_lookup_handler({"property_name": "kioskRequireOtp"})
    assert result["found"]
    assert result["source"] == "config_db"
    assert result["property_name"] == "kioskRequireOTPBeforeRegister"


def test_schema_has_fuzzy_param():
    props = CONFIG_LOOKUP_SCHEMA["input_schema"]["properties"]
    assert "fuzzy" in props
