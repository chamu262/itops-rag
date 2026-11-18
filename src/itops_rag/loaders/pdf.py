"""PDF text extraction with page markers, so answers can point at a page.

Metadata comes from the PDF's own fields (Title, Subject) and, if present, ``itops:*`` keys in the document info
dictionary (``/itops_id``, ``/itops_access`` ...) or a sidecar ``<name>.meta.yaml`` next to the file.
Scanned PDFs without a text layer produce no text and are reported as errors; OCR them first.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from itops_rag.core.models import Document
from itops_rag.loaders.common import make_document


def load_pdf(path: Path, root: Path) -> list[Document]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages: list[str] = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            # Each page becomes a section, so chunks keep "Page N" as their heading breadcrumb.
            pages.append(f"## Page {i}\n\n{text}")
    if not pages:
        raise ValueError("no extractable text (scanned PDF?)")

    meta: dict[str, Any] = {}
    info = reader.metadata or {}
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
    return [make_document(meta, "\n\n".join(pages), path, root, default_type="vendor",
                          extra={"pages": len(reader.pages)})]
