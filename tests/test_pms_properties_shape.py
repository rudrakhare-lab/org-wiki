"""Regression: the live /properties response is a flat {name: value} dict, not a
list of {propertyName, propertyValue}. Parsing it as a list raised
'string indices must be integers, not str' for any BUID with overrides."""
import importlib.util
from pathlib import Path

_path = Path(__file__).resolve().parent.parent / "scripts" / "pms_session.py"
_spec = importlib.util.spec_from_file_location("pms_session", _path)
pms_session = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pms_session)
_normalize = pms_session._normalize_properties


def test_dict_response_is_passed_through():
    raw = {"kioskRequireOTP": True, "Visitor_Document_Storage_Duration": 180}
    assert _normalize(raw) == {"kioskRequireOTP": True, "Visitor_Document_Storage_Duration": 180}


def test_empty_dict_is_zero_configs():
    assert _normalize({}) == {}


def test_list_of_objects_shape_still_supported():
    raw = [{"propertyName": "a", "propertyValue": 1},
           {"propertyName": "b", "propertyValue": "x"}]
    assert _normalize(raw) == {"a": 1, "b": "x"}


def test_non_dict_non_list_is_empty():
    assert _normalize(None) == {}
    assert _normalize("oops") == {}
    assert _normalize(42) == {}


def test_dict_with_nested_values_does_not_crash():
    # The real VISITOR response includes nested JSON values — must not raise.
    raw = {"visitorCheckinMsTeamsTemplate": {"header1": "Hi"}, "showTeamOnKiosk": False}
    out = _normalize(raw)
    assert out["visitorCheckinMsTeamsTemplate"] == {"header1": "Hi"}
    assert out["showTeamOnKiosk"] is False
