from fastapi.testclient import TestClient
from backend.api import app, _get_user


def _admin():
    return {"email": "admin@x.com", "role": "admin", "approved": True}


def test_create_agent_endpoint(clean_db, tmp_path, monkeypatch):
    from backend import config, agent_registry
    monkeypatch.setattr(config, "_BASE", tmp_path, raising=False)
    monkeypatch.setattr(agent_registry, "_BASE", tmp_path, raising=False)
    # Purge any non-builtin agents (clean_db does not truncate the agents table).
    from backend import db
    with db.connection() as c:
        c.execute("DELETE FROM agents WHERE id NOT IN ('conwo', 'infosec')")
    agent_registry.invalidate_cache()
    app.dependency_overrides[_get_user] = _admin
    try:
        c = TestClient(app)
        r = c.post("/admin/agents", json={"name": "Legal"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["id"] == "legal" and body["accent"].startswith("#")
        # Now visible in the public list
        ids = {a["id"] for a in c.get("/agents").json()}
        assert "legal" in ids
        # Duplicate → 409
        assert c.post("/admin/agents", json={"name": "legal"}).status_code == 409
    finally:
        app.dependency_overrides.clear()
        with db.connection() as conn:
            conn.execute("DELETE FROM agents WHERE id NOT IN ('conwo', 'infosec')")
        agent_registry.invalidate_cache()
