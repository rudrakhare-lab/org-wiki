"""POST /api/ingest/bulk + GET /api/ingest/bulk/{id}: create, resolve uploads, gate."""
import pathlib
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.fixture
def client(clean_db, tmp_path, monkeypatch):
    import backend.ingest_api as ia
    monkeypatch.setattr(ia, "UPLOAD_DIR", str(tmp_path), raising=False)
    from backend import api, auth_store
    auth_store.create_user("dev@moveinsync.com", role="developer", approved=True)
    tok = auth_store.create_token("dev@moveinsync.com")
    return TestClient(api.app, raise_server_exceptions=False), {"Authorization": f"Bearer {tok}"}, tmp_path


def _make_upload(root: pathlib.Path, upload_id: str, filename: str) -> None:
    d = root / upload_id
    d.mkdir(parents=True, exist_ok=True)
    (d / filename).write_text("dummy")


def test_bulk_creates_batch_and_starts_runner(client):
    c, h, root = client
    _make_upload(root, "u0", "a.pdf"); _make_upload(root, "u1", "b.pdf")
    # Don't actually run the pipeline — patch run_batch to a no-op coroutine.
    async def _noop(_bid): return None
    with patch("backend.ingest_batch.run_batch", _noop):
        r = c.post("/api/ingest/bulk", json={"upload_ids": ["u0", "u1"]}, headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2 and body["batch_id"]
    got = c.get(f"/api/ingest/bulk/{body['batch_id']}", headers=h).json()
    assert len(got["items"]) == 2
    assert {i["filename"] for i in got["items"]} == {"a.pdf", "b.pdf"}


def test_bulk_rejects_empty(client):
    c, h, _ = client
    r = c.post("/api/ingest/bulk", json={"upload_ids": []}, headers=h)
    assert r.status_code == 400


def test_bulk_rejects_unknown_upload(client):
    c, h, _ = client
    async def _noop(_bid): return None
    with patch("backend.ingest_batch.run_batch", _noop):
        r = c.post("/api/ingest/bulk", json={"upload_ids": ["does-not-exist"]}, headers=h)
    assert r.status_code == 400


def test_bulk_status_404_unknown(client):
    c, h, _ = client
    assert c.get("/api/ingest/bulk/nope", headers=h).status_code == 404


def test_bulk_requires_auth(client):
    c, _, root = client
    _make_upload(root, "u0", "a.pdf")
    r = c.post("/api/ingest/bulk", json={"upload_ids": ["u0"]})  # no token
    assert r.status_code in (401, 403)
