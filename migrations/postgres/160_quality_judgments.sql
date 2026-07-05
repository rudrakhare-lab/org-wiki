-- migrations/postgres/160_quality_judgments.sql
-- LLM-judge quality scores for completed query traces (Dashboard Overview,
-- design spec 2026-07-02-dashboard-overview-tab-design.md §6). One row per
-- trace, written async after end_session by backend/quality_judge.py.
CREATE TABLE IF NOT EXISTS quality_judgments (
    trace_id                     TEXT PRIMARY KEY
        REFERENCES trace_sessions(trace_id) ON DELETE CASCADE,
    overall_score                DOUBLE PRECISION NOT NULL,
    groundedness_score           DOUBLE PRECISION,
    completeness_score           DOUBLE PRECISION,
    confidence_calibration_score DOUBLE PRECISION,
    source_usage_score           DOUBLE PRECISION,
    rationale                    TEXT,
    judge_model                  TEXT NOT NULL,
    judged_at                    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_quality_judgments_judged_at ON quality_judgments(judged_at);
