"""Heading-aware chunking.

Markdown is first cut into sections at headings (so a chunk never spans two procedures), then each section is split
recursively on paragraph, line, sentence and word boundaries to at most ``size`` characters with ``overlap``
characters carried over. Each chunk keeps its heading breadcrumb, which is prepended when embedding.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from itops_rag.core.models import Chunk, Document

CHUNKER_VERSION = 4
"""Bump when splitting or ``Chunk.embed_text`` changes, so ingest re-chunks instead of skipping unchanged docs."""

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_SEPARATORS = ("\n\n", "\n", ". ", "; ", ", ", " ")


@dataclass(slots=True)
class Section:
    heading: str
    text: str


def split_sections(text: str) -> list[Section]:
    """Split Markdown into sections keyed by their heading breadcrumb (``H2 > H3``). Code fences are respected."""
    sections: list[Section] = []
    stack: list[tuple[int, str]] = []
    buf: list[str] = []
    in_fence = False

    def flush() -> None:
        body = "\n".join(buf).strip()
        if body:
            sections.append(Section(" > ".join(h for _, h in stack), body))
        buf.clear()

    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
        m = None if in_fence else _HEADING.match(line)
        if m:
            flush()
            level = len(m.group(1))
            # The H1 is normally the document title, which is already on every chunk.
            if level == 1:
                stack.clear()
                continue
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, m.group(2).strip()))
        else:
            buf.append(line)
    flush()
    return sections


def split_text(text: str, size: int, overlap: int) -> list[str]:
    """Recursive character splitter (same idea as LangChain's, no dependency)."""
    if size <= 0:
        raise ValueError("size must be positive")
    if not 0 <= overlap < size:
        raise ValueError("overlap must be >= 0 and smaller than size")
    text = text.strip()
    if len(text) <= size:
        return [text] if text else []
    pieces = _split(text, size, 0)
    return _merge(pieces, size, overlap)


def _split(text: str, size: int, sep_idx: int) -> list[str]:
    if len(text) <= size:
        return [text]
    if sep_idx >= len(_SEPARATORS):
        return [text[i : i + size] for i in range(0, len(text), size)]
    sep = _SEPARATORS[sep_idx]
    parts = text.split(sep)
    if len(parts) == 1:
        return _split(text, size, sep_idx + 1)
    out: list[str] = []
    for i, part in enumerate(parts):
        piece = part + (sep if i < len(parts) - 1 else "")
        if len(piece) > size:
            out.extend(_split(piece, size, sep_idx + 1))
        elif piece:
            out.append(piece)
    return out


def _merge(pieces: list[str], size: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    current = ""
    for piece in pieces:
        if current and len(current) + len(piece) > size:
            chunks.append(current.strip())
            # Carry over up to `overlap` characters, shrunk if needed so tail + next piece still fits in `size`
            # (dropping the overlap entirely would lose context at exactly the boundaries that need it).
            room = min(overlap, size - len(piece))
            tail = current[-room:] if room > 0 else ""
            # Start the overlap at a word boundary so chunks don't begin mid-word.
            if tail and " " in tail:
                tail = tail[tail.index(" ") + 1 :]
            current = tail
        current += piece
    if current.strip():
        chunks.append(current.strip())
    return [c for c in chunks if c]


def join_overlapping(parts: list[str], max_overlap: int = 400) -> str:
    """Re-join consecutive chunks of one section, dropping the text each chunk repeats from the previous one."""
    out = ""
    for part in parts:
        if not out:
            out = part
            continue
        best = 0
        for n in range(min(len(out), len(part), max_overlap), 10, -1):
            if out.endswith(part[:n]):
                best = n
                break
        out += ("" if best else "\n") + part[best:]
    return out


@dataclass(slots=True, frozen=True)
class ChunkOptions:
    size: int = 800
    overlap: int = 100
    min_section_chars: int = 0
    """Merge a section into its neighbour when either is shorter than this (0 = off). Heading-split runbooks produce
    many 100–300-character sections, and tiny chunks are weak candidates for the reranker."""
    table_rows: bool = False
    """Index each Markdown table row as its own chunk, with the header row repeated, so a lookup like
    "who is on call for Jamf?" can match the one row that answers it."""
    split_ticket_comments: bool = False
    """Tickets: one chunk for summary + resolution + description, comments in separate chunks."""


_TABLE_LINE = re.compile(r"^\s*\|.*\|\s*$")
_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{2,}")


def _split_tables(section: Section) -> list[Section]:
    """Pull Markdown tables out of a section: one Section per data row (header repeated), plus the remaining text."""
    lines = section.text.splitlines()
    rest: list[str] = []
    rows: list[Section] = []
    i = 0
    while i < len(lines):
        if _TABLE_LINE.match(lines[i]) and i + 1 < len(lines) and _TABLE_SEP.match(lines[i + 1]):
            header = lines[i].strip()
            j = i + 2
            while j < len(lines) and _TABLE_LINE.match(lines[j]):
                row = lines[j].strip()
                rows.append(
                    Section(f"{section.heading} > table" if section.heading else "table", f"{header}\n{row}")
                )
                j += 1
            i = j
            continue
        rest.append(lines[i])
        i += 1
    remaining = "\n".join(rest).strip()
    if not rows:
        return [section]
    return ([Section(section.heading, remaining)] if remaining else []) + rows


def _common_heading(a: str, b: str) -> str:
    pa, pb = a.split(" > "), b.split(" > ")
    common = []
    for x, y in zip(pa, pb, strict=False):
        if x != y:
            break
        common.append(x)
    return " > ".join(common) if common else a


def _merge_small(sections: list[Section], min_chars: int, size: int) -> list[Section]:
    out: list[Section] = []
    for sec in sections:
        if (
            out
            and "table" not in sec.heading.split(" > ")[-1:]
            and "table" not in out[-1].heading.split(" > ")[-1:]
        ):
            prev = out[-1]
            leaf = sec.heading.split(" > ")[-1] if sec.heading else ""
            joined = (
                f"{prev.text}\n\n{leaf + ':' if leaf and leaf != prev.heading else ''}\n{sec.text}".replace(
                    "\n\n\n", "\n\n"
                )
            )
            if (len(prev.text) < min_chars or len(sec.text) < min_chars) and len(joined) <= size:
                out[-1] = Section(_common_heading(prev.heading, sec.heading), joined.strip())
                continue
        out.append(sec)
    return out


def _ticket_sections(sections: list[Section]) -> list[Section]:
    core = [s for s in sections if s.heading != "Comments"]
    comments = [s for s in sections if s.heading == "Comments"]
    merged = "\n\n".join((f"{s.heading}:\n{s.text}" if s.heading else s.text) for s in core)
    return ([Section("", merged)] if merged else []) + comments


def chunk_document(
    doc: Document, size: int = 800, overlap: int = 100, options: ChunkOptions | None = None
) -> list[Chunk]:
    """Turn a document into chunks. Documents that already fit in one chunk stay whole."""
    opts = options or ChunkOptions(size=size, overlap=overlap)
    meta = doc.meta()
    sections = split_sections(doc.text) if doc.extra.get("markdown", True) else [Section("", doc.text)]
    if not sections:
        return []
    if doc.doc_type == "ticket" and doc.extra.get("markdown", True):
        sections = (
            _ticket_sections(sections)
            if opts.split_ticket_comments
            else [
                Section(
                    "", "\n\n".join((f"{s.heading}:\n{s.text}" if s.heading else s.text) for s in sections)
                )
            ]
        )
    if opts.table_rows:
        sections = [part for sec in sections for part in _split_tables(sec)]
    if opts.min_section_chars > 0:
        sections = _merge_small(sections, opts.min_section_chars, opts.size)
    chunks: list[Chunk] = []
    for section in sections:
        for body in split_text(section.text, opts.size, opts.overlap):
            n = len(chunks)
            chunks.append(
                Chunk(
                    id=f"{doc.id}#{n}",
                    doc_id=doc.id,
                    ordinal=n,
                    text=body,
                    heading=section.heading,
                    meta=meta,
                )
            )
    return chunks
