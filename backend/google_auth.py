"""
Google Identity Services token verification.

verify_google_credential() accepts a Google ID token (credential from the
GSI JS callback), verifies it against Google's public keys, enforces the
@moveinsync.com hosted domain, and returns {email, name, picture}.

Raises ValueError for any invalid or non-company token.
"""
from __future__ import annotations

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests


def verify_google_credential(credential: str, client_id: str) -> dict:
    """Verify a Google ID token and return user info.

    Args:
        credential: The raw ID token string from the GSI JS callback.
        client_id: The OAuth 2.0 client ID to verify against.

    Returns:
        dict with keys: email, name, picture

    Raises:
        ValueError: If the token is invalid, expired, or from outside moveinsync.com.
    """
    id_info = id_token.verify_oauth2_token(
        credential,
        google_requests.Request(),
        client_id,
    )
    if id_info.get("hd") != "moveinsync.com":
        raise ValueError(
            f"Domain '{id_info.get('hd')}' not allowed. "
            "Only @moveinsync.com accounts can sign in."
        )
    return {
        "email": id_info["email"],
        "name": id_info.get("name", id_info["email"]),
        "picture": id_info.get("picture", ""),
    }
