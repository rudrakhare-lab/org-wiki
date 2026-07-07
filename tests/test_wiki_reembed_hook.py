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
