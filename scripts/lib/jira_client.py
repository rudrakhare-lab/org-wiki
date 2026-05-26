"""
lib/jira_client.py — Thin wrapper around the Jira Cloud REST API.

Responsibilities:
- Basic auth from env vars
- Token-bucket rate limiting (req/sec)
- Exponential backoff on 429 + 5xx via tenacity
- Custom field discovery via /rest/api/3/field (with createmeta fallback)
- Paginated JQL search via the new /rest/api/3/search/jql endpoint with
  `nextPageToken` cursor
- Single-issue fetch for `--ticket KEY`

The client is deliberately stateless beyond the rate limiter and a `requests.Session`.
Higher-level concerns (checkpointing, dedupe, normalization) live in the sync script.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Iterator

# Inject the OS trust store BEFORE requests imports its SSL machinery.
# On corporate networks (e.g. MoveInSync) outbound HTTPS is intercepted by
# a proxy with a self-signed root CA. The OS keychain trusts that cert but
# certifi's bundled list does not — without truststore, every Jira call
# fails with `CERTIFICATE_VERIFY_FAILED: self-signed certificate in
# certificate chain`. Inject is best-effort: if truststore isn't installed
# we fall through and rely on REQUESTS_CA_BUNDLE / certifi.
try:
    import truststore  # type: ignore
    truststore.inject_into_ssl()
except ImportError:  # pragma: no cover
    pass

import requests
from requests.auth import HTTPBasicAuth
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


log = logging.getLogger("jira_client")


class JiraError(RuntimeError):
    """Non-retriable client/server error."""


class JiraRetriable(RuntimeError):
    """Retriable error (429 / 5xx). Tenacity reads this to know to back off."""


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

class _TokenBucket:
    """Simple thread-safe rate limiter — `acquire()` blocks until a slot opens."""

    def __init__(self, rps: float) -> None:
        self._interval = 1.0 / max(rps, 0.1)
        self._lock = threading.Lock()
        self._next_at = 0.0

    def acquire(self) -> None:
        with self._lock:
            now = time.monotonic()
            wait = self._next_at - now
            if wait > 0:
                time.sleep(wait)
                self._next_at += self._interval
            else:
                self._next_at = now + self._interval


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class JiraClient:
    def __init__(
        self,
        *,
        base_url: str,
        email: str,
        token: str,
        api_version: str = "3",
        rate_limit_rps: float = 10.0,
        retry_initial_seconds: int = 30,
        retry_max_attempts: int = 5,
        timeout_seconds: int = 60,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_version = api_version
        self.timeout = timeout_seconds
        self._session = requests.Session()
        self._session.auth = HTTPBasicAuth(email, token)
        self._session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "org-wiki-jira-sync/1.0",
        })
        self._bucket = _TokenBucket(rate_limit_rps)
        self._retry_initial = retry_initial_seconds
        self._retry_max = retry_max_attempts

    # ------------------------- low-level request -------------------------

    def _request(self, method: str, path: str, **kwargs: Any) -> dict:
        """Single HTTP call with rate limit + retry."""
        url = f"{self.base_url}/rest/api/{self.api_version}{path}"

        @retry(
            retry=retry_if_exception_type(JiraRetriable),
            wait=wait_exponential(multiplier=self._retry_initial, max=600),
            stop=stop_after_attempt(self._retry_max),
            before_sleep=before_sleep_log(log, logging.WARNING),
            reraise=True,
        )
        def _do() -> dict:
            self._bucket.acquire()
            try:
                resp = self._session.request(
                    method, url, timeout=self.timeout, **kwargs
                )
            except requests.RequestException as e:
                raise JiraRetriable(f"network error: {e}") from e

            if resp.status_code == 429:
                raise JiraRetriable(f"429 rate limited: {resp.text[:200]}")
            if 500 <= resp.status_code < 600:
                raise JiraRetriable(f"{resp.status_code}: {resp.text[:200]}")
            if resp.status_code == 401:
                raise JiraError(
                    "401 Unauthorized — check JIRA_EMAIL and JIRA_API_TOKEN"
                )
            if resp.status_code == 403:
                raise JiraError(f"403 Forbidden: {resp.text[:200]}")
            if resp.status_code == 404:
                raise JiraError(f"404 Not Found: {url}")
            if resp.status_code >= 400:
                raise JiraError(
                    f"HTTP {resp.status_code}: {resp.text[:500]}"
                )
            if not resp.content:
                return {}
            try:
                return resp.json()
            except ValueError:
                raise JiraError(
                    f"non-JSON response from {url}: {resp.text[:200]}"
                )

        return _do()

    # ------------------------- public API --------------------------------

    def myself(self) -> dict:
        """Sanity-check auth. Returns the current user's profile."""
        return self._request("GET", "/myself")

    def list_fields(self) -> list[dict]:
        """All visible fields. Token scope may limit results."""
        result = self._request("GET", "/field")
        return result if isinstance(result, list) else []

    def discover_field_id(self, display_name: str) -> str | None:
        """
        Try to resolve a custom field's customfield_NNNNN by display name.
        Returns None if the token lacks scope to see custom fields — caller
        should fall back to the configured ID.
        """
        target = display_name.strip().lower()
        try:
            for f in self.list_fields():
                name = (f.get("name") or "").strip().lower()
                if name == target:
                    fid = f.get("id") or f.get("key")
                    if fid:
                        return fid
        except JiraError as e:
            log.warning("field discovery failed: %s", e)
        return None

    def search_jql(
        self,
        *,
        jql: str,
        fields: list[str],
        expand: str | None = None,
        next_page_token: str | None = None,
        page_size: int = 100,
    ) -> dict:
        """
        Single page of /rest/api/3/search/jql results.

        Returns the raw response dict (including `issues`, `nextPageToken`,
        and `isLast`). The new endpoint uses `nextPageToken` instead of
        `startAt` — if a token is returned, pass it on the next call.
        """
        body: dict[str, Any] = {
            "jql": jql,
            "fields": fields,
            "maxResults": page_size,
        }
        if expand:
            body["expand"] = expand
        if next_page_token:
            body["nextPageToken"] = next_page_token
        return self._request("POST", "/search/jql", json=body)

    def iter_search(
        self,
        *,
        jql: str,
        fields: list[str],
        expand: str | None = None,
        page_size: int = 100,
        start_token: str | None = None,
        page_callback: Any = None,
    ) -> Iterator[tuple[dict, str | None]]:
        """
        Generator: yields (issue_dict, next_token_after_this_page) pairs.

        The caller can persist `next_token_after_this_page` to a checkpoint
        once a whole page is committed, so a crash mid-page doesn't lose
        progress (worst case: we re-process a single page on restart).

        `page_callback(issues_in_page, next_token)` if provided is invoked
        after each page is yielded, useful for logging.
        """
        token = start_token
        first = True
        while True:
            page = self.search_jql(
                jql=jql,
                fields=fields,
                expand=expand,
                next_page_token=token,
                page_size=page_size,
            )
            issues = page.get("issues") or []
            next_token = page.get("nextPageToken")
            is_last = page.get("isLast", not next_token)

            if first and not issues:
                log.info("search returned 0 issues")
                return

            first = False
            if page_callback:
                try:
                    page_callback(len(issues), next_token)
                except Exception as e:
                    log.warning("page_callback raised: %s", e)

            for issue in issues:
                yield issue, next_token

            if is_last or not next_token:
                return
            token = next_token

    def get_issue(
        self, key: str, *, fields: list[str], expand: str | None = None
    ) -> dict:
        """Fetch one issue by key."""
        params: dict[str, Any] = {"fields": ",".join(fields)}
        if expand:
            params["expand"] = expand
        return self._request("GET", f"/issue/{key}", params=params)
