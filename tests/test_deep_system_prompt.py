"""Structural assertions on the assembled deep-search system prompt."""
from backend.deep_system_prompt import load_deep_system_prompt
from backend import agent_registry


def _conwo():
    return agent_registry.get("conwo")


def test_jira_pms_agent_has_exactly_one_answer_format_and_calibration():
    prompt = load_deep_system_prompt(_conwo())
    assert prompt.count("## Required answer format") == 1, "duplicate answer-format block"
    assert prompt.count("**Confidence calibration:**") == 1, "duplicate confidence calibration"


def test_all_agents_get_universal_hard_rules():
    prompt = load_deep_system_prompt(_conwo())
    assert "## Hard rules" in prompt
    assert "Never invent property names" in prompt
