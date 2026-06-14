"""Dev-only email-login path: flag gating, provisioning, and prod-inert behavior."""
import importlib
import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize("value", ["1", "true", "True", "TRUE", "yes", "on"])
def test_dev_login_enabled_flag_truthy(monkeypatch, value):
    import backend.config as config
    monkeypatch.setenv("CONWO_DEV_LOGIN", value)
    importlib.reload(config)
    assert config.dev_login_enabled() is True


@pytest.mark.parametrize("value", ["0", "false", "no", "off", ""])
def test_dev_login_enabled_flag_falsy(monkeypatch, value):
    import backend.config as config
    monkeypatch.setenv("CONWO_DEV_LOGIN", value)
    importlib.reload(config)
    assert config.dev_login_enabled() is False


def test_dev_login_enabled_flag_unset(monkeypatch):
    import backend.config as config
    monkeypatch.delenv("CONWO_DEV_LOGIN", raising=False)
    importlib.reload(config)
    assert config.dev_login_enabled() is False
