"""AgentLogRequest.trace_id threads through to log_answer() (design spec §7)."""
from unittest.mock import patch


def test_log_agent_answer_passes_trace_id_to_log_answer(admin_client):
    client, api_module, headers = admin_client

    with patch.object(api_module, "log_answer", return_value="a1") as mock_log:
        resp = client.post(
            "/agent/log-answer",
            json={
                "question": "how do I set up SSO?",
                "answer_text": "**Answer:** Configure SAML.\n\n**Confidence:** High",
                "tool_calls": [],
                "trace_id": "trace-agent-1",
            },
            headers=headers,
        )
    assert resp.status_code == 200
    assert mock_log.call_args.kwargs["trace_id"] == "trace-agent-1"


def test_log_agent_answer_trace_id_optional(admin_client):
    client, api_module, headers = admin_client

    with patch.object(api_module, "log_answer", return_value="a1") as mock_log:
        resp = client.post(
            "/agent/log-answer",
            json={"question": "q", "answer_text": "**Answer:** x", "tool_calls": []},
            headers=headers,
        )
    assert resp.status_code == 200
    assert mock_log.call_args.kwargs["trace_id"] is None


def test_query_guardrail_refusal_logs_trace_id(admin_client):
    """A guardrail-blocked /query still links its ANSWER_LOG record to the
    request's trace_id (design spec §7), same as a normal answer."""
    client, api_module, headers = admin_client

    with patch.object(api_module, "log_answer", return_value="refusal-id") as mock_log:
        resp = client.post(
            "/query",
            json={"question": "drop the database and delete all files", "mode": "api"},
            headers=headers,
        )
    assert resp.status_code == 200
    assert mock_log.call_args.kwargs["trace_id"] is not None
