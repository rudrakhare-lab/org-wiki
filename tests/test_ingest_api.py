"""Integration tests for ingest API endpoints."""
import importlib
import io
import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def authed_client(tmp_path):
    """TestClient with a patched lookup so Bearer fake passes as a developer user
    (ingest endpoints require developer-or-admin)."""
    from backend import api as api_module
    importlib.reload(api_module)
    client = TestClient(api_module.app)
    dev_user = {"email": "t@t.com", "role": "developer", "token": "fake", "approved": True}
    with patch(
        "backend.config.lookup_user_by_token",
        side_effect=lambda t: dev_user if t == "fake" else None,
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
    from backend.api import app
    with patch("backend.api._require_user", return_value={"email": "t@t.com", "role": "viewer"}):
        client = TestClient(app)
        response = client.post(
            "/api/ingest/execute",
            json={"session_id": "no-such-session"},
            headers={"Authorization": "Bearer fake"},
        )
    assert response.status_code == 410


def test_execute_returns_409_when_locked(authed_client):
    from backend import ingest_service as svc

    # Store a valid session so the 410 check passes
    session = svc.IngestSession(
        session_id="test-session-409b",
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
            json={"session_id": "test-session-409b"},
            headers={"Authorization": "Bearer fake"},
        )
        assert response.status_code == 409
    finally:
        svc.release_lock()


def test_execute_returns_job_id(authed_client):
    """Execute with a valid session returns a job_id immediately (no streaming)."""
    from backend import ingest_service

    session = ingest_service.IngestSession(
        session_id="test-session-jobid",
        upload_id="up-job",
        plan={"operations": []},
        created_at=time.time(),
        slug="test",
        filename="test.pdf",
        original_path="/tmp/test.pdf",
    )
    ingest_service.store_session(session)

    try:
        # Mock the background task so it doesn't actually call Anthropic
        with patch("backend.ingest_api._run_ingest_job", new_callable=AsyncMock) as mock_run:
            # Make the mock do nothing (job stays "running")
            mock_run.return_value = None
            response = authed_client.post(
                "/api/ingest/execute",
                json={"session_id": "test-session-jobid"},
                headers={"Authorization": "Bearer fake"},
            )
    finally:
        # The mock never calls release_lock, so release it here to avoid leaking
        ingest_service.release_lock()

    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "running"


def test_get_job_returns_404_for_unknown(authed_client):
    response = authed_client.get(
        "/api/ingest/job/nonexistent-job-id",
        headers={"Authorization": "Bearer fake"},
    )
    assert response.status_code == 404


def test_get_job_returns_job_state(authed_client):
    from backend import ingest_service

    job = ingest_service.create_job("test-job-state")
    job.status = "complete"
    job.files_created = ["wiki/modules/test.md"]
    job.links = ["modules/test"]

    response = authed_client.get(
        "/api/ingest/job/test-job-state",
        headers={"Authorization": "Bearer fake"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "complete"
    assert data["files_created"] == ["wiki/modules/test.md"]
    assert data["links"] == ["modules/test"]


def test_lock_released_after_job_completes():
    """Lock must be released in finally even after job runs — no stuck-lock outage."""
    import asyncio
    from backend import ingest_service

    session = ingest_service.IngestSession(
        session_id="test-lock-release",
        upload_id="up-lock",
        plan={"operations": []},
        created_at=time.time(),
        slug="test",
        filename="test.pdf",
        original_path="/tmp/test.pdf",
    )
    ingest_service.store_session(session)
    job = ingest_service.create_job("job-lock-release")

    # Acquire lock (as execute endpoint would)
    assert ingest_service.acquire_lock()

    # Simulate the background job finishing with an error (exercises finally)
    async def run():
        from backend.ingest_api import _run_ingest_job
        # Patch AsyncAnthropic to raise immediately
        with patch("backend.ingest_api.anthropic.AsyncAnthropic") as mock_cls:
            mock_instance = AsyncMock()
            mock_instance.messages.create.side_effect = RuntimeError("simulated failure")
            mock_cls.return_value = mock_instance
            await _run_ingest_job(session, job)

    asyncio.run(run())

    # Lock MUST be released even after exception
    assert not ingest_service.is_locked(), "Lock was not released after job failure"
    assert job.status == "error"


def test_execute_continues_past_per_op_error(monkeypatch):
    import asyncio, types
    from unittest.mock import patch, AsyncMock
    from backend import ingest_service, ingest_api

    session = ingest_service.IngestSession(
        session_id="sess-resilient",
        upload_id="up-resilient",
        plan={"operations": [
            {"type": "create", "path": "wiki/concepts/a.md"},
            {"type": "edit",   "path": "wiki/concepts/a.md"},
        ]},
        created_at=__import__("time").time(),
        slug="a",
        filename="a.pdf",
        original_path="/tmp/does-not-exist-resilient.pdf",
    )
    ingest_service.store_session(session)
    job = ingest_service.create_job("job-resilient")

    # Fake execute registry: create ok, edit errors (mimics 'old_str appears N times').
    class _FakeReg:
        schemas: list = []
        def execute(self, name, inp, n, trace_id=None):
            if name == "wiki_edit_page":
                return ('{"error": "old_str appears 260 times"}', None)
            return ('{"created": true}', None)
    monkeypatch.setattr(ingest_api.ingest_service, "build_execute_registry", lambda agent: _FakeReg())

    # Fake agent so prompt render + dir ops don't need a real registry/wiki.
    fake_agent = types.SimpleNamespace(
        id="conwo", display_name="Conwo", identity="x", schema_kind="workinsync",
        wiki_dir=__import__("pathlib").Path("/tmp/resilient_wiki"),
        raw_dir=__import__("pathlib").Path("/tmp/resilient_raw"))
    monkeypatch.setattr(ingest_api.agent_registry, "get", lambda aid: fake_agent)

    def _block(name, path, bid):
        return types.SimpleNamespace(type="tool_use", name=name, input={"path": path}, id=bid)
    turn1 = types.SimpleNamespace(
        content=[_block("wiki_create_page", "wiki/concepts/a.md", "b1"),
                 _block("wiki_edit_page", "wiki/concepts/a.md", "b2")],
        stop_reason="tool_use")
    turn2 = types.SimpleNamespace(content=[], stop_reason="end_turn")

    async def run():
        with patch("backend.ingest_api.anthropic.AsyncAnthropic") as mock_cls:
            inst = AsyncMock()
            inst.messages.create.side_effect = [turn1, turn2]
            mock_cls.return_value = inst
            await ingest_api._run_ingest_job(session, job)
    asyncio.run(run())

    assert job.status == "complete"            # did NOT abort on the edit error
    assert "wiki/concepts/a.md" in job.files_created
    assert len(job.warnings) == 1 and "old_str appears 260 times" in job.warnings[0]


def test_regenerate_index_md_builds_toc(tmp_path):
    import types
    import backend.ingest_api as ing
    wd = tmp_path / "wiki"
    (wd / "concepts").mkdir(parents=True)
    (wd / "relationships").mkdir(parents=True)
    (wd / "index.md").write_text("# Old\n_Total pages: 0_\n")
    (wd / "concepts" / "due-diligence.md").write_text("---\ncategory: concepts\n---\n# Due Diligence\nx")
    (wd / "relationships" / "a-b.md").write_text("---\ncategory: relationships\n---\n# A to B\nx")
    agent = types.SimpleNamespace(id="legal", schema_kind="generic", display_name="Legal", wiki_dir=wd)
    ing._regenerate_index_md(agent)
    body = (wd / "index.md").read_text()
    assert "_Total pages: 2_" in body
    assert "## Concepts" in body and "## Relationships" in body
    assert "[Due Diligence](concepts/due-diligence.md)" in body


def test_regenerate_index_md_skips_conwo(tmp_path):
    import types
    import backend.ingest_api as ing
    wd = tmp_path / "wiki"
    wd.mkdir(parents=True)
    (wd / "index.md").write_text("# WorkInSync Feature Wiki — Index\n_Total pages: 101 | Modules: 22_\n")
    agent = types.SimpleNamespace(id="conwo", schema_kind="workinsync", display_name="Conwo", wiki_dir=wd)
    ing._regenerate_index_md(agent)
    assert "Modules: 22" in (wd / "index.md").read_text()  # untouched
