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
