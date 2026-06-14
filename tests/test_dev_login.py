"""Dev-only email-login path: flag gating, provisioning, and prod-inert behavior."""
import importlib
import pytest
from fastapi.testclient import TestClient


def test_dev_login_enabled_flag(monkeypatch):
    import backend.config as config
    monkeypatch.delenv("CONWO_DEV_LOGIN", raising=False)
    importlib.reload(config)
    assert config.dev_login_enabled() is False
    monkeypatch.setenv("CONWO_DEV_LOGIN", "true")
    assert config.dev_login_enabled() is True
    monkeypatch.setenv("CONWO_DEV_LOGIN", "off")
    assert config.dev_login_enabled() is False
