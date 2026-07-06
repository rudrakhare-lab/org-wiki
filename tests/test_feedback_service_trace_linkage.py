"""trace_id linkage between ANSWER_LOG records and trace_sessions (design spec
2026-07-02-dashboard-overview-tab-design.md §7) — enables Escalation Rate and
the quality judge to resolve a trace's answer text/sources."""
import json


def test_log_answer_stores_trace_id(tmp_path, monkeypatch):
    from backend import feedback_service
    answer_log = tmp_path / "answer_log.jsonl"
    monkeypatch.setattr(feedback_service, "ANSWER_LOG", answer_log)

    answer_id = feedback_service.log_answer(
        question="q", answer_text="a", confidence="High", trace_id="trace-abc",
    )

    lines = answer_log.read_text().strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["answer_id"] == answer_id
    assert record["trace_id"] == "trace-abc"


def test_log_answer_trace_id_defaults_to_none(tmp_path, monkeypatch):
    from backend import feedback_service
    answer_log = tmp_path / "answer_log.jsonl"
    monkeypatch.setattr(feedback_service, "ANSWER_LOG", answer_log)

    feedback_service.log_answer(question="q", answer_text="a", confidence="High")

    record = json.loads(answer_log.read_text().strip())
    assert record["trace_id"] is None


def test_find_answer_by_trace_id_returns_matching_record(tmp_path, monkeypatch):
    from backend import feedback_service
    answer_log = tmp_path / "answer_log.jsonl"
    monkeypatch.setattr(feedback_service, "ANSWER_LOG", answer_log)
    feedback_service.log_answer(question="q1", answer_text="a1", confidence="Low", trace_id="t1")
    feedback_service.log_answer(question="q2", answer_text="a2", confidence="High", trace_id="t2")

    found = feedback_service.find_answer_by_trace_id("t2")

    assert found is not None
    assert found["question"] == "q2"
    assert found["trace_id"] == "t2"


def test_find_answer_by_trace_id_returns_none_when_missing(tmp_path, monkeypatch):
    from backend import feedback_service
    answer_log = tmp_path / "answer_log.jsonl"
    monkeypatch.setattr(feedback_service, "ANSWER_LOG", answer_log)
    feedback_service.log_answer(question="q1", answer_text="a1", confidence="Low", trace_id="t1")

    assert feedback_service.find_answer_by_trace_id("does-not-exist") is None


def test_load_all_feedback_returns_every_status(tmp_path, monkeypatch):
    from backend import feedback_service
    # Isolate BOTH stores: record_feedback() reads feedback_service.ANSWER_LOG
    # at call time to auto-link the answer_log record — leaving it unpatched
    # would read the real (possibly huge) production file.
    monkeypatch.setattr(feedback_service, "ANSWER_LOG", tmp_path / "answer_log.jsonl")
    monkeypatch.setattr(feedback_service, "FEEDBACK_LOG", tmp_path / "answer_feedback.jsonl")
    feedback_service.record_feedback(
        answer_id="a1", question="q1", score=2, label="wrong",
    )
    feedback_service.record_feedback(
        answer_id="a2", question="q2", score=5, label="correct",
    )

    records = feedback_service.load_all_feedback()

    assert len(records) == 2
    assert {r["answer_id"] for r in records} == {"a1", "a2"}
