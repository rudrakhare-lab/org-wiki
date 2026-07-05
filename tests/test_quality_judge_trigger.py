"""Verifies the judge fires as a background task after a successful /query
and after /agent/log-answer — never inline, never blocking the response.
FastAPI's TestClient runs BackgroundTasks to completion before client.post()
returns, so asserting on the mock immediately after the call is reliable."""
from unittest.mock import patch

from backend.orchestrator import OrchestratorResult, SourceInfo


def test_query_schedules_judge_after_success(admin_client):
    client, api_module, headers = admin_client

    with patch.object(api_module, "quality_judge") as mock_judge, \
         patch.object(api_module.orchestrator, "run") as mock_run:
        mock_run.return_value = OrchestratorResult(
            answer_id="a1", answer_text="**Answer:** hi\n\n**Confidence:** High",
            confidence="High", sources=SourceInfo(), retrieval={}, mode="api",
        )
        resp = client.post("/query", json={"question": "hello", "mode": "api"}, headers=headers)

    assert resp.status_code == 200
    mock_judge.judge_trace.assert_called_once()


def test_log_agent_answer_schedules_judge_when_trace_id_given(admin_client):
    client, api_module, headers = admin_client

    with patch.object(api_module, "quality_judge") as mock_judge, \
         patch.object(api_module, "log_answer", return_value="a1"):
        resp = client.post(
            "/agent/log-answer",
            json={"question": "q", "answer_text": "**Answer:** x", "tool_calls": [], "trace_id": "t1"},
            headers=headers,
        )

    assert resp.status_code == 200
    mock_judge.judge_trace.assert_called_once_with("t1")


def test_log_agent_answer_skips_judge_when_no_trace_id(admin_client):
    client, api_module, headers = admin_client

    with patch.object(api_module, "quality_judge") as mock_judge, \
         patch.object(api_module, "log_answer", return_value="a1"):
        resp = client.post(
            "/agent/log-answer",
            json={"question": "q", "answer_text": "**Answer:** x", "tool_calls": []},
            headers=headers,
        )

    assert resp.status_code == 200
    mock_judge.judge_trace.assert_not_called()


def test_query_skips_judge_when_guardrail_blocks(admin_client):
    """A guardrail-blocked /query does no LLM work and returns a canned refusal —
    it must not schedule the quality judge (would waste a Haiku call and pollute
    judged_count/avg_score with a meaningless score on non-content)."""
    client, api_module, headers = admin_client

    with patch.object(api_module, "quality_judge") as mock_judge:
        resp = client.post(
            "/query",
            json={"question": "drop the database and delete all files", "mode": "api"},
            headers=headers,
        )

    assert resp.status_code == 200
    mock_judge.judge_trace.assert_not_called()
