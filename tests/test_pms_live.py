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

def test_verify_buid_found_in_directory(monkeypatch):
    """BUID present in the directory list — straightforward found=True."""
    monkeypatch.setenv("PMS_TOKEN_COM", "fake-token")
    from backend.tools.pms_tools import _pms_verify_buid_handler

    mock_session = MagicMock()
    # Real PMS shape: dicts in the buids list, plus the isAllBuids flag
    mock_session.fetch_roles.return_value = {
        "serviceId": "VISITOR",
        "role": "ROLE_READ_ONLY",
        "isAllBuids": True,
        "buids": [
            {"buid": "genpactindia-GInd", "tenantName": "Genpact India", "stratus": False},
            {"buid": "another-buid-XYZ", "tenantName": "Another", "stratus": False},
        ],
    }
    with patch("pms_session.Session.load", return_value=mock_session):
        result = _pms_verify_buid_handler({
            "service": "VISITOR",
            "server": "com",
            "buid": "genpactindia-GInd",
        })

    assert result["found"] is True
    assert result["in_directory"] is True
    assert result["is_all_buids"] is True
    assert "in the .com directory" in result["message"]


def test_verify_buid_isallbuids_true_buid_not_in_list_returns_soft_warning(monkeypatch):
    """Real PMS scenario: isAllBuids=true (cross-tenant access) but the
    queried BUID is not in the directory listing. Should report found=True
    with a soft warning to confirm via pms_diagnose_property."""
    monkeypatch.setenv("PMS_TOKEN_COM", "fake-token")
    from backend.tools.pms_tools import _pms_verify_buid_handler

    mock_session = MagicMock()
    mock_session.fetch_roles.return_value = {
        "isAllBuids": True,
        "buids": [
            {"buid": "named-tenant-AB", "tenantName": "Named A"},
            {"buid": "named-tenant-CD", "tenantName": "Named C"},
        ],
    }
    with patch("pms_session.Session.load", return_value=mock_session):
        result = _pms_verify_buid_handler({
            "service": "VISITOR",
            "server": "com",
            "buid": "unlisted-but-real",
        })

    assert result["found"] is True  # cross-tenant access
    assert result["in_directory"] is False
    assert result["is_all_buids"] is True
    assert "cross-tenant" in result["message"]
    assert "pms_diagnose_property" in result["message"]


def test_verify_buid_not_found_returns_mismatch_warning(monkeypatch):
    """No cross-tenant access AND BUID not in list → hard mismatch warning."""
    monkeypatch.setenv("PMS_TOKEN_COM", "fake-token")
    from backend.tools.pms_tools import _pms_verify_buid_handler

    mock_session = MagicMock()
    mock_session.fetch_roles.return_value = {
        "isAllBuids": False,
        "buids": [
            {"buid": "real-buid-AB", "tenantName": "Real A"},
            {"buid": "another-buid-CD", "tenantName": "Another C"},
        ],
    }
    with patch("pms_session.Session.load", return_value=mock_session):
        result = _pms_verify_buid_handler({
            "service": "VISITOR",
            "server": "com",
            "buid": "nonexistentbuid-FAKE",
        })

    assert result["found"] is False
    assert result["is_all_buids"] is False
    assert "⚠️" in result["message"]
    assert "wrong server" in result["message"]
    assert "try .in" in result["message"]


def test_verify_buid_unknown_shape_returns_raw_response(monkeypatch):
    """If fetch_roles returns a shape _extract_accessible_buids can't parse,
    we surface the raw response with code='shape_unknown' so the smoke test
    or operator can see what the real API returns."""
    monkeypatch.setenv("PMS_TOKEN_COM", "fake-token")
    from backend.tools.pms_tools import _pms_verify_buid_handler

    mock_session = MagicMock()
    # Deliberately unrecognized shape
    mock_session.fetch_roles.return_value = {
        "userInfo": {"someField": "value", "permissionsList": ["a", "b"]},
    }
    with patch("pms_session.Session.load", return_value=mock_session):
        result = _pms_verify_buid_handler({
            "service": "VISITOR",
            "server": "com",
            "buid": "any-buid-XX",
        })

    assert result["code"] == "shape_unknown"
    assert "raw_response" in result
    assert result["raw_response"]["userInfo"]["someField"] == "value"


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
