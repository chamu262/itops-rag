"""Heading-aware chunking.

Markdown is first cut into sections at headings (so a chunk never spans two procedures), then each section is split
recursively on paragraph, line, sentence and word boundaries to at most ``size`` characters with ``overlap``
characters carried over. Each chunk keeps its heading breadcrumb, which is prepended when embedding.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from itops_rag.core.models import Chunk, Document

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
            tail = current[-overlap:] if overlap else ""
            # Start the overlap at a word boundary so chunks don't begin mid-word.
            if tail and " " in tail:
                tail = tail[tail.index(" ") + 1 :]
            current = tail if len(tail) + len(piece) <= size else ""
        current += piece
    if current.strip():
        chunks.append(current.strip())
    return [c for c in chunks if c]


def chunk_document(doc: Document, size: int = 800, overlap: int = 100) -> list[Chunk]:
    """Turn a document into chunks. Documents that already fit in one chunk stay whole."""
    meta = doc.meta()
    sections = split_sections(doc.text) if doc.extra.get("markdown", True) else [Section("", doc.text)]
    if not sections:
        return []
    chunks: list[Chunk] = []
    for section in sections:
        for body in split_text(section.text, size, overlap):
            n = len(chunks)
            chunks.append(Chunk(id=f"{doc.id}#{n}", doc_id=doc.id, ordinal=n, text=body,
                                heading=section.heading, meta=meta))
    return chunks
