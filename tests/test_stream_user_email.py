"""
Test that the /query/stream endpoint passes user_email to create_conversation.

The stream endpoint calls claude_available() BEFORE creating a conversation, so
we must mock it to True and stub out the downstream subprocess and preflight to
avoid spawning a real claude process.
"""
import importlib
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def stream_client(tmp_path, monkeypatch):
    import backend.auth_store as auth_module
    import backend.conversation_store as cs
    auth_dir = tmp_path / "raw" / "auth"
    auth_dir.mkdir(parents=True)
    monkeypatch.setattr(auth_module, "AUTH_DB", auth_dir / "auth.sqlite", raising=False)
    monkeypatch.setattr(auth_module, "AUTH_DIR", auth_dir, raising=False)
    monkeypatch.setattr(cs, "CONVERSATIONS_DB", tmp_path / "c.sqlite", raising=False)
    monkeypatch.setattr(cs, "CONVERSATIONS_DIR", tmp_path, raising=False)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-id")
    auth_module.create_user("stream@moveinsync.com", role="admin", approved=True)
    token = auth_module.create_token("stream@moveinsync.com")
    return tmp_path, monkeypatch, auth_module, cs, token


def test_stream_conversation_is_owned_by_user(stream_client):
    tmp_path, monkeypatch, auth_module, cs, token = stream_client

    captured_email = {}
    original_create = cs.create_conversation

    def spy_create(title=None, user_email=None, **kwargs):
        captured_email["value"] = user_email
        return original_create(title=title, user_email=user_email, **kwargs)

    # Disable preflight so we don't need to patch the locally-imported
    # run_preflight / build_agent_preamble inside query_stream.
    import os
    os.environ["CONWO_AGENT_PREFLIGHT"] = "false"

    with patch("backend.api.claude_available", return_value=True), \
         patch("backend.api.conversation_store.create_conversation",
               side_effect=spy_create):

        from backend import api as api_module
        importlib.reload(api_module)
        from fastapi.testclient import TestClient

        with patch.object(api_module, "query_stream",
                          wraps=api_module.query_stream):
            test_client = TestClient(api_module.app, raise_server_exceptions=False)
            test_client.post(
                "/query/stream",
                json={"question": "hello world"},
                headers={"Authorization": f"Bearer {token}"},
            )

    assert captured_email.get("value") == "stream@moveinsync.com", (
        f"Expected user_email='stream@moveinsync.com' but got: {captured_email.get('value')!r}"
    )
