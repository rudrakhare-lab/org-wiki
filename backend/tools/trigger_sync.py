"""
STEP 8 — backend/tools/trigger_sync.py (new file, admin-only tool).

Provides an in-API path for admins to invoke the same daily sync the cron
job runs. Same script (scripts/jira_daily_sync.py), two trigger paths —
this satisfies the post-deployment constraint that everything happens via
Anthropic API (no terminal required).

──────────────────────────────────────────────────────────────────────────────
MODE SAFETY
──────────────────────────────────────────────────────────────────────────────

  mode="delta"                — sync + classify recent N days. Default. Safe.
  mode="classification_only"  — re-classify only (skip Jira sync). Safe.
  mode="full"                 — re-classify ALL 37k tickets (~$37, ~6 hours).
                                Requires confirm="yes-reclassify-all" to prevent
                                accidental triggers.

──────────────────────────────────────────────────────────────────────────────
EXECUTION MODEL
──────────────────────────────────────────────────────────────────────────────

  mode="delta" / "classification_only":
    Synchronous subprocess. Captures stdout/stderr to in-memory buffer.
    May take several minutes (typically 30s-5min for small deltas).
    Configurable timeout (default 60 min).

  mode="full":
    DETACHED subprocess (Popen + start_new_session=True). Returns
    immediately with the PID. Operator monitors logs/jira_sync.log.
    Reason: an api-mode tool call shouldn't block for 6 hours.

──────────────────────────────────────────────────────────────────────────────
ROLE GATING
──────────────────────────────────────────────────────────────────────────────

  Registered in backend/tools/registry.py::_TOOL_PERMISSIONS as "admin"-only.
  See /tmp/step8_registry_edit.txt for the registry.py edit.
"""
from __future__ import annotations

import logging
import os
import subprocess
import time
from pathlib import Path

_LOG = logging.getLogger("trigger_sync")

REPO = Path(__file__).resolve().parents[2]
VENV_PY = REPO / "venv" / "bin" / "python"
DAILY_SYNC = REPO / "scripts" / "jira_daily_sync.py"
LOG_FILE = REPO / "logs" / "jira_sync.log"

# Default timeouts (seconds)
DELTA_TIMEOUT_S = 3600     # 60 min — generous for backlog catch-up
CLASS_ONLY_TIMEOUT_S = 3600


# ── Schema ────────────────────────────────────────────────────────────────────

TRIGGER_JIRA_SYNC_SCHEMA: dict = {
    "name": "trigger_jira_sync",
    "description": (
        "ADMIN-ONLY: trigger the Jira daily-sync orchestrator. Three modes:\n"
        "  - 'delta': run jira_sync --incremental + classify_jira --delta N. "
        "Default daily-use mode. May take a few minutes for small deltas, "
        "up to 60min for large backlogs.\n"
        "  - 'classification_only': skip the Jira sync; only run classify_jira "
        "with the configured delta window. Useful after a classifier_version bump "
        "to refresh recent tickets without re-fetching from Jira.\n"
        "  - 'full': RE-CLASSIFY ALL ~37k TICKETS (≈$37, ≈6 hours). Requires "
        "confirm='yes-reclassify-all' to prevent accidental triggers. Runs "
        "DETACHED — returns immediately with a PID for monitoring."
    ),
    "input_schema": {
        "type": "object",
        "required": ["mode"],
        "properties": {
            "mode": {
                "type": "string",
                "enum": ["delta", "full", "classification_only"],
                "description": "Sync mode (see tool description for safety implications).",
            },
            "days": {
                "type": "integer",
                "minimum": 1,
                "maximum": 90,
                "default": 2,
                "description": (
                    "Delta window in days for mode='delta' or mode='classification_only'. "
                    "Ignored for mode='full'. Default 2."
                ),
            },
            "confirm": {
                "type": "string",
                "description": (
                    "REQUIRED when mode='full'. Must be exactly "
                    "'yes-reclassify-all' to confirm intent. Ignored for other modes."
                ),
            },
        },
    },
}


# ── Handler ───────────────────────────────────────────────────────────────────

def _trigger_jira_sync_handler(inp: dict) -> dict:
    """See module docstring. Returns structured result with success/failure + counts."""
    mode = (inp.get("mode") or "").strip()
    if mode not in {"delta", "full", "classification_only"}:
        return {"error": f"invalid mode: {mode!r}", "code": "invalid_input"}

    try:
        days = int(inp.get("days", 2))
    except (TypeError, ValueError):
        return {"error": "days must be an integer", "code": "invalid_input"}
    if days < 1 or days > 90:
        return {"error": f"days={days} out of range (1-90)", "code": "invalid_input"}

    confirm = (inp.get("confirm") or "").strip()

    # ── Safety check for full mode ────────────────────────────────────────────
    if mode == "full" and confirm != "yes-reclassify-all":
        return {
            "error": (
                "mode='full' requires confirm='yes-reclassify-all'. "
                "This will re-classify all ~37,267 tickets at ~$37 cost over ~6 hours."
            ),
            "code": "confirmation_required",
        }

    # ── Environment check ─────────────────────────────────────────────────────
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return {
            "error": "ANTHROPIC_API_KEY not set in server environment",
            "code": "env_misconfigured",
        }

    if not DAILY_SYNC.exists():
        return {
            "error": f"daily-sync script not found at {DAILY_SYNC}",
            "code": "script_missing",
        }

    # ── Dispatch by mode ──────────────────────────────────────────────────────
    if mode == "full":
        return _run_full_detached(confirm_token=confirm)

    if mode == "delta":
        return _run_synchronous(
            args=["--classification-days", str(days)],
            timeout=DELTA_TIMEOUT_S,
            label="delta",
        )

    # classification_only
    return _run_synchronous(
        args=["--classification-only", "--classification-days", str(days)],
        timeout=CLASS_ONLY_TIMEOUT_S,
        label="classification_only",
    )


def _run_synchronous(args: list[str], timeout: int, label: str) -> dict:
    """Run jira_daily_sync.py synchronously and parse the structured DONE line."""
    cmd = [str(VENV_PY), str(DAILY_SYNC)] + args
    start = time.time()
    _LOG.info(f"trigger_jira_sync[{label}] starting: {' '.join(cmd)}")

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(REPO),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {
            "error": f"sync exceeded {timeout}s timeout",
            "code": "timeout",
            "mode": label,
            "elapsed_s": time.time() - start,
        }
    except OSError as exc:
        return {
            "error": f"could not spawn subprocess: {exc}",
            "code": "spawn_failed",
            "mode": label,
        }

    elapsed = time.time() - start
    # Parse last few lines for counts and cost. jira_daily_sync.py emits
    # "STAGE_OK sync — fetched=N, new=N, ..." and "STAGE_OK classify — N tickets, $C"
    out = (proc.stdout or "") + (proc.stderr or "")
    sync_summary = _extract_after(out, "STAGE_OK sync — ")
    classify_summary = _extract_after(out, "STAGE_OK classify — ")
    done_line = _extract_after(out, "DONE ")

    success = proc.returncode == 0
    return {
        "success": success,
        "mode": label,
        "exit_code": proc.returncode,
        "elapsed_s": round(elapsed, 1),
        "sync_summary": sync_summary,
        "classify_summary": classify_summary,
        "done_line": done_line,
        "log_path": str(LOG_FILE),
        "stderr_tail": _tail((proc.stderr or ""), 5) if not success else None,
    }


def _run_full_detached(confirm_token: str) -> dict:
    """Spawn the full reclassify in a detached subprocess; return PID."""
    # We invoke classify_jira.py --full directly here — daily-sync wrapper isn't
    # the right tool for a 6-hour --full pass. The wrapper exists for delta and
    # classification_only orchestration.
    classify_script = REPO / "scripts" / "classify_jira.py"
    if not classify_script.exists():
        return {
            "error": f"classify script not found at {classify_script}",
            "code": "script_missing",
        }

    cmd = [str(VENV_PY), str(classify_script), "--full", "--yes"]
    log_path = REPO / "logs" / "classify_full.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        out_fh = open(log_path, "a", encoding="utf-8")
        proc = subprocess.Popen(
            cmd,
            cwd=str(REPO),
            stdout=out_fh,
            stderr=subprocess.STDOUT,
            start_new_session=True,  # detach from this server's session
        )
    except OSError as exc:
        return {
            "error": f"could not spawn detached process: {exc}",
            "code": "spawn_failed",
        }

    return {
        "success": True,
        "mode": "full",
        "detached": True,
        "pid": proc.pid,
        "log_path": str(log_path),
        "expected_runtime": "~6 hours, ~$37 cost",
        "monitoring_hint": (
            f"tail -f {log_path}  # to watch progress\n"
            f"ps -p {proc.pid}    # to confirm still running"
        ),
        "warning": (
            "DETACHED process. Will continue running even if the backend restarts. "
            "Use ps + kill if you need to stop it."
        ),
    }


def _extract_after(text: str, marker: str) -> str:
    """Return the first line containing `marker`, with the marker stripped."""
    for line in text.splitlines():
        if marker in line:
            return line.split(marker, 1)[1].strip()
    return ""


def _tail(text: str, n: int) -> list[str]:
    lines = text.splitlines()
    return lines[-n:] if len(lines) > n else lines


# ── End ──────────────────────────────────────────────────────────────────────
#
# Edge cases this handler covers:
#   - mode missing or invalid                    → invalid_input
#   - days out of range                          → invalid_input
#   - mode='full' without confirm                → confirmation_required
#   - mode='full' with wrong confirm token       → confirmation_required
#   - ANTHROPIC_API_KEY missing                  → env_misconfigured
#   - daily-sync script missing                  → script_missing
#   - subprocess spawn failure                   → spawn_failed
#   - subprocess timeout (delta/class_only only) → timeout
#   - subprocess exits non-zero                  → success=false + stderr_tail
#
# What this handler does NOT do (by design):
#   - Does NOT stream output back to the agent (sync mode buffers; full mode
#     detaches). Agents typically don't benefit from streaming sync output —
#     they need the summary line at the end.
#   - Does NOT cancel running syncs. To stop a detached full run, the admin
#     uses ps + kill.
#   - Does NOT block the FastAPI event loop indefinitely — synchronous modes
#     have a 60-min timeout; full mode is detached.
