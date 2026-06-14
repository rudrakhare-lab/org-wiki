import importlib
import json
import pytest
from pathlib import Path


# ── Proposals agent-scoping tests ────────────────────────────────────────────


@pytest.fixture
def isolated_wp(tmp_path, monkeypatch):
    """Point wiki_proposals at a fresh JSONL under tmp_path."""
    import backend.wiki_proposals as wp_module
    importlib.reload(wp_module)
    feedback_dir = tmp_path / "raw" / "feedback"
    feedback_dir.mkdir(parents=True)
    proposals_file = feedback_dir / "wiki_proposals.jsonl"
    monkeypatch.setattr(wp_module, "PROPOSALS_FILE", proposals_file, raising=False)
    monkeypatch.setattr(wp_module, "FEEDBACK_DIR", feedback_dir, raising=False)
    return wp_module


def test_proposals_carry_agent_id(isolated_wp):
    """A proposal created with agent_id='infosec' stores the field."""
    wp = isolated_wp
    pid = wp.create_proposal(
        page_path="modules/vis.md",
        proposed_change="some change",
        submitter_email="a@b.com",
        agent_id="infosec",
    )
    rec = wp.get_proposal(pid)
    assert rec is not None
    assert rec.get("agent_id") == "infosec"


def test_proposals_filtered_by_agent_id(isolated_wp):
    """list_proposals(agent_id=) returns only records for that agent."""
    wp = isolated_wp
    pid_infosec = wp.create_proposal(
        page_path="modules/vis.md",
        proposed_change="infosec change",
        submitter_email="a@b.com",
        agent_id="infosec",
    )
    pid_conwo = wp.create_proposal(
        page_path="modules/meeting.md",
        proposed_change="conwo change",
        submitter_email="b@b.com",
        agent_id="conwo",
    )

    infosec_list = wp.list_proposals(agent_id="infosec")
    conwo_list = wp.list_proposals(agent_id="conwo")

    assert [p["id"] for p in infosec_list] == [pid_infosec]
    assert [p["id"] for p in conwo_list] == [pid_conwo]


def test_proposals_infosec_not_in_conwo_list(isolated_wp):
    """An infosec proposal must NOT appear in a conwo list."""
    wp = isolated_wp
    wp.create_proposal(
        page_path="modules/vis.md",
        proposed_change="infosec only",
        submitter_email="a@b.com",
        agent_id="infosec",
    )
    conwo_list = wp.list_proposals(agent_id="conwo")
    assert conwo_list == []


def test_proposals_legacy_records_treated_as_conwo(isolated_wp, tmp_path):
    """Records lacking agent_id are treated as 'conwo' when filtering."""
    wp = isolated_wp
    # Write a legacy record (no agent_id) directly to the file
    legacy = {
        "id": "prop_legacy01",
        "submitter_email": "old@b.com",
        "answer_id": None,
        "reason": "",
        "validation_log": [],
        "suggested_companion_edit": None,
        "status": "pending",
        "admin_note": None,
        "created_at": "2024-01-01T00:00:00+00:00",
        "resolved_at": None,
        "applied_at": None,
        "applied_by": None,
        "proposal_type": "legacy_text",
        "page_path": "modules/old.md",
        "proposed_change": "old change",
        # NOTE: no agent_id field
    }
    with wp.PROPOSALS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(legacy) + "\n")

    conwo_list = wp.list_proposals(agent_id="conwo")
    infosec_list = wp.list_proposals(agent_id="infosec")

    conwo_ids = [p["id"] for p in conwo_list]
    assert "prop_legacy01" in conwo_ids
    infosec_ids = [p["id"] for p in infosec_list]
    assert "prop_legacy01" not in infosec_ids


def test_new_proposal_default_agent_id_is_conwo(isolated_wp):
    """When agent_id is not specified, it defaults to 'conwo'."""
    wp = isolated_wp
    pid = wp.create_proposal(
        page_path="modules/foo.md",
        proposed_change="something",
        submitter_email="x@y.com",
    )
    rec = wp.get_proposal(pid)
    assert rec.get("agent_id") == "conwo"
    # Also appears in conwo list
    assert any(p["id"] == pid for p in wp.list_proposals(agent_id="conwo"))


# ── Answer-log agent-scoping tests ────────────────────────────────────────────


@pytest.fixture
def isolated_feedback(tmp_path, monkeypatch):
    """Point feedback_service at fresh JSONL files under tmp_path."""
    import backend.feedback_service as fs_module
    importlib.reload(fs_module)
    feedback_dir = tmp_path / "raw" / "feedback"
    feedback_dir.mkdir(parents=True)
    answer_log = feedback_dir / "answer_log.jsonl"
    monkeypatch.setattr(fs_module, "ANSWER_LOG", answer_log, raising=False)
    return fs_module, answer_log


def test_log_answer_carries_agent_id(isolated_feedback):
    """log_answer stores agent_id in the written JSONL record."""
    fs, answer_log = isolated_feedback
    fs.log_answer(
        question="What is X?",
        answer_text="X is Y.",
        confidence="High",
        agent_id="infosec",
    )
    lines = answer_log.read_text().strip().splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec.get("agent_id") == "infosec"


def test_log_answer_default_agent_id_is_conwo(isolated_feedback):
    """When agent_id is omitted from log_answer, it defaults to 'conwo'."""
    fs, answer_log = isolated_feedback
    fs.log_answer(
        question="What is Z?",
        answer_text="Z is W.",
        confidence="Medium",
    )
    lines = answer_log.read_text().strip().splitlines()
    rec = json.loads(lines[0])
    assert rec.get("agent_id") == "conwo"


# ── DB-backed tests (existing) ────────────────────────────────────────────────


def test_migration_adds_agent_id_columns(clean_db):
    from backend import db
    for table in ("conversations", "messages", "trace_sessions"):
        with db.connection() as conn:
            cols = {
                r[0]
                for r in conn.execute(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = %s",
                    (table,),
                ).fetchall()
            }
        assert "agent_id" in cols, f"{table} missing agent_id"


def test_conversations_scoped_by_agent(isolated_store):
    cs = isolated_store
    c1 = cs.create_conversation("conwo chat", user_email="u@x.com", agent_id="conwo")
    c2 = cs.create_conversation("infosec chat", user_email="u@x.com", agent_id="infosec")

    conwo_list = cs.list_conversations(user_email="u@x.com", agent_id="conwo")
    infosec_list = cs.list_conversations(user_email="u@x.com", agent_id="infosec")

    assert [c["id"] for c in conwo_list] == [c1["id"]]
    assert [c["id"] for c in infosec_list] == [c2["id"]]


def test_add_message_carries_agent_id(isolated_store):
    cs = isolated_store
    conv = cs.create_conversation("c", user_email="u@x.com", agent_id="infosec")
    msg = cs.add_message(conv["id"], "user", "hello", agent_id="infosec")
    assert msg["agent_id"] == "infosec"


def test_trace_sessions_scoped_by_agent(clean_db):
    from backend import trace_store, db
    trace_store.start_session("t-conwo", mode="api", question="q1", agent_id="conwo")
    trace_store.start_session("t-info", mode="api", question="q2", agent_id="infosec")
    with db.connection() as conn:
        n_info = conn.execute(
            "SELECT COUNT(*) FROM trace_sessions WHERE agent_id = %s", ("infosec",)
        ).fetchone()[0]
        n_conwo = conn.execute(
            "SELECT COUNT(*) FROM trace_sessions WHERE agent_id = %s", ("conwo",)
        ).fetchone()[0]
    assert n_info == 1 and n_conwo == 1
