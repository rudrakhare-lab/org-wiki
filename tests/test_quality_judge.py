"""LLM-as-judge scoring pipeline (design spec 2026-07-02-dashboard-overview-tab-design.md §6).
Every external call (Anthropic, wiki_retriever) is mocked — these tests never hit
the network. Postgres reads/writes use the real test DB via the clean_db fixture."""
import json
from unittest.mock import MagicMock, patch

from backend import db, feedback_service, quality_judge, trace_store


def _fake_judge_response(payload: dict):
    return MagicMock(content=[MagicMock(text=json.dumps(payload))])


def test_judge_trace_writes_a_row(clean_db, tmp_path, monkeypatch):
    answer_log = tmp_path / "answer_log.jsonl"
    monkeypatch.setattr(feedback_service, "ANSWER_LOG", answer_log)

    trace_store.start_session("t-judge-1", mode="api")
    feedback_service.log_answer(
        question="How do I set up SSO?",
        answer_text="**Answer:** Configure SAML via Okta.\n\n**Confidence:** High",
        confidence="High",
        wiki_pages=["wiki/modules/sso.md"],
        jira_keys=[],
        trace_id="t-judge-1",
    )
    monkeypatch.setattr(quality_judge.wiki_retriever, "get_page", lambda path: None)

    fake = MagicMock()
    fake.messages.create.return_value = _fake_judge_response({
        "groundedness": 90, "completeness": 85, "confidence_calibration": 80,
        "source_usage": 70, "rationale": "Solid answer, cites the SSO page.",
    })
    with patch.object(quality_judge, "_client", fake):
        quality_judge.judge_trace("t-judge-1")

    with db.connection() as conn:
        row = conn.execute(
            "SELECT * FROM quality_judgments WHERE trace_id = %s", ("t-judge-1",)
        ).fetchone()
    assert row is not None
    assert row["overall_score"] == 81.25  # (90+85+80+70)/4
    assert row["groundedness_score"] == 90
    assert row["judge_model"] == "claude-haiku-4-5-20251001"


def test_judge_trace_is_a_noop_when_no_answer_log_record(clean_db):
    """A trace with no linked ANSWER_LOG record (e.g. it never reached
    log_answer) must not raise and must not write a row."""
    trace_store.start_session("t-judge-2", mode="api")

    quality_judge.judge_trace("t-judge-2")  # must not raise

    with db.connection() as conn:
        row = conn.execute(
            "SELECT * FROM quality_judgments WHERE trace_id = %s", ("t-judge-2",)
        ).fetchone()
    assert row is None


def test_judge_trace_is_fail_open_on_anthropic_error(clean_db, tmp_path, monkeypatch):
    answer_log = tmp_path / "answer_log.jsonl"
    monkeypatch.setattr(feedback_service, "ANSWER_LOG", answer_log)
    trace_store.start_session("t-judge-3", mode="api")
    feedback_service.log_answer(
        question="q", answer_text="a", confidence="Medium", trace_id="t-judge-3",
    )

    fake = MagicMock()
    fake.messages.create.side_effect = RuntimeError("network down")
    with patch.object(quality_judge, "_client", fake):
        quality_judge.judge_trace("t-judge-3")  # must not raise

    with db.connection() as conn:
        row = conn.execute(
            "SELECT * FROM quality_judgments WHERE trace_id = %s", ("t-judge-3",)
        ).fetchone()
    assert row is None


def test_judge_trace_upserts_on_rerun(clean_db, tmp_path, monkeypatch):
    """Re-judging the same trace_id updates the row instead of erroring on the
    PK conflict."""
    answer_log = tmp_path / "answer_log.jsonl"
    monkeypatch.setattr(feedback_service, "ANSWER_LOG", answer_log)
    trace_store.start_session("t-judge-4", mode="api")
    feedback_service.log_answer(
        question="q", answer_text="a", confidence="Medium", trace_id="t-judge-4",
    )
    fake = MagicMock()
    fake.messages.create.return_value = _fake_judge_response({
        "groundedness": 50, "completeness": 50, "confidence_calibration": 50,
        "source_usage": 50, "rationale": "first pass",
    })
    with patch.object(quality_judge, "_client", fake):
        quality_judge.judge_trace("t-judge-4")

    fake.messages.create.return_value = _fake_judge_response({
        "groundedness": 90, "completeness": 90, "confidence_calibration": 90,
        "source_usage": 90, "rationale": "second pass",
    })
    with patch.object(quality_judge, "_client", fake):
        quality_judge.judge_trace("t-judge-4")

    with db.connection() as conn:
        rows = conn.execute(
            "SELECT overall_score FROM quality_judgments WHERE trace_id = %s", ("t-judge-4",)
        ).fetchall()
    assert len(rows) == 1
    assert rows[0]["overall_score"] == 90.0


def test_judge_trace_tolerates_markdown_fenced_json(clean_db, tmp_path, monkeypatch):
    """Haiku occasionally wraps its JSON output in a ```json fence despite the
    'Output JSON only' instruction. judge_trace must still extract and write
    the judgment instead of silently failing closed on json.loads."""
    answer_log = tmp_path / "answer_log.jsonl"
    monkeypatch.setattr(feedback_service, "ANSWER_LOG", answer_log)
    trace_store.start_session("t-judge-5", mode="api")
    feedback_service.log_answer(
        question="q", answer_text="a", confidence="Medium", trace_id="t-judge-5",
    )

    fenced_payload = json.dumps({
        "groundedness": 60, "completeness": 70, "confidence_calibration": 80,
        "source_usage": 90, "rationale": "fenced response",
    })
    fake = MagicMock()
    fake.messages.create.return_value = MagicMock(
        content=[MagicMock(text=f"```json\n{fenced_payload}\n```")]
    )
    with patch.object(quality_judge, "_client", fake):
        quality_judge.judge_trace("t-judge-5")

    with db.connection() as conn:
        row = conn.execute(
            "SELECT * FROM quality_judgments WHERE trace_id = %s", ("t-judge-5",)
        ).fetchone()
    assert row is not None
    assert row["overall_score"] == 75.0  # (60+70+80+90)/4


def test_fetch_cited_context_includes_wiki_and_jira(clean_db, monkeypatch):
    from backend.wiki_retriever import WikiPage
    fake_page = WikiPage(path="modules/sso.md", title="SSO", full_text="SSO uses SAML.")
    monkeypatch.setattr(quality_judge.wiki_retriever, "get_page", lambda path: fake_page)
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO tickets (key, project, created_at, updated_at, fetched_at, "
            "normalized_at, summary, description_text) VALUES "
            "(%s,%s,%s,%s,%s,%s,%s,%s)",
            ("SSO-1", "SSO", "2026-01-01", "2026-01-01", "2026-01-01", "2026-01-01",
             "SSO ticket", "Configure SAML metadata."),
        )

    context = quality_judge._fetch_cited_context(["wiki/modules/sso.md"], ["SSO-1"])

    assert "SSO uses SAML" in context
    assert "Configure SAML metadata" in context
