"""Global seed evidence budget with intent-aware, rank-ordered eviction
(spec §5.7). Evicted items are demoted to pull — never hidden: the seed
ends with a trim-note listing every evicted item + its fetch tool."""
from __future__ import annotations

from dataclasses import dataclass, field

SEED_BUDGET_TOKENS = 6000
KEEP_MIN = 3  # never evict a block's top-N items (direct hits stay)

# Per intent, block names in EVICT-FIRST order (last = most protected).
# CONFIGURATION/DEBUGGING/STATUS evict wiki prose first — Jira context must
# not be starved for the intents where operational evidence matters most.
EVICTION_ORDER: dict[str, list[str]] = {
    "CONFIGURATION": ["wiki_related", "wiki_direct", "jira_historical",
                      "jira_latest", "config_evidence"],
    "DEBUGGING":     ["wiki_related", "wiki_direct", "jira_historical",
                      "jira_latest", "config_evidence"],
    "STATUS":        ["wiki_related", "wiki_direct", "jira_historical",
                      "jira_latest", "config_evidence"],
    "HOW_TO":        ["jira_historical", "jira_latest", "wiki_related",
                      "config_evidence", "wiki_direct"],
    "DEFINITION":    ["jira_historical", "config_evidence", "jira_latest",
                      "wiki_related", "wiki_direct"],
    "ARCHITECTURAL": ["jira_historical", "config_evidence", "jira_latest",
                      "wiki_related", "wiki_direct"],
}
_DEFAULT_ORDER = ["wiki_related", "jira_historical", "wiki_direct",
                  "jira_latest", "config_evidence"]


_SEP = "\n\n---\n\n"  # separator between items within a block


def est_tokens(text: str) -> int:
    return len(text) // 4


@dataclass
class SeedBlock:
    name: str
    priority: int
    text: str
    # (item_id, rendered_text, fetch_hint) per evictable item, in rank order
    # (best first). Eviction pops from the END — the first KEEP_MIN items of
    # a block are never evicted.
    evictable: list[tuple[str, str, str]] = field(default_factory=list)
    # Prefix (e.g. "## Section\n\n") kept when the block's text is rebuilt from
    # surviving items after eviction. Empty for atomic (evictable=[]) blocks,
    # whose `text` is used verbatim and never rebuilt.
    header: str = ""
    # Separator used BOTH for the initial join and the post-eviction rebuild —
    # must match how the caller built `text` so rerender is byte-consistent.
    item_sep: str = _SEP

    def rerender(self) -> None:
        """Rebuild `text` from the surviving evictable items — rejoining with
        `item_sep` so eviction never leaves an orphaned separator. No-op for
        atomic blocks (no evictable items)."""
        if self.evictable:
            self.text = self.header + self.item_sep.join(t for _, t, _ in self.evictable)


def apply_budget(blocks: list[SeedBlock], intent: str) -> tuple[str, list[str]]:
    """Assemble the seed evidence text under SEED_BUDGET_TOKENS.

    Under budget → pure passthrough (blocks joined, no trim-note, same text
    as an unbudgeted render). Over budget → evict items from the intent's
    evict-first blocks (bottom of each block first, top KEEP_MIN always
    survive) and append a mandatory trim-note listing every evicted item +
    its fetch tool, so trimmed evidence is demoted to pull — never hidden.

    Returns (final_seed_text, trimmed_item_descriptions).
    """
    order = EVICTION_ORDER.get(intent, _DEFAULT_ORDER)
    for blk in blocks:  # observability: protectedness rank per this intent
        blk.priority = order.index(blk.name) if blk.name in order else len(order)
    total = sum(est_tokens(b.text) for b in blocks)
    trimmed: list[str] = []

    if total > SEED_BUDGET_TOKENS:
        for name in order:                       # evict-first order
            if total <= SEED_BUDGET_TOKENS:
                break
            blk = next((b for b in blocks if b.name == name), None)
            if not blk or not blk.evictable:
                continue
            # evict from the bottom (lowest-ranked last items), keep top KEEP_MIN
            while (total > SEED_BUDGET_TOKENS
                   and len(blk.evictable) > KEEP_MIN):
                item_id, _item_text, hint = blk.evictable.pop()
                blk.rerender()  # rebuild from survivors — no orphaned separators
                trimmed.append(f"{item_id} — fetch via {hint}")
                total = sum(est_tokens(b.text) for b in blocks)

    parts = [b.text for b in blocks if b.text.strip()]
    if trimmed:
        parts.append("## Trimmed (fetch on demand)\n\n"
                     + "\n".join(f"- {t}" for t in trimmed))
    return "\n\n---\n\n".join(parts), trimmed
