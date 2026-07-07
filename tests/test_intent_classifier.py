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


# ── UPPER_SNAKE_CASE config names ──────────────────────────────────────────────

def test_upper_snake_what_does_is_configuration():
    # "MEETING_ROOM_ENABLED" is UPPER_SNAKE_CASE — must route to CONFIGURATION not DEFINITION
    r = classify_intent("What does MEETING_ROOM_ENABLED do?")
    assert r.intent == QueryIntent.CONFIGURATION
    assert r.confidence >= 0.85


def test_upper_snake_what_is_is_configuration():
    r = classify_intent("What does MEETING_ROOM_ENABLED do and at what level can it be set?")
    assert r.intent == QueryIntent.CONFIGURATION


def test_upper_snake_alone_is_configuration():
    r = classify_intent("VISITOR_DIGIPASS")
    assert r.intent == QueryIntent.CONFIGURATION


def test_upper_snake_with_config_noun_is_configuration():
    r = classify_intent("RELEASE_MEETING_ROOM config meaning")
    assert r.intent == QueryIntent.CONFIGURATION


# ── COMPARISON tie-breaking over DEFINITION ─────────────────────────────────────

def test_what_is_difference_between_is_comparison():
    # "what is" (DEFINITION=2.0) + "difference between" (COMPARISON=3.0) → COMPARISON wins
    r = classify_intent("What is the difference between visitor configs on .in vs .com servers?")
    assert r.intent == QueryIntent.COMPARISON


def test_what_is_difference_between_simple_is_comparison():
    r = classify_intent("what is the difference between .in and .com?")
    assert r.intent == QueryIntent.COMPARISON


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


# ── Deterministic tie-break (_break_tie / _TIE_PRIORITY) ────────────────────────
#
# NOTE: the task brief's suggested test for this
# (`test_score_tie_breaks_by_fixed_priority`) asserted against a
# `ic._last_tied_intents` module attribute that doesn't exist anywhere in the
# interface contract, wrapped in a conditional that would vacuously pass when
# absent. Replaced with (a) a same-input-repeatability check, which is real but
# weak (classify_intent is already pure/deterministic without any tie-break),
# and (b) a direct unit test of the tie-break rule against a synthetic tied
# scores dict — the only way to *actually* exercise "which intent wins a tie"
# deterministically, since crafting a real question that ties two intents'
# scores exactly is brittle and would break silently if regex weights change.

def test_classify_intent_is_repeatable_for_same_question():
    r1 = classify_intent("how does desk booking work end to end")
    r2 = classify_intent("how does desk booking work end to end")
    assert r1.intent == r2.intent
    assert r1.confidence == r2.confidence


def test_tie_priority_list_matches_spec_order():
    from backend import intent_classifier as ic
    assert ic._TIE_PRIORITY == [
        ic.QueryIntent.CONFIGURATION, ic.QueryIntent.DEBUGGING, ic.QueryIntent.HOW_TO,
        ic.QueryIntent.DEFINITION, ic.QueryIntent.COMPARISON, ic.QueryIntent.ARCHITECTURAL,
        ic.QueryIntent.STATUS, ic.QueryIntent.GENERAL,
    ]


def test_break_tie_picks_highest_priority_among_tied():
    from backend import intent_classifier as ic
    # DEFINITION and HOW_TO tied — priority list says HOW_TO wins.
    tied = [ic.QueryIntent.DEFINITION, ic.QueryIntent.HOW_TO]
    assert ic._break_tie(tied) == ic.QueryIntent.HOW_TO


def test_break_tie_order_independent():
    from backend import intent_classifier as ic
    # Same tied set, reversed input order — must still pick the same winner.
    tied = [ic.QueryIntent.HOW_TO, ic.QueryIntent.DEFINITION]
    assert ic._break_tie(tied) == ic.QueryIntent.HOW_TO


def test_break_tie_single_intent_returns_itself():
    from backend import intent_classifier as ic
    assert ic._break_tie([ic.QueryIntent.STATUS]) == ic.QueryIntent.STATUS


def test_break_tie_configuration_beats_all():
    from backend import intent_classifier as ic
    tied = [ic.QueryIntent.GENERAL, ic.QueryIntent.CONFIGURATION, ic.QueryIntent.ARCHITECTURAL]
    assert ic._break_tie(tied) == ic.QueryIntent.CONFIGURATION


# ── combine_intent — LLM second opinion ──────────────────────────────────────────

def test_combine_llm_wins_on_low_confidence_disagreement():
    from backend import intent_classifier as ic
    regex = ic.IntentResult(intent=ic.QueryIntent.GENERAL, rewritten_query="q",
                             confidence=0.5, retrieval_hints={})
    out = ic.combine_intent(regex, "CONFIGURATION")
    assert out.intent == ic.QueryIntent.CONFIGURATION
    assert out.rewritten_query == "q"  # rewrite text carried forward, intent-independent


def test_combine_regex_wins_when_confident():
    from backend import intent_classifier as ic
    regex = ic.IntentResult(intent=ic.QueryIntent.DEBUGGING, rewritten_query="q",
                             confidence=0.95, retrieval_hints={})
    out = ic.combine_intent(regex, "HOW_TO")
    assert out.intent == ic.QueryIntent.DEBUGGING
    assert out is regex  # unchanged verdict returns the same object


def test_combine_regex_wins_when_intents_agree():
    from backend import intent_classifier as ic
    regex = ic.IntentResult(intent=ic.QueryIntent.CONFIGURATION, rewritten_query="q",
                             confidence=0.5, retrieval_hints={})
    out = ic.combine_intent(regex, "CONFIGURATION")
    assert out.intent == ic.QueryIntent.CONFIGURATION
    assert out is regex


def test_combine_regex_wins_when_no_llm_intent():
    from backend import intent_classifier as ic
    regex = ic.IntentResult(intent=ic.QueryIntent.STATUS, rewritten_query="q",
                             confidence=0.5, retrieval_hints={})
    out = ic.combine_intent(regex, None)
    assert out.intent == ic.QueryIntent.STATUS
    assert out is regex


def test_combine_invalid_llm_intent_ignored():
    from backend import intent_classifier as ic
    regex = ic.IntentResult(intent=ic.QueryIntent.STATUS, rewritten_query="q",
                             confidence=0.6, retrieval_hints={})
    out = ic.combine_intent(regex, "BANANA")
    assert out.intent == ic.QueryIntent.STATUS
    assert out is regex


def test_combine_both_weak_falls_back_to_general():
    from backend import intent_classifier as ic
    # regex confidence < 0.65 (weak) and LLM says GENERAL → GENERAL.
    # Here regex itself is already GENERAL, so this also validates the
    # no-op path when both verdicts already agree on GENERAL.
    regex = ic.IntentResult(intent=ic.QueryIntent.GENERAL, rewritten_query="q",
                             confidence=0.4, retrieval_hints={})
    out = ic.combine_intent(regex, "GENERAL")
    assert out.intent == ic.QueryIntent.GENERAL


def test_combine_weak_regex_disagreement_llm_wins_not_general():
    from backend import intent_classifier as ic
    # regex weak (< 0.65) and disagrees with a *non*-GENERAL LLM verdict —
    # rule (2): LLM wins because regex confidence < 0.75 threshold.
    regex = ic.IntentResult(intent=ic.QueryIntent.GENERAL, rewritten_query="q",
                             confidence=0.4, retrieval_hints={})
    out = ic.combine_intent(regex, "DEBUGGING")
    assert out.intent == ic.QueryIntent.DEBUGGING


def test_combine_result_retrieval_hints_match_winner():
    from backend import intent_classifier as ic
    regex = ic.IntentResult(intent=ic.QueryIntent.GENERAL, rewritten_query="q",
                             confidence=0.5, retrieval_hints={})
    out = ic.combine_intent(regex, "CONFIGURATION")
    assert out.retrieval_hints == ic._HINTS[ic.QueryIntent.CONFIGURATION]
