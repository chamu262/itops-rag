"""PDF text extraction with page markers, so answers can point at a page.

Metadata comes from the PDF's own fields (Title, Subject) and, if present, ``itops:*`` keys in the document info
dictionary (``/itops_id``, ``/itops_access`` ...) or a sidecar ``<name>.meta.yaml`` next to the file.
Scanned PDFs without a text layer produce no text and are reported as errors; OCR them first.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from itops_rag.core.models import Document
from itops_rag.loaders.common import make_document


def _by_page(reader: Any) -> list[str]:
    """Fallback: each page becomes a section headed "Page N"."""
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append(f"## Page {i}\n\n{text}")
    return pages


def _with_headings(reader: Any) -> list[str]:
    """Recover real section headings from font sizes: lines set clearly larger than the body text become ``##``
    headings (with the page number kept, for citations). Returns [] when the PDF gives no usable size information,
    so the caller falls back to page sections."""
    lines: list[tuple[float, str, int]] = []
    for page_no, page in enumerate(reader.pages, start=1):
        frags: list[tuple[float, str]] = []

        def visit(
            text: str, cm: Any, tm: Any, font: Any, size: float, frags: list[tuple[float, str]] = frags
        ) -> None:
            scale = abs(float(tm[0] or 1)) * abs(float(cm[0] or 1))
            frags.append((round(float(size or 0) * scale, 1), text))

        page.extract_text(visitor_text=visit)
        current, current_size = "", 0.0
        for size, text in frags:
            for k, part in enumerate(text.split("\n")):
                if k > 0:
                    if current.strip():
                        lines.append((current_size, current.strip(), page_no))
                    current, current_size = "", 0.0
                if part.strip():
                    current += part
                    current_size = max(current_size, size)
        if current.strip():
            lines.append((current_size, current.strip(), page_no))
    if not lines:
        return []
    weights: Counter[float] = Counter()
    for size, text, _ in lines:
        weights[size] += len(text)
    body = weights.most_common(1)[0][0]
    if body <= 0:
        return []
    out: list[str] = []
    found = False
    for size, text, page_no in lines:
        if size >= body * 1.15 and len(text) <= 120:
            found = True
            out.append(f"\n## {text} (p. {page_no})\n")
        else:
            out.append(text)
    return ["\n".join(out).strip()] if found else []


def load_pdf(path: Path, root: Path) -> list[Document]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = _with_headings(reader) or _by_page(reader)
    if not pages:
        raise ValueError("no extractable text (scanned PDF?)")

    meta: dict[str, Any] = {}
    info: Any = reader.metadata or {}
    if info.get("/Title"):
        meta["title"] = str(info["/Title"])
    for key in ("id", "doc_type", "system", "owner", "access", "updated", "tags"):
        v = info.get(f"/itops_{key}")
        if v:
            meta[key] = str(v)
    sidecar = path.with_suffix(".meta.yaml")
    if sidecar.exists():
        meta.update(yaml.safe_load(sidecar.read_text(encoding="utf-8")) or {})
    meta.setdefault("doc_type", "vendor")
    return [
        make_document(
            meta, "\n\n".join(pages), path, root, default_type="vendor", extra={"pages": len(reader.pages)}
        )
    ]
