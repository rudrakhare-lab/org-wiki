"""Re-embed hook — background, coalesced, fail-open."""
import threading
import time
from backend.retrieval.wiki_v2 import reembed


def test_schedule_runs_delta_in_background(monkeypatch):
    ran = threading.Event()
    monkeypatch.setattr(reembed, "_run_delta", lambda aid: ran.set())
    reembed.schedule_delta_reembed("conwo")
    assert ran.wait(timeout=2.0)


def test_schedule_coalesces_concurrent_calls(monkeypatch):
    calls = []
    gate = threading.Event()

    def slow(aid):
        calls.append(aid)
        gate.wait(timeout=2.0)
    monkeypatch.setattr(reembed, "_run_delta", slow)
    reembed.schedule_delta_reembed("conwo")
    time.sleep(0.05)
    reembed.schedule_delta_reembed("conwo")   # coalesced — no second run queued twice
    reembed.schedule_delta_reembed("conwo")
    gate.set()
    time.sleep(0.2)
    assert len(calls) <= 2   # first run + at most one queued follow-up


def test_failure_is_swallowed(monkeypatch):
    def boom(aid):
        raise RuntimeError("gemini down")
    monkeypatch.setattr(reembed, "_run_delta", boom)
    reembed.schedule_delta_reembed("conwo")   # must not raise
    time.sleep(0.1)


def test_thread_start_failure_does_not_wedge_agent(monkeypatch, caplog):
    # If Thread.start() raises (thread/resource exhaustion), the worker never
    # runs — so schedule_delta_reembed must itself undo the _running claim,
    # or the agent is stuck forever (every future call just sets _pending).
    aid = "wedge-test-agent"

    class _BoomThread:
        def __init__(self, *a, **k):
            pass

        def start(self):
            raise RuntimeError("can't start new thread")

    monkeypatch.setattr(reembed.threading, "Thread", _BoomThread)

    with caplog.at_level("WARNING", logger="wiki_reembed"):
        reembed.schedule_delta_reembed(aid)   # must NOT raise

    # The failed claim must have been undone — agent not stuck in _running.
    with reembed._state_lock:
        assert aid not in reembed._running
    assert any("failed to start re-embed worker" in r.message for r in caplog.records)

    # A subsequent call can still spawn a worker (agent is not wedged).
    ran = threading.Event()
    monkeypatch.undo()   # restore the real threading.Thread
    monkeypatch.setattr(reembed, "_run_delta", lambda a: ran.set())
    reembed.schedule_delta_reembed(aid)
    assert ran.wait(timeout=2.0)
