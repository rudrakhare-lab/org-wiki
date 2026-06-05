import pytest
from unittest.mock import patch, MagicMock
from backend.google_auth import verify_google_credential


def _make_id_info(**overrides):
    base = {
        "email": "rudra.khare@moveinsync.com",
        "name": "Rudra Khare",
        "picture": "https://lh3.googleusercontent.com/photo.jpg",
        "hd": "moveinsync.com",
        "email_verified": True,
    }
    base.update(overrides)
    return base


def test_verify_returns_user_info_for_valid_company_token():
    with patch("backend.google_auth.id_token.verify_oauth2_token") as mock_verify:
        mock_verify.return_value = _make_id_info()
        result = verify_google_credential("fake-credential", "fake-client-id")
    assert result["email"] == "rudra.khare@moveinsync.com"
    assert result["name"] == "Rudra Khare"
    assert result["picture"] == "https://lh3.googleusercontent.com/photo.jpg"


def test_verify_raises_for_non_moveinsync_domain():
    with patch("backend.google_auth.id_token.verify_oauth2_token") as mock_verify:
        mock_verify.return_value = _make_id_info(hd="gmail.com", email="attacker@gmail.com")
        with pytest.raises(ValueError, match="not allowed"):
            verify_google_credential("fake-credential", "fake-client-id")


def test_verify_raises_when_hd_missing():
    with patch("backend.google_auth.id_token.verify_oauth2_token") as mock_verify:
        info = _make_id_info()
        del info["hd"]
        mock_verify.return_value = info
        with pytest.raises(ValueError, match="not allowed"):
            verify_google_credential("fake-credential", "fake-client-id")


def test_verify_raises_on_google_error():
    with patch("backend.google_auth.id_token.verify_oauth2_token") as mock_verify:
        mock_verify.side_effect = ValueError("Token expired")
        with pytest.raises(ValueError):
            verify_google_credential("bad-credential", "fake-client-id")
