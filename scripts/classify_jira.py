"""
classify_jira_draft.py — multi-module classification of Jira tickets via Anthropic API.

Reads from raw/jira/tickets.sqlite. Writes to ticket_module_tags + ticket_classifications.

Design (per Step 3 plan):
  - Model: claude-haiku-4-5 (latest snapshot resolved by SDK alias).
  - Pricing: $1.00/M input, $5.00/M output (2026-05).
  - Prompt caching (ephemeral): static module-vocabulary block cached;
    cache_read = 10% of input rate, cache_write = 125% of input rate.
  - Tool Use: classify_tickets tool forces structured output. No free-text drift.
  - LLM returns ONLY modules[]. type/status/priority buckets + is_bug + is_resolved
    are deterministic (computed from existing tickets columns).
  - Idempotent: skips tickets already in ticket_classifications.
  - Batches: 8 tickets per call; commit per batch.
  - Modes: --full / --delta N / --reclassify.
  - --dry-run N: process only N tickets; useful for end-to-end smoke test.

Date-window note: tickets.updated_at is ISO 8601 with tz offset (e.g.
'2026-05-26T01:52:37.511+0530'). SQLite's datetime() does NOT recognize the
+HHMM suffix and returns NULL — date filters use substr(updated_at,1,10).

Slug validation: LLM-emitted module slugs are checked against the loaded
module_classification_context. Hallucinated slugs are logged and dropped.

Operational safety: this script lives in /tmp/ for review. Copy to
scripts/classify_jira.py only after approval.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import anthropic
from anthropic.types import ToolUseBlock
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# ── Constants ─────────────────────────────────────────────────────────────

CLASSIFIER_VERSION = "v1.2"  # v1.2 = G1 (textual-evidence rule) + G2 (0.65 confidence floor) atop F1 (full functional_area mapping)
MODEL = "claude-haiku-4-5"  # SDK alias; resolves to latest claude-haiku-4-5 snapshot
BATCH_SIZE = 8
MAX_TOKENS = 2048

# Empirical: 0.5-0.64 confidence band is dominated by
# functional_area-only guesses without textual evidence.
# Raised from 0.5 to 0.65 after recovery validation
# showed clean separation: real evidence-backed tags
# cluster at >=0.70, spurious guesses cluster at 0.55-0.60.
MIN_CONFIDENCE_TO_WRITE = 0.65

# Pricing (USD per 1M tokens, Claude Haiku 4.5 as of 2026-05-28)
INPUT_COST_PER_M = 1.00
OUTPUT_COST_PER_M = 5.00
CACHE_READ_FACTOR = 0.10   # cached reads = 10% of input rate
CACHE_WRITE_FACTOR = 1.25  # ephemeral cache writes = 125% of input rate

REPO = Path(__file__).resolve().parents[1] if "scripts" in str(Path(__file__).resolve()) else Path("/Users/rudrakhare/Desktop/my-wiki/org-wiki")
JIRA_DB = REPO / "raw" / "jira" / "tickets.sqlite"
MODULE_CONTEXT_PATH = REPO / "config" / "module_classification_context.json"
ERROR_LOG = Path("/tmp/classify_errors.log")

# Bucket mappings — deterministic, derived from existing columns (NOT LLM)
TYPE_BUCKETS = {
    "Task": "task",
    "Sub-task": "task",
    "Bug": "bug",
    "Story": "story",
    "Epic": "epic",
}
STATUS_BUCKETS = {
    "done": "resolved",
    "indeterminate": "in_progress",
    "new": "open",
    "undefined": "other",
}
PRIORITY_BUCKETS = {
    "P0": "p0",
    "P1": "p1",
    "P3": "p3",  # NB: no P2 in this dataset; preserved as enum slot for future
}


def type_to_bucket(t: str | None) -> str:
    return TYPE_BUCKETS.get(t or "", "other")


def status_to_bucket(s: str | None) -> str:
    return STATUS_BUCKETS.get(s or "", "other")


def priority_to_bucket(p: str | None) -> str:
    return PRIORITY_BUCKETS.get(p or "", "other")


# ── Tool schema (forces structured JSON output) ───────────────────────────

CLASSIFY_TICKETS_TOOL = {
    "name": "classify_tickets",
    "description": (
        "Submit module classifications for the batch of tickets. One entry per "
        "ticket, in the same order as the input batch. Each entry has the "
        "ticket key and a `modules` array — possibly empty if the ticket is "
        "unrelated to any product module."
    ),
    "input_schema": {
        "type": "object",
        "required": ["classifications"],
        "properties": {
            "classifications": {
                "type": "array",
                "description": "One entry per input ticket, in input order.",
                "items": {
                    "type": "object",
                    "required": ["key", "modules"],
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "Jira ticket key (e.g. 'TS-12345'). Must match input.",
                        },
                        "modules": {
                            "type": "array",
                            "description": (
                                "Modules this ticket touches. Empty array if no "
                                "product module applies (infrastructure, HR, admin, "
                                "monitoring, deployment, etc.). Approx 20% of "
                                "tickets are expected to have no module tags."
                            ),
                            "items": {
                                "type": "object",
                                "required": ["slug", "confidence", "reason"],
                                "properties": {
                                    "slug": {
                                        "type": "string",
                                        "description": "Module slug (e.g. 'meal-management'). Must match the vocabulary.",
                                    },
                                    "confidence": {
                                        "type": "number",
                                        "minimum": 0.5,
                                        "maximum": 1.0,
                                        "description": "Confidence 0.5-1.0. Below 0.5 → do not include.",
                                    },
                                    "reason": {
                                        "type": "string",
                                        "description": "Short justification tying ticket text to this module.",
                                    },
                                },
                            },
                        },
                    },
                },
            },
        },
    },
}


# ── Prompts ───────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are classifying Jira tickets into WorkInSync product modules.

Each ticket may touch ONE OR MORE modules. Multi-module tagging is expected — for
example, "Kiosk camera offline blocks meal check-in" touches BOTH floor-kiosk AND
meal-management.

Examples:
- "Kiosk camera offline blocks meal check-in"
    → floor-kiosk (0.9), meal-management (0.85)
- "MS Teams notification fails for visitor approval"
    → visitor-management (0.9), ms-teams-integration (0.85)
- "Delegated meeting room booking shows wrong organizer"
    → delegation (0.85), meeting-rooms (0.8)
- "RFID swipe at lunch fails after auth update"
    → meal-management (0.85), access-management (0.85)

Vocabulary-mismatch examples (symptom-style summaries — classify by vocabulary, not just named features):
- "walkin form back button bug"
    → visitor-management (0.85) — "walkin" is visitor-management terminology
- "kiosk reboot loop on POE port"
    → floor-kiosk (0.9) — kiosk hardware issues map to floor-kiosk
- "RFID badge sync failing across offices"
    → access-management (0.85) — RFID is access-management vocabulary

The pattern: classify by vocabulary (walkin, kiosk, RFID, digipass, meal cutoff,
booking, swipe, badge, OTP, NDA, etc.), not just by explicitly-named module features.

Confidence calibration:
- 0.9+      : ticket explicitly names the module's feature
- 0.7-0.89  : strong contextual + textual evidence
- 0.5-0.69  : weak — abstain unless textual evidence is explicit
              (the system filters these out)
- below 0.5 : DO NOT include

About 20% of tickets won't relate to any product module (infrastructure, HR,
admin, monitoring, deployment). For those, return modules: []. Do not force-fit.

components_json, labels_json, and functional_area are EVIDENCE (not gates). The
ticket text may point to additional or different modules than these signals suggest.

functional_area mappings (use as evidence to narrow plausibly relevant modules):
- WF-empexp: employee-experience (employee-facing surface, dashboards, profiles, notifications)
- WF-wis-meeting-vms: meeting-rooms + visitor-management
- WF-wis-booking: desk-management + parking-management + meal-management + meeting-rooms (booking flows)
- WF-wis-admin: admin-experience (admin tooling for IND deployment; may also overlap employee-experience for employee-facing admin pages)
- WP-admin: admin-experience (admin tooling, .com deployment)
- WP-workflows: cross-cutting workflows that may touch delegation, sso, ms-teams-integration, employee-provisioning. When WP-workflows is the functional area, look harder at the ticket text for module evidence; this area spans multiple modules.

Critical: functional_area is a routing hint, not sufficient evidence. Require
module-specific vocabulary in ticket text (summary, description, components, or
labels) before tagging any module. A ticket with functional_area=WF-empexp but
no employee-experience-specific terms in its text should return modules: [] —
functional_area alone is insufficient. The same applies to all functional areas.
Hedging language in your reason ("likely related to", "could be", "might support")
is a signal you should NOT tag — abstain instead.

Stub modules (marked ⚠️ STUB in the vocabulary) are sparsely documented. Use them
ONLY with strong textual evidence; otherwise default to better-documented modules.

Submit results via the `classify_tickets` tool. Always include EVERY ticket from
the input batch — even those with empty modules."""


def build_module_context_block(context: dict) -> str:
    """Render the (long, static, cacheable) module vocabulary as markdown."""
    lines = ["# Module classification vocabulary\n"]
    lines.append(
        f"Below are the {len(context)} WorkInSync product modules. Each entry has "
        "overview, key_features, depends_on, used_by, and stub_status.\n"
    )
    for slug, info in sorted(context.items()):
        marker = " ⚠️ STUB" if info.get("stub_status") else ""
        lines.append(f"\n## {slug}{marker}\n")
        lines.append(f"**Overview:** {info.get('overview', '')}\n")
        if info.get("key_features"):
            lines.append(f"\n**Key Features:**\n{info['key_features']}\n")
        if info.get("depends_on"):
            lines.append(f"\n**depends_on:** {', '.join(info['depends_on'])}\n")
        if info.get("used_by"):
            lines.append(f"\n**used_by:** {', '.join(info['used_by'])}\n")
    return "".join(lines)


def format_ticket_batch(tickets: list[dict]) -> str:
    """Format a batch of tickets as user-message markdown."""
    parts = ["# Ticket batch to classify\n"]
    parts.append(
        f"Classify each of the {len(tickets)} tickets below. Return ONE entry per "
        "ticket in the `classifications` array via the `classify_tickets` tool, "
        "in the same order as the tickets appear here.\n"
    )
    for i, t in enumerate(tickets, 1):
        components = ", ".join(t.get("components") or []) or "—"
        labels = ", ".join(t.get("labels") or []) or "—"
        desc = (t.get("description_text") or "")[:500].replace("\n", " ").strip() or "—"
        parts.append(
            f"\n## {i}. `{t['key']}`\n"
            f"- type: {t.get('type') or '—'} | status_category: {t.get('status_category') or '—'} "
            f"| priority: {t.get('priority') or '—'}\n"
            f"- components: {components}\n"
            f"- labels: {labels}\n"
            f"- functional_area: {t.get('functional_area') or 'unset'}\n"
            f"- summary: {t.get('summary') or '—'}\n"
            f"- description (first 500 chars): {desc}\n"
        )
    return "".join(parts)


# ── DB helpers ────────────────────────────────────────────────────────────

def open_db_rw() -> sqlite3.Connection:
    """Open the SQLite DB read-write. Backend opens with mode=ro;
    SQLite WAL handles single-writer/multi-reader concurrency."""
    conn = sqlite3.connect(JIRA_DB, isolation_level=None)  # autocommit; we use explicit BEGIN
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")  # FK columns are documentation, not enforced
    return conn


def select_tickets_for_classification(conn, mode: str, delta_days: int | None, limit: int | None) -> list[dict]:
    """Pick the tickets that need classification under the given mode."""
    if mode == "reclassify":
        where = "1=1"
        params: list = []
    elif mode == "delta":
        where = "(substr(t.updated_at,1,10) >= date('now', ?) OR c.ticket_key IS NULL)"
        params = [f"-{int(delta_days)} days"]
    else:  # full
        where = "c.ticket_key IS NULL"
        params = []

    sql = f"""
        SELECT t.key, t.type, t.status_category, t.priority, t.summary,
               t.description_text, t.components_json, t.labels_json,
               t.functional_area
        FROM tickets t
        LEFT JOIN ticket_classifications c ON c.ticket_key = t.key
        WHERE {where}
        ORDER BY t.updated_at DESC
    """
    if limit is not None:
        sql += f" LIMIT {int(limit)}"

    rows = conn.execute(sql, params).fetchall()

    out: list[dict] = []
    for row in rows:
        components = _parse_json_list(row["components_json"])
        labels = _parse_json_list(row["labels_json"])
        out.append({
            "key": row["key"],
            "type": row["type"],
            "status_category": row["status_category"],
            "priority": row["priority"],
            "summary": row["summary"],
            "description_text": row["description_text"],
            "components": components,
            "labels": labels,
            "functional_area": row["functional_area"],
        })
    return out


def select_specific_tickets(conn, keys: list[str]) -> list[dict]:
    """Select tickets matching a specific list of keys (for validation mode).
    Does NOT filter by classified_at — re-selects even already-classified tickets."""
    if not keys:
        return []
    placeholders = ",".join("?" for _ in keys)
    sql = f"""
        SELECT key, type, status_category, priority, summary,
               description_text, components_json, labels_json,
               functional_area
        FROM tickets
        WHERE key IN ({placeholders})
        ORDER BY key
    """
    rows = conn.execute(sql, keys).fetchall()
    out: list[dict] = []
    for row in rows:
        out.append({
            "key": row["key"],
            "type": row["type"],
            "status_category": row["status_category"],
            "priority": row["priority"],
            "summary": row["summary"],
            "description_text": row["description_text"],
            "components": _parse_json_list(row["components_json"]),
            "labels": _parse_json_list(row["labels_json"]),
            "functional_area": row["functional_area"],
        })
    return out


def _parse_json_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        v = json.loads(raw)
        if isinstance(v, list):
            return [str(x).strip() for x in v if x is not None]
    except json.JSONDecodeError:
        pass
    return []


def write_batch_results(
    conn,
    tickets: list[dict],
    classifications: list[dict],
    valid_slugs: set[str],
    now_iso: str,
    log: logging.Logger,
) -> tuple[int, int]:
    """Persist one batch. Returns (ticket_rows_written, module_tag_rows_written)."""
    classmap: dict[str, list] = {}
    for c in classifications:
        if isinstance(c, dict) and "key" in c:
            classmap[c["key"]] = c.get("modules") or []

    rows_written = 0
    tag_rows_written = 0
    cur = conn.cursor()
    cur.execute("BEGIN")
    try:
        for t in tickets:
            key = t["key"]
            modules = classmap.get(key, [])

            type_bucket = type_to_bucket(t.get("type"))
            status_bucket = status_to_bucket(t.get("status_category"))
            priority_bucket = priority_to_bucket(t.get("priority"))
            is_bug = 1 if t.get("type") == "Bug" else 0
            is_resolved = 1 if t.get("status_category") == "done" else 0

            cur.execute("""
                INSERT INTO ticket_classifications
                  (ticket_key, type_bucket, status_bucket, is_bug, is_resolved,
                   priority_bucket, classified_at, classifier_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticket_key) DO UPDATE SET
                  type_bucket = excluded.type_bucket,
                  status_bucket = excluded.status_bucket,
                  is_bug = excluded.is_bug,
                  is_resolved = excluded.is_resolved,
                  priority_bucket = excluded.priority_bucket,
                  classified_at = excluded.classified_at,
                  classifier_version = excluded.classifier_version
            """, (key, type_bucket, status_bucket, is_bug, is_resolved,
                  priority_bucket, now_iso, CLASSIFIER_VERSION))
            rows_written += 1

            # Wipe prior tags for this ticket (idempotent reclassify with the same version)
            cur.execute(
                "DELETE FROM ticket_module_tags WHERE ticket_key = ?",
                (key,),
            )

            # Dedup modules — LLM occasionally returns the same slug twice for a
            # single ticket. The PK (ticket_key, module_slug) would reject the
            # second INSERT and the whole batch transaction would rollback (this
            # caused the 1 error during the --full run, batch 2088). Keep the
            # first occurrence, drop duplicates.
            seen_slugs: set[str] = set()
            deduped_modules: list[dict] = []
            for mod in modules:
                slug = (mod.get("slug") or "").strip()
                if not slug:
                    continue
                if slug in seen_slugs:
                    log.debug(f"  [{key}] dedup: dropping duplicate slug {slug}")
                    continue
                seen_slugs.add(slug)
                deduped_modules.append(mod)

            for mod in deduped_modules:
                slug = (mod.get("slug") or "").strip()
                if slug not in valid_slugs:
                    log.warning(f"  [{key}] dropping unknown slug '{slug}'")
                    continue
                try:
                    conf = float(mod.get("confidence", 0))
                except (TypeError, ValueError):
                    conf = 0.0
                if conf < MIN_CONFIDENCE_TO_WRITE:
                    log.warning(f"  [{key}] dropping {slug} — confidence {conf:.2f} below {MIN_CONFIDENCE_TO_WRITE} floor")
                    continue
                reason = (mod.get("reason") or "").strip()[:500]
                cur.execute("""
                    INSERT INTO ticket_module_tags
                      (ticket_key, module_slug, confidence, reason,
                       source, classified_at, classifier_version)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (key, slug, conf, reason, "llm_batch", now_iso, CLASSIFIER_VERSION))
                tag_rows_written += 1

        cur.execute("COMMIT")
    except Exception:
        cur.execute("ROLLBACK")
        raise

    return rows_written, tag_rows_written


# ── API call ──────────────────────────────────────────────────────────────

@retry(
    retry=retry_if_exception_type(anthropic.RateLimitError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=30),
    reraise=True,
)
def call_anthropic_batch(
    client,
    module_context_text: str,
    batch: list[dict],
) -> tuple[list[dict], dict]:
    """One API call. Returns (classifications, usage_dict).

    System prompt is two text blocks: short instructions (uncached) +
    long module vocabulary (cached via ephemeral cache_control). The
    cache hit rate after the first call is ~99% for the vocab portion.
    """
    system_blocks = [
        {
            "type": "text",
            "text": SYSTEM_PROMPT,
        },
        {
            "type": "text",
            "text": module_context_text,
            "cache_control": {"type": "ephemeral"},
        },
    ]

    user_message = format_ticket_batch(batch)

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system_blocks,
        tools=[CLASSIFY_TICKETS_TOOL],
        tool_choice={"type": "tool", "name": "classify_tickets"},
        messages=[{"role": "user", "content": user_message}],
    )

    tool_block = None
    for block in response.content:
        if isinstance(block, ToolUseBlock) and block.name == "classify_tickets":
            tool_block = block
            break

    if tool_block is None:
        raise RuntimeError(f"Model did not call classify_tickets tool. stop_reason={response.stop_reason}")

    classifications = tool_block.input.get("classifications", []) if isinstance(tool_block.input, dict) else []

    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "cache_read_input_tokens": getattr(response.usage, "cache_read_input_tokens", 0) or 0,
        "cache_creation_input_tokens": getattr(response.usage, "cache_creation_input_tokens", 0) or 0,
    }
    return classifications, usage


def compute_call_cost(usage: dict) -> float:
    """USD cost of one API call."""
    return (
        usage["input_tokens"] / 1_000_000 * INPUT_COST_PER_M
        + usage["cache_read_input_tokens"] / 1_000_000 * (INPUT_COST_PER_M * CACHE_READ_FACTOR)
        + usage["cache_creation_input_tokens"] / 1_000_000 * (INPUT_COST_PER_M * CACHE_WRITE_FACTOR)
        + usage["output_tokens"] / 1_000_000 * OUTPUT_COST_PER_M
    )


# ── Cost estimate ─────────────────────────────────────────────────────────

def estimate_total_cost(n_tickets: int, context_chars: int) -> dict:
    """Pre-run estimate. Assumes 5-min ephemeral cache TTL ≈ ~80 calls before refresh."""
    batches = math.ceil(n_tickets / BATCH_SIZE)
    context_tokens = context_chars // 4  # rough chars/token heuristic

    per_batch_user_tokens = 1_000   # estimated per-batch user message tokens
    per_batch_output_tokens = 1_200  # estimated structured output tokens

    first_call = (
        context_tokens / 1_000_000 * (INPUT_COST_PER_M * CACHE_WRITE_FACTOR)
        + per_batch_user_tokens / 1_000_000 * INPUT_COST_PER_M
        + per_batch_output_tokens / 1_000_000 * OUTPUT_COST_PER_M
    )
    cached_call = (
        context_tokens / 1_000_000 * (INPUT_COST_PER_M * CACHE_READ_FACTOR)
        + per_batch_user_tokens / 1_000_000 * INPUT_COST_PER_M
        + per_batch_output_tokens / 1_000_000 * OUTPUT_COST_PER_M
    )

    cache_writes = max(1, math.ceil(batches / 80))
    cache_reads = batches - cache_writes
    total = cache_writes * first_call + cache_reads * cached_call

    return {
        "n_tickets": n_tickets,
        "batches": batches,
        "context_tokens_est": context_tokens,
        "cache_writes_est": cache_writes,
        "cache_reads_est": cache_reads,
        "first_call_cost": first_call,
        "cached_call_cost": cached_call,
        "total_estimated": total,
    }


# ── Runner ────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Classify Jira tickets into product modules")
    g = parser.add_mutually_exclusive_group(required=False)
    g.add_argument("--full", action="store_true", help="Classify all unclassified tickets")
    g.add_argument("--delta", type=int, metavar="DAYS", help="Classify tickets updated in last N days OR unclassified")
    g.add_argument("--reclassify", action="store_true", help="Force re-classification of all tickets")
    parser.add_argument("--ticket-keys-file", type=str, default=None,
                        help="Validation mode: path to file of ticket keys (one per line) to classify. "
                             "Overrides --full/--delta/--reclassify selection. Re-classifies even if already done.")
    parser.add_argument("--yes", action="store_true", help="Skip cost confirmation prompt")
    parser.add_argument("--dry-run", type=int, default=None, metavar="N",
                        help="Process only first N tickets — useful for smoke test")
    parser.add_argument("--show-prompts", action="store_true",
                        help="Print system+user prompts for first batch and exit (no API call)")
    parser.add_argument("--limit", type=int, default=None, help="Hard limit on tickets to classify")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stdout,
    )
    log = logging.getLogger("classify_jira")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        log.error("ANTHROPIC_API_KEY not set. Source .env or export it.")
        return 2

    if not MODULE_CONTEXT_PATH.exists():
        log.error(f"Module context not found: {MODULE_CONTEXT_PATH}")
        return 2

    with open(MODULE_CONTEXT_PATH) as fh:
        module_context = json.load(fh)
    module_context_text = build_module_context_block(module_context)
    valid_slugs = set(module_context.keys())
    log.info(
        f"Loaded module context: {len(module_context)} modules, "
        f"{len(module_context_text)} chars (~{len(module_context_text)//4} tokens)"
    )

    conn = open_db_rw()

    if args.ticket_keys_file:
        keys_path = Path(args.ticket_keys_file)
        if not keys_path.exists():
            log.error(f"Keys file not found: {keys_path}")
            return 2
        keys = [line.strip() for line in keys_path.read_text().splitlines() if line.strip()]
        log.info(f"Validation mode: loaded {len(keys)} keys from {keys_path}")
        tickets = select_specific_tickets(conn, keys)
        missing = set(keys) - {t["key"] for t in tickets}
        if missing:
            log.warning(f"  {len(missing)} keys not found in tickets table: {sorted(missing)[:5]}...")
        mode = "validation"
    else:
        if not (args.full or args.delta is not None or args.reclassify):
            parser.error("Must specify one of --full, --delta N, --reclassify, or --ticket-keys-file")
        mode = "full" if args.full else ("delta" if args.delta is not None else "reclassify")
        tickets = select_tickets_for_classification(conn, mode, delta_days=args.delta, limit=args.limit)

    if args.dry_run is not None:
        tickets = tickets[: args.dry_run]
    n = len(tickets)

    if n == 0:
        log.info("No tickets to classify. Done.")
        return 0

    log.info(f"Selected {n} tickets for classification (mode={mode}).")

    est = estimate_total_cost(n, len(module_context_text))
    print()
    print("─" * 64)
    print(f"PRE-RUN ESTIMATE")
    print(f"  Tickets to classify : {est['n_tickets']:,}")
    print(f"  Batches (size {BATCH_SIZE}) : {est['batches']:,}")
    print(f"  Module context size : ~{est['context_tokens_est']:,} tokens (cached)")
    print(f"  Cache writes (~80 calls/TTL) : {est['cache_writes_est']}")
    print(f"  Cache reads : {est['cache_reads_est']:,}")
    print(f"  First call cost : ${est['first_call_cost']:.4f}")
    print(f"  Cached call cost : ${est['cached_call_cost']:.4f}")
    print(f"  TOTAL ESTIMATED COST : ${est['total_estimated']:.2f}")
    print("─" * 64)
    print()

    if args.show_prompts:
        first_batch = tickets[:BATCH_SIZE]
        print("=" * 64)
        print("SYSTEM PROMPT — block 1 (uncached, ~250 tokens)")
        print("=" * 64)
        print(SYSTEM_PROMPT)
        print()
        print("=" * 64)
        print(f"SYSTEM PROMPT — block 2 (cached via ephemeral cache_control, "
              f"~{len(module_context_text)//4} tokens)")
        print("=" * 64)
        print(module_context_text[:2000] + "\n…" if len(module_context_text) > 2000 else module_context_text)
        print()
        print("=" * 64)
        print(f"USER MESSAGE — first batch ({len(first_batch)} tickets)")
        print("=" * 64)
        print(format_ticket_batch(first_batch))
        print()
        print("=" * 64)
        print("TOOL SCHEMA")
        print("=" * 64)
        print(json.dumps(CLASSIFY_TICKETS_TOOL, indent=2))
        return 0

    if not args.yes:
        resp = input(f"Will classify {n} tickets. Estimated cost: ${est['total_estimated']:.2f} "
                     "(with prompt caching enabled). Continue? [y/N]: ").strip().lower()
        if resp != "y":
            log.info("Aborted by user.")
            return 0

    client = anthropic.Anthropic(api_key=api_key)
    total_cost = 0.0
    total_processed = 0
    total_tags = 0
    total_errors = 0
    start = time.time()

    for batch_start in range(0, n, BATCH_SIZE):
        batch = tickets[batch_start: batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        batch_total = est["batches"]
        t0 = time.time()
        try:
            classifications, usage = call_anthropic_batch(client, module_context_text, batch)
            batch_cost = compute_call_cost(usage)
            total_cost += batch_cost

            now_iso = datetime.now(timezone.utc).isoformat()
            rows_written, tag_rows = write_batch_results(
                conn, batch, classifications, valid_slugs, now_iso, log
            )
            total_processed += rows_written
            total_tags += tag_rows

            log.info(
                f"[batch {batch_num}/{batch_total}] {rows_written} tickets, {tag_rows} tags, "
                f"{time.time() - t0:.1f}s — cost ${batch_cost:.4f}, "
                f"total ${total_cost:.2f}, "
                f"cache_read={usage['cache_read_input_tokens']}, "
                f"cache_write={usage['cache_creation_input_tokens']}, "
                f"in={usage['input_tokens']}, out={usage['output_tokens']}"
            )

            # In dry-run mode, also print classifications inline for review
            if args.dry_run is not None:
                print()
                print(f"=== DRY-RUN classifications (batch {batch_num}) ===")
                print(json.dumps(classifications, indent=2, ensure_ascii=False))
                print()

        except Exception as exc:
            total_errors += 1
            log.error(f"[batch {batch_num}/{batch_total}] ERROR: {type(exc).__name__}: {exc}")
            with open(ERROR_LOG, "a") as fh:
                fh.write(
                    f"{datetime.now(timezone.utc).isoformat()} batch={batch_num} "
                    f"keys={[t['key'] for t in batch]} error={type(exc).__name__}: {exc!r}\n"
                )

    conn.close()
    elapsed_min = (time.time() - start) / 60
    print()
    print("=" * 64)
    print(f"SUMMARY")
    print(f"  Tickets classified : {total_processed}")
    print(f"  Module tags written : {total_tags}")
    print(f"  Errors : {total_errors} (see {ERROR_LOG})")
    print(f"  Total cost : ${total_cost:.2f}")
    print(f"  Total time : {elapsed_min:.1f} minutes")
    print("=" * 64)
    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
