"""SQLite manifest for the SE-runbook reference crawl — the coverage ledger.

Each row in `refs` is one discovered reference. The crawl is provably complete
when coverage_complete() returns True (no refs still in flight AND no images
pending OCR).

R2 addition: an `images` table tracks screenshots found in source documents.
coverage_complete() is True only when both conditions hold:
  (a) no refs rows with status in ('discovered', 'fetched', 'error')
  (b) no images rows with ocr_status != 'done'
With no image rows, condition (b) is vacuously true.
"""
from __future__ import annotations

import sqlite3

_SCHEMA = """
CREATE TABLE IF NOT EXISTS refs (
    url             TEXT PRIMARY KEY,
    file_id         TEXT,
    ref_type        TEXT NOT NULL,
    referenced_from TEXT,
    depth           INTEGER NOT NULL,
    status          TEXT NOT NULL DEFAULT 'discovered',
    local_path      TEXT,
    sha256          TEXT,
    error           TEXT,
    fetched_at      TEXT
);

CREATE TABLE IF NOT EXISTS images (
    image_path     TEXT PRIMARY KEY,
    source_file    TEXT,
    section        TEXT,
    nearby_text    TEXT,
    ocr_status     TEXT NOT NULL DEFAULT 'pending',
    ocr_text_path  TEXT
);
"""

# Statuses that mean "still needs work" — coverage is complete when none remain.
_IN_FLIGHT = ("discovered", "fetched", "error")
_ALLOWED_FIELDS = {"local_path", "sha256", "error", "fetched_at"}


class Manifest:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    # ── refs API ─────────────────────────────────────────────────────────────

    def add_if_new(self, url: str, ref_type: str, depth: int,
                   referenced_from: str, file_id: str | None = None) -> bool:
        """Insert a discovered row; return False if url already present (dedupe)."""
        if self.conn.execute("SELECT 1 FROM refs WHERE url=?", (url,)).fetchone():
            return False
        self.conn.execute(
            "INSERT INTO refs(url, file_id, ref_type, referenced_from, depth, status) "
            "VALUES(?,?,?,?,?,'discovered')",
            (url, file_id, ref_type, referenced_from, depth),
        )
        self.conn.commit()
        return True

    def next_discovered(self) -> sqlite3.Row | None:
        """Return the lowest-depth discovered row, or None."""
        return self.conn.execute(
            "SELECT * FROM refs WHERE status='discovered' ORDER BY depth, url LIMIT 1"
        ).fetchone()

    def update_status(self, url: str, status: str, **fields) -> None:
        """Set status plus any of local_path, sha256, error, fetched_at."""
        bad = set(fields) - _ALLOWED_FIELDS
        if bad:
            raise ValueError(f"unknown manifest fields: {bad}")
        fields["status"] = status
        cols = ", ".join(f"{k}=?" for k in fields)
        self.conn.execute(
            f"UPDATE refs SET {cols} WHERE url=?", [*fields.values(), url]
        )
        self.conn.commit()

    def coverage_complete(self) -> bool:
        """True when no refs are in-flight AND no images are pending OCR."""
        # Condition (a): no refs in flight
        placeholders = ",".join("?" * len(_IN_FLIGHT))
        n_refs = self.conn.execute(
            f"SELECT COUNT(*) AS n FROM refs WHERE status IN ({placeholders})",
            _IN_FLIGHT,
        ).fetchone()["n"]
        if n_refs > 0:
            return False
        # Condition (b): no images with ocr_status != 'done'
        n_images = self.conn.execute(
            "SELECT COUNT(*) AS n FROM images WHERE ocr_status != 'done'"
        ).fetchone()["n"]
        return n_images == 0

    def report(self) -> dict[str, int]:
        """Count of refs rows by status. Does NOT include image counts."""
        rows = self.conn.execute(
            "SELECT status, COUNT(*) AS n FROM refs GROUP BY status"
        ).fetchall()
        return {r["status"]: r["n"] for r in rows}

    def access_holes(self) -> list[sqlite3.Row]:
        """Rows with status access_denied."""
        return self.conn.execute(
            "SELECT url, referenced_from, error FROM refs WHERE status='access_denied'"
        ).fetchall()

    def requeue_denied(self) -> int:
        """Flip every access_denied row back to discovered; return count requeued."""
        cur = self.conn.execute(
            "UPDATE refs SET status='discovered', error=NULL WHERE status='access_denied'"
        )
        self.conn.commit()
        return cur.rowcount

    # ── images API (R2) ──────────────────────────────────────────────────────

    def add_image_if_new(self, image_path: str, source_file: str,
                          section: str | None = None,
                          nearby_text: str | None = None) -> bool:
        """Insert a pending image row; return False if image_path already present."""
        if self.conn.execute(
            "SELECT 1 FROM images WHERE image_path=?", (image_path,)
        ).fetchone():
            return False
        self.conn.execute(
            "INSERT INTO images(image_path, source_file, section, nearby_text, ocr_status) "
            "VALUES(?,?,?,?,'pending')",
            (image_path, source_file, section, nearby_text),
        )
        self.conn.commit()
        return True

    def next_pending_image(self) -> sqlite3.Row | None:
        """One row with ocr_status='pending' ordered by image_path, or None."""
        return self.conn.execute(
            "SELECT * FROM images WHERE ocr_status='pending' ORDER BY image_path LIMIT 1"
        ).fetchone()

    def set_image_ocr(self, image_path: str, ocr_status: str,
                       ocr_text_path: str | None = None) -> None:
        """Update ocr_status (and ocr_text_path when provided)."""
        if ocr_text_path is not None:
            self.conn.execute(
                "UPDATE images SET ocr_status=?, ocr_text_path=? WHERE image_path=?",
                (ocr_status, ocr_text_path, image_path),
            )
        else:
            self.conn.execute(
                "UPDATE images SET ocr_status=? WHERE image_path=?",
                (ocr_status, image_path),
            )
        self.conn.commit()

    def is_image_done(self, image_path: str) -> bool:
        """Return True iff image_path exists in the images table with ocr_status='done'."""
        row = self.conn.execute(
            "SELECT 1 FROM images WHERE image_path=? AND ocr_status='done'", (image_path,)
        ).fetchone()
        return row is not None

    def requeue_incomplete_fetches(self) -> int:
        """Reopen rows fetched-but-not-fully-processed (interrupted mid-extract/OCR) so a
        resumed run reprocesses them. next_discovered() only returns 'discovered' rows, so a
        'fetched' row would otherwise be stranded."""
        cur = self.conn.execute("UPDATE refs SET status='discovered' WHERE status='fetched'")
        self.conn.commit()
        return cur.rowcount
