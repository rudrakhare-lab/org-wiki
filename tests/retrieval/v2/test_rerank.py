import decimal
import re
from unittest.mock import patch, MagicMock

from backend.retrieval.v2 import rerank

def test_score_returns_pairs_sorted_descending():
    from backend.retrieval.v2 import rerank
    cands = [
        {"key": "TS-1", "summary": "Login", "description_text": "x"},
        {"key": "TS-2", "summary": "Meal",  "description_text": "y"},
        {"key": "TS-3", "summary": "Auth",  "description_text": "z"},
    ]
    fake = MagicMock()
    fake.predict.return_value = [0.2, 0.9, 0.5]
    with patch.object(rerank, "_model", fake):
        out = rerank.score("login fails", cands)
    assert [c["key"] for c, _ in out] == ["TS-2", "TS-3", "TS-1"]

def test_score_truncates_long_text_for_speed():
    from backend.retrieval.v2 import rerank
    cands = [{"key": "TS-1", "summary": "x", "description_text": "y" * 100000}]
    fake = MagicMock()
    fake.predict.return_value = [0.5]
    with patch.object(rerank, "_model", fake):
        rerank.score("q", cands)
    pair = fake.predict.call_args[0][0][0]
    # Budget changed from a single global MAX_DOC_CHARS to fixed per-field
    # budgets (see rerank._SUMMARY_MAX / _DESC_MAX / _COMMENTS_MAX). This
    # candidate has no comments, so worst case is summary + "\n" + desc.
    max_len = rerank._SUMMARY_MAX + rerank._DESC_MAX + rerank._COMMENTS_MAX + len("[comments] ") + 2
    assert len(pair[1]) <= max_len

def test_score_handles_empty_candidates():
    from backend.retrieval.v2 import rerank
    assert rerank.score("q", []) == []


def test_doc_text_truncates_summary_to_200(monkeypatch):
    # Legacy fixed-budget layout only applies with smart-window off.
    monkeypatch.setenv("CONWO_RERANK_SMART_WINDOW", "off")
    from backend.retrieval.v2.rerank import _doc_text
    long_summary = "s" * 500
    out = _doc_text({"summary": long_summary, "description_text": "", "comments_text": ""}, "q")
    assert out == "s" * 200


def test_doc_text_truncates_description_to_500(monkeypatch):
    # Legacy fixed-budget layout only applies with smart-window off.
    monkeypatch.setenv("CONWO_RERANK_SMART_WINDOW", "off")
    from backend.retrieval.v2.rerank import _doc_text
    long_desc = "d" * 1200
    out = _doc_text({"summary": "sum", "description_text": long_desc, "comments_text": ""}, "q")
    # summary + "\n" + first 500 chars of desc
    assert out == "sum\n" + ("d" * 500)


def test_doc_text_truncates_comments_to_300_with_prefix():
    from backend.retrieval.v2.rerank import _doc_text
    long_comments = "c" * 1000
    out = _doc_text({"summary": "sum", "description_text": "", "comments_text": long_comments}, "q")
    assert "[comments] " in out


def test_doc_text_omits_comments_prefix_when_empty():
    from backend.retrieval.v2.rerank import _doc_text
    out = _doc_text({"summary": "sum", "description_text": "desc", "comments_text": ""}, "q")
    assert "[comments]" not in out
    assert out == "sum\ndesc"


def test_doc_text_full_layout_all_three_fields():
    from backend.retrieval.v2.rerank import _doc_text
    out = _doc_text({
        "summary": "s" * 200,
        "description_text": "d" * 500,
        "comments_text": "c" * 300,
    }, "q")
    assert ("s" * 200) in out
    assert ("d" * 500) in out
    assert "[comments] " in out


def test_doc_text_handles_none_fields_defensively():
    from backend.retrieval.v2.rerank import _doc_text
    out = _doc_text({"summary": None, "description_text": None, "comments_text": None}, "q")
    assert out == ""


def test_doc_text_handles_minimal_column_row_from_links_py():
    """links.py's _TICKETS_BY_KEY_SQL selects only:
    key, summary, description_text, comments_text, status_category, priority,
    updated_at, resolved_at, functional_area, links_json, comment_count.
    No tsvector/embedding fields. _doc_text must never KeyError on this shape,
    which is exactly what one-hop-expansion / supersession candidates look like
    when they reach the reranker."""
    from backend.retrieval.v2.rerank import _doc_text
    minimal_row = {
        "key": "TS-100",
        "summary": "Visitor OTP not sent",
        "description_text": "OTP fails to send on kiosk registration.",
        "comments_text": "Confirmed reproduced on office 42.",
        "status_category": "done",
        "priority": "P1",
        "updated_at": "2026-06-01T10:00:00",
        "resolved_at": "2026-06-02T09:00:00",
        "functional_area": "WF-wis-meeting-vms",
        "links_json": "[]",
        "comment_count": 3,
    }
    out = _doc_text(minimal_row, "visitor otp")
    assert isinstance(out, str)
    assert "Visitor OTP not sent" in out
    assert "[comments] Confirmed reproduced on office 42." in out


def test_score_handles_prod_realistic_types_without_crashing():
    """Prod SQL boundary: updated_at/resolved_at are TEXT columns (ISO strings,
    not datetime objects) and fused_score arrives as decimal.Decimal from
    Postgres numeric aggregation. _doc_text/score must not crash when a
    candidate carries these prod-realistic extra fields alongside the fields
    it actually reads (summary/description_text/comments_text)."""
    from backend.retrieval.v2 import rerank
    cands = [{
        "key": "TS-200",
        "summary": "Meal cutoff wrong",
        "description_text": "Cutoff time off by one hour for evening shift.",
        "comments_text": "Reproduced; root cause is timezone offset.",
        "status_category": "done",
        "priority": "P2",
        "updated_at": "2026-05-20T14:30:00",
        "resolved_at": "2026-05-21T08:00:00",
        "functional_area": "WF-empexp",
        "links_json": "[]",
        "comment_count": 2,
        "fused_score": decimal.Decimal("0.8734"),
    }]
    fake = MagicMock()
    fake.predict.return_value = [0.5]
    with patch.object(rerank, "_model", fake):
        out = rerank.score("meal cutoff", cands)
    assert out[0][0]["key"] == "TS-200"
    assert isinstance(out[0][1], float)


def test_score_returns_probabilities_not_logits(monkeypatch):
    """ms-marco MiniLM predict() returns raw logits (≈ -11..+11). score()
    must sigmoid them into [0,1] so gate thresholds (0.5/0.7) mean what
    they say. Regression for audit Critical #1."""
    from backend.retrieval.v2 import rerank

    class FakeModel:
        def predict(self, pairs):
            return [7.3, -4.1, 0.0]  # raw logits

    monkeypatch.setattr(rerank, "_model", FakeModel())
    cands = [{"summary": f"c{i}", "description_text": "", "comments_text": ""}
             for i in range(3)]
    out = rerank.score("q", cands)
    scores = sorted((s for _, s in out), reverse=True)
    assert all(0.0 <= s <= 1.0 for s in scores)
    assert scores[0] > 0.99      # sigmoid(7.3)
    assert 0.49 < scores[1] < 0.51  # sigmoid(0.0)
    assert scores[2] < 0.02      # sigmoid(-4.1)


def test_score_ordering_preserved_after_sigmoid(monkeypatch):
    from backend.retrieval.v2 import rerank

    class FakeModel:
        def predict(self, pairs):
            return [2.0, 5.0, -1.0]

    monkeypatch.setattr(rerank, "_model", FakeModel())
    cands = [{"summary": s, "description_text": "", "comments_text": ""}
             for s in ("a", "b", "c")]
    out = rerank.score("q", cands)
    assert [c["summary"] for c, _ in out] == ["b", "a", "c"]


def test_smart_window_selects_query_relevant_comment(monkeypatch):
    monkeypatch.delenv("CONWO_RERANK_SMART_WINDOW", raising=False)
    # The relevant line is buried well past the first 300 chars of comments.
    filler = "unrelated chatter about lunch. " * 20            # ~600 chars
    comment = filler + "The kioskRequireOTPBeforeRegister flag controls guard OTP."
    c = {"summary": "Guard app", "description_text": "desc", "comments_text": comment}
    out = rerank._doc_text(c, "how does guard OTP registration work")
    assert "kioskRequireOTPBeforeRegister" in out              # buried relevant line surfaced


def test_smart_window_off_falls_back_to_head(monkeypatch):
    monkeypatch.setenv("CONWO_RERANK_SMART_WINDOW", "off")
    c = {"summary": "s", "description_text": "d", "comments_text": "x" * 5000}
    out = rerank._doc_text(c, "anything")
    assert len(out) <= 1013                                    # legacy fixed-budget layout


def test_max_len_default_is_512(monkeypatch):
    monkeypatch.delenv("CONWO_RERANK_MAX_LEN", raising=False)
    assert rerank._max_len() == 512
