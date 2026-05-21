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

WIKI_DIR = ROOT / "wiki"
RAW_DIR = ROOT / "raw"
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
    """Return the server-side key if set, else fall back to the caller-supplied key."""
    server_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if server_key:
        return server_key
    if request_key:
        return request_key
    raise ValueError(
        "No Anthropic API key. Set ANTHROPIC_API_KEY on the server "
        "or pass claude_api_key in the request."
    )


def lookup_user_by_token(token: str) -> dict | None:
    for _name, user in _load_users().items():
        if user.get("token") != token:
            continue
        expires = user.get("expires_at")
        if expires:
            try:
                if date.fromisoformat(str(expires)) < date.today():
                    return None   # expired
            except ValueError:
                pass  # malformed date — don't block, let it through
        return user
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
