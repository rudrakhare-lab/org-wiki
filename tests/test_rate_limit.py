"""
Rate limiter tests — now backed by the Postgres `rate_limits` table.
The `clean_db` fixture (conftest) truncates it for isolation.
"""
import pytest
from datetime import datetime, timedelta, timezone


@pytest.fixture(autouse=True)
def reset_rate_limit(clean_db):
    """Each test starts with an empty rate_limits table (truncated by clean_db)."""
    yield


def test_viewer_allowed_up_to_limit():
    import backend.rate_limit as rl
    for i in range(30):
        assert rl.check_rate_limit("tok1", "viewer") is True
    # 31st call should be denied
    assert rl.check_rate_limit("tok1", "viewer") is False


def test_contributor_same_limit():
    import backend.rate_limit as rl
    for i in range(30):
        rl.check_rate_limit("tok2", "contributor")
    assert rl.check_rate_limit("tok2", "contributor") is False


def test_admin_unlimited():
    import backend.rate_limit as rl
    for i in range(100):
        assert rl.check_rate_limit("tokadmin", "admin") is True


def test_different_tokens_independent():
    import backend.rate_limit as rl
    for i in range(30):
        rl.check_rate_limit("user_a", "viewer")
    # user_a is exhausted; user_b has a fresh counter
    assert rl.check_rate_limit("user_b", "viewer") is True


def test_counter_resets_on_new_day():
    """A token that exhausted its quota YESTERDAY starts fresh today — the
    counter is keyed on the UTC day, so yesterday's row doesn't carry over."""
    import backend.rate_limit as rl
    from backend import db

    tok = "tok_yesterday"
    yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    # Simulate an exhausted quota for yesterday.
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO rate_limits (token, day, count) VALUES (%s, %s, %s)",
            (tok, yesterday, rl.DAILY_LIMIT),
        )
    # Today's check must be allowed — today's row is separate and starts fresh.
    assert rl.check_rate_limit(tok, "viewer") is True
