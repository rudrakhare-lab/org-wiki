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
