"""Structural assertions on the assembled deep-search system prompt."""
from backend.deep_system_prompt import load_deep_system_prompt
from backend import agent_registry


def _conwo():
    return agent_registry.get("conwo")


def test_jira_pms_agent_has_exactly_one_answer_format_and_calibration():
    prompt = load_deep_system_prompt(_conwo())
    assert prompt.count("## Required answer format") == 1, "duplicate answer-format block"
    assert prompt.count("**Confidence calibration:**") == 1, "duplicate confidence calibration"


def test_jira_pms_agent_gets_hard_rules():
    prompt = load_deep_system_prompt(_conwo())
    assert "## Hard rules" in prompt
    assert "Never invent property names" in prompt


def test_wiki_only_assembly_has_exactly_one_answer_format():
    """The wiki-only path = evidence block (no format) + wiki-only format (one) +
    hard rules. Verifies the de-dup invariant on the branch conwo's path doesn't cover."""
    from backend.deep_system_prompt import (
        _EVIDENCE_BLOCK_WIKI_ONLY,
        _WIKI_ONLY_ANSWER_FORMAT,
        _HARD_RULES_BLOCK,
    )
    # The evidence block must NOT carry an answer format (that lives in the format constant)
    assert _EVIDENCE_BLOCK_WIKI_ONLY.count("## Required answer format") == 0
    # The wiki-only format constant carries exactly one format + one calibration
    assert _WIKI_ONLY_ANSWER_FORMAT.count("## Required answer format") == 1
    assert _WIKI_ONLY_ANSWER_FORMAT.count("**Confidence calibration:**") == 1
    # Hard rules are universal
    assert "## Hard rules" in _HARD_RULES_BLOCK


def test_wiki_only_agent_assembled_prompt_one_of_each():
    import pytest
    from backend import agent_registry
    from backend.deep_system_prompt import load_deep_system_prompt
    accessor = getattr(agent_registry, "all", None)
    agents = accessor() if callable(accessor) else []
    wiki_only = next((a for a in agents if not a.has_jira and not a.has_pms), None)
    if wiki_only is None:
        pytest.skip("no wiki-only agent registered in this environment")
    prompt = load_deep_system_prompt(wiki_only)
    assert prompt.count("## Required answer format") == 1
    assert prompt.count("**Confidence calibration:**") == 1
    assert "## Hard rules" in prompt
