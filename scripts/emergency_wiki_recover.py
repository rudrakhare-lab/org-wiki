#!/usr/bin/env python3
"""Emergency wiki/ recovery — read every page from the running backend's
in-memory WikiIndex (via HTTP) and write it back to disk under wiki/.

This is a ONE-TIME recovery tool. It MUST NOT trigger a backend restart or
rebuild_index() call (which would re-read empty disk and wipe the cache).
The path:
  1. Use POST /query to instruct the agent to call wiki_grep(pattern='^type:',
     regex=true, max_matches=500) and return a JSON array of unique paths
     from the match results. The agent receives the full tool output (the
     300-char trace truncation does NOT apply to the message sent to the
     agent itself).
  2. Parse the agent's JSON paths.
  3. For each path, GET /wiki/{path} (public endpoint, reads page.full_text
     directly from in-memory).
  4. Write each file to disk.

Limitations (worth flagging in the report):
  - wiki/log.md is in WIKI_INDEX_EXCLUDE so it's NOT in the in-memory index;
    this script cannot recover it.
  - Obsidian artifacts at root (Untitled*.md, dated daily notes) are also
    filtered at build time and won't be in the index.

After dumping, the script verifies count vs /health and reports.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BACKEND = "http://localhost:8000"
REPO_ROOT = Path(__file__).resolve().parents[1]
WIKI_DIR = REPO_ROOT / "wiki"
AUTH_DB = REPO_ROOT / "raw" / "auth" / "auth.sqlite"


def get_token() -> str:
    row = sqlite3.connect(str(AUTH_DB)).execute(
        "SELECT token FROM tokens WHERE user_email='test@conwo.local' "
        "AND revoked=0 LIMIT 1"
    ).fetchone()
    if not row:
        raise SystemExit("no token in auth.sqlite — cannot authenticate")
    return row[0]


def http_json(method: str, path: str, token: str, body: dict | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    req = Request(f"{BACKEND}{path}", method=method, headers=headers, data=data)
    with urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode("utf-8"))


def health_count() -> int:
    return http_json("GET", "/health", token="").get("wiki_pages", -1)


def enumerate_paths(token: str) -> list[str]:
    """Single /query call: ask the agent to grep for every page's `type:`
    frontmatter line and return a JSON array of unique paths."""
    prompt = (
        "EMERGENCY WIKI ENUMERATION — system is in recovery mode. Do exactly "
        "this and nothing else:\n\n"
        "1. Call the wiki_grep tool ONCE with these exact arguments:\n"
        "     pattern: \"^type:\"\n"
        "     regex: true\n"
        "     max_matches: 500\n"
        "2. From the returned matches array, collect every unique value of "
        "the `path` field.\n"
        "3. Respond with ONLY a JSON object of the shape:\n"
        "     {\"paths\": [\"modules/foo.md\", \"concepts/bar.md\", ...]}\n"
        "   No prose. No commentary. No markdown fences. No **Answer:** "
        "block. No feedback footer. Just the raw JSON object.\n\n"
        "The wiki index has ~127 pages; the paths array must contain every "
        "unique path found, deduplicated."
    )
    resp = http_json("POST", "/query", token=token, body={
        "question": prompt,
        "mode": "api",
        "server": "com",
    })
    answer = resp.get("answer_text") or ""
    # Strip any preface/postscript the model added despite instructions
    start = answer.find("{")
    end = answer.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise SystemExit(f"no JSON object in answer:\n{answer[:500]}")
    blob = answer[start:end+1]
    try:
        parsed = json.loads(blob)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"JSON parse failed: {exc}\nblob: {blob[:500]}")
    paths = parsed.get("paths") or []
    if not isinstance(paths, list):
        raise SystemExit(f"paths field is not a list: {type(paths)}")
    # dedupe + sort for determinism
    return sorted(set(str(p) for p in paths))


def fetch_page(rel_path: str) -> str | None:
    """GET /wiki/{path} — public endpoint, reads page.full_text from memory."""
    try:
        # quote each path segment so spaces/specials survive
        url_path = "/" + "/".join(quote(seg, safe="") for seg in rel_path.split("/"))
        req = Request(f"{BACKEND}/wiki{url_path}", method="GET")
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("content")
    except HTTPError as exc:
        sys.stderr.write(f"  ! {rel_path}: HTTP {exc.code}\n")
        return None
    except Exception as exc:
        sys.stderr.write(f"  ! {rel_path}: {exc}\n")
        return None


def main() -> int:
    print(f"== Pre-flight ==")
    pre_count = health_count()
    print(f"  /health wiki_pages: {pre_count}")
    if pre_count <= 0:
        print("  CACHE EMPTY — aborting. The in-memory index has already been wiped.")
        return 1
    if WIKI_DIR.exists() and any(WIKI_DIR.rglob("*.md")):
        print(f"  WARNING: wiki/ already has *.md files on disk. Refusing to overwrite.")
        return 2

    print(f"\n== Enumerating paths via /query → wiki_grep ==")
    token = get_token()
    t0 = time.monotonic()
    paths = enumerate_paths(token)
    print(f"  agent returned {len(paths)} unique paths in {time.monotonic()-t0:.1f}s")

    if not paths:
        print("  no paths — aborting")
        return 3

    print(f"\n== Dumping pages via /wiki/{{path}} ==")
    written: list[str] = []
    failed: list[str] = []
    for i, rel_path in enumerate(paths, 1):
        content = fetch_page(rel_path)
        if content is None:
            failed.append(rel_path)
            continue
        target = WIKI_DIR / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written.append(rel_path)
        if i % 20 == 0:
            print(f"  ... {i}/{len(paths)}")

    print(f"\n== Post-flight ==")
    post_count = health_count()
    print(f"  /health wiki_pages: {post_count} (was {pre_count}, expect unchanged)")
    print(f"  files written to disk: {len(written)}")
    print(f"  files failed: {len(failed)}")
    if failed:
        print(f"  failed list:")
        for p in failed:
            print(f"    {p}")

    # Save the path list as a recovery manifest
    manifest = REPO_ROOT / "eval_runs" / "wiki_recovery_manifest.json"
    manifest.write_text(json.dumps({
        "pre_health_count": pre_count,
        "post_health_count": post_count,
        "enumerated": paths,
        "written": written,
        "failed": failed,
    }, indent=2))
    print(f"\n  manifest: {manifest}")

    if post_count != pre_count:
        print(f"\n  ⚠️  /health count changed during recovery — cache may have been disturbed.")
        return 4
    if len(written) != pre_count:
        print(f"\n  ⚠️  Wrote {len(written)} pages but cache had {pre_count}. "
              f"Difference likely = WIKI_INDEX_EXCLUDE (log.md) + Obsidian artifacts.")
        return 5
    print("\n  ✅ Recovery complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
