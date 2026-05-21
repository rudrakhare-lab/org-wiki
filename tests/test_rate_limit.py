import pytest


@pytest.fixture(autouse=True)
def reset_rate_limit():
    """Each test starts with a clean rate-limit state."""
    import backend.rate_limit as rl
    rl._COUNTS.clear()
    yield
    rl._COUNTS.clear()


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
    import backend.rate_limit as rl
    from datetime import date, timedelta
    # Exhaust quota
    for i in range(30):
        rl.check_rate_limit("tok3", "viewer")
    assert rl.check_rate_limit("tok3", "viewer") is False
    # Simulate next day by patching _RESET_DATE to yesterday
    rl._RESET_DATE = date.today() - timedelta(days=1)
    assert rl.check_rate_limit("tok3", "viewer") is True
