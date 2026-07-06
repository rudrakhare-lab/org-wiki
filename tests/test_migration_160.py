"""Verifies the 160_quality_judgments migration created the expected schema."""
from backend import db


def test_quality_judgments_table_exists(clean_db):
    with db.connection() as conn:
        row = conn.execute("SELECT to_regclass('quality_judgments')").fetchone()
    assert row[0] is not None


def test_quality_judgments_columns(clean_db):
    with db.connection() as conn:
        cols = {
            r[0]
            for r in conn.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'quality_judgments'"
            ).fetchall()
        }
    assert cols == {
        "trace_id", "overall_score", "groundedness_score", "completeness_score",
        "confidence_calibration_score", "source_usage_score", "rationale",
        "judge_model", "judged_at",
    }


def test_quality_judgments_fk_cascades_on_session_delete(clean_db):
    from backend import trace_store
    trace_store.start_session("t-mig-160", mode="api")
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO quality_judgments "
            "(trace_id, overall_score, judge_model, judged_at) "
            "VALUES (%s, %s, %s, %s)",
            ("t-mig-160", 80.0, "claude-haiku-4-5-20251001", "2026-07-02T00:00:00Z"),
        )
        conn.execute("DELETE FROM trace_sessions WHERE trace_id = %s", ("t-mig-160",))
        row = conn.execute(
            "SELECT 1 FROM quality_judgments WHERE trace_id = %s", ("t-mig-160",)
        ).fetchone()
    assert row is None
