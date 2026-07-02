"""shadow.log emits bucket_counts via Python logger (no schema change in Phase 1)."""
from unittest.mock import MagicMock, patch
from dataclasses import dataclass


@dataclass
class _FakeResult:
    tickets: list
    confidence: str = "Medium"
    diagnostics: dict = None


def test_shadow_log_emits_bucket_counts_via_logger(caplog):
    import logging
    from backend.retrieval.v2 import shadow

    result = _FakeResult(
        tickets=[{"key": "TS-1", "reranker_score": 0.8}],
        diagnostics={"bucket_counts": {"latest": 1, "historical": 0, "stale_open": 0}},
    )

    with patch("backend.retrieval.v2.shadow.db") as mock_db:
        # Make the SQL insert into a no-op (we only care about the logger call).
        mock_db.connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = MagicMock()
        with caplog.at_level(logging.INFO, logger="backend.retrieval.v2.shadow"):
            shadow.log(trace_id="t1", question="q",
                       v1_keys=["TS-9"], v2_result=result,
                       v2_latency_ms=100, served_v2=False)

    log_text = " ".join(r.getMessage() for r in caplog.records)
    assert "bucket_counts" in log_text
    assert "'latest': 1" in log_text or '"latest": 1' in log_text


def test_shadow_log_no_bucket_counts_when_diagnostics_missing(caplog):
    """Gracefully handle results with no diagnostics (defensive)."""
    import logging
    from backend.retrieval.v2 import shadow

    result = _FakeResult(tickets=[], diagnostics=None)

    with patch("backend.retrieval.v2.shadow.db") as mock_db:
        mock_db.connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = MagicMock()
        with caplog.at_level(logging.INFO, logger="backend.retrieval.v2.shadow"):
            shadow.log(trace_id="t1", question="q",
                       v1_keys=[], v2_result=result,
                       v2_latency_ms=0, served_v2=False)

    # Should not raise, and should not include the string 'bucket_counts'.
    log_text = " ".join(r.getMessage() for r in caplog.records)
    assert "bucket_counts" not in log_text
