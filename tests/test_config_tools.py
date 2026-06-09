"""
Tests for config_tools._config_lookup_handler.
Uses a temp SQLite DB to avoid touching the real configs.sqlite.
"""
from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import backend.tools.config_tools as ct
from backend.tools.config_tools import _config_lookup_handler, CONFIG_LOOKUP_SCHEMA


def _make_test_db(path: str) -> None:
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE configs (id INTEGER PRIMARY KEY AUTOINCREMENT, property_name TEXT NOT NULL,
            service TEXT NOT NULL, server TEXT NOT NULL, description TEXT, data_type TEXT,
            default_value TEXT, customizable INTEGER, criteria_priority_list TEXT, category TEXT,
            UNIQUE(property_name, service, server));
        CREATE VIRTUAL TABLE configs_fts USING fts5(property_name, description, category,
            content=configs, content_rowid=id);
        CREATE TRIGGER configs_ai AFTER INSERT ON configs BEGIN
            INSERT INTO configs_fts(rowid, property_name, description, category)
            VALUES (new.id, new.property_name, new.description, new.category);
        END;
        INSERT INTO configs (property_name, service, server, description, data_type,
            default_value, criteria_priority_list)
        VALUES ('kioskRequireOTPBeforeRegister', 'VISITOR', 'both',
            'Requires OTP verification before kiosk self-registration.', 'Boolean', 'false',
            '["BUID","OFFICEID"]');
        CREATE TABLE jira_links (property_name TEXT, jira_key TEXT, relevance REAL,
            PRIMARY KEY(property_name, jira_key));
        INSERT INTO jira_links VALUES ('kioskRequireOTPBeforeRegister', 'VIS-1234', 1.0);
        CREATE TABLE module_links (property_name TEXT, module_slug TEXT, link_type TEXT,
            PRIMARY KEY(property_name, module_slug));
        INSERT INTO module_links VALUES ('kioskRequireOTPBeforeRegister',
            'modules/visitor-management', 'service_match');
        CREATE TABLE dependencies (property_a TEXT, property_b TEXT, dep_type TEXT,
            direction TEXT, confidence REAL, evidence TEXT,
            PRIMARY KEY(property_a, property_b, dep_type));
    """)
    con.close()


class TestConfigLookupHandler(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self._tmp.close()
        _make_test_db(self._tmp.name)

    def test_exact_match(self):
        with patch.object(ct, "_DB_PATH", self._tmp.name):
            result = _config_lookup_handler({"property_name": "kioskRequireOTPBeforeRegister"})
        self.assertTrue(result["found"])
        self.assertEqual(result["source"], "sqlite")
        self.assertEqual(result["service"], "VISITOR")
        self.assertIn("OTP", result["description"])
        self.assertEqual(result["criteria_priority_list"], ["BUID", "OFFICEID"])

    def test_jira_tickets_returned(self):
        with patch.object(ct, "_DB_PATH", self._tmp.name):
            result = _config_lookup_handler({"property_name": "kioskRequireOTPBeforeRegister"})
        self.assertEqual(len(result["jira_tickets"]), 1)
        self.assertEqual(result["jira_tickets"][0]["key"], "VIS-1234")

    def test_module_pages_returned(self):
        with patch.object(ct, "_DB_PATH", self._tmp.name):
            result = _config_lookup_handler({"property_name": "kioskRequireOTPBeforeRegister"})
        self.assertIn("modules/visitor-management", result["module_pages"])

    def test_empty_property_name_returns_error(self):
        result = _config_lookup_handler({"property_name": ""})
        self.assertIn("error", result)
        self.assertEqual(result["code"], "missing_input")

    def test_missing_property_falls_through(self):
        """When DB path doesn't exist, should fall through to wiki TF-IDF fallback."""
        mock_page = MagicMock()
        mock_page.path = "wiki/modules/visitor-management.md"
        mock_page.title = "Visitor Management"
        mock_page.excerpt.return_value = "Some excerpt"

        with patch.object(ct, "_DB_PATH", "/nonexistent/path/configs.sqlite"):
            with patch.object(ct.wiki_retriever, "search", return_value=[mock_page]) as mock_search:
                result = _config_lookup_handler({"property_name": "nonExistentXYZ999"})

        self.assertEqual(result["source"], "wiki_tfidf")
        self.assertEqual(result["property_name"], "nonExistentXYZ999")
        self.assertIn("wiki_matches", result)

    def test_schema_has_fuzzy_param(self):
        props = CONFIG_LOOKUP_SCHEMA["input_schema"]["properties"]
        self.assertIn("fuzzy", props)


if __name__ == "__main__":
    unittest.main()
