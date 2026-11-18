"""Confluence space export (HTML). Keeps the page body and breadcrumb, drops navigation and footer chrome.

Headings become Markdown headings and lists become Markdown lists, so the heading-aware chunker works the same way it
does for runbooks. Metadata is read from ``<meta name="itops:...">`` tags when present (the private repo's live
Confluence connector writes them); otherwise the breadcrumb and title are used.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from itops_rag.core.models import Document
from itops_rag.loaders.common import make_document

_CHROME_IDS = (
    "breadcrumb-section",
    "footer",
    "navigation",
    "page-metadata",
    "likes-and-labels-container",
    "comments-section",
    "attachments",
)


def _to_markdown(node: Any) -> str:
    from bs4.element import NavigableString, Tag

    out: list[str] = []
    for el in node.children:
        if isinstance(el, NavigableString):
            s = str(el).strip()
            if s:
                out.append(s)
            continue
        if not isinstance(el, Tag):
            continue
        name = el.name or ""
        if name in {"script", "style"}:
            continue
        if name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            out.append(f"\n{'#' * int(name[1])} {el.get_text(' ', strip=True)}\n")
        elif name in {"ul", "ol"}:
            for i, li in enumerate(el.find_all("li", recursive=False), start=1):
                bullet = f"{i}." if name == "ol" else "-"
                out.append(f"{bullet} {li.get_text(' ', strip=True)}")
            out.append("")
        elif name == "pre":
            out.append(f"\n```\n{el.get_text()}\n```\n")
        elif name == "table":
            for row in el.find_all("tr"):
                cells = [c.get_text(" ", strip=True) for c in row.find_all(["th", "td"])]
                out.append("| " + " | ".join(cells) + " |")
            out.append("")
        elif name in {"p", "blockquote"}:
            out.append(el.get_text(" ", strip=True) + "\n")
        elif name == "br":
            out.append("\n")
        else:
            out.append(_to_markdown(el))
    return "\n".join(out)


def load_confluence_html(path: Path, root: Path) -> list[Document]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    meta: dict[str, Any] = {}
    for m in soup.find_all("meta"):
        name = str(m.get("name") or "")
        if name.startswith("itops:"):
            meta[name.split(":", 1)[1]] = str(m.get("content") or "")

    breadcrumb = ""
    crumb = soup.find(id="breadcrumb-section")
    if crumb:
        breadcrumb = " > ".join(a.get_text(strip=True) for a in crumb.find_all("a"))
    for chrome_id in _CHROME_IDS:
        for el in soup.find_all(id=chrome_id):
            el.decompose()

    title = ""
    header = soup.find(id="title-text") or soup.find(id="main-header")
    if header:
        title = header.get_text(" ", strip=True)
    elif soup.title:
        title = soup.title.get_text(strip=True)
    if " : " in title:  # Confluence titles look like "Space : Page"
        title = title.split(" : ", 1)[1]

    body = soup.find(id="main-content") or soup.body or soup
    text = _to_markdown(body).strip()
    if not text:
        raise ValueError("empty page body")
    meta.setdefault("doc_type", "standard")
    return [
        make_document(
            meta,
            text,
            path,
            root,
            default_type="standard",
            default_title=title,
            extra={"breadcrumb": breadcrumb},
        )
    ]
