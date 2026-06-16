"""APP_SERVER_CONFIG / ETS have no live PMS endpoint — handlers must short-circuit
with a clear no_live_endpoint status BEFORE any network call (so these run offline)."""
from backend.tools.pms_tools import (
    _pms_default_properties_handler,
    _pms_runtime_values_handler,
    _pms_diagnose_property_handler,
)


def test_default_properties_app_server_config_no_live_endpoint():
    r = _pms_default_properties_handler({"service": "APP_SERVER_CONFIG", "server": "com"})
    assert r["status"] == "no_live_endpoint"
    assert r["service"] == "APP_SERVER_CONFIG"


def test_runtime_values_ets_no_live_endpoint():
    r = _pms_runtime_values_handler({"service": "ETS", "server": "com", "buid": "x"})
    assert r["status"] == "no_live_endpoint"
    assert "no live PMS API endpoint" in r["message"]


def test_diagnose_app_server_config_no_live_endpoint():
    r = _pms_diagnose_property_handler(
        {"service": "APP_SERVER_CONFIG", "server": "com", "buid": "x", "property": "p"}
    )
    assert r["status"] == "no_live_endpoint"


def test_real_services_not_in_no_live_set():
    # Real, queryable services must NOT be in the no-live-endpoint set (network-free).
    from backend.tools.pms_tools import _NO_LIVE_ENDPOINT
    assert "VISITOR" not in _NO_LIVE_ENDPOINT
    assert "MEETING_ROOMS" not in _NO_LIVE_ENDPOINT
    assert _NO_LIVE_ENDPOINT == frozenset({"APP_SERVER_CONFIG", "ETS"})
