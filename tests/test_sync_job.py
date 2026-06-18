"""In-process sync-job tracker: state transitions, overlap blocking, fail-open."""
import threading
import time

import pytest

from backend import sync_job


@pytest.fixture(autouse=True)
def reset_state():
    # Reset the module-global state before each test.
    with sync_job._lock:
        sync_job._state.update({
            "_running": False, "state": "idle",
            "started_at": None, "ended_at": None, "result": None, "message": "",
        })
    yield


def _wait_until_idle_done(timeout=3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if sync_job.status()["state"] in ("done", "error"):
            return
        time.sleep(0.02)
    raise AssertionError(f"job did not finish; state={sync_job.status()['state']}")


def test_initial_status_is_idle():
    s = sync_job.status()
    assert s["state"] == "idle"
    assert "_running" not in s          # internal flag is never exposed


def test_start_runs_and_records_success(monkeypatch):
    monkeypatch.setattr(
        "backend.tools.trigger_sync._trigger_jira_sync_handler",
        lambda inp: {"success": True, "mode": "delta", "sync_summary": "fetched=5",
                     "classify_summary": "5 tickets, $0.01", "done_line": "DONE total=12s"},
    )
    assert sync_job.start() == {"status": "started"}
    _wait_until_idle_done()
    s = sync_job.status()
    assert s["state"] == "done"
    assert s["result"]["classify_summary"] == "5 tickets, $0.01"
    assert s["ended_at"] is not None


def test_failed_pipeline_sets_error(monkeypatch):
    monkeypatch.setattr(
        "backend.tools.trigger_sync._trigger_jira_sync_handler",
        lambda inp: {"success": False, "mode": "delta", "error": "boom"},
    )
    sync_job.start()
    _wait_until_idle_done()
    s = sync_job.status()
    assert s["state"] == "error"
    assert s["message"] == "boom"


def test_overlap_is_blocked(monkeypatch):
    gate = threading.Event()
    monkeypatch.setattr(
        "backend.tools.trigger_sync._trigger_jira_sync_handler",
        lambda inp: (gate.wait(2.0), {"success": True})[1],   # block until released
    )
    assert sync_job.start() == {"status": "started"}
    # second click while running:
    assert sync_job.start() == {"status": "already_running"}
    gate.set()
    _wait_until_idle_done()


def test_worker_exception_sets_error(monkeypatch):
    def boom(inp):
        raise RuntimeError("kaboom")
    monkeypatch.setattr("backend.tools.trigger_sync._trigger_jira_sync_handler", boom)
    sync_job.start()
    _wait_until_idle_done()
    s = sync_job.status()
    assert s["state"] == "error"
    assert "kaboom" in s["message"]


def test_status_result_is_a_copy(monkeypatch):
    monkeypatch.setattr(
        "backend.tools.trigger_sync._trigger_jira_sync_handler",
        lambda inp: {"success": True, "sync_summary": "x"},
    )
    sync_job.start()
    _wait_until_idle_done()
    sync_job.status()["result"]["sync_summary"] = "MUTATED"
    assert sync_job.status()["result"]["sync_summary"] == "x"
