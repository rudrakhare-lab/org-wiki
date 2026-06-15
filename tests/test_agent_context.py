from backend import agent_context, agent_registry


def test_default_is_conwo():
    assert agent_context.get_current_agent_id() == "conwo"
    assert agent_context.get_current_agent().id == "conwo"


def test_set_and_reset():
    token = agent_context.set_current_agent("infosec")
    assert agent_context.get_current_agent_id() == "infosec"
    assert agent_context.get_current_agent().id == "infosec"
    agent_context.reset_current_agent(token)
    assert agent_context.get_current_agent_id() == "conwo"


def test_unknown_id_resolves_to_conwo_spec():
    token = agent_context.set_current_agent("bogus")
    assert agent_context.get_current_agent().id == "conwo"
    agent_context.reset_current_agent(token)
