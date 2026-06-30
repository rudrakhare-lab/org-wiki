"""Directory-scoped conftest for tests/scripts/.

Overrides the session-scoped autouse `_pg_test_db` fixture defined in
tests/conftest.py so that tests under this directory can run without a
Postgres connection.  Script tests only assert on constants and pure
functions — they do not touch the database or Gemini.
"""
import pytest


@pytest.fixture(scope="session", autouse=True)
def _pg_test_db():  # noqa: PT004
    """No-op override of the global Postgres fixture for script tests.

    embed_tickets tests only check SQL string constants and the compose_text
    pure function, so the autouse Postgres setup in tests/conftest.py would
    block them in environments without Postgres.  This directory-scoped
    fixture takes priority (inner scope wins) and simply yields without
    opening any DB connection.
    """
    yield
