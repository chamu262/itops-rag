"""Helpers shared by the loaders: front matter parsing and metadata normalisation."""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import Any

import yaml

from itops_rag.core.models import ACCESS_LEVELS, Document

_FRONT = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def split_front_matter(text: str) -> tuple[dict[str, Any], str]:
    m = _FRONT.match(text)
    if not m:
        return {}, text
    data = yaml.safe_load(m.group(1)) or {}
    if not isinstance(data, dict):
        raise ValueError("front matter must be a mapping")
    return data, text[m.end() :]


# Exports name the same system many ways ("Entra ID", "Azure AD", "Intune / Autopilot"). One canonical name per
# system keeps the --system filter and per-system stats honest. Unknown names pass through, lower-cased.
SYSTEM_ALIASES: dict[str, str] = {
    "entra id": "entra",
    "azure ad": "entra",
    "aad": "entra",
    "identity": "entra",
    "microsoft entra": "entra",
    "google workspace": "gws",
    "g suite": "gws",
    "gmail": "email",
    "mail": "email",
    "jamf pro": "jamf",
    "jamf / macos": "jamf",
    "jamf connect": "jamf",
    "intune / windows": "intune",
    "intune / autopilot": "intune",
    "autopilot": "intune",
    "microsoft intune": "intune",
    "wi-fi": "network",
    "wifi": "network",
    "printing": "network",
    "printers": "network",
    "vpn": "meshgate",
    "meshgate vpn": "meshgate",
    "lost / stolen device": "security",
    "phishing": "security",
    "joiner / leaver": "general",
    "onboarding": "general",
    "offboarding": "general",
}


def normalise_system(value: str) -> str:
    """``"Intune / Autopilot"`` -> ``"intune"``; ``"Entra ID"`` -> ``"entra"``; unknown -> lower-cased as is."""
    key = " ".join(value.strip().lower().split())
    if not key:
        return "general"
    if key in SYSTEM_ALIASES:
        return SYSTEM_ALIASES[key]
    first = key.split("/")[0].strip()
    return SYSTEM_ALIASES.get(first, first if "/" in key else key)


def slug(path: Path) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", path.stem).strip("-").upper() or "DOC"


def as_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dt.datetime | dt.date):
        return value.isoformat()[:10]
    return str(value)


def as_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [t.strip() for t in value.split(",") if t.strip()]
    return [str(t).strip() for t in value if str(t).strip()]


def make_document(
    meta: dict[str, Any],
    text: str,
    path: Path,
    root: Path,
    *,
    default_type: str,
    default_title: str = "",
    markdown: bool = True,
    extra: dict[str, Any] | None = None,
) -> Document:
    # Fail closed: a document without an access tag is NOT public. load_path() applies the configured default.
    access_defaulted = not as_str(meta.get("access"))
    access = as_str(meta.get("access")) or "it-staff"
    if access not in ACCESS_LEVELS:
        raise ValueError(f"access {access!r} is not one of {ACCESS_LEVELS}")
    try:
        source = str(path.relative_to(root))
    except ValueError:
        source = str(path)
    return Document(
        id=as_str(meta.get("id")) or slug(path),
        title=as_str(meta.get("title")) or default_title or path.stem.replace("-", " ").replace("_", " "),
        text=text.strip(),
        doc_type=as_str(meta.get("doc_type")) or default_type,
        system=normalise_system(as_str(meta.get("system"))),
        owner=as_str(meta.get("owner")),
        access=access,
        updated=as_str(meta.get("updated")),
        tags=as_tags(meta.get("tags")),
        source=source,
        extra={
            "markdown": markdown,
            **({"access_defaulted": True} if access_defaulted else {}),
            **(extra or {}),
        },
    )
