"""Regression: the sync subprocess interpreter must be the running interpreter
(sys.executable), not a hardcoded venv/bin/python path — the prod container has
no project venv, so the hardcoded path raised
'No such file or directory: /app/venv/bin/python'."""
import sys
import importlib.util
from pathlib import Path


def test_trigger_sync_uses_sys_executable():
    # Must be the running interpreter (dynamic), NOT a hardcoded REPO/venv path
    # that doesn't exist in the prod container.
    from backend.tools import trigger_sync
    assert trigger_sync.VENV_PY == sys.executable
    assert trigger_sync.VENV_PY != str(trigger_sync.REPO / "venv" / "bin" / "python")


def test_jira_daily_sync_uses_sys_executable():
    # scripts/ is not a package — load the module by path.
    path = Path(__file__).resolve().parent.parent / "scripts" / "jira_daily_sync.py"
    spec = importlib.util.spec_from_file_location("jira_daily_sync", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.VENV_PY == sys.executable
    assert mod.VENV_PY != str(mod.REPO / "venv" / "bin" / "python")
