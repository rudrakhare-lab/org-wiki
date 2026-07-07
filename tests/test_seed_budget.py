"""Seed budget — protects per-intent, evicts rank-ordered, always trim-notes."""
from backend import seed_budget as sb


# NOTE: the task brief's fixture used chars_per=400, but at that size the
# over-budget fixtures total only ~4.0–4.5k est. tokens — UNDER the specified
# SEED_BUDGET_TOKENS=6000 interface constant, so nothing would ever be evicted
# and the eviction tests would fail (verified against the brief's own reference
# implementation). Bumped to 1000 so the over-budget cases genuinely exceed the
# budget and invariants (a)/(b)/(c) are exercised non-vacuously.
def _block(name, n_items, chars_per=1000):
    items = [(f"{name}-item-{i}", "x" * chars_per, "wiki_read_page")
             for i in range(n_items)]
    return sb.SeedBlock(name=name, priority=0,
                        text="\n".join(t for _, t, _ in items), evictable=items)


def test_under_budget_passes_through_untouched():
    blocks = [_block("wiki_direct", 2), _block("jira_latest", 2)]
    text, trimmed = sb.apply_budget(blocks, "GENERAL")
    assert trimmed == [] and "Trimmed" not in text


def test_over_budget_evicts_wiki_related_first_protects_config():
    blocks = [_block("wiki_related", 30), _block("config_evidence", 5),
              _block("jira_latest", 10)]
    text, trimmed = sb.apply_budget(blocks, "CONFIGURATION")
    assert trimmed                                          # something evicted
    # CONFIGURATION evicts wiki_related before jira; config block is protected
    assert all(t.startswith("wiki_related") for t in trimmed) \
        or (any(t.startswith("wiki_related") for t in trimmed)
            and not any(t.startswith("config_evidence") for t in trimmed))
    assert "## Trimmed (fetch on demand)" in text


def test_jira_protected_wiki_fully_drained_before_any_jira_evicted():
    """The hard requirement: for CONFIGURATION, no jira_* item may be evicted
    while any non-KEEP_MIN wiki item still survives. Fixture is sized so wiki
    alone CANNOT get under budget (both wiki blocks drained to KEEP_MIN still
    leave the total over), forcing eviction to reach jira — and asserting it
    only reaches jira_latest, never before wiki is exhausted, and never
    config_evidence."""
    blocks = [
        _block("wiki_related", 8, chars_per=2000),   # 8 → drains to 3
        _block("wiki_direct", 8, chars_per=2000),    # 8 → drains to 3
        _block("jira_latest", 8, chars_per=2000),
        # config_evidence is atomic (evictable=[]) in production — model that.
        sb.SeedBlock("config_evidence", 0, "c" * 8000, []),
    ]
    _, trimmed = sb.apply_budget(blocks, "CONFIGURATION")
    evicted = [t.split(" — ")[0] for t in trimmed]
    # config never evicted
    assert not any(e.startswith("config_evidence") for e in evicted)
    # if any jira_latest was evicted, BOTH wiki blocks must be fully drained to
    # KEEP_MIN first (5 evicted each = 8 - 3)
    if any(e.startswith("jira_latest") for e in evicted):
        assert sum(e.startswith("wiki_related") for e in evicted) == 8 - sb.KEEP_MIN
        assert sum(e.startswith("wiki_direct") for e in evicted) == 8 - sb.KEEP_MIN


def test_eviction_leaves_no_orphaned_separators():
    """Regression: eviction rebuilds block text from survivors (rerender), so
    the rendered seed must never contain doubled `\\n\\n---\\n\\n` runs."""
    import re
    blocks = [_block("wiki_related", 40, chars_per=1000)]
    text, trimmed = sb.apply_budget(blocks, "GENERAL")
    assert trimmed  # eviction happened
    assert not re.search(r"(?:\n\n---\n\n){2,}", text), "orphaned separator run"


def test_trim_note_lists_every_evicted_id_with_fetch_hint():
    blocks = [_block("wiki_related", 40)]
    text, trimmed = sb.apply_budget(blocks, "GENERAL")
    assert trimmed
    for entry in trimmed:
        item_id, _, hint = entry.partition(" — ")
        assert item_id in text          # (a) every evicted id in the trim-note
        assert "fetch via" in hint


def test_top_keep_min_items_never_evicted():
    # chars_per=10000 → even at KEEP_MIN items the block stays over budget,
    # so eviction drains ALL the way down to KEEP_MIN — items 0..KEEP_MIN-1
    # survive strictly because of the KEEP_MIN floor, not budget slack.
    blocks = [_block("wiki_related", 40, chars_per=10000)]
    _, trimmed = sb.apply_budget(blocks, "GENERAL")
    evicted_ids = {t.split(" — ")[0] for t in trimmed}
    assert len(trimmed) == 40 - sb.KEEP_MIN   # drained to the floor
    # (b) the first KEEP_MIN items of a block always survive
    for i in range(sb.KEEP_MIN):
        assert f"wiki_related-item-{i}" not in evicted_ids


# ── Integration: build_seed_message's over-budget guard (spec §5.7) ──────────

def _chunk(i, related=False):
    from backend.retrieval.wiki_v2.pipeline import ChunkHit
    return ChunkHit(
        page_path=f"modules/m{i}.md", section_anchor="overview",
        section_title="Overview", page_type="module",
        chunk_text="x" * 1500, last_updated="2026-06-01", score=0.9,
        related_via=(f"modules/seed.md —depends_on→ modules/m{i}.md"
                     if related else None))


class _FakeAgent:
    has_jira = False


def _bundle_with_chunks(n):
    from backend.preflight import PreflightBundle
    b = PreflightBundle()
    # mix of direct + related so both wiki blocks exist and eviction has targets
    b.seed_wiki_chunks = [_chunk(i, related=(i % 3 == 0)) for i in range(n)]
    return b


def test_build_seed_message_under_budget_has_no_trim_note():
    from backend.preflight import build_seed_message
    bundle = _bundle_with_chunks(3)  # ~4.5k chars << 24k budget
    out = build_seed_message("q", "scope", bundle, agent=_FakeAgent())
    assert "## Trimmed (fetch on demand)" not in out
    assert "Pre-fetched wiki evidence" in out


def test_build_seed_message_over_budget_trims_and_notes():
    from backend.preflight import build_seed_message
    # 40 chunks × 1500 chars ≈ 60k chars ≈ 15k est-tokens >> 6k budget
    bundle = _bundle_with_chunks(40)
    out = build_seed_message("q", "scope", bundle, agent=_FakeAgent())
    assert "## Trimmed (fetch on demand)" in out          # trim-note present
    assert "fetch via wiki_read_page" in out               # demoted to pull
    assert "**Question:** q" in out                         # header_pre preserved
    # KEEP_MIN direct chunks always survive in-body (not only in the trim-note)
    assert "modules/m1.md#overview" in out
