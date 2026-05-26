"""Tests for env-driven config in backend.providers.deep_query.

Module-level constants pick up env vars at IMPORT time, so each test must
reload the module after setting the env var. The reload pattern mirrors the
existing approach in tests/test_conversations.py.
"""
from __future__ import annotations

import importlib


def test_anthropic_model_defaults_to_sonnet_4_6(monkeypatch):
    """G24: default model when ANTHROPIC_MODEL is unset."""
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    import backend.providers.deep_query as dq
    importlib.reload(dq)
    assert dq._MODEL == "claude-sonnet-4-6"


def test_anthropic_model_respects_env_override(monkeypatch):
    """G24: setting ANTHROPIC_MODEL overrides the default."""
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-opus-4-7")
    import backend.providers.deep_query as dq
    importlib.reload(dq)
    assert dq._MODEL == "claude-opus-4-7"


def test_max_tool_rounds_defaults_to_twelve(monkeypatch):
    """G10: default cap is 12 (bumped from the original 8) so complex
    PMS-debug queries don't get force-synthesized prematurely."""
    monkeypatch.delenv("MAX_TOOL_ROUNDS", raising=False)
    import backend.providers.deep_query as dq
    importlib.reload(dq)
    assert dq._MAX_ROUNDS_ABSOLUTE == 12


def test_max_tool_rounds_respects_env_override(monkeypatch):
    """G10: production can tune the cap without redeploy."""
    monkeypatch.setenv("MAX_TOOL_ROUNDS", "20")
    import backend.providers.deep_query as dq
    importlib.reload(dq)
    assert dq._MAX_ROUNDS_ABSOLUTE == 20


def test_max_tool_rounds_invalid_value_raises_at_import(monkeypatch):
    """G10: a non-integer MAX_TOOL_ROUNDS should fail loudly at import
    rather than silently fall back. Better than running queries with an
    unexpected cap."""
    monkeypatch.setenv("MAX_TOOL_ROUNDS", "not-a-number")
    import backend.providers.deep_query as dq
    try:
        importlib.reload(dq)
        raise AssertionError("Expected ValueError on bad MAX_TOOL_ROUNDS")
    except ValueError:
        pass
    finally:
        monkeypatch.delenv("MAX_TOOL_ROUNDS", raising=False)
        importlib.reload(dq)  # restore default for other tests
