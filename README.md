# WorkInSync Feature Wiki

An AI-maintained, persistent knowledge base for the WorkInSync product. Built on Karpathy's [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) pattern.

---

## What This Is

- **`raw/`** — source of truth (PDFs, specs, transcripts). AI reads only, never writes.
- **`wiki/`** — AI-generated, structured, interlinked markdown pages. Browsable in Obsidian.
- **`CLAUDE.md`** — the AI's rulebook. Read first in every session.
- **`WORKFLOW.md`** — guide for adding new docs and asking questions.

## Quick Start

1. Open this folder as an Obsidian vault (File → Open Vault).
2. Drop a PDF into `raw/modules/<feature>/`.
3. In Cursor chat: `ingest raw/modules/<feature>/<filename>.pdf`
4. Ask questions: `How does <feature> connect to <other-feature>?`

See **`WORKFLOW.md`** for the full guide.
