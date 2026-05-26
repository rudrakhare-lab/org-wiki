"""
Headless Claude Code subprocess streamer.

Spawns `claude -p <question> --output-format=stream-json --verbose` in the
repo root and yields each NDJSON event as it arrives on stdout.

Event shapes (per Claude Code stream-json schema):
  {"type": "system", "subtype": "init", ...}
  {"type": "assistant", "message": {"content": [{"type": "text", "text": ...},
                                                 {"type": "tool_use", ...}]}}
  {"type": "user",      "message": {"content": [{"type": "tool_result", ...}]}}
  {"type": "result",    "subtype": "success"|"error_max_turns"|..., "result": "..."}

Caller is responsible for handling asyncio.CancelledError (sent on client
disconnect). On cancellation we SIGTERM the child, then SIGKILL after 3s.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import signal
from pathlib import Path
from typing import AsyncIterator

# Repo root: backend/providers/claude_code_agent.py → parents[2]
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_TIMEOUT_S = 600
_KILL_GRACE_S = 3


def claude_available() -> bool:
    return shutil.which("claude") is not None


async def stream_claude_code(
    question: str,
    timeout_seconds: int = _DEFAULT_TIMEOUT_S,
) -> AsyncIterator[dict]:
    """
    Run `claude -p <question>` with stream-json output in the repo root.
    Yields one dict per NDJSON event.

    Raises:
        FileNotFoundError if the claude binary is not on PATH.
        asyncio.TimeoutError if the subprocess exceeds timeout_seconds.
    """
    if not claude_available():
        raise FileNotFoundError("claude executable not found on PATH")

    proc = await asyncio.create_subprocess_exec(
        "claude",
        "-p", question,
        "--output-format", "stream-json",
        "--verbose",
        cwd=str(_REPO_ROOT),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ},
    )

    try:
        async with asyncio.timeout(timeout_seconds):
            assert proc.stdout is not None
            async for raw_line in proc.stdout:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    yield {"type": "raw", "line": line}
    except (asyncio.CancelledError, asyncio.TimeoutError) as exc:
        await _terminate(proc)
        if isinstance(exc, asyncio.TimeoutError):
            yield {"type": "error", "error": f"timeout after {timeout_seconds}s"}
        raise
    finally:
        # Drain stderr and surface nonzero exit codes
        if proc.returncode is None:
            await _terminate(proc)
        if proc.returncode is not None and proc.returncode != 0:
            stderr_bytes = b""
            if proc.stderr is not None:
                try:
                    stderr_bytes = await asyncio.wait_for(proc.stderr.read(), timeout=1)
                except asyncio.TimeoutError:
                    pass
            stderr_text = stderr_bytes.decode("utf-8", errors="replace")[:2000]
            yield {
                "type": "error",
                "returncode": proc.returncode,
                "stderr": stderr_text,
            }


async def _terminate(proc: asyncio.subprocess.Process) -> None:
    if proc.returncode is not None:
        return
    try:
        proc.send_signal(signal.SIGTERM)
        await asyncio.wait_for(proc.wait(), timeout=_KILL_GRACE_S)
    except (asyncio.TimeoutError, ProcessLookupError):
        try:
            proc.kill()
            await proc.wait()
        except ProcessLookupError:
            pass
