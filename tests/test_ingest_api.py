"""Integration tests for ingest API endpoints."""
import importlib
import io
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def authed_client(tmp_path):
    """TestClient with a patched lookup so Bearer fake passes as a viewer user."""
    from backend import api as api_module
    importlib.reload(api_module)
    client = TestClient(api_module.app)
    viewer = {"email": "t@t.com", "role": "viewer", "token": "fake"}
    with patch(
        "backend.config.lookup_user_by_token",
        side_effect=lambda t: viewer if t == "fake" else None,
    ):
        yield client


def test_upload_returns_upload_id(tmp_path, authed_client):
    with patch("backend.ingest_api.UPLOAD_DIR", str(tmp_path)):
        response = authed_client.post(
            "/api/ingest/upload",
            files={"file": ("test.txt", b"hello world", "text/plain")},
            data={"notes": "test upload"},
            headers={"Authorization": "Bearer fake"},
        )
    assert response.status_code == 200
    data = response.json()
    assert "upload_id" in data
    assert data["filename"] == "test.txt"
    assert data["notes"] == "test upload"  # verifies notes is read as Form field


def test_upload_rejects_unsupported_type(tmp_path, authed_client):
    with patch("backend.ingest_api.UPLOAD_DIR", str(tmp_path)):
        response = authed_client.post(
            "/api/ingest/upload",
            files={"file": ("file.exe", b"binary", "application/octet-stream")},
            headers={"Authorization": "Bearer fake"},
        )
    assert response.status_code == 400
    assert "unsupported" in response.json()["detail"].lower()


def test_upload_rejects_large_file(tmp_path, authed_client):
    big = b"x" * (101 * 1024 * 1024)  # 101 MB
    with patch("backend.ingest_api.UPLOAD_DIR", str(tmp_path)):
        response = authed_client.post(
            "/api/ingest/upload",
            files={"file": ("big.pdf", big, "application/pdf")},
            headers={"Authorization": "Bearer fake"},
        )
    assert response.status_code == 413


def test_plan_returns_409_when_locked(authed_client):
    from backend import ingest_service

    ingest_service.acquire_lock()
    try:
        response = authed_client.post(
            "/api/ingest/plan",
            json={"upload_id": "fake-id"},
            headers={"Authorization": "Bearer fake"},
        )
        assert response.status_code == 409
    finally:
        ingest_service.release_lock()


def test_execute_returns_410_for_expired_session(authed_client):
    response = authed_client.post(
        "/api/ingest/execute",
        json={"session_id": "no-such-session"},
        headers={"Authorization": "Bearer fake"},
    )
    assert response.status_code == 410


def test_execute_returns_409_when_locked(authed_client):
    from backend import ingest_service as svc
    import time

    # Store a valid session so the 410 check passes
    session = svc.IngestSession(
        session_id="test-session-409",
        upload_id="up-1",
        plan={"operations": []},
        created_at=time.time(),
        slug="test",
        filename="test.pdf",
        original_path="/tmp/test.pdf",
    )
    svc.store_session(session)

    svc.acquire_lock()
    try:
        response = authed_client.post(
            "/api/ingest/execute",
            json={"session_id": "test-session-409"},
            headers={"Authorization": "Bearer fake"},
        )
        assert response.status_code == 409
    finally:
        svc.release_lock()
