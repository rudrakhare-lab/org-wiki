# Retrieval Accuracy — Phase 1 (Ranking) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Jira v2 final ranking + confidence use all three signals it already computes (reranker + recency + fusion), and let the reranker judge on the relevant slice of a ticket instead of a truncated head.

**Architecture:** Insert a `blend` step between `rerank` and `gate` in the v2 pipeline. Blend a min-max-normalized fusion score, the recency `timeline_score`, and the sigmoid reranker score into one ranking score (all in [0,1], weights sum to 1.0). The gate orders + tiers confidence on the blend but keeps the *abstain* decision on the reranker score (semantic floor). Separately, widen the reranker read-window and feed it the query-relevant comment slice. Thread the gate's retrieval confidence onto the bundle so the orchestrator can cap the answer confidence by it (stricter-of).

**Tech Stack:** Python 3, psycopg, sentence-transformers CrossEncoder (ms-marco-MiniLM-L-6-v2), pytest.

## Global Constraints

- **Accuracy over latency** — never trade correctness for speed; extra compute (wider rerank window) is acceptable.
- **Every risky change behind a cheap env kill-switch, defaulting to the new behavior.** Phase 1 switches: `CONWO_RANK_BLEND` (default on), `CONWO_RERANK_SMART_WINDOW` (default on). Blend weights: `CONWO_RANK_W_RERANK`=0.5, `CONWO_RANK_W_TIMELINE`=0.3, `CONWO_RANK_W_FUSED`=0.2. Rerank window: `CONWO_RERANK_MAX_LEN`=512.
- **Golden-eval gate:** run `tests/retrieval/v2/eval/run_eval.py` before and after (needs a live DB + `GOOGLE_GENAI_API_KEY` — run in the app pod or a local checkout pointed at the DB). Ship only if recall@10 improves or holds and abstention rate does not worsen.
- **Operational safety (CLAUDE.md §1):** never write a `.py` in the repo tree while the backend runs with `--reload`; throwaway scripts go in `/tmp/`. Use `python3`, not `python`.
- **Confidence tiers:** `High > Medium > Low > Abstain/Unknown`.

---

### Task 1: `blend.py` — pure blend function

**Files:**
- Create: `backend/retrieval/v2/blend.py`
- Test: `tests/retrieval/v2/test_blend.py`

**Interfaces:**
- Produces: `blend_scores(scored: list[tuple[dict, float]]) -> list[tuple[dict, float]]` — takes reranker output `[(candidate, rerank_prob), ...]`, stashes `reranker_score` and `blend_score` on each candidate dict, returns the list re-sorted by blend descending. Also `enabled() -> bool` and `weights() -> tuple[float, float, float]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/retrieval/v2/test_blend.py
import os
from backend.retrieval.v2.blend import blend_scores, enabled, weights


def _cand(key, fused, timeline):
    return {"key": key, "fused_score": fused, "timeline_score": timeline}


def test_blend_lets_recency_and_fusion_reorder_equal_rerank(monkeypatch):
    monkeypatch.delenv("CONWO_RANK_BLEND", raising=False)
    # Two candidates with identical rerank prob; B is far more recent + higher fusion.
    a = _cand("A", fused=0.01, timeline=0.10)
    b = _cand("B", fused=0.05, timeline=0.95)
    out = blend_scores([(a, 0.6), (b, 0.6)])
    assert [c["key"] for c, _ in out] == ["B", "A"]      # recency+fusion breaks the tie
    assert all("blend_score" in c and "reranker_score" in c for c, _ in out)


def test_blend_scores_stay_in_unit_range(monkeypatch):
    monkeypatch.delenv("CONWO_RANK_BLEND", raising=False)
    out = blend_scores([(_cand("A", 0.05, 1.0), 1.0), (_cand("B", 0.0, 0.05), 0.0)])
    for _, s in out:
        assert 0.0 <= s <= 1.0


def test_missing_fields_default_zero_no_crash(monkeypatch):
    monkeypatch.delenv("CONWO_RANK_BLEND", raising=False)
    out = blend_scores([({"key": "A"}, 0.7)])           # no fused_score / timeline_score
    assert out[0][0]["reranker_score"] == 0.7


def test_disabled_is_identity_order(monkeypatch):
    monkeypatch.setenv("CONWO_RANK_BLEND", "off")
    a = _cand("A", fused=0.9, timeline=0.9)             # would win under blend
    b = _cand("B", fused=0.0, timeline=0.0)
    out = blend_scores([(b, 0.9), (a, 0.1)])            # but B has higher rerank
    assert [c["key"] for c, _ in out] == ["B", "A"]
    assert out[0][0]["blend_score"] == 0.9              # identity: blend == rerank


def test_weights_env_override(monkeypatch):
    monkeypatch.setenv("CONWO_RANK_W_RERANK", "1.0")
    monkeypatch.setenv("CONWO_RANK_W_TIMELINE", "0.0")
    monkeypatch.setenv("CONWO_RANK_W_FUSED", "0.0")
    assert weights() == (1.0, 0.0, 0.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/retrieval/v2/test_blend.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.retrieval.v2.blend'`

- [ ] **Step 3: Write the implementation**

```python
# backend/retrieval/v2/blend.py
"""Blend rerank + recency + fusion into one ranking score (spec A1).

Before this, the reranker score alone decided ordering + confidence, and the
RRF `fused_score` and recency `timeline_score` (both computed upstream) were
discarded after admitting candidates. This folds all three back in.

All three inputs are in [0,1] (reranker is sigmoid-calibrated; timeline_score
is a 0..1 decay×status weight; fused_score is min-max normalized within the
candidate set here), and the weights sum to 1.0, so the blended score is in
[0,1] and gate.py's thresholds stay meaningful.
"""
from __future__ import annotations
import os


def _w(env: str, default: float) -> float:
    try:
        return float(os.getenv(env, str(default)))
    except (TypeError, ValueError):
        return default


def enabled() -> bool:
    return os.getenv("CONWO_RANK_BLEND", "on").strip().lower() != "off"


def weights() -> tuple[float, float, float]:
    return (
        _w("CONWO_RANK_W_RERANK", 0.5),
        _w("CONWO_RANK_W_TIMELINE", 0.3),
        _w("CONWO_RANK_W_FUSED", 0.2),
    )


def blend_scores(scored: list[tuple[dict, float]]) -> list[tuple[dict, float]]:
    """Attach `reranker_score` + `blend_score` to each candidate and return the
    list re-sorted by blend descending.

    `scored` is the reranker output: [(candidate_dict, rerank_prob), ...].
    When disabled (CONWO_RANK_BLEND=off), blend_score == rerank_prob (identity),
    but reranker_score is still stashed so the gate can attach it uniformly.
    """
    if not scored:
        return []
    w_r, w_t, w_f = weights()
    on = enabled()
    fused_vals = [float(c.get("fused_score") or 0.0) for c, _ in scored]
    lo, hi = min(fused_vals), max(fused_vals)
    span = hi - lo
    out: list[tuple[dict, float]] = []
    for c, rr in scored:
        c["reranker_score"] = rr
        if on:
            f = float(c.get("fused_score") or 0.0)
            nf = (f - lo) / span if span > 0 else 0.0
            ts = float(c.get("timeline_score") or 0.0)
            b = w_r * rr + w_t * ts + w_f * nf
        else:
            b = rr
        c["blend_score"] = b
        out.append((c, b))
    out.sort(key=lambda x: x[1], reverse=True)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/retrieval/v2/test_blend.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/retrieval/v2/blend.py tests/retrieval/v2/test_blend.py
git commit -m "feat(retrieval-v2): blend rerank+recency+fusion ranking score (A1)"
```

---

### Task 2: Wire blend into the pipeline + gate scores on blend, abstains on reranker

**Files:**
- Modify: `backend/retrieval/v2/pipeline.py:43-49`
- Modify: `backend/retrieval/v2/gate.py:68-99`
- Test: `tests/retrieval/v2/test_gate.py` (create if absent)

**Interfaces:**
- Consumes: `blend_scores` (Task 1).
- Produces: gate tickets now carry `reranker_score` (true rerank prob) **and** `rank_score` (the blend value used for ordering). `RetrievalResult.diagnostics["top_score"]` remains the top blend score.

- [ ] **Step 1: Write the failing test**

```python
# tests/retrieval/v2/test_gate.py
from backend.retrieval.v2.gate import apply


def _c(key, fa=None, bucket="latest"):
    return {"key": key, "functional_area": fa, "bucket": bucket}


def test_abstain_uses_reranker_not_blend():
    # Top candidate is semantically weak (reranker 0.30 < 0.5 abstain) but its
    # blend was boosted to 0.72 by recency+fusion. Must STILL abstain — recency
    # cannot rescue an irrelevant ticket past the semantic floor.
    weak = {**_c("A"), "reranker_score": 0.30}
    scored = [(weak, 0.72)]
    r = apply(scored)
    assert r.abstain is True


def test_confidence_tier_uses_blend_score():
    # Reranker 0.55 (would be Medium band alone) but blend 0.80 >= HIGH; with
    # agreeing top-3 → High.
    top3 = [
        ({**_c("A", fa="WF-empexp"), "reranker_score": 0.55}, 0.80),
        ({**_c("B", fa="WF-empexp"), "reranker_score": 0.52}, 0.75),
        ({**_c("C", fa="WF-empexp"), "reranker_score": 0.50}, 0.72),
    ]
    r = apply(top3)
    assert r.abstain is False and r.confidence == "High"


def test_gate_preserves_true_reranker_score_and_adds_rank_score():
    c = {**_c("A"), "reranker_score": 0.61}
    r = apply([(c, 0.80)])
    t = r.tickets[0]
    assert t["reranker_score"] == 0.61     # true reranker preserved, not clobbered by blend
    assert t["rank_score"] == 0.80          # blend value exposed for downstream/debug
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/retrieval/v2/test_gate.py -v`
Expected: FAIL — `test_abstain_uses_reranker_not_blend` fails (current gate abstains on `scored[0][1]`, the blend 0.72 ≥ 0.5, so it does NOT abstain); `test_gate_preserves_true_reranker_score...` fails (current gate sets `reranker_score` to the tuple score 0.80).

- [ ] **Step 3: Edit `gate.py`**

Replace the block at `gate.py:77` (`top_score = scored[0][1]`) and the ticket-build loop at `gate.py:95-99`.

Change the top-score extraction (after the empty-guard, ~line 77) to read both the blend score and the true reranker score:

```python
    top_blend = scored[0][1]
    top_rerank = float(scored[0][0].get("reranker_score", top_blend))
    diag = {
        "top_score": top_blend,
        "top_reranker_score": top_rerank,
        "candidate_count": len(scored),
        "bucket_counts": timeline.bucket_counts(c for c, _ in scored),
    }
```

Change the abstain check (was `if top_score < abstain_t:`) to gate on the reranker (semantic floor):

```python
    if top_rerank < abstain_t:
```

Change the two tiering comparisons that used `top_score` to use `top_blend`:

```python
    elif top_blend >= high_t:
```
(the `else` branch comment becomes `# abstain_t <= top_blend < high_t`)

Replace the ticket-build loop (`gate.py:96-99`) so it preserves the true reranker score and exposes the blend as `rank_score`:

```python
    tickets = []
    for c, s in scored[:10]:
        out = {**c}
        out.setdefault("reranker_score", s)   # blend stashes true reranker; direct callers fall back to s
        out["rank_score"] = s
        tickets.append(out)
```

- [ ] **Step 4: Edit `pipeline.py`**

Add the import near the other v2 imports (after line 9):

```python
from backend.retrieval.v2.blend import blend_scores
```

Change the search body (`pipeline.py:47-49`) from:

```python
        candidates = expand_links(conn, candidates)
        scored = rerank_score(question, candidates)
        return gate_apply(scored)
```

to:

```python
        candidates = expand_links(conn, candidates)
        scored = rerank_score(question, candidates)
        scored = blend_scores(scored)          # A1: fold recency+fusion into ranking
        return gate_apply(scored)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/retrieval/v2/test_gate.py tests/retrieval/v2/test_blend.py -v`
Expected: PASS (all)

- [ ] **Step 6: Run the existing v2 suite for regressions**

Run: `python3 -m pytest tests/retrieval/v2 -q`
Expected: PASS (no regressions in rerank/gate/pipeline tests). If a pre-existing gate test asserted `reranker_score == tuple_score`, update it to the new `rank_score` semantics.

- [ ] **Step 7: Commit**

```bash
git add backend/retrieval/v2/pipeline.py backend/retrieval/v2/gate.py tests/retrieval/v2/test_gate.py
git commit -m "feat(retrieval-v2): gate orders+tiers on blend, abstains on reranker floor (A1)"
```

---

### Task 3: Smart rerank read-window (A2)

**Files:**
- Modify: `backend/retrieval/v2/rerank.py:30-37,56-106`
- Test: `tests/retrieval/v2/test_rerank.py` (add cases; create if absent)

**Interfaces:**
- Produces: `_doc_text(c: dict, query: str) -> str` (signature gains `query`); `score()` passes the query through. Behavior gated by `CONWO_RERANK_SMART_WINDOW` (default on) and `CONWO_RERANK_MAX_LEN` (default 512).

- [ ] **Step 1: Write the failing test**

```python
# tests/retrieval/v2/test_rerank.py  (add to existing file)
import re
from backend.retrieval.v2 import rerank


def test_smart_window_selects_query_relevant_comment(monkeypatch):
    monkeypatch.delenv("CONWO_RERANK_SMART_WINDOW", raising=False)
    # The relevant line is buried well past the first 300 chars of comments.
    filler = "unrelated chatter about lunch. " * 20            # ~600 chars
    comment = filler + "The kioskRequireOTPBeforeRegister flag controls guard OTP."
    c = {"summary": "Guard app", "description_text": "desc", "comments_text": comment}
    out = rerank._doc_text(c, "how does guard OTP registration work")
    assert "kioskRequireOTPBeforeRegister" in out              # buried relevant line surfaced


def test_smart_window_off_falls_back_to_head(monkeypatch):
    monkeypatch.setenv("CONWO_RERANK_SMART_WINDOW", "off")
    c = {"summary": "s", "description_text": "d", "comments_text": "x" * 5000}
    out = rerank._doc_text(c, "anything")
    assert len(out) <= 1013                                    # legacy fixed-budget layout


def test_max_len_default_is_512(monkeypatch):
    monkeypatch.delenv("CONWO_RERANK_MAX_LEN", raising=False)
    assert rerank._max_len() == 512
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/retrieval/v2/test_rerank.py -k "smart_window or max_len" -v`
Expected: FAIL — `_doc_text()` takes 1 arg (not 2); `_max_len` undefined.

- [ ] **Step 3: Edit `rerank.py`**

Add near the top (after `MODEL_DIR`, ~line 30):

```python
import re

def _max_len() -> int:
    try:
        return int(os.getenv("CONWO_RERANK_MAX_LEN", "512"))
    except (TypeError, ValueError):
        return 512

def _smart_window() -> bool:
    return os.getenv("CONWO_RERANK_SMART_WINDOW", "on").strip().lower() != "off"
```

Change `_load_model` (line 37) to use the env window:

```python
    return CrossEncoder(MODEL_DIR, max_length=_max_len())
```

Add smart-window budgets alongside the legacy ones (after `_COMMENTS_MAX`, ~line 58):

```python
# Smart-window budgets (larger — we now target the 512-token window, ~2000 chars).
_SW_SUMMARY_MAX  = 300
_SW_DESC_MAX     = 900
_SW_COMMENTS_MAX = 700
```

Add the query-relevant comment selector (before `_doc_text`):

```python
def _relevant_comment_slice(comments: str, query: str, budget: int) -> str:
    """Pick the comment lines most lexically-overlapping the query, up to
    `budget` chars — so a relevant line buried deep in a long thread still
    reaches the reranker instead of being truncated away."""
    comments = (comments or "").strip()
    if not comments:
        return ""
    q_tokens = set(re.findall(r"[a-z0-9]{3,}", query.lower()))
    lines = [ln.strip() for ln in comments.splitlines() if ln.strip()]
    if not q_tokens or not lines:
        return comments[:budget]
    ranked = sorted(
        lines,
        key=lambda ln: len(q_tokens & set(re.findall(r"[a-z0-9]{3,}", ln.lower()))),
        reverse=True,
    )
    out, total = [], 0
    for ln in ranked:
        if total + len(ln) + 1 > budget:
            continue
        out.append(ln)
        total += len(ln) + 1
    return "\n".join(out) if out else comments[:budget]
```

Change `_doc_text` (line 73) to take `query` and branch on the switch:

```python
def _doc_text(c: dict, query: str) -> str:
    """Build the reranker document for candidate `c` relative to `query`.

    Smart-window (default): larger field budgets + the query-relevant comment
    slice, targeting the 512-token window. Legacy (switch off): the original
    fixed 1013-char head layout.
    """
    if not _smart_window():
        summary  = (c.get("summary")          or "").strip()[:_SUMMARY_MAX]
        desc     = (c.get("description_text") or "").strip()[:_DESC_MAX]
        comments = (c.get("comments_text")    or "").strip()[:_COMMENTS_MAX]
        parts = []
        if summary:  parts.append(summary)
        if desc:     parts.append(desc)
        if comments: parts.append(f"[comments] {comments}")
        return "\n".join(parts)

    summary  = (c.get("summary")          or "").strip()[:_SW_SUMMARY_MAX]
    desc     = (c.get("description_text") or "").strip()[:_SW_DESC_MAX]
    comments = _relevant_comment_slice(c.get("comments_text") or "", query, _SW_COMMENTS_MAX)
    parts = []
    if summary:  parts.append(summary)
    if desc:     parts.append(desc)
    if comments: parts.append(f"[comments] {comments}")
    return "\n".join(parts)
```

Change the pair construction in `score()` (line 98) to pass the query:

```python
    pairs = [(query, _doc_text(c, query)) for c in candidates]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/retrieval/v2/test_rerank.py -v`
Expected: PASS (including the existing sigmoid/probability regression test — unchanged).

- [ ] **Step 5: Commit**

```bash
git add backend/retrieval/v2/rerank.py tests/retrieval/v2/test_rerank.py
git commit -m "feat(retrieval-v2): smart rerank window — query-relevant slice + 512 tokens (A2)"
```

---

### Task 4: Thread retrieval confidence to the bundle + cap answer confidence (stricter-of)

**Files:**
- Modify: `backend/jira_retriever.py:139-147`
- Modify: `backend/orchestrator.py` (add `_cap_confidence_by_retrieval`; call it in both answer paths after `_extract_confidence`/`_verify_and_gate`)
- Test: `tests/test_orchestrator_confidence_cap.py` (create)

**Interfaces:**
- Consumes: `bundle.seed_jira` is the full `_v2_search` dict.
- Produces: `_v2_search` dict gains `"confidence"` and `"abstain"`. `orchestrator._cap_confidence_by_retrieval(confidence: str, bundle) -> str`.

**Scope note:** Phase 1 caps only when retrieval returned a concrete tier (`High`/`Medium`/`Low`) lower than the answer's. The Abstain / missing-source case is deliberately left to Phase 2 (B3 — honest degradation), so this task stays bounded.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_orchestrator_confidence_cap.py
from types import SimpleNamespace
from backend.orchestrator import _cap_confidence_by_retrieval


def _bundle(retrieval_conf):
    return SimpleNamespace(seed_jira={"confidence": retrieval_conf} if retrieval_conf else {})


def test_caps_answer_to_lower_retrieval_confidence():
    assert _cap_confidence_by_retrieval("High", _bundle("Medium")) == "Medium"


def test_does_not_raise_confidence():
    assert _cap_confidence_by_retrieval("Low", _bundle("High")) == "Low"


def test_abstain_and_missing_are_left_to_phase2():
    assert _cap_confidence_by_retrieval("High", _bundle("Abstain")) == "High"
    assert _cap_confidence_by_retrieval("High", _bundle(None)) == "High"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_orchestrator_confidence_cap.py -v`
Expected: FAIL — `ImportError: cannot import name '_cap_confidence_by_retrieval'`.

- [ ] **Step 3: Edit `jira_retriever.py`**

In `_v2_search`, add the retrieval confidence to the returned dict (`jira_retriever.py:139`):

```python
    return {
        "keywords": extract_keywords(question),
        "confidence": result.confidence,        # A1: thread retrieval confidence to the bundle
        "abstain": result.abstain,
        "markdown": _render_v2_markdown(
            tickets, confidence=result.confidence, message=result.message,
            include_stale=include_stale,
        ),
        "rows": tickets,
        "buckets": buckets,
    }
```

- [ ] **Step 4: Edit `orchestrator.py`**

Add the helper near `_extract_confidence` (~line 588):

```python
_CONF_RANK = {"High": 3, "Medium": 2, "Low": 1, "Abstain": 0, "Unknown": 0}


def _cap_confidence_by_retrieval(confidence: str, bundle) -> str:
    """Cap the answer confidence by the Jira retrieval confidence (stricter-of).

    Phase 1: only when retrieval returned a concrete tier (High/Medium/Low)
    that is LOWER than the answer's. Abstain / missing retrieval confidence is
    handled by Phase 2 (B3 honest degradation), not here.
    """
    rc = (getattr(bundle, "seed_jira", None) or {}).get("confidence")
    if rc in ("High", "Medium", "Low") and _CONF_RANK.get(confidence, 0) > _CONF_RANK[rc]:
        return rc
    return confidence
```

Call it in the api-mode path, right after `_verify_and_gate` (~line 306):

```python
        raw_answer, confidence, _cite_report = _verify_and_gate(
            raw_answer, confidence, bundle, deep_result.tool_trace)
        confidence = _cap_confidence_by_retrieval(confidence, bundle)
```

And in the other answer path, right after its `confidence = _extract_confidence(raw_answer)` (~line 428):

```python
    confidence = _extract_confidence(raw_answer)
    confidence = _cap_confidence_by_retrieval(confidence, bundle)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_orchestrator_confidence_cap.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Regression check on orchestrator + citation tests**

Run: `python3 -m pytest tests/test_citation_check.py tests/test_orchestrator_confidence_cap.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/jira_retriever.py backend/orchestrator.py tests/test_orchestrator_confidence_cap.py
git commit -m "feat(retrieval-v2): cap answer confidence by Jira retrieval confidence (A1 stricter-of)"
```

---

### Task 5: Golden-eval gate + weight tuning

**Files:**
- Modify (if needed): `tests/retrieval/v2/eval/queries.json` (add cases that exercise recency/fusion reordering)
- No production code changes.

**This task is the accuracy gate.** It runs in an environment with a live DB + `GOOGLE_GENAI_API_KEY` (the app pod, or a local checkout pointed at the DB). It is NOT a mockable unit test.

- [ ] **Step 1: Capture the BEFORE baseline (on `main` / pre-Phase-1 code)**

Run (in the pod or DB-connected checkout):
```bash
CONWO_RANK_BLEND=off CONWO_RERANK_SMART_WINDOW=off \
  python3 tests/retrieval/v2/eval/run_eval.py | tee /tmp/eval_before.txt
```
Record the `recall@10` and `abstention_rate` lines.

- [ ] **Step 2: Capture the AFTER result (Phase 1 defaults on)**

Run:
```bash
python3 tests/retrieval/v2/eval/run_eval.py | tee /tmp/eval_after.txt
```
Record `recall@10` and `abstention_rate`.

- [ ] **Step 3: Compare and gate**

Expected: `recall@10` (after) ≥ (before) AND `abstention_rate` (after) not materially worse. If recall regressed, tune the weights and re-run:
```bash
CONWO_RANK_W_RERANK=0.6 CONWO_RANK_W_TIMELINE=0.25 CONWO_RANK_W_FUSED=0.15 \
  python3 tests/retrieval/v2/eval/run_eval.py
```
Sweep a small grid (e.g. rerank ∈ {0.5,0.6,0.7}, remainder split timeline:fused ≈ 60:40) and pick the weights with the best recall@10 without raising abstention. Set those as the committed env defaults for prod (Facets env), not code changes.

- [ ] **Step 4: Add discriminating eval cases (if the set is too small to detect movement)**

If the current `queries.json` doesn't include a case where the correct ticket is recent-but-not-top-lexical (the scenario the blend fixes), add 2–3 such cases with `expected_any_of` keys, so future regressions are caught.

- [ ] **Step 5: Record the result**

Append the before/after numbers and chosen weights to the plan's PR description (or `docs/reports/`). No commit of secrets or DB data.

---

## Self-Review

**Spec coverage (Phase 1 slice of the spec):**
- A1 blend (order + confidence) → Tasks 1, 2. ✅
- A1 confidence combination (stricter-of) → Task 4. ✅
- A2 smart rerank window (slice + larger limit) → Task 3. ✅
- Golden-eval gate → Task 5. ✅
- Per-change kill-switches → `CONWO_RANK_BLEND`, `CONWO_RERANK_SMART_WINDOW` (Tasks 1–3). ✅
- (B*, C*, D* are later phases — out of scope for this plan, by design.)

**Placeholder scan:** none — every code step has full code.

**Type consistency:** `blend_scores` signature identical across Tasks 1/2; gate exposes `reranker_score` + `rank_score` consistently; `_doc_text(c, query)` updated at its one call site in `score()`; `_cap_confidence_by_retrieval(confidence, bundle)` consistent between definition and both call sites; `seed_jira["confidence"]` produced in Task 4 Step 3 and read in Task 4 Step 4.

**Note on abstain refinement:** the plan intentionally gates abstain on `reranker_score` (semantic floor) while ordering/tiering on the blend — discovered while reading `gate.py`; prevents recency/fusion from rescuing an irrelevant top hit. Captured in Task 2 tests.
