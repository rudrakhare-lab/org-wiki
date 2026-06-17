import pytest

from backend import agent_provisioning as ap


def test_slugify():
    assert ap.slugify("Legal") == "legal"
    assert ap.slugify("HR Policies & Ops") == "hr-policies-ops"


def test_accent_is_deterministic_hex():
    a1 = ap.accent_for_slug("legal")
    a2 = ap.accent_for_slug("legal")
    assert a1 == a2 and a1.startswith("#") and len(a1) == 7
    assert ap.accent_for_slug("finance") != a1   # different slug → different hue


def test_identity_fallback_when_no_llm(monkeypatch):
    # Force the LLM path to fail → deterministic template fallback.
    monkeypatch.setattr(ap, "_llm_identity", lambda name: None)
    out = ap.generate_identity("Legal")
    assert "Legal" in out and "knowledge base" in out.lower()


@pytest.fixture
def no_extra_agents():
    """The agents table is not truncated by clean_db; purge non-builtin rows so
    create-agent tests are repeatable."""
    from backend import db, agent_registry

    def _purge():
        with db.connection() as c:
            c.execute("DELETE FROM agents WHERE id NOT IN ('conwo', 'infosec')")
        agent_registry.invalidate_cache()

    _purge()
    yield
    _purge()


def test_create_agent_provisions_row_and_dirs(clean_db, no_extra_agents, tmp_path, monkeypatch):
    from backend import agent_provisioning as ap, agent_registry, db, config
    # Point agent data dirs at tmp so the test writes nowhere real.
    monkeypatch.setattr(config, "_BASE", tmp_path, raising=False)
    monkeypatch.setattr(agent_registry, "_BASE", tmp_path, raising=False)

    spec = ap.create_agent("Legal", created_by="admin@x.com")
    assert spec.id == "legal" and spec.has_jira is False and spec.schema_kind == "generic"
    # DB row exists + active
    with db.connection() as c:
        row = c.execute("SELECT * FROM agents WHERE id='legal'").fetchone()
    assert row and row["status"] == "active"
    # Dirs + seeded index created under tmp
    assert (tmp_path / "agents" / "legal" / "wiki" / "index.md").is_file()
    assert (tmp_path / "agents" / "legal" / "raw").is_dir()
    # Appears in the registry
    agent_registry.invalidate_cache()
    assert "legal" in {a.id for a in agent_registry.all()}


def test_create_agent_rejects_duplicate_and_reserved(clean_db, no_extra_agents, tmp_path, monkeypatch):
    from backend import agent_provisioning as ap, config, agent_registry
    monkeypatch.setattr(config, "_BASE", tmp_path, raising=False)
    monkeypatch.setattr(agent_registry, "_BASE", tmp_path, raising=False)
    with pytest.raises(ap.AgentExists):
        ap.create_agent("Infosec", created_by="a")   # reserved/existing
    ap.create_agent("Legal", created_by="a")
    with pytest.raises(ap.AgentExists):
        ap.create_agent("legal", created_by="a")      # duplicate slug
