from unittest.mock import patch, MagicMock

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
    assert len(pair[1]) <= rerank.MAX_DOC_CHARS

def test_score_handles_empty_candidates():
    from backend.retrieval.v2 import rerank
    assert rerank.score("q", []) == []
