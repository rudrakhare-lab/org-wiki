"""
Shared pytest fixtures for the Conwo backend test suite.

DB isolation: all DB-touching tests run against a dedicated `wis_conwo_test`
database, NEVER the dev `wis_conwo` (which holds the live ETL'd data). A session
fixture creates + migrates the test DB and repoints the app pool at it; a guarded
truncate keeps tests isolated. Every truncate asserts current_database() first —
a misconfigured fixture must never wipe the dev DB.
"""
import os
import pytest

TEST_DB_NAME = "wis_conwo_test"

# Tables truncated between DB tests (CASCADE covers FK children; order irrelevant).
_APP_TABLES = [
    "tokens", "users",
    "messages", "conversations",
    "trace_events", "trace_metrics", "trace_sessions",
    "ticket_module_tags", "ticket_classifications", "sync_runs",
    "custom_field_map", "tickets",
    "jira_links", "module_links", "dependencies", "configs",
    "rate_limits",
]


@pytest.fixture(scope="session", autouse=True)
def _pg_test_db():
    """Create + migrate an isolated test database and point the app pool at it.

    NOTE: CREATE DATABASE needs createdb privilege + autocommit + connecting to a
    different DB. Fine on local Docker (the wis_conwo role is a superuser). On a
    managed PG without createdb, switch to schema-based isolation
    (CREATE SCHEMA test + search_path) — left as a portability note.
    """
    import psycopg
    from backend import db as _db

    # admin_dsn currently targets CONWO_DB_NAME (dev wis_conwo) — connect there to
    # CREATE the test DB (can't create a DB while connected to it).
    admin_dsn = _db._dsn()
    with psycopg.connect(admin_dsn, autocommit=True) as c:
        exists = c.execute(
            "SELECT 1 FROM pg_database WHERE datname=%s", (TEST_DB_NAME,)
        ).fetchone()
        if not exists:
            c.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')

    # Repoint the pool at the test DB for the whole session.
    os.environ["CONWO_DB_NAME"] = TEST_DB_NAME
    _db.close_pool()
    _db.init_pool()
    _db.init_db()

    # Safety guard — refuse to run if we're somehow not on the test DB.
    with _db.connection() as conn:
        current = conn.execute("SELECT current_database()").fetchone()[0]
    assert current == TEST_DB_NAME, (
        f"Test DB guard failed: connected to {current!r}, expected {TEST_DB_NAME!r}. "
        "Aborting to avoid mutating the dev database."
    )

    yield
    _db.close_pool()


def _truncate_all():
    """Truncate all app tables in the TEST database. Guarded: asserts we are on
    wis_conwo_test before issuing TRUNCATE, so it can never wipe the dev DB."""
    from backend import db as _db
    with _db.connection() as conn:
        current = conn.execute("SELECT current_database()").fetchone()[0]
        assert current == TEST_DB_NAME, (
            f"TRUNCATE guard: refusing to truncate {current!r} (not the test DB)."
        )
        conn.execute("TRUNCATE " + ", ".join(_APP_TABLES) + " RESTART IDENTITY CASCADE")


@pytest.fixture
def clean_db():
    """Truncate all app tables before a DB test for isolation."""
    _truncate_all()
    yield


@pytest.fixture
def isolated_auth():
    """auth_store backed by the test Postgres DB (tables truncated for isolation)."""
    _truncate_all()
    from backend import auth_store
    return auth_store


@pytest.fixture
def isolated_store():
    """conversation_store backed by the test Postgres DB (truncated for isolation)."""
    _truncate_all()
    from backend import conversation_store
    return conversation_store


@pytest.fixture(autouse=False)
def clear_pms_env(monkeypatch):
    """Clear all PMS credential environment variables."""
    for var in (
        "PMS_TOKEN_COM", "PMS_TOKEN_IN", "PMS_TOKEN",
        "PMS_COOKIE_COM", "PMS_COOKIE_IN", "PMS_COOKIE",
    ):
        monkeypatch.delenv(var, raising=False)
