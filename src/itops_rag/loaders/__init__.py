"""Turn files into ``Document`` objects. One loader per source type, chosen by extension and content.

| Source | Extension | Loader |
|---|---|---|
| Markdown with YAML front matter (runbooks, KB, post-mortems, notes) | .md, .markdown, .txt | ``markdown`` |
| PDF (vendor docs, exported policies) | .pdf | ``pdf`` |
| Confluence space export (HTML) | .html, .htm | ``confluence_html`` |
| Ticket exports: Jira-style CSV, ServiceNow-style JSON | .csv, .json | ``tickets`` |
| Change records and other structured records | .yaml, .yml | ``records`` |
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from pathlib import Path

from itops_rag.core.models import ACCESS_LEVELS, Document
from itops_rag.loaders.confluence import load_confluence_html
from itops_rag.loaders.markdown import load_markdown
from itops_rag.loaders.pdf import load_pdf
from itops_rag.loaders.records import load_yaml_record
from itops_rag.loaders.tickets import load_ticket_csv, load_ticket_json

log = logging.getLogger(__name__)

Loader = Callable[[Path, Path], list[Document]]

LOADERS: dict[str, Loader] = {
    ".md": load_markdown,
    ".markdown": load_markdown,
    ".txt": load_markdown,
    ".pdf": load_pdf,
    ".html": load_confluence_html,
    ".htm": load_confluence_html,
    ".csv": load_ticket_csv,
    ".json": load_ticket_json,
    ".yaml": load_yaml_record,
    ".yml": load_yaml_record,
}

SKIP_NAMES = {"README.md", "readme.md"}


def iter_files(root: Path) -> Iterator[Path]:
    if root.is_file():
        yield root
        return
    for p in sorted(root.rglob("*")):
        if (
            p.is_file()
            and p.suffix.lower() in LOADERS
            and p.name not in SKIP_NAMES
            and not p.name.endswith(".meta.yaml")
            and not any(part.startswith(".") for part in p.relative_to(root).parts)
        ):
            yield p


def load_tree(path: Path, default_access: str = "it-staff") -> tuple[list[Document], list[str], list[str]]:
    """Load every supported file under ``path``.

    Returns ``(documents, errors, failed_sources)``; never raises for a single bad file. Documents without an access
    tag get ``default_access`` (fail closed: the default is ``it-staff``, not ``public``).
    """
    if default_access not in ACCESS_LEVELS:
        raise ValueError(f"default_access must be one of {ACCESS_LEVELS}")
    root = path if path.is_dir() else path.parent
    docs: list[Document] = []
    errors: list[str] = []
    failed: list[str] = []
    for f in iter_files(path):
        try:
            docs.extend(LOADERS[f.suffix.lower()](f, root))
        except Exception as e:
            errors.append(f"{f}: {type(e).__name__}: {e}")
            failed.append(f.relative_to(root).as_posix())
            log.warning("skipped %s: %s", f, e)
    seen: dict[str, str] = {}
    unique: list[Document] = []
    for d in docs:
        if d.extra.pop("access_defaulted", False):
            d.access = default_access
        if d.id in seen:
            errors.append(f"duplicate id {d.id} in {d.source} (first seen in {seen[d.id]}); kept the first")
            continue
        seen[d.id] = d.source
        unique.append(d)
    return unique, errors, failed


def load_path(path: Path, default_access: str = "it-staff") -> tuple[list[Document], list[str]]:
    """Load every supported file under ``path``. Returns documents and per-file errors (never raises)."""
    docs, errors, _ = load_tree(path, default_access)
    return docs, errors


__all__ = ["LOADERS", "iter_files", "load_path"]
