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
