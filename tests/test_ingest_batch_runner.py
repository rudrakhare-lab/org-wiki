"""run_batch: serial processing, done/failed per item, failure isolation, counts."""
import asyncio
import time
import pytest
from backend import ingest_batch, ingest_service


@pytest.fixture(autouse=True)
def clean(clean_db):
    yield


def _items(n):
    return [{"upload_id": f"u{i}", "filename": f"f{i}.pdf", "file_path": f"/tmp/f{i}.pdf"}
            for i in range(n)]


def _stub_plan(monkeypatch, *, fail_on=()):
    """Stub _run_plan_job: set job.status done + a session, or error for fail_on filenames.
    Mirrors the real coroutine by releasing the global ingest lock in its finally block."""
    from backend import ingest_api

    async def fake_plan(job, file_path, filename, notes, target_slug):
        try:
            if filename in fail_on:
                job.status = "error"; job.error_msg = f"plan failed: {filename}"
                return
            sid = ingest_service.new_session_id()
            ingest_service.store_session(ingest_service.IngestSession(
                session_id=sid, upload_id=job.upload_id, plan={"operations": []},
                created_at=time.time(), slug="x", filename=filename, original_path=file_path,
                agent_id=job.agent_id))
            job.session_id = sid; job.status = "done"
        finally:
            ingest_service.release_lock()
    monkeypatch.setattr(ingest_api, "_run_plan_job", fake_plan)


def _stub_execute(monkeypatch, *, fail_on=()):
    from backend import ingest_api

    async def fake_exec(session, job):
        try:
            if session.filename in fail_on:
                job.status = "error"; job.error_msg = f"exec failed: {session.filename}"
                return
            job.status = "complete"; job.files_created = [f"wiki/modules/{session.filename}.md"]
        finally:
            ingest_service.release_lock()
    monkeypatch.setattr(ingest_api, "_run_ingest_job", fake_exec)


def test_run_batch_all_succeed(monkeypatch):
    _stub_plan(monkeypatch); _stub_execute(monkeypatch)
    r = ingest_batch.create_batch("conwo", "a@x.com", _items(3))
    asyncio.run(ingest_batch.run_batch(r["batch_id"]))
    got = ingest_batch.get_batch(r["batch_id"])
    assert got["batch"]["status"] == "done"
    assert got["batch"]["completed"] == 3 and got["batch"]["failed"] == 0
    assert all(i["status"] == "done" for i in got["items"])


def test_run_batch_isolates_a_plan_failure(monkeypatch):
    _stub_plan(monkeypatch, fail_on=("f1.pdf",)); _stub_execute(monkeypatch)
    r = ingest_batch.create_batch("conwo", "a@x.com", _items(3))
    asyncio.run(ingest_batch.run_batch(r["batch_id"]))
    got = ingest_batch.get_batch(r["batch_id"])
    assert got["batch"]["completed"] == 2 and got["batch"]["failed"] == 1
    by_ord = {i["ord"]: i for i in got["items"]}
    assert by_ord[1]["status"] == "failed" and "plan failed" in by_ord[1]["error"]
    assert by_ord[0]["status"] == "done" and by_ord[2]["status"] == "done"


def test_run_batch_isolates_an_execute_failure(monkeypatch):
    _stub_plan(monkeypatch); _stub_execute(monkeypatch, fail_on=("f0.pdf",))
    r = ingest_batch.create_batch("conwo", "a@x.com", _items(2))
    asyncio.run(ingest_batch.run_batch(r["batch_id"]))
    got = ingest_batch.get_batch(r["batch_id"])
    assert got["batch"]["failed"] == 1 and got["batch"]["completed"] == 1
    assert ingest_service.is_locked() is False  # lock always released


def test_run_batch_all_failed_sets_failed(monkeypatch):
    _stub_plan(monkeypatch, fail_on=("f0.pdf", "f1.pdf")); _stub_execute(monkeypatch)
    r = ingest_batch.create_batch("conwo", "a@x.com", _items(2))
    asyncio.run(ingest_batch.run_batch(r["batch_id"]))
    got = ingest_batch.get_batch(r["batch_id"])
    assert got["batch"]["status"] == "failed" and got["batch"]["failed"] == 2
