#!/usr/bin/env python3
"""
jira_sync.py — Tier 0 sync: Jira → raw/jira/tickets.sqlite.

Usage
-----
    python scripts/jira_sync.py --backfill                 # full historical
    python scripts/jira_sync.py --incremental              # nightly cron
    python scripts/jira_sync.py --ticket TS-1234           # one ticket
    python scripts/jira_sync.py --backfill --dry-run       # no DB writes
    python scripts/jira_sync.py --backfill --limit 100     # Checkpoint 2 sample
    python scripts/jira_sync.py --report                   # distribution report
    python scripts/jira_sync.py --backfill --filter A      # one filter only
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Local imports — keep relative-style by adjusting sys.path so the script
# works whether invoked as `python scripts/jira_sync.py` or via cron.
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from lib import db, normalize  # noqa: E402
from lib.jira_client import JiraClient, JiraError  # noqa: E402


# ---------------------------------------------------------------------------
# Logging setup — JSON lines to file + human-readable to stderr
# ---------------------------------------------------------------------------

class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for k in ("event", "key", "filter", "page", "fetched", "next_token"):
            v = getattr(record, k, None)
            if v is not None:
                payload[k] = v
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def _setup_logging(log_path: Path, verbose: bool) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    root.handlers.clear()

    file_h = logging.FileHandler(log_path, encoding="utf-8")
    file_h.setFormatter(_JsonFormatter())
    file_h.setLevel(logging.INFO)
    root.addHandler(file_h)

    stream_h = logging.StreamHandler(sys.stderr)
    stream_h.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    stream_h.setLevel(logging.DEBUG if verbose else logging.INFO)
    root.addHandler(stream_h)


log = logging.getLogger("jira_sync")


# ---------------------------------------------------------------------------
# Config & env
# ---------------------------------------------------------------------------

def _load_config(path: Path) -> dict[str, Any]:
    with open(path, "rb") as f:
        return tomllib.load(f)


def _resolve_credentials(cfg: dict[str, Any]) -> tuple[str, str, str]:
    conn_cfg = cfg.get("connection", {})
    base_url = os.environ.get(conn_cfg.get("base_url_env", "JIRA_BASE_URL"), "").strip()
    email    = os.environ.get(conn_cfg.get("email_env", "JIRA_EMAIL"), "").strip()
    token    = os.environ.get(conn_cfg.get("token_env", "JIRA_API_TOKEN"), "").strip()
    missing = [
        n for n, v in [("JIRA_BASE_URL", base_url), ("JIRA_EMAIL", email), ("JIRA_API_TOKEN", token)]
        if not v
    ]
    if missing:
        raise SystemExit(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Make sure .env is loaded (set -a && source .env && set +a) "
            "or run from a shell where they're exported."
        )
    return base_url, email, token


def _build_client(cfg: dict[str, Any]) -> JiraClient:
    base_url, email, token = _resolve_credentials(cfg)
    rl = cfg.get("rate_limit", {})
    return JiraClient(
        base_url=base_url,
        email=email,
        token=token,
        api_version=cfg.get("connection", {}).get("api_version", "3"),
        rate_limit_rps=float(rl.get("requests_per_second", 10)),
        retry_initial_seconds=int(rl.get("retry_initial_seconds", 30)),
        retry_max_attempts=int(rl.get("retry_max_attempts", 5)),
    )


# ---------------------------------------------------------------------------
# Custom field resolution
# ---------------------------------------------------------------------------

def _resolve_functional_area_field(
    client: JiraClient, conn, cfg: dict[str, Any]
) -> str:
    fa_cfg = cfg.get("custom_fields", {}).get("functional_area", {})
    display = fa_cfg.get("display_name", "Functional Area")
    fallback = fa_cfg.get("fallback_id", "customfield_11516")
    cache_hours = int(cfg.get("sync", {}).get("custom_field_cache_hours", 24))

    cached = db.get_field_id(conn, display, "_global", cache_hours)
    if cached:
        log.info("functional_area field id (cached): %s", cached)
        return cached

    discovered = client.discover_field_id(display)
    if discovered:
        log.info("functional_area field id (discovered): %s", discovered)
        db.set_field_id(conn, display, "_global", discovered)
        conn.commit()
        return discovered

    log.warning(
        "field discovery returned nothing (token scope likely limited); "
        "using fallback %s from config", fallback
    )
    db.set_field_id(conn, display, "_global", fallback)
    conn.commit()
    return fallback


# ---------------------------------------------------------------------------
# Checkpoints
# ---------------------------------------------------------------------------

def _checkpoint_path(filter_name: str) -> Path:
    return ROOT / "raw" / "jira" / "checkpoints" / f"{filter_name}.json"


def _load_checkpoint(filter_name: str) -> dict[str, Any]:
    p = _checkpoint_path(filter_name)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            log.warning("checkpoint %s unreadable, ignoring", p)
    return {}


def _save_checkpoint(filter_name: str, payload: dict[str, Any]) -> None:
    p = _checkpoint_path(filter_name)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _clear_checkpoint(filter_name: str) -> None:
    p = _checkpoint_path(filter_name)
    if p.exists():
        p.unlink()


# ---------------------------------------------------------------------------
# Run a single filter
# ---------------------------------------------------------------------------

def _run_filter(
    client: JiraClient,
    conn,
    cfg: dict[str, Any],
    *,
    filter_def: dict[str, Any],
    fa_field_id: str,
    mode: str,
    limit: int | None,
    dry_run: bool,
    incremental_since: str | None,
) -> dict[str, Any]:
    filter_name = filter_def["name"]
    base_jql = filter_def["jql"].strip()
    if incremental_since:
        # Add an updated > '...' clause; preserve ORDER BY semantics
        base_jql = _splice_incremental(base_jql, incremental_since)

    fetch_cfg = cfg.get("fetch", {})
    fields = list(fetch_cfg.get("fields", []))
    if fa_field_id not in fields:
        fields.append(fa_field_id)
    expand = fetch_cfg.get("expand")
    page_size = int(cfg.get("pagination", {}).get("page_size", 100))

    checkpoint = _load_checkpoint(filter_name) if mode == "backfill" else {}
    start_token = checkpoint.get("next_token") if not incremental_since else None
    fetched_so_far = checkpoint.get("fetched", 0) if not incremental_since else 0

    run_id = db.start_sync_run(conn, filter_name, mode)
    counts = {"fetched": 0, "new": 0, "updated": 0, "unchanged": 0}
    errors: list[dict[str, Any]] = []

    log.info(
        "[%s] starting %s mode (start_token=%s, since=%s)",
        filter_name, mode, bool(start_token), incremental_since,
    )

    try:
        page_buffer: list[dict[str, Any]] = []
        last_seen_token = start_token

        for issue, next_token_after in client.iter_search(
            jql=base_jql,
            fields=fields,
            expand=expand,
            page_size=page_size,
            start_token=start_token,
        ):
            page_buffer.append(issue)
            counts["fetched"] += 1

            # Flush every page_size issues — commit + checkpoint atomically
            if len(page_buffer) >= page_size:
                _flush_page(conn, page_buffer, fa_field_id, filter_name, dry_run, counts, errors)
                page_buffer.clear()
                if not dry_run and mode == "backfill":
                    _save_checkpoint(filter_name, {
                        "next_token": next_token_after,
                        "fetched": fetched_so_far + counts["fetched"],
                        "updated_at": db.utcnow_iso(),
                    })
                last_seen_token = next_token_after
                log.info(
                    "[%s] page committed (total fetched=%d, new=%d, updated=%d)",
                    filter_name, counts["fetched"], counts["new"], counts["updated"],
                )

            if limit is not None and counts["fetched"] >= limit:
                log.info("[%s] hit --limit %d, stopping", filter_name, limit)
                break

        # Final flush of the partial page
        if page_buffer:
            _flush_page(conn, page_buffer, fa_field_id, filter_name, dry_run, counts, errors)
            page_buffer.clear()

        # On clean completion of a backfill, clear the checkpoint
        if mode == "backfill" and limit is None and not dry_run:
            _clear_checkpoint(filter_name)
            log.info("[%s] backfill complete, checkpoint cleared", filter_name)

    except KeyboardInterrupt:
        log.warning("[%s] interrupted — checkpoint preserved at %s", filter_name, last_seen_token)
        db.end_sync_run(
            conn, run_id, status="interrupted",
            fetched=counts["fetched"], new=counts["new"], updated=counts["updated"],
            errors=errors,
        )
        raise
    except Exception as e:
        log.exception("[%s] failed: %s", filter_name, e)
        errors.append({"error": str(e), "type": type(e).__name__})
        db.end_sync_run(
            conn, run_id, status="error",
            fetched=counts["fetched"], new=counts["new"], updated=counts["updated"],
            errors=errors,
        )
        raise

    db.end_sync_run(
        conn, run_id, status="success",
        fetched=counts["fetched"], new=counts["new"], updated=counts["updated"],
        errors=errors or None,
    )
    log.info(
        "[%s] done: fetched=%d new=%d updated=%d unchanged=%d",
        filter_name, counts["fetched"], counts["new"], counts["updated"], counts["unchanged"],
    )
    return counts


def _flush_page(
    conn,
    issues: list[dict[str, Any]],
    fa_field_id: str,
    filter_name: str,
    dry_run: bool,
    counts: dict[str, int],
    errors: list[dict[str, Any]],
) -> None:
    if dry_run:
        for issue in issues:
            try:
                normalize.normalize_issue(
                    issue,
                    fa_field_id=fa_field_id,
                    source_filter=filter_name,
                    fetched_at=db.utcnow_iso(),
                )
            except Exception as e:
                errors.append({"key": issue.get("key"), "error": str(e)})
        return

    fetched_at = db.utcnow_iso()
    with db.transaction(conn):
        for issue in issues:
            try:
                row = normalize.normalize_issue(
                    issue,
                    fa_field_id=fa_field_id,
                    source_filter=filter_name,
                    fetched_at=fetched_at,
                )
                outcome = db.upsert_ticket(conn, row)
                if outcome == "new":
                    counts["new"] += 1
                elif outcome == "updated":
                    counts["updated"] += 1
                else:
                    counts["unchanged"] += 1
            except Exception as e:
                log.exception("normalize/upsert failed for %s", issue.get("key"))
                errors.append({"key": issue.get("key"), "error": str(e)})


def _splice_incremental(jql: str, since_iso: str) -> str:
    """
    Insert `AND updated > '<since>'` before the ORDER BY clause.

    Jira accepts `updated > "yyyy/MM/dd HH:mm"` or `> -7d`; we use the
    relative form built from `since_iso`. Simpler is better — we just use
    the ISO timestamp Jira itself returned, formatted to its accepted form.
    """
    # Convert ISO to Jira's accepted "yyyy-MM-dd HH:mm" form
    try:
        dt = datetime.fromisoformat(since_iso.replace("Z", "+00:00"))
        stamp = dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        stamp = since_iso  # fall back to whatever we had; Jira will error if invalid

    upper = jql.upper()
    if "ORDER BY" in upper:
        idx = upper.index("ORDER BY")
        head = jql[:idx].rstrip()
        tail = jql[idx:]
        return f"{head} AND updated > \"{stamp}\" {tail}"
    return f"{jql.rstrip()} AND updated > \"{stamp}\""


# ---------------------------------------------------------------------------
# Single-ticket mode
# ---------------------------------------------------------------------------

def _refresh_one_ticket(
    client: JiraClient, conn, cfg: dict[str, Any], key: str, fa_field_id: str, dry_run: bool
) -> None:
    fetch_cfg = cfg.get("fetch", {})
    fields = list(fetch_cfg.get("fields", []))
    if fa_field_id not in fields:
        fields.append(fa_field_id)

    issue = client.get_issue(key, fields=fields, expand=fetch_cfg.get("expand"))
    row = normalize.normalize_issue(
        issue,
        fa_field_id=fa_field_id,
        source_filter="manual",
        fetched_at=db.utcnow_iso(),
    )
    if dry_run:
        log.info("dry-run: would upsert %s (functional_area=%s, status=%s)",
                 row["key"], row["functional_area"], row["status"])
        return
    with db.transaction(conn):
        outcome = db.upsert_ticket(conn, row)
    log.info("ticket %s: %s", key, outcome)


# ---------------------------------------------------------------------------
# Report mode
# ---------------------------------------------------------------------------

def _print_report(conn) -> None:
    r = db.report(conn)
    print("\n=== Jira Tier 0 — Distribution Report ===\n")
    print(f"Total tickets: {r['total_tickets']}")
    if r["oldest_created"]:
        print(f"Date range:    {r['oldest_created']}  →  {r['newest_created']}")
    print(f"Empty-shells:  {r['empty_shell_count']}")
    print(f"With resolution text: {r['with_resolution_text']}")
    print(f"With external URLs:   {r['with_external_urls']}")

    def _print_dist(title: str, rows: list[dict[str, Any]], key: str) -> None:
        print(f"\n--- {title} ---")
        if not rows:
            print("  (no data)")
            return
        for row in rows:
            label = row.get(key) or "(null)"
            print(f"  {label:<30} {row['n']}")

    _print_dist("By project", r["by_project"], "project")
    _print_dist("By functional_area", r["by_functional_area"], "functional_area")
    _print_dist("By status_category", r["by_status_category"], "status_category")
    _print_dist("By priority (canonical)", r["by_priority"], "priority")

    print("\n--- Recent sync runs ---")
    for run in r["recent_runs"]:
        print(
            f"  #{run['id']:<4} {run['status']:<10} {run['mode']:<12} "
            f"filter={run['filter_name']:<6} fetched={run['tickets_fetched'] or 0:<5} "
            f"new={run['tickets_new'] or 0:<5} updated={run['tickets_updated'] or 0:<5} "
            f"started={run['started_at']}"
        )
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _filter_set(cfg: dict[str, Any], chosen: str) -> list[dict[str, Any]]:
    all_filters = cfg.get("filters", [])
    if chosen == "all":
        return all_filters
    return [f for f in all_filters if f.get("name") == chosen]


def main() -> int:
    p = argparse.ArgumentParser(description="Tier 0 Jira → SQLite sync")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--backfill", action="store_true", help="Full historical pull, resumable")
    mode.add_argument("--incremental", action="store_true", help="Only tickets updated since last successful run")
    mode.add_argument("--ticket", metavar="KEY", help="Refresh a single ticket")
    mode.add_argument("--report", action="store_true", help="Print distribution report from existing SQLite (no API call)")

    p.add_argument("--filter", default="all", help="Filter name from jira.toml ('A', 'B', or 'all')")
    p.add_argument("--limit", type=int, default=None, help="Stop after N issues per filter (testing)")
    p.add_argument("--dry-run", action="store_true", help="Fetch + normalize but do not write to SQLite")
    p.add_argument("--config", type=Path, default=ROOT / "config" / "jira.toml")
    p.add_argument("--db", type=Path, default=ROOT / "raw" / "jira" / "tickets.sqlite")
    p.add_argument("--log", type=Path, default=ROOT / "raw" / "jira" / "sync.log")
    p.add_argument("--env-file", type=Path, default=ROOT / ".env")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()

    _setup_logging(args.log, args.verbose)
    if args.env_file.exists():
        load_dotenv(args.env_file)
    cfg = _load_config(args.config)

    conn = db.connect(args.db)
    db.bootstrap_schema(conn)

    if args.report:
        _print_report(conn)
        return 0

    client = _build_client(cfg)

    # Auth probe — fail fast with a clear message
    try:
        me = client.myself()
        log.info("authenticated as %s (%s)", me.get("displayName"), me.get("emailAddress"))
    except JiraError as e:
        log.error("auth probe failed: %s", e)
        return 2

    fa_field_id = _resolve_functional_area_field(client, conn, cfg)

    if args.ticket:
        _refresh_one_ticket(client, conn, cfg, args.ticket, fa_field_id, args.dry_run)
        return 0

    incremental_since = None
    if args.incremental:
        incremental_since = db.last_successful_incremental(conn)
        if not incremental_since:
            log.error(
                "no successful prior sync found — run --backfill at least once first"
            )
            return 2

    filters = _filter_set(cfg, args.filter)
    if not filters:
        log.error("no filters matched --filter=%s", args.filter)
        return 2

    totals = {"fetched": 0, "new": 0, "updated": 0, "unchanged": 0}
    for f in filters:
        c = _run_filter(
            client, conn, cfg,
            filter_def=f,
            fa_field_id=fa_field_id,
            mode="backfill" if args.backfill else "incremental",
            limit=args.limit,
            dry_run=args.dry_run,
            incremental_since=incremental_since,
        )
        for k in totals:
            totals[k] += c.get(k, 0)

    log.info(
        "ALL DONE: fetched=%d new=%d updated=%d unchanged=%d",
        totals["fetched"], totals["new"], totals["updated"], totals["unchanged"],
    )
    if not args.dry_run:
        print()
        _print_report(conn)
    return 0


if __name__ == "__main__":
    sys.exit(main())
