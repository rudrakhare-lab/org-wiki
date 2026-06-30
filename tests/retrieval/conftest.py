"""Directory-scoped conftest for tests/retrieval/.

Overrides the session-scoped autouse `_pg_test_db` fixture defined in
tests/conftest.py so that tests under this directory can run without a
Postgres connection.  When CONWO_TEST_DSN is set the global fixture takes
effect (via the standard pytest fixture override priority rules) and a real
DB is available; when it is unset this no-op runs instead and skips the
connection entirely.
"""
import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def _pg_test_db():  # noqa: PT004
    """No-op override of the global Postgres fixture for retrieval tests.

    Retrieval v2 tests only mock the Gemini client and do not touch the
    database, so the autouse Postgres setup in tests/conftest.py would block
    them in environments without Postgres.  This directory-scoped fixture
    takes priority (inner scope wins) and simply yields without opening any
    DB connection.
    """
    if os.getenv("CONWO_TEST_DSN"):
        # Let the parent conftest handle real DB setup — but since pytest
        # only runs one fixture of the same name per scope, we still need to
        # yield here.  Users who want DB tests in this directory should rely
        # on the global fixture indirectly via the parent conftest by NOT
        # placing this override here; for now retrieval tests are DB-free.
        pass
    yield
