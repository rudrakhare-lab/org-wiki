from pathlib import Path
from backend import agent_registry


def test_loads_both_agents():
    ids = {a.id for a in agent_registry.all()}
    assert {"conwo", "infosec"} <= ids


def test_conwo_spec_fields():
    conwo = agent_registry.get("conwo")
    assert conwo.display_name == "Conwo"
    assert conwo.has_jira is True and conwo.has_pms is True
    assert conwo.tool_allowed("jira_search_ranked") is True   # "*" allows all
    assert conwo.wiki_dir.name == "wiki"
    assert conwo.claude_md.name == "CLAUDE.md"


def test_infosec_is_wiki_only():
    info = agent_registry.get("infosec")
    assert info.has_jira is False and info.has_pms is False
    assert info.modes == ("api",)
    assert info.tool_allowed("wiki_search") is True
    assert info.tool_allowed("jira_search_ranked") is False
    assert info.tool_allowed("pms_runtime_values") is False
    assert info.wiki_dir.parts[-3:] == ("agents", "infosec", "wiki")


def test_unknown_agent_falls_back_to_conwo():
    assert agent_registry.get("does-not-exist").id == "conwo"
    assert agent_registry.get(None).id == "conwo"
    assert agent_registry.default().id == "conwo"


def test_mode_allowed():
    conwo = agent_registry.get("conwo")
    info = agent_registry.get("infosec")
    assert conwo.mode_allowed("api") is True
    assert conwo.mode_allowed("agent") is True
    assert info.mode_allowed("api") is True
    assert info.mode_allowed("agent") is False


def test_invalidate_cache_resets_load():
    first = agent_registry.get("conwo")
    agent_registry.invalidate_cache()
    second = agent_registry.get("conwo")
    # Fresh objects after cache reset, same logical content.
    assert first is not second
    assert first == second
