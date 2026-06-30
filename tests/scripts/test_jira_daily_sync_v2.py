from unittest.mock import patch
import importlib

def test_daily_sync_skips_v2_steps_when_flag_off(monkeypatch):
    monkeypatch.setenv("CONWO_RETRIEVAL_V2", "off")
    daily = importlib.import_module("scripts.jira_daily_sync")
    with patch.object(daily, "_run_embed_delta") as e, \
         patch.object(daily, "_run_links_delta") as l, \
         patch.object(daily, "_run_incremental") as i, \
         patch.object(daily, "_run_classify_delta") as c:
        i.return_value = 0; c.return_value = 0
        daily.run()
    e.assert_not_called(); l.assert_not_called()

def test_daily_sync_runs_v2_steps_when_flag_on(monkeypatch):
    monkeypatch.setenv("CONWO_RETRIEVAL_V2", "shadow")
    daily = importlib.import_module("scripts.jira_daily_sync")
    with patch.object(daily, "_run_embed_delta") as e, \
         patch.object(daily, "_run_links_delta") as l, \
         patch.object(daily, "_run_incremental") as i, \
         patch.object(daily, "_run_classify_delta") as c:
        i.return_value = 0; c.return_value = 0; e.return_value = 0; l.return_value = 0
        daily.run()
    e.assert_called_once(); l.assert_called_once()
