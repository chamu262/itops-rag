"""Ticket exports: Jira-style CSV and ServiceNow-style JSON. One ticket becomes one document.

The resolution is what makes a past ticket useful, so it goes near the top of the text. People fields (reporter,
assignee, caller) are dropped here; free-text PII (emails, phones, tokens) is masked later by the redactor, and ticket
text also gets IP masking.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from itops_rag.core.models import Document
from itops_rag.loaders.common import as_str, make_document

_DROP_FIELDS = {"reporter", "assignee", "caller", "caller_id", "opened_by", "resolved_by", "watchers"}


def _ticket_doc(key: str, summary: str, body: dict[str, str], meta_extra: dict[str, Any], path: Path,
                root: Path) -> Document:
    lines = [f"Ticket {key}: {summary}"]
    for label in ("Status", "Priority", "Component", "Team", "Created", "Resolved"):
        v = body.get(label.lower())
        if v:
            lines.append(f"{label}: {v}")
    for label in ("Resolution", "Description", "Comments"):
        v = body.get(label.lower())
        if v:
            lines += ["", f"{label}:", v]
    meta = {"id": key, "title": f"{key}: {summary}", "doc_type": "ticket", "access": "it-staff",
            "updated": body.get("resolved") or body.get("created") or "", **meta_extra}
    return make_document(meta, "\n".join(lines), path, root, default_type="ticket", markdown=False,
                         extra={"redact_ip": True})


def load_ticket_csv(path: Path, root: Path) -> list[Document]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows or "key" not in rows[0] or "summary" not in rows[0]:
        raise ValueError("ticket CSV needs at least 'key' and 'summary' columns")
    docs = []
    for r in rows:
        r = {k.strip().lower(): (v or "").strip() for k, v in r.items() if k and k.strip().lower() not in _DROP_FIELDS}
        comments = r.get("comments", "").replace(" || ", "\n")
        body = {**r, "comments": comments, "team": r.get("assignee_team", "")}
        docs.append(_ticket_doc(r["key"], r["summary"], body,
                                {"system": r.get("component", "general").lower() or "general",
                                 "owner": r.get("assignee_team", "")}, path, root))
    return docs


def load_ticket_json(path: Path, root: Path) -> list[Document]:
    data = json.loads(path.read_text(encoding="utf-8"))
    records = data.get("records") if isinstance(data, dict) else data
    if not isinstance(records, list):
        raise ValueError("expected a list of records or {'records': [...]}")
    docs = []
    for rec in records:
        if not isinstance(rec, dict) or not rec.get("number"):
            continue
        rec = {k: v for k, v in rec.items() if k not in _DROP_FIELDS}
        notes = rec.get("work_notes") or []
        body = {
            "status": as_str(rec.get("state")),
            "priority": as_str(rec.get("priority")),
            "component": as_str(rec.get("category")),
            "team": as_str(rec.get("assignment_group")),
            "created": as_str(rec.get("opened_at")),
            "resolved": as_str(rec.get("resolved_at")),
            "resolution": "; ".join(x for x in (as_str(rec.get("close_code")), as_str(rec.get("close_notes"))) if x),
            "description": as_str(rec.get("description")),
            "comments": "\n".join(as_str(n) for n in notes) if isinstance(notes, list) else as_str(notes),
        }
        docs.append(_ticket_doc(as_str(rec["number"]), as_str(rec.get("short_description")), body,
                                {"system": as_str(rec.get("category")).lower() or "general",
                                 "owner": as_str(rec.get("assignment_group"))}, path, root))
    return docs
