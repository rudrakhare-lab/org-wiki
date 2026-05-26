"""
Cross-process file lock helper (POSIX). Used by the Track A admin apply
handler (Sub-pass C) so two concurrent apply calls on the same wiki page
serialize at the filesystem layer.

Usage:
    from backend.file_locks import locked_write
    with locked_write(target_path) as fh:
        fh.write(new_content)

The context manager:
  - Opens (or creates) the target path in 'w' mode with an exclusive flock.
  - Releases the lock on exit (success or exception).
  - On Windows (no fcntl), falls back to a no-op lock with a warning.

Pilot is single-process / single-worker uvicorn, so flock contention is
expected to be rare. The lock is defensive against a future multi-worker
deployment AND against two admin clicks racing on the same proposal.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, TextIO

_log = logging.getLogger(__name__)

try:
    import fcntl  # POSIX only
    _HAVE_FCNTL = True
except ImportError:  # pragma: no cover (Windows-only path)
    fcntl = None  # type: ignore[assignment]
    _HAVE_FCNTL = False
    _log.warning(
        "fcntl not available (non-POSIX platform) — file locks are a no-op. "
        "Concurrent writes to the same wiki page are not serialized."
    )


@contextmanager
def locked_write(path: Path | str) -> Iterator[TextIO]:
    """Open `path` for writing with an exclusive flock held for the duration.

    Creates parent directories if needed. Truncates the file. Releases the
    lock + closes the file on context exit (including on exception).
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Open for writing; flock lives on the file descriptor.
    fh = target.open("w", encoding="utf-8")
    try:
        if _HAVE_FCNTL:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)  # type: ignore[union-attr]
        try:
            yield fh
        finally:
            if _HAVE_FCNTL:
                try:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)  # type: ignore[union-attr]
                except OSError:
                    # Lock release best-effort; closing fd releases anyway
                    pass
    finally:
        fh.close()


@contextmanager
def locked_read_write(path: Path | str) -> Iterator[Path]:
    """Hold an exclusive lock on `path` while the caller does
    read-modify-write through the returned Path.

    Useful for str_replace edits: the caller reads the file, computes the
    new content, then writes it back, all within the lock so a concurrent
    writer can't slip in between read and write.

    Uses a sidecar `<path>.lock` file so we hold the lock without
    truncating the target. The lock file is left behind (cheap; admins
    can ignore).
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lockfile = target.with_suffix(target.suffix + ".lock")
    fh = lockfile.open("a")  # 'a' to create if missing without truncating
    try:
        if _HAVE_FCNTL:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)  # type: ignore[union-attr]
        try:
            yield target
        finally:
            if _HAVE_FCNTL:
                try:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)  # type: ignore[union-attr]
                except OSError:
                    pass
    finally:
        fh.close()
