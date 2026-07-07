"""Background delta re-embed on wiki writes (spec §5.2 sync triggers).

Coalesced per agent: one running + at most one queued. Fail-open — a
failed embed leaves the previous chunks in place (stale beats missing);
the nightly delta pass is the backstop."""
from __future__ import annotations
import logging
import threading

_log = logging.getLogger("wiki_reembed")
_state_lock = threading.Lock()
_pending: dict[str, bool] = {}   # agent_id -> a run is queued behind the current one
_running: set[str] = set()


def _run_delta(agent_id: str) -> None:
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(root / "scripts"))
    import embed_wiki
    from backend import agent_registry
    spec = agent_registry.get(agent_id)
    embed_wiki.run("delta", agent_id, spec.wiki_dir)


def _worker(agent_id: str) -> None:
    while True:
        try:
            _run_delta(agent_id)
        except Exception as exc:
            _log.warning("delta re-embed failed (agent=%s): %s", agent_id, exc)
        with _state_lock:
            if _pending.pop(agent_id, False):
                continue          # a write arrived mid-run — go again
            _running.discard(agent_id)
            return


def schedule_delta_reembed(agent_id: str) -> None:
    with _state_lock:
        if agent_id in _running:
            _pending[agent_id] = True   # coalesce
            return
        _running.add(agent_id)
    try:
        threading.Thread(target=_worker, args=(agent_id,), daemon=True,
                         name=f"wiki-reembed-{agent_id}").start()
    except Exception as exc:
        # Thread/resource exhaustion: the worker never ran, so nothing will
        # ever clear _running. Undo the claim here or the agent is wedged
        # forever (every future call would just set _pending and return).
        # Fail-open — the nightly backstop still covers it.
        with _state_lock:
            _running.discard(agent_id)
        _log.warning("failed to start re-embed worker for %s: %s", agent_id, exc)
