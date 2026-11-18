"""Structured records in YAML: CAB change records, incident records, asset notes.

Known keys get a readable layout (plan and backout as numbered steps); any other keys are kept as ``Key: value``
lines, so a new field in the export still ends up searchable.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from itops_rag.core.models import Document
from itops_rag.loaders.common import as_str, make_document

_META_KEYS = {"id", "title", "system", "owner", "access", "updated", "tags", "doc_type"}
_HEADER_KEYS = ("type", "risk", "status", "window_start", "window_end")
_SECTION_ORDER = ("summary", "impact", "plan", "backout", "validation", "outcome", "lessons", "related")


def _fmt(value: Any) -> str:
    if isinstance(value, list):
        return "\n".join(f"{i}. {as_str(v)}" for i, v in enumerate(value, start=1))
    if isinstance(value, dict):
        return "\n".join(f"- {k}: {as_str(v)}" for k, v in value.items())
    return as_str(value)


def load_yaml_record(path: Path, root: Path) -> list[Document]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else [data]
    docs = []
    for rec in items:
        if not isinstance(rec, dict) or not rec.get("id"):
            raise ValueError("each record needs an 'id'")
        lines = [f"{as_str(rec['id'])}: {as_str(rec.get('title'))}"]
        lines += [f"{k.replace('_', ' ').capitalize()}: {as_str(rec[k])}" for k in _HEADER_KEYS if rec.get(k)]
        keys = [k for k in _SECTION_ORDER if k in rec] + sorted(
            k for k in rec if k not in _SECTION_ORDER and k not in _META_KEYS and k not in _HEADER_KEYS)
        for k in keys:
            if rec.get(k) in (None, "", []):
                continue
            lines += ["", f"## {k.replace('_', ' ').capitalize()}", _fmt(rec[k])]
        meta = dict(rec)
        meta.setdefault("doc_type", "change" if as_str(rec["id"]).upper().startswith("CHG") else "record")
        meta.setdefault("updated", as_str(rec.get("window_end") or rec.get("window_start"))[:10])
        meta.setdefault("access", "it-staff")
        docs.append(make_document(meta, "\n".join(lines), path, root, default_type="record",
                                  default_title=as_str(rec.get("title"))))
    return docs
