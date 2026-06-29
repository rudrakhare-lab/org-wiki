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
    """Exercise the wiki-only assembly branch deterministically with a duck-typed
    agent (has_jira == has_pms == False), independent of which agents are registered."""
    import types
    from backend.deep_system_prompt import load_deep_system_prompt
    wiki_only = types.SimpleNamespace(identity="Test agent.", has_jira=False, has_pms=False)
    prompt = load_deep_system_prompt(wiki_only)
    assert prompt.count("## Required answer format") == 1
    assert prompt.count("**Confidence calibration:**") == 1
    assert "## Hard rules" in prompt
    assert "Release-notes history pages" in prompt


def test_jira_pms_prompt_has_ported_accuracy_rules():
    prompt = load_deep_system_prompt(_conwo())
    assert "Corroborate across sources" in prompt          # G1+G2
    assert "Shape the body to the question's intent" in prompt  # G3
    assert "Release-notes history pages" in prompt          # history rule


def test_wiki_only_prompt_has_history_rule():
    # A wiki-only agent (no jira, no pms). Build a minimal stand-in if no such
    # agent is registered: load conwo's assembler path is jira/pms; for wiki-only
    # use any registered agent with has_jira == has_pms == False, else skip.
    from backend.deep_system_prompt import _EVIDENCE_BLOCK_WIKI_ONLY
    assert "Release-notes history pages" in _EVIDENCE_BLOCK_WIKI_ONLY
