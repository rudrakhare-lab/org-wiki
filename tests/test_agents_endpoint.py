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
