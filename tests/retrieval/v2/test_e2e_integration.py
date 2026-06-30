"""End-to-end integration test. Requires CONWO_TEST_DSN + GOOGLE_GENAI_API_KEY."""
import os
import pytest

pytestmark = pytest.mark.skipif(
    not (os.getenv("CONWO_TEST_DSN") and os.getenv("GOOGLE_GENAI_API_KEY")),
    reason="requires Postgres + Gemini key",
)

def test_e2e_returns_either_tickets_or_abstain():
    os.environ["CONWO_DSN"] = os.environ["CONWO_TEST_DSN"]
    from backend.retrieval.v2.pipeline import search
    r = search("kioskRequireOTP behaviour for new visitors")
    assert r.confidence in {"High","Medium","Low","Abstain"}
    if not r.abstain:
        assert len(r.tickets) >= 1
        assert all("reranker_score" in t for t in r.tickets)
    else:
        assert r.tickets == []
        assert "verify" in r.message.lower() or "couldn't" in r.message.lower()
