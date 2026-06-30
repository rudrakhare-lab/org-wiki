from unittest.mock import patch, MagicMock
import os, pytest

@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in ["CONWO_RETRIEVAL_V2","CONWO_RETRIEVAL_V2_PCT"]:
        monkeypatch.delenv(k, raising=False)

def test_default_off_serves_v1(monkeypatch):
    from backend import jira_retriever
    v1 = MagicMock(return_value="v1-result")
    v2 = MagicMock(return_value="v2-result")
    monkeypatch.setattr(jira_retriever, "_v1_search", v1)
    monkeypatch.setattr(jira_retriever, "_v2_search", v2)
    out = jira_retriever.search("q")
    assert out == "v1-result"
    v2.assert_not_called()

def test_shadow_runs_both_serves_v1(monkeypatch):
    monkeypatch.setenv("CONWO_RETRIEVAL_V2", "shadow")
    from backend import jira_retriever
    v1 = MagicMock(return_value="v1-result")
    v2 = MagicMock(return_value="v2-result")
    log = MagicMock()
    monkeypatch.setattr(jira_retriever, "_v1_search", v1)
    monkeypatch.setattr(jira_retriever, "_v2_search", v2)
    monkeypatch.setattr(jira_retriever, "_shadow_log", log)
    out = jira_retriever.search("q")
    assert out == "v1-result"
    v2.assert_called_once()
    log.assert_called_once()

def test_on_serves_v2(monkeypatch):
    monkeypatch.setenv("CONWO_RETRIEVAL_V2", "on")
    from backend import jira_retriever
    v1 = MagicMock(); v2 = MagicMock(return_value="v2-result")
    monkeypatch.setattr(jira_retriever, "_v1_search", v1)
    monkeypatch.setattr(jira_retriever, "_v2_search", v2)
    assert jira_retriever.search("q") == "v2-result"
    v1.assert_not_called()
