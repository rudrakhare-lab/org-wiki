from fastapi.testclient import TestClient
from backend.api import app

client = TestClient(app)


def test_list_agents_public_shape():
    r = client.get("/agents")
    assert r.status_code == 200
    by_id = {a["id"]: a for a in r.json()}
    assert "conwo" in by_id and "infosec" in by_id
    assert by_id["infosec"]["has_jira"] is False
    assert by_id["infosec"]["modes"] == ["api"]
    assert by_id["conwo"]["display_name"] == "Conwo"
    # Never leak filesystem paths to the client.
    assert "wiki_dir" not in by_id["conwo"]
    assert "claude_md" not in by_id["conwo"]


def test_middleware_tolerates_header_present_unknown_and_absent():
    # The agent-resolution middleware must not choke on any header state:
    # present+known, present+unknown (falls back to conwo), or absent.
    assert client.get("/agents", headers={"X-Agent-Id": "infosec"}).status_code == 200
    assert client.get("/agents", headers={"X-Agent-Id": "does-not-exist"}).status_code == 200
    assert client.get("/agents").status_code == 200
