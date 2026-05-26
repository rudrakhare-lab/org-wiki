# Editorial Policy — When a Ticket Earns a Wiki Page

> **Status**: skeleton — to be expanded in Phase 3 (after we've used the SQLite
> layer for at least a week and observed the kinds of questions that get asked).

The classifier in `scripts/triage.py` decides each ticket's `triage_tier`:

- **`wiki`** — promote to `wiki/sources/jira/<KEY>.md` via the ingest workflow
- **`evidence`** — keep in SQLite only; surfaceable to the agent via SQL queries
- **`ignore`** — empty shells, status-only updates, no content of value

A ticket is **wiki-worthy** if **any** of these apply:

1. Documents a non-obvious architectural decision affecting multiple components
2. Captures a root cause that other systems might encounter (postmortem-style)
3. Records a deliberate tradeoff with explicit rationale
4. Is a parent epic with substantive scope/decisions documented in body
5. Contains design rationale not captured in any PRD or design doc

A ticket is **NOT wiki-worthy** even if it looks important, when:

- It's a routine bug fix with no architectural lesson
- It's a config or dependency bump
- It's a status-tracking ticket with empty body
- It's a customer-specific issue with no generalizable insight
- It's primarily a thread of comments without a synthesizable conclusion

Default verdict on uncertainty: `evidence`. We'd rather under-promote and surface
via SQL than pollute the wiki with low-signal content.

---

(Full classifier prompt lives in `docs/classifier-prompt.md`.)
