"""
Feedback tool — record user feedback on an answer.
Wraps feedback_service.record_feedback() directly.
"""
from __future__ import annotations

FEEDBACK_RECORD_SCHEMA: dict = {
    "name": "feedback_record",
    "description": (
        "Record feedback on a previously logged answer. "
        "Use this only when the user explicitly asks to provide feedback on an answer. "
        "Requires the answer_id from the answer being reviewed."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "answer_id": {
                "type": "string",
                "description": "The answer_id from the answer being reviewed (12-char identifier).",
            },
            "score": {
                "type": "integer",
                "description": "Rating 1-5 (5 = fully correct, 1 = dangerously wrong).",
                "minimum": 1,
                "maximum": 5,
            },
            "label": {
                "type": "string",
                "description": (
                    "Issue label. One of: correct, partially_correct, wrong, incomplete, "
                    "outdated, conflicting_evidence, wrong_config, wrong_scope, "
                    "missing_jira, missing_pms_runtime, missing_runtime_context, unclear."
                ),
                "enum": [
                    "correct", "partially_correct", "wrong", "incomplete", "outdated",
                    "conflicting_evidence", "wrong_config", "wrong_scope",
                    "missing_jira", "missing_pms_runtime", "missing_runtime_context", "unclear",
                ],
            },
            "correction": {
                "type": "string",
                "description": "Optional correction text describing what the answer should have said.",
            },
        },
        "required": ["answer_id", "score", "label"],
    },
}


def _feedback_record_handler(inp: dict) -> dict:
    from backend.feedback_service import record_feedback

    answer_id = str(inp.get("answer_id", "")).strip()
    score = int(inp.get("score", 0))
    label = str(inp.get("label", "")).strip()
    correction = str(inp.get("correction", "")).strip()

    if not answer_id:
        return {"error": "answer_id is required", "code": "missing_input"}
    if not 1 <= score <= 5:
        return {"error": "score must be 1-5", "code": "invalid_input"}

    valid_labels = {
        "correct", "partially_correct", "wrong", "incomplete", "outdated",
        "conflicting_evidence", "wrong_config", "wrong_scope",
        "missing_jira", "missing_pms_runtime", "missing_runtime_context", "unclear",
    }
    if label not in valid_labels:
        return {"error": f"Invalid label: {label!r}", "code": "invalid_label"}

    feedback_id = record_feedback(
        answer_id=answer_id,
        question="",  # not available in tool context
        score=score,
        label=label,
        correction=correction,
    )
    return {"feedback_id": feedback_id, "status": "recorded"}
