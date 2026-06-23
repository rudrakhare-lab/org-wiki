"""Admin endpoints drive the full-pipeline job tracker."""
import time
import pytest
from backend import admin_api, sync_job


@pytest.fixture(autouse=True)
def reset_state():
    with sync_job._lock:
        sync_job._state.update({"_running": False, "state": "idle",
                                "started_at": None, "ended_at": None,
                                "result": None, "message": ""})
    yield


def test_trigger_starts_full_pipeline(monkeypatch):
    monkeypatch.setattr(
        "backend.tools.trigger_sync._trigger_jira_sync_handler",
        lambda inp: {"success": True, "mode": "delta", "done_line": "DONE"},
    )
    assert admin_api.trigger_jira_sync() == {"status": "started"}
    # wait for completion
    for _ in range(150):
        if sync_job.status()["state"] in ("done", "error"):
            break
        time.sleep(0.02)
    assert sync_job.status()["state"] == "done"


def test_sync_status_includes_job_block():
    status = admin_api.get_sync_status()
    assert "job" in status
    assert status["job"]["state"] in ("idle", "running", "done", "error")
