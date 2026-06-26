"""Fetch a Google-native Drive file by ID via rclone, exporting to Office format.

This is the ONLY module that touches the network. Swapping the fetch mechanism
(e.g. to the Drive API later) means replacing only this file.
"""
from __future__ import annotations

import hashlib
import pathlib
import subprocess
from dataclasses import dataclass

_EXPORT_FMT = {"gdoc": "docx", "gsheet": "xlsx", "gslide": "pptx"}
_EXT = {"gdoc": ".docx", "gsheet": ".xlsx", "gslide": ".pptx"}
_DENIED_MARKERS = ("404", "notfound", "403", "forbidden", "permission")


@dataclass
class FetchResult:
    status: str
    local_path: str | None = None
    sha256: str | None = None
    error: str | None = None


def fetch_drive_file(file_id, ref_type, dest_dir, remote="gdrive:", runner=subprocess.run, timeout=180):
    fmt = _EXPORT_FMT[ref_type]
    dest = pathlib.Path(dest_dir) / f"{file_id}{_EXT[ref_type]}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "rclone", "backend", "copyid",
        "--drive-export-formats", fmt,
        remote, file_id, str(dest),
    ]
    try:
        proc = runner(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return FetchResult("error", error=f"rclone timeout after {timeout}s")
    blob = (getattr(proc, "stdout", "") or "") + (getattr(proc, "stderr", "") or "")
    if proc.returncode == 0 and dest.exists():
        data = dest.read_bytes()
        return FetchResult("fetched", str(dest), hashlib.sha256(data).hexdigest())
    low = blob.lower()
    if any(m in low for m in _DENIED_MARKERS):
        return FetchResult("access_denied", error=blob.strip()[:300])
    return FetchResult("error", error=blob.strip()[:300])


def fetch_pdf(file_id, dest_dir, remote="gdrive:", runner=subprocess.run, timeout=180):
    """Best-effort PDF render for link scraping. Returns path or None; never raises."""
    dest = pathlib.Path(dest_dir) / f"{file_id}.pdf"
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["rclone", "backend", "copyid", "--drive-export-formats", "pdf",
           remote, file_id, str(dest)]
    try:
        proc = runner(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception:
        return None
    return str(dest) if proc.returncode == 0 and dest.exists() else None
