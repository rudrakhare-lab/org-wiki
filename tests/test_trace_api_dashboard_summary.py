"""New Overview-tab endpoints (design spec 2026-07-02-dashboard-overview-tab-design.md §8)."""
from backend import db, feedback_service, trace_store


def _seed_session(trace_id, *, agent_id="conwo", conversation_id="c1", status="success",
                   duration_ms=1000, cost=0.01):
    trace_store.start_session(trace_id, mode="api", conversation_id=conversation_id, agent_id=agent_id)
    with db.connection() as conn:
        conn.execute(
            "UPDATE trace_sessions SET status=%s, duration_ms=%s, total_cost_usd=%s "
            "WHERE trace_id=%s",
            (status, duration_ms, cost, trace_id),
        )


def test_dashboard_summary_counts_conversations_and_queries(admin_client, clean_db):
    client, _, headers = admin_client
    _seed_session("t1", conversation_id="c1")
    _seed_session("t2", conversation_id="c1")
    _seed_session("t3", conversation_id="c2")

    resp = client.get("/api/traces/dashboard/summary?time_range=all&agent_id=conwo", headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["conversations"] == 2
    assert body["queries"] == 3
    assert body["msgs_per_conversation"] == 1.5


def test_dashboard_summary_agent_all_aggregates_across_agents(admin_client, clean_db):
    client, _, headers = admin_client
    _seed_session("t1", agent_id="conwo")
    _seed_session("t2", agent_id="infosec")

    resp = client.get("/api/traces/dashboard/summary?time_range=all&agent_id=all", headers=headers)

    assert resp.json()["queries"] == 2


def test_dashboard_summary_quality_score_from_quality_judgments(admin_client, clean_db):
    client, _, headers = admin_client
    _seed_session("t1")
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO quality_judgments (trace_id, overall_score, judge_model, judged_at) "
            "VALUES (%s,%s,%s,%s)",
            ("t1", 88.0, "claude-haiku-4-5-20251001", "2026-07-02T00:00:00Z"),
        )

    resp = client.get("/api/traces/dashboard/summary?time_range=all&agent_id=conwo", headers=headers)

    body = resp.json()
    assert body["quality"]["avg_score"] == 88.0
    assert body["quality"]["judged_count"] == 1


def test_dashboard_summary_escalation_rate_from_negative_feedback(
    admin_client, clean_db, tmp_path, monkeypatch
):
    client, _, headers = admin_client
    answer_log = tmp_path / "answer_log.jsonl"
    feedback_log = tmp_path / "answer_feedback.jsonl"
    monkeypatch.setattr(feedback_service, "ANSWER_LOG", answer_log)
    monkeypatch.setattr(feedback_service, "FEEDBACK_LOG", feedback_log)

    _seed_session("t1")
    _seed_session("t2")
    feedback_service.log_answer(question="q1", answer_text="a1", confidence="Low", trace_id="t1")
    feedback_service.log_answer(question="q2", answer_text="a2", confidence="High", trace_id="t2")
    real_answer_id = feedback_service.find_answer_by_trace_id("t1")["answer_id"]
    feedback_service.record_feedback(answer_id=real_answer_id, question="q1", score=2, label="wrong")

    resp = client.get(
        "/api/traces/dashboard/summary?time_range=all&agent_id=conwo", headers=headers
    )

    body = resp.json()
    assert body["escalation"]["feedback_count"] == 1
    assert body["escalation"]["rate"] == 0.5  # 1 negative / 2 total queries


def test_dashboard_summary_disabled_tracing_returns_zeroed_shape(admin_client, monkeypatch):
    client, _, headers = admin_client
    monkeypatch.setattr(trace_store, "_TRACING_ENABLED", False)

    resp = client.get("/api/traces/dashboard/summary?time_range=all&agent_id=conwo", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["queries"] == 0


def test_dashboard_daily_volume_returns_per_day_counts(admin_client, clean_db):
    client, _, headers = admin_client
    _seed_session("t1", conversation_id="c1")
    _seed_session("t2", conversation_id="c2")

    resp = client.get(
        "/api/traces/dashboard/daily-volume?time_range=all&agent_id=conwo", headers=headers
    )

    assert resp.status_code == 200
    days = resp.json()["days"]
    assert len(days) == 1
    assert days[0]["queries"] == 2
    assert days[0]["conversations"] == 2
