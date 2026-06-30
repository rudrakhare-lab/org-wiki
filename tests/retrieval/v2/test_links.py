from unittest.mock import MagicMock

def _fake_conn(by_src: dict[str, list[tuple[str,str]]], rows: dict[str, dict]):
    """Build a fake conn whose cursor.execute / fetchall returns scripted data."""
    cur = MagicMock()
    state = {"mode": None, "arg": None}
    def execute(sql, params):
        if "FROM ticket_links" in sql and "src_key = ANY" in sql:
            state["mode"], state["arg"] = "links", params[0]
        elif "FROM tickets" in sql and "key = ANY" in sql:
            state["mode"], state["arg"] = "tickets", params[0]
    def fetchall():
        if state["mode"] == "links":
            out = []
            for src in state["arg"]:
                for dst, lt in by_src.get(src, []):
                    out.append({"src_key": src, "dst_key": dst, "link_type": lt})
            return out
        if state["mode"] == "tickets":
            return [rows[k] for k in state["arg"] if k in rows]
        return []
    cur.execute.side_effect = execute
    cur.fetchall.side_effect = fetchall
    cur.__enter__ = MagicMock(return_value=cur); cur.__exit__ = MagicMock(return_value=False)
    conn = MagicMock(); conn.cursor.return_value = cur
    return conn

def test_drops_superseded_and_replaces_with_newer():
    from backend.retrieval.v2 import links
    cands = [
        {"key": "TS-1", "updated_at": "2024-01-01", "fused_score": 1.0},
        {"key": "TS-9", "updated_at": "2020-01-01", "fused_score": 0.5},
    ]
    by_src = {"TS-1": [("TS-2", "supersedes")]}
    rows = {"TS-2": {"key": "TS-2", "updated_at": "2026-01-01",
                     "summary": "newer", "description_text": "", "comments_text": "",
                     "status_category": "done", "priority": "P2",
                     "resolved_at": None, "functional_area": "WP-admin",
                     "links_json": "[]"}}
    conn = _fake_conn(by_src, rows)
    out = links.expand(conn, cands, top_for_expansion=20, max_added=20)
    keys = [c["key"] for c in out]
    assert "TS-2" in keys and "TS-1" not in keys

def test_one_hop_expansion_adds_linked_tickets():
    from backend.retrieval.v2 import links
    cands = [{"key": "TS-1", "updated_at": "2026-01-01", "fused_score": 1.0}]
    by_src = {"TS-1": [("TS-5", "blocks")]}
    rows = {"TS-5": {"key": "TS-5", "summary": "x", "description_text": "", "comments_text": "",
                     "status_category": "done", "priority": "P1", "updated_at": "2026-02-01",
                     "resolved_at": "2026-02-01", "functional_area": "WP-admin", "links_json": "[]"}}
    conn = _fake_conn(by_src, rows)
    out = links.expand(conn, cands, top_for_expansion=20, max_added=20)
    assert any(c["key"] == "TS-5" for c in out)
