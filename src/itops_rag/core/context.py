"""Build the ``<context>`` block the model reads, and keep retrieved text in its place: data, never instructions.

Three defences, layered:
1. Every chunk is fenced in ``<chunk n=.. doc_id=..>`` tags inside ``<context>``, and any tag-like text inside a chunk
   that could close the fence early is neutralised.
2. Chunks that look like prompt injection are flagged ``suspicious="true"`` and the system prompt tells the model to
   treat them as content to report, not orders to follow.
3. The answer's citations are validated afterwards against the chunk numbers that were actually supplied.
"""

from __future__ import annotations

import html
import re
from collections.abc import Sequence

from itops_rag.core.models import Hit

_FENCE_TAGS = re.compile(r"</?\s*(context|chunk|system|instructions?|question|user|assistant)\b[^>]*>", re.I)

_INJECTION_PATTERNS = [
    r"ignore (all|any|the)? ?(previous|prior|above|earlier) (instructions|prompts?|rules)",
    r"disregard (all|any|the)? ?(previous|prior|above) ",
    r"\b(system|developer) (note|prompt|message|override)\s*:",
    r"you are now\b",
    r"new instructions?\s*:",
    r"(send|email|share|reply with) (me |us )?(your|the user'?s?) (password|credentials|mfa|one[- ]time|otp|token)",
    r"do not (tell|inform|mention).{0,40}(user|anyone)",
    r"act as (an? )?(admin|administrator|root|system)",
]
_INJECTION = re.compile("|".join(f"(?:{p})" for p in _INJECTION_PATTERNS), re.I)


def looks_like_injection(text: str) -> bool:
    return bool(_INJECTION.search(text))


def neutralise(text: str) -> str:
    """Make fence-like tags inert by escaping their angle brackets."""
    return _FENCE_TAGS.sub(lambda m: html.escape(m.group(0)), text)


def _attr(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def build_context(hits: Sequence[Hit]) -> tuple[str, list[int]]:
    """Return the context block and the 1-based numbers of chunks flagged as suspicious."""
    parts = ["<context>"]
    suspicious: list[int] = []
    for n, h in enumerate(hits, start=1):
        m = h.chunk.meta
        flag = looks_like_injection(h.chunk.text)
        if flag:
            suspicious.append(n)
        attrs = (
            f'n="{n}" doc_id="{_attr(h.doc_id)}" title="{_attr(m.get("title"))}" '
            f'section="{_attr(h.chunk.heading)}" type="{_attr(m.get("doc_type"))}" '
            f'system="{_attr(m.get("system"))}" owner="{_attr(m.get("owner"))}" updated="{_attr(m.get("updated"))}"'
        )
        if flag:
            attrs += ' suspicious="true"'
        parts.append(f"<chunk {attrs}>\n{neutralise(h.chunk.text)}\n</chunk>")
    parts.append("</context>")
    return "\n".join(parts), suspicious


_CITE = re.compile(r"\[(\d+(?:\s*[-–,;]\s*\d+)*)\]")


def extract_citations(text: str) -> list[int]:
    """All chunk numbers cited as ``[1]``, ``[2, 3]``, ``[2; 3]`` or ``[1-3]``, in first-seen order."""
    seen: list[int] = []
    for m in _CITE.finditer(text):
        for part in re.split(r"[,;]", m.group(1)):
            lo, _, hi = part.replace("–", "-").partition("-")
            start, end = int(lo.strip()), int((hi or lo).strip())
            for n in range(start, min(end, start + 50) + 1):
                if n not in seen:
                    seen.append(n)
    return seen
