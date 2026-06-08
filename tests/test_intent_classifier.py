"""
Tests for backend.intent_classifier.
All tests are pure — no DB, no HTTP, no subprocess.
Run: venv/bin/pytest tests/test_intent_classifier.py -v
"""
import pytest
from backend.intent_classifier import classify_intent, QueryIntent, IntentResult


# ── CONFIGURATION ──────────────────────────────────────────────────────────────

def test_camelcase_what_is_is_configuration():
    r = classify_intent("what is kioskRequireOTPBeforeRegister")
    assert r.intent == QueryIntent.CONFIGURATION
    assert r.confidence >= 0.85


def test_how_to_configure_is_configuration():
    r = classify_intent("how to configure visitor OTP")
    assert r.intent == QueryIntent.CONFIGURATION
    assert r.retrieval_hints["boost_config_pages"] is True


def test_camelcase_config_noun_is_configuration():
    r = classify_intent("showEmployeeOfficePlan config")
    assert r.intent == QueryIntent.CONFIGURATION
    assert r.confidence >= 0.80


# ── DEBUGGING ──────────────────────────────────────────────────────────────────

def test_not_working_is_debugging():
    r = classify_intent("OTP not working for visitors")
    assert r.intent == QueryIntent.DEBUGGING
    assert r.retrieval_hints["jira_latest_limit"] >= 4


def test_broken_beats_status_in_debugging():
    r = classify_intent("visitor check-in broken after latest update")
    assert r.intent == QueryIntent.DEBUGGING


def test_error_with_simple_camel_is_debugging_not_config():
    r = classify_intent("kioskMode error on floor kiosk")
    assert r.intent == QueryIntent.DEBUGGING


# ── DEFINITION ─────────────────────────────────────────────────────────────────

def test_what_is_plain_term_is_definition():
    r = classify_intent("what is SSO")
    assert r.intent == QueryIntent.DEFINITION
    assert r.rewritten_query == "what is SSO"


def test_define_keyword_is_definition():
    r = classify_intent("define meal management")
    assert r.intent == QueryIntent.DEFINITION


# ── HOW_TO ─────────────────────────────────────────────────────────────────────

def test_how_do_i_enable_is_how_to():
    r = classify_intent("how do I enable desk booking")
    assert r.intent == QueryIntent.HOW_TO


def test_steps_to_is_how_to():
    r = classify_intent("steps to set up parking management")
    assert r.intent == QueryIntent.HOW_TO


# ── COMPARISON ─────────────────────────────────────────────────────────────────

def test_difference_between_is_comparison():
    r = classify_intent("difference between .in and .com server")
    assert r.intent == QueryIntent.COMPARISON
    assert r.retrieval_hints["wiki_top_n"] >= 5


def test_vs_is_comparison():
    r = classify_intent("visitor vs meeting rooms")
    assert r.intent == QueryIntent.COMPARISON


# ── ARCHITECTURAL ──────────────────────────────────────────────────────────────

def test_how_does_flow_work_is_architectural():
    r = classify_intent("how does the SSO auth flow work")
    assert r.intent == QueryIntent.ARCHITECTURAL


def test_architecture_keyword_is_architectural():
    r = classify_intent("architecture of the booking rule engine")
    assert r.intent == QueryIntent.ARCHITECTURAL
    assert r.retrieval_hints["wiki_top_n"] >= 4


# ── STATUS ─────────────────────────────────────────────────────────────────────

def test_status_of_is_status():
    r = classify_intent("status of visitor rollout")
    assert r.intent == QueryIntent.STATUS
    assert r.retrieval_hints["jira_latest_limit"] >= 4


def test_latest_update_with_jira_key_is_status():
    r = classify_intent("latest update on PB-12345")
    assert r.intent == QueryIntent.STATUS


# ── GENERAL ────────────────────────────────────────────────────────────────────

def test_vague_query_is_general_low_confidence():
    r = classify_intent("tell me about WorkInSync")
    assert r.intent == QueryIntent.GENERAL
    assert r.confidence < 0.65


def test_single_word_is_general_query_unchanged():
    r = classify_intent("help")
    assert r.intent == QueryIntent.GENERAL
    assert r.rewritten_query == "help"


# ── BEHAVIORAL / CROSS-CUTTING ─────────────────────────────────────────────────

def test_complex_camelcase_alone_is_high_confidence_configuration():
    r = classify_intent("kioskRequireOTPBeforeRegister")
    assert r.intent == QueryIntent.CONFIGURATION
    assert r.confidence >= 0.85


def test_debugging_hints_have_high_jira_limit():
    r = classify_intent("something is broken")
    assert r.intent == QueryIntent.DEBUGGING
    assert r.retrieval_hints["jira_latest_limit"] >= 4


def test_long_query_rewritten_query_preserved():
    q = "how does the booking rule engine prioritize desk reservations for employees"
    r = classify_intent(q)
    assert r.rewritten_query == q


def test_intent_result_is_dataclass_with_all_fields():
    r = classify_intent("what is SSO")
    assert isinstance(r, IntentResult)
    assert isinstance(r.intent, QueryIntent)
    assert isinstance(r.rewritten_query, str)
    assert 0.0 <= r.confidence <= 1.0
    assert "wiki_top_n" in r.retrieval_hints
    assert "jira_latest_limit" in r.retrieval_hints
    assert "boost_config_pages" in r.retrieval_hints
