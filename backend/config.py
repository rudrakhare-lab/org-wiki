"""
Backend configuration — paths, settings, constants.
"""
from __future__ import annotations

import hashlib
import os
from datetime import date
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-reuse-import]

ROOT = Path(__file__).resolve().parent.parent

# Atlassian Jira Cloud base URL (e.g. https://moveinsync.atlassian.net). Used
# by jira_live_tools to hit /rest/api/3/issue/{key} directly when the local
# mirror is missing a recently-filed ticket. Empty string means "not configured."
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "").rstrip("/")


def _usd_inr_rate() -> float:
    """USD→INR rate used to show per-query cost in the chat UI. Override via
    CONWO_USD_INR; a malformed value falls back to the default rather than crashing."""
    try:
        return float(os.getenv("CONWO_USD_INR", "88"))
    except (TypeError, ValueError):
        return 88.0


CONWO_USD_INR: float = _usd_inr_rate()

# wiki/ and raw/ live under CONWO_DATA_DIR when set (e.g. /app/data, a mounted
# PVC in k8s) so they persist across pod restarts; otherwise under the repo root
# (local dev — unchanged). Everything derived from RAW_DIR below follows the base.
# The image bakes a wiki/ baseline at ROOT/wiki; api.py seeds it onto an empty
# volume at startup (see _seed_wiki_if_empty).
SEED_WIKI_DIR = ROOT / "wiki"   # baked into the image; seed source
_DATA_DIR = os.getenv("CONWO_DATA_DIR", "").strip()
_BASE = Path(_DATA_DIR) if _DATA_DIR else ROOT

WIKI_DIR = _BASE / "wiki"
RAW_DIR = _BASE / "raw"
JIRA_DB = RAW_DIR / "jira" / "tickets.sqlite"
FEEDBACK_DIR = RAW_DIR / "feedback"
ANSWER_LOG = FEEDBACK_DIR / "answer_log.jsonl"
FEEDBACK_LOG = FEEDBACK_DIR / "answer_feedback.jsonl"
CONVERSATIONS_DIR = RAW_DIR / "conversations"
CONVERSATIONS_DB = CONVERSATIONS_DIR / "conversations.sqlite"
JIRA_SYNC_LOG = RAW_DIR / "jira" / "sync.log"
SYNC_MANIFEST = RAW_DIR / ".sync_manifest.json"
ALLOWED_USERS_TOML = ROOT / "config" / "allowed_users.toml"
CLAUDE_MD = ROOT / "CLAUDE.md"
KNOWN_PATTERNS_MD = WIKI_DIR / "known-answer-patterns.md"

# Sections of CLAUDE.md to include in the backend system prompt.
# These cover QUERY workflow (5), Jira awareness (9), and Live Config Debug (12).
SYSTEM_PROMPT_SECTIONS = [5, 9, 12]

WIKI_INDEX_EXCLUDE = {"log.md"}  # too large / append-only, skip from search index


def _load_users() -> dict[str, dict]:
    if not ALLOWED_USERS_TOML.exists():
        return {}
    with ALLOWED_USERS_TOML.open("rb") as f:
        data = tomllib.load(f)
    return data.get("users", {})


def token_for_email(email: str) -> str:
    return hashlib.sha256(email.encode()).hexdigest()[:32]


def resolve_api_key(request_key: str | None = None) -> str:
    """Return the server-side Anthropic API key.

    Single-key deployment: the server's `ANTHROPIC_API_KEY` env var is the
    only accepted source. The `request_key` parameter is preserved on the
    signature only so callers still importing this name don't break at
    import time — its value is ignored.
    """
    del request_key  # explicitly discarded — single-key deployment
    server_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if server_key:
        return server_key
    raise ValueError(
        "ANTHROPIC_API_KEY is not configured on the server. "
        "Set it in the backend's environment (e.g. .env) and restart."
    )


def lookup_user_by_token(token: str) -> dict | None:
    # Check SQLite auth store first (Layer 2 users).
    # NOTE: if auth_store returns None (revoked/expired), we fall through to the
    # TOML fallback. This means a TOML entry with the same token value could
    # bypass auth_store revocation. In practice this is prevented by operational
    # discipline: remove TOML entries for users who have been provisioned in
    # auth_store. The TOML path exists only for migration compatibility and
    # should be removed once all users are in auth_store.
    try:
        from backend import auth_store
        result = auth_store.lookup_token(token)
        if result is not None:
            return result
    except Exception:
        pass  # auth_store unavailable or DB not yet initialized — fall through to TOML

    # Fall back to TOML (Layer 1 / migration compatibility)
    for _name, user in _load_users().items():
        if user.get("token") != token:
            continue
        expires = user.get("expires_at")
        if expires:
            try:
                if date.fromisoformat(str(expires)) < date.today():
                    return None
            except ValueError:
                pass
        # TOML users predate the approval flow and the role-column default. Treat
        # them as approved operators so the /query approval gate never 403s them;
        # default a missing role to 'general' (least privilege).
        return {**user, "approved": user.get("approved", True),
                "role": user.get("role", "general")}
    return None


def is_admin_token(token: str) -> bool:
    user = lookup_user_by_token(token)
    return user is not None and user.get("role") == "admin"


def local_claude_code_enabled() -> bool:
    """
    True when the operator has explicitly opted into the local-dev no-auth
    bypass for Claude Code endpoints via the CONWO_LOCAL_CLAUDE_CODE env var.

    Intended for the case where the backend runs on the user's own laptop and
    the only consumer is the user's own browser on localhost. Must NOT be set
    on shared / production deployments — anyone who can reach the backend would
    be able to drive the server's Claude Code session.
    """
    return os.getenv("CONWO_LOCAL_CLAUDE_CODE", "").strip().lower() in {
        "1", "true", "yes", "on"
    }


def dev_login_enabled() -> bool:
    """
    True when the operator has explicitly enabled the dev-only email-login path
    via the CONWO_DEV_LOGIN env var.

    Lets test users sign in by typing an @moveinsync.com email (no Google), so the
    three roles and the approval flow can be exercised in dev. Must NOT be set on
    production — anyone who can reach the backend could mint a session for any
    @moveinsync.com email. Google OAuth remains the only prod login path.
    """
    return os.getenv("CONWO_DEV_LOGIN", "").strip().lower() in {
        "1", "true", "yes", "on"
    }
