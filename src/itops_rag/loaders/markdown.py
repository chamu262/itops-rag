"""Markdown (and plain text) with optional YAML front matter."""

from __future__ import annotations

import re
from pathlib import Path

from itops_rag.core.models import Document
from itops_rag.loaders.common import make_document, split_front_matter

_H1 = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def load_markdown(path: Path, root: Path) -> list[Document]:
    raw = path.read_text(encoding="utf-8")
    meta, body = split_front_matter(raw)
    h1 = _H1.search(body)
    return [make_document(meta, body, path, root, default_type="doc", default_title=h1.group(1).strip() if h1 else "",
                          markdown=path.suffix.lower() != ".txt")]
