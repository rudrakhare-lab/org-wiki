import subprocess
from scripts.lib.ref_fetch import fetch_drive_file


class _Proc:
    def __init__(self, rc, out="", err=""):
        self.returncode, self.stdout, self.stderr = rc, out, err


def test_command_shape_and_success(tmp_path):
    captured = {}

    def runner(cmd, **kw):
        captured["cmd"] = cmd
        (tmp_path / "FID.docx").write_bytes(b"hello")   # simulate rclone writing the file
        return _Proc(0)

    res = fetch_drive_file("FID", "gdoc", str(tmp_path), runner=runner)
    assert res.status == "fetched"
    assert res.sha256 == __import__("hashlib").sha256(b"hello").hexdigest()
    assert "--drive-export-formats" in captured["cmd"]
    assert "docx" in captured["cmd"]
    assert "gdrive:" in captured["cmd"] and "FID" in captured["cmd"]


def test_404_is_access_denied(tmp_path):
    def runner(cmd, **kw):
        return _Proc(1, err='Error 404: File not found: FID., notFound')
    res = fetch_drive_file("FID", "gsheet", str(tmp_path), runner=runner)
    assert res.status == "access_denied"


def test_other_failure_is_error(tmp_path):
    def runner(cmd, **kw):
        return _Proc(1, err="some transient network blip")
    res = fetch_drive_file("FID", "gslide", str(tmp_path), runner=runner)
    assert res.status == "error"


from scripts.lib.ref_fetch import fetch_pdf


def test_fetch_pdf_success_and_failure(tmp_path):
    def ok(cmd, **kw):
        (tmp_path / "FID.pdf").write_bytes(b"%PDF-1.4")
        return _Proc(0)
    assert fetch_pdf("FID", str(tmp_path), runner=ok).endswith("FID.pdf")

    def fail(cmd, **kw):
        return _Proc(1, err="404 notFound")
    assert fetch_pdf("FID2", str(tmp_path), runner=fail) is None


def test_fetch_pdf_runner_raises_returns_none(tmp_path):
    def raising_runner(cmd, **kw):
        raise OSError("rclone not found")
    assert fetch_pdf("FID3", str(tmp_path), runner=raising_runner) is None


# ── Task R: Resilience — timeout tests ──────────────────────────────────────

def test_fetch_drive_file_timeout_returns_error(tmp_path):
    """A runner raising TimeoutExpired → FetchResult with status 'error'."""
    def timeout_runner(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, 180)

    res = fetch_drive_file("FID", "gdoc", str(tmp_path), runner=timeout_runner)
    assert res.status == "error"


def test_fetch_pdf_timeout_returns_none(tmp_path):
    """A runner raising TimeoutExpired → fetch_pdf returns None (covered by except Exception)."""
    def timeout_runner(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, 180)

    assert fetch_pdf("FID", str(tmp_path), runner=timeout_runner) is None
