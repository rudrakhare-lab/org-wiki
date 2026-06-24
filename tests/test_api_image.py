"""
Tests for image upload via multipart/form-data on POST /query.

Covers:
  - Multipart POST with a valid PNG image returns 200
  - Existing JSON POST continues to work (no regression)
  - Unsupported image media type returns 415
"""
import io
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def authed_client(clean_db):
    """TestClient with a pre-approved general user token."""
    from backend import api as api_module
    from backend import auth_store

    auth_store.create_user("imgtest@moveinsync.com", role="general", approved=True)
    token = auth_store.create_token("imgtest@moveinsync.com")
    client = TestClient(api_module.app, raise_server_exceptions=False)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def _mock_result(answer_text="It shows a flowchart.", conversation_id="conv-1"):
    m = MagicMock()
    m.answer_id = "abc123"
    m.answer_text = answer_text
    m.confidence = "Medium"
    m.sources = MagicMock(wiki_pages=[], jira_keys=[], pms_configs=[])
    m.retrieval = {}
    m.mode = "api"
    m.error = ""
    m.tool_trace = []
    m.missing_context = []
    m.deep_search_used = True
    m.conversation_id = conversation_id
    m.intent = "GENERAL"
    m.rewritten_query = ""
    m.intent_confidence = 0.0
    m.cost_usd = 0.0
    m.cost_inr = 0.0
    return m


def test_query_with_image_multipart(authed_client):
    """POST /query with multipart form data including a PNG image returns 200."""
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
    mock_result = _mock_result()

    with patch("backend.api.orchestrator.run", return_value=mock_result):
        resp = authed_client.post(
            "/query",
            data={"question": "what is this diagram?", "mode": "api", "server": "com"},
            files={"image": ("diagram.png", io.BytesIO(png), "image/png")},
        )

    assert resp.status_code == 200
    assert resp.json()["answer_text"] == "It shows a flowchart."


def test_query_json_still_works(authed_client):
    """Existing JSON POST /query is unchanged (no regression)."""
    mock_result = _mock_result(answer_text="Normal answer.", conversation_id="conv-2")

    with patch("backend.api.orchestrator.run", return_value=mock_result):
        resp = authed_client.post(
            "/query",
            json={"question": "how does visitor management work?", "mode": "api", "server": "com"},
        )

    assert resp.status_code == 200
    assert resp.json()["answer_text"] == "Normal answer."


def test_query_unsupported_image_type_returns_415(authed_client):
    """POST /query with an unsupported image media type returns 415."""
    resp = authed_client.post(
        "/query",
        data={"question": "what is this?", "mode": "api", "server": "com"},
        files={"image": ("file.bmp", io.BytesIO(b"BM\x00"), "image/bmp")},
    )

    assert resp.status_code == 415


def test_query_multipart_no_image(authed_client):
    """POST /query multipart without image field works like a normal query."""
    mock_result = _mock_result(answer_text="Text only answer.", conversation_id="conv-3")

    with patch("backend.api.orchestrator.run", return_value=mock_result) as mock_run:
        resp = authed_client.post(
            "/query",
            data={"question": "how does desk booking work?", "mode": "api", "server": "com"},
        )

    assert resp.status_code == 200
    # image_data and image_media_type should both be None
    call_kwargs = mock_run.call_args.kwargs
    assert call_kwargs.get("image_data") is None
    assert call_kwargs.get("image_media_type") is None


def test_query_image_passes_bytes_to_orchestrator(authed_client):
    """Image bytes are passed through to orchestrator.run()."""
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
    mock_result = _mock_result()

    with patch("backend.api.orchestrator.run", return_value=mock_result) as mock_run:
        authed_client.post(
            "/query",
            data={"question": "describe this image", "mode": "api", "server": "com"},
            files={"image": ("test.png", io.BytesIO(png), "image/png")},
        )

    call_kwargs = mock_run.call_args.kwargs
    assert call_kwargs.get("image_data") == png
    assert call_kwargs.get("image_media_type") == "image/png"
