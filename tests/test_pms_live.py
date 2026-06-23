"""Mocked unit tests for the four G05 PMS handlers — no live API calls.

The live smoke test in tests/manual/g05_smoke.py covers the happy paths
against real PMS; this file covers credential gating, input validation,
error envelopes, the BUID-not-found case, and the unknown-shape fallback
in pms_verify_buid.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch


# ──────────────────────────────────────────────────────────────────────────────
# pms_list_offices

def test_list_offices_happy_path(monkeypatch):
    monkeypatch.setenv("PMS_TOKEN_COM", "fake-token")
    from backend.tools.pms_tools import _pms_list_offices_handler

    mock_session = MagicMock()
    mock_session.fetch_offices.return_value = {
        "LOpwcind-OFC-0001": "WorkInSync Pune Office (Pune, India)",
        "LOpwcind-OFC-0002": "WorkInSync Bangalore Office (Bangalore, India)",
    }
    with patch("pms_session.Session.load", return_value=mock_session):
        result = _pms_list_offices_handler({
            "service": "VISITOR",
            "server": "com",
            "buid": "genpactindia-GInd",
        })

    assert "error" not in result
    assert result["total"] == 2
    assert result["offices"][0]["officeid"].startswith("LOpwcind-OFC-")
    assert "Pune Office" in result["offices"][0]["name"]


def test_list_offices_missing_buid_returns_missing_input(monkeypatch):
    monkeypatch.setenv("PMS_TOKEN_COM", "fake-token")
    from backend.tools.pms_tools import _pms_list_offices_handler

    result = _pms_list_offices_handler({
        "service": "VISITOR",
        "server": "com",
    })
    assert result["code"] == "missing_input"


def test_list_offices_no_credentials_returns_credentials_required(monkeypatch):
    monkeypatch.delenv("PMS_TOKEN_COM", raising=False)
    monkeypatch.delenv("PMS_TOKEN", raising=False)
    from backend.tools.pms_tools import _pms_list_offices_handler

    result = _pms_list_offices_handler({
        "service": "VISITOR",
        "server": "com",
        "buid": "genpactindia-GInd",
    })
    assert result["status"] == "credentials_required"


# ──────────────────────────────────────────────────────────────────────────────
# pms_list_criteria

def test_list_criteria_happy_path(monkeypatch):
    monkeypatch.setenv("PMS_TOKEN_COM", "fake-token")
    from backend.tools.pms_tools import _pms_list_criteria_handler

    mock_session = MagicMock()
    mock_session.fetch_criteria_values.return_value = [
        "LOpwcind-OFC-0001",
        "LOpwcind-OFC-0002",
        "LOpwcind-OFC-0003",
    ]
    with patch("pms_session.Session.load", return_value=mock_session):
        result = _pms_list_criteria_handler({
            "service": "VISITOR",
            "server": "com",
            "buid": "genpactindia-GInd",
            "criteria": "OFFICEID",
        })

    assert "error" not in result
    assert result["total"] == 3
    assert result["criteria"] == "OFFICEID"


def test_list_criteria_missing_criteria_returns_missing_input(monkeypatch):
    monkeypatch.setenv("PMS_TOKEN_COM", "fake-token")
    from backend.tools.pms_tools import _pms_list_criteria_handler

    result = _pms_list_criteria_handler({
        "service": "VISITOR",
        "server": "com",
        "buid": "genpactindia-GInd",
    })
    assert result["code"] == "missing_input"


# ──────────────────────────────────────────────────────────────────────────────
# pms_verify_buid

def test_verify_buid_found_when_offices_returned(monkeypatch):
    """A valid BUID on the right server returns offices (token-free) → found=True."""
    monkeypatch.setenv("PMS_TOKEN_COM", "fake-token")
    from backend.tools.pms_tools import _pms_verify_buid_handler

    mock_session = MagicMock()
    mock_session.fetch_offices.return_value = {
        "LOpwc-OFC-0001": "PwC Pune (Pune, India)",
        "LOpwc-OFC-0002": "PwC Bangalore (Bangalore, India)",
    }
    with patch("pms_session.Session.load", return_value=mock_session):
        result = _pms_verify_buid_handler({
            "service": "PROJECT-MANAGEMENT-SERVICE",
            "server": "com",
            "buid": "pwc-WP",
        })

    assert result["found"] is True
    assert result["office_count"] == 2
    assert result["server"] == "com"
    assert len(result["offices_sample"]) == 2
    assert ".com" in result["message"]
    # Must NOT report the dead route_unavailable / shape_unknown errors any more
    assert result.get("code") not in ("route_unavailable", "shape_unknown")


def test_verify_buid_not_found_when_no_offices_warns_other_server(monkeypatch):
    """Wrong server / invalid BUID returns zero offices → found=False with a
    warning to try the other server before concluding the BUID is invalid."""
    monkeypatch.setenv("PMS_TOKEN_COM", "fake-token")
    from backend.tools.pms_tools import _pms_verify_buid_handler

    mock_session = MagicMock()
    mock_session.fetch_offices.return_value = {}
    with patch("pms_session.Session.load", return_value=mock_session):
        result = _pms_verify_buid_handler({
            "service": "PROJECT-MANAGEMENT-SERVICE",
            "server": "com",
            "buid": "pwc-WP",
        })

    assert result["found"] is False
    assert result["office_count"] == 0
    assert "⚠️" in result["message"]
    assert "try .in" in result["message"]


def test_verify_buid_works_token_free(monkeypatch):
    """The offices endpoint is token-free, so verify must succeed even when no
    PMS credentials are configured — it must NOT return credentials_required."""
    monkeypatch.delenv("PMS_TOKEN_COM", raising=False)
    monkeypatch.delenv("PMS_TOKEN", raising=False)
    from backend.tools.pms_tools import _pms_verify_buid_handler

    mock_session = MagicMock()
    mock_session.fetch_offices.return_value = {"LO-1": "Office One"}
    with patch("pms_session.Session.load", return_value=mock_session):
        result = _pms_verify_buid_handler({
            "service": "PROJECT-MANAGEMENT-SERVICE",
            "server": "com",
            "buid": "pwc-WP",
        })

    assert result.get("status") != "credentials_required"
    assert result["found"] is True


def test_verify_buid_missing_buid_returns_missing_input(monkeypatch):
    from backend.tools.pms_tools import _pms_verify_buid_handler

    result = _pms_verify_buid_handler({"service": "VISITOR", "server": "com", "buid": ""})
    assert result["code"] == "missing_input"


# ──────────────────────────────────────────────────────────────────────────────
# pms_diagnose_property

def test_diagnose_property_happy_path(monkeypatch):
    monkeypatch.setenv("PMS_TOKEN_COM", "fake-token")
    from backend.tools.pms_tools import _pms_diagnose_property_handler

    mock_session = MagicMock()
    # _defaults is consulted to decide value_found — populate it
    mock_session._defaults = {
        "kioskRequireOTPBeforeRegister": {"propertyValue": "true", "propertyDataType": "BOOLEAN"},
    }
    mock_session.fetch_defaults.return_value = 1
    mock_session.fetch_level.return_value = []
    mock_session.debug_report.return_value = (
        "## `kioskRequireOTPBeforeRegister` — level comparison\n\n"
        "| Level | Value |\n| BUID | true |\n\n"
        "**Effective value:** `true`  **Winning level:** `BUID`"
    )
    with patch("pms_session.Session.load", return_value=mock_session):
        result = _pms_diagnose_property_handler({
            "service": "VISITOR",
            "server": "com",
            "buid": "genpactindia-GInd",
            "property": "kioskRequireOTPBeforeRegister",
        })

    assert "error" not in result
    assert result["value_found"] is True
    assert result["property"] == "kioskRequireOTPBeforeRegister"
    assert "level comparison" in result["report_markdown"]


def test_diagnose_property_not_in_defaults(monkeypatch):
    monkeypatch.setenv("PMS_TOKEN_COM", "fake-token")
    from backend.tools.pms_tools import _pms_diagnose_property_handler

    mock_session = MagicMock()
    mock_session._defaults = {"someOtherProperty": {"propertyValue": "x"}}
    mock_session.fetch_defaults.return_value = 1
    mock_session.fetch_level.return_value = []
    mock_session.debug_report.return_value = (
        "Property `madeUpProperty` not found in loaded defaults. "
        "Did you mean: someOtherProperty?"
    )
    with patch("pms_session.Session.load", return_value=mock_session):
        result = _pms_diagnose_property_handler({
            "service": "VISITOR",
            "server": "com",
            "buid": "genpactindia-GInd",
            "property": "madeUpProperty",
        })

    assert result["value_found"] is False
    assert "not found" in result["report_markdown"].lower()


def test_diagnose_property_missing_inputs_returns_missing_input(monkeypatch):
    monkeypatch.setenv("PMS_TOKEN_COM", "fake-token")
    from backend.tools.pms_tools import _pms_diagnose_property_handler

    result = _pms_diagnose_property_handler({
        "service": "VISITOR",
        "server": "com",
        # missing buid and property
    })
    assert result["code"] == "missing_input"
