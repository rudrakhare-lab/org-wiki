"""Section-level chunking for wiki pages (spec §5.2).

Pure functions — no I/O, no DB. Pages split at `##` headings; markdown
tables split into row-groups of TABLE_ROWS_PER_CHUNK with the header
repeated per group; long prose split at paragraph boundaries near
MAX_PROSE_CHARS. Anchors are GitHub-style heading slugs, stable across
re-embeds.
"""
from __future__ import annotations
import re
from dataclasses import dataclass

MAX_PROSE_CHARS = 1200
TABLE_ROWS_PER_CHUNK = 15

_FM_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
_H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


@dataclass
class Chunk:
    page_path: str
    page_title: str
    section_anchor: str
    section_title: str
    page_type: str
    chunk_index: int
    chunk_text: str
    last_updated: str | None = None

    @property
    def embed_text(self) -> str:
        head = self.page_title
        if self.section_title:
            head = f"{self.page_title} — {self.section_title}"
        return f"{head}\n{self.chunk_text}"


def slugify(heading: str) -> str:
    s = heading.strip().lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s]+", "-", s).strip("-")
    return re.sub(r"-{2,}", "-", s)


_TYPE_MAP = {
    "modules": "module", "configs": "config", "runbooks": "runbook",
    "decisions": "decision", "concepts": "concept", "entities": "entity",
    "integrations": "integration", "cross-module": "cross-module",
    "history": "history", "sources": "source", "persons": "person",
    "patterns": "pattern", "epics": "epic",
}


def page_type_from_path(page_path: str) -> str:
    first = page_path.split("/", 1)[0]
    return _TYPE_MAP.get(first, "") if "/" in page_path else ""


def _is_table_line(line: str) -> bool:
    return line.lstrip().startswith("|")


def _split_table(lines: list[str]) -> list[str]:
    """Row-group split: header (first 2 lines) repeated per group."""
    if len(lines) <= 2 + TABLE_ROWS_PER_CHUNK:
        return ["\n".join(lines)]
    header, rows = lines[:2], lines[2:]
    out = []
    for i in range(0, len(rows), TABLE_ROWS_PER_CHUNK):
        out.append("\n".join(header + rows[i:i + TABLE_ROWS_PER_CHUNK]))
    return out


def _split_prose(text: str) -> list[str]:
    if len(text) <= MAX_PROSE_CHARS:
        return [text]
    paras, out, cur = text.split("\n\n"), [], ""
    for p in paras:
        cand = f"{cur}\n\n{p}".strip() if cur else p
        if len(cand) > MAX_PROSE_CHARS and cur:
            out.append(cur)
            cur = p
        else:
            cur = cand
    if cur:
        out.append(cur)
    return out


def _split_section_body(body: str) -> list[str]:
    """Split a section into pieces: tables by row-group, prose by paragraph."""
    lines = body.splitlines()
    blocks: list[tuple[bool, list[str]]] = []  # (is_table, lines)
    for line in lines:
        t = _is_table_line(line)
        if blocks and blocks[-1][0] == t:
            blocks[-1][1].append(line)
        else:
            blocks.append((t, [line]))
    pieces: list[str] = []
    for is_table, blk in blocks:
        text = "\n".join(blk).strip()
        if not text:
            continue
        pieces.extend(_split_table(blk) if is_table else _split_prose(text))
    return pieces


def split_page(page_path: str, text: str, page_type: str = "",
               last_updated: str | None = None) -> list[Chunk]:
    body = _FM_RE.sub("", text)
    m = _H1_RE.search(body)
    page_title = m.group(1).strip() if m else page_path.rsplit("/", 1)[-1].removesuffix(".md")
    ptype = page_type or page_type_from_path(page_path)

    # Split into (section_title, section_body) at ## headings.
    sections: list[tuple[str, str]] = []
    cur_title, cur_lines = "", []
    for line in body.splitlines():
        if line.startswith("## "):
            sections.append((cur_title, "\n".join(cur_lines)))
            cur_title, cur_lines = line[3:].strip(), []
        else:
            cur_lines.append(line)
    sections.append((cur_title, "\n".join(cur_lines)))

    chunks: list[Chunk] = []
    for title, sec_body in sections:
        sec_body = sec_body.strip()
        if title == "" and sec_body:
            sec_body = _H1_RE.sub("", sec_body).strip()  # drop the H1 line itself
        if not sec_body:
            continue
        anchor = slugify(title) if title else ""
        for idx, piece in enumerate(_split_section_body(sec_body)):
            chunks.append(Chunk(
                page_path=page_path, page_title=page_title,
                section_anchor=anchor, section_title=title,
                page_type=ptype, chunk_index=idx, chunk_text=piece,
                last_updated=last_updated,
            ))
    return chunks
