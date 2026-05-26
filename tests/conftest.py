"""
Shared pytest fixtures for the Conwo backend test suite.
"""
import os
import pytest


@pytest.fixture(autouse=False)
def clear_pms_env(monkeypatch):
    """Clear all PMS credential environment variables."""
    for var in (
        "PMS_TOKEN_COM", "PMS_TOKEN_IN", "PMS_TOKEN",
        "PMS_COOKIE_COM", "PMS_COOKIE_IN", "PMS_COOKIE",
    ):
        monkeypatch.delenv(var, raising=False)
