# LLM Wiki — Reference Pattern (Karpathy)

> Original: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
> Copied here for reference. This org-wiki is based on and extends this pattern.

---

## Core Idea

An LLM Wiki is a **persistent, AI-maintained knowledge base** where:

1. You feed source documents (PDFs, notes, specs) to an LLM.
2. The LLM builds and maintains structured wiki pages — not ephemeral chat responses.
3. Each new document ingested **updates** existing pages rather than starting fresh.
4. The wiki pages become the authoritative, navigable reference — the LLM reads the wiki on future sessions, not the raw sources.

This is fundamentally different from RAG (Retrieval-Augmented Generation):
- **RAG**: LLM reads source docs on every query → stateless, no cumulative understanding.
- **LLM Wiki**: LLM maintains wiki pages → stateful, cumulative, browsable by humans.

---

## Why This Pattern Works

- **Persistence**: Wiki pages survive session boundaries. The LLM doesn't forget.
- **Human-readable**: Engineers and PMs can browse the wiki directly in Obsidian.
- **Incrementally updatable**: New docs refine existing pages rather than creating noise.
- **Cross-referencing**: The LLM builds links between related concepts across documents.
- **Auditable**: Every page cites its source. Every change is logged.

---

## Key Conventions (Karpathy's Original)

1. The AI **reads** from a raw/ folder (never writes).
2. The AI **writes** to a wiki/ folder (always structured markdown).
3. Pages use `[[wikilinks]]` to create a navigable graph.
4. An `index.md` is the master table of contents, always kept current.
5. A `log.md` is append-only — a history of all ingests and changes.
6. The AI is told to "ingest" a specific file, triggering a structured workflow.
7. Contradictions are flagged, never silently overwritten.

---

## Extensions in This Org-Wiki

This implementation extends Karpathy's pattern with:

- **8 explicit page types** with enforced schemas (module, entity, concept, integration, decision, cross-module, source, person)
- **Cross-module dependency tracking** — bidirectional links between modules, automatic cross-module page generation
- **9-step ingest workflow** — structured pipeline ensuring nothing is missed
- **LINT workflow** — periodic health checks for broken links, orphans, contradictions, stale pages
- **QUERY workflow** — structured question-answering that cites wiki pages (not raw sources) and optionally saves answers back to the wiki
- **Obsidian graph view** — color-coded by page type, arrow directions show dependencies
- **Frontmatter schema** — machine-readable metadata on every page for filtering in Obsidian

---

## Recommended Session Opening

Every AI session should start with:
```
Read CLAUDE.md, then read wiki/index.md and wiki/log.md (last 10 entries).
Tell me the current state of the wiki, then ask what I want to do.
```

This ensures the LLM always has the full context before acting.
