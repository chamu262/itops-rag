"""Mask secrets and personal data before anything is embedded or stored.

Redaction runs at ingest, so the index (and therefore every prompt and every answer) never holds the original value.
Patterns are deliberately conservative: a false positive costs a little context, a false negative leaks a secret.

What regexes cannot do: recognise personal names in free text. Loaders drop known people fields (reporter,
assignee) instead, and the README says so.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

# Order matters: multi-line and specific secrets first, generic patterns last.
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "private_key",
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL),
    ),
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{12,20}\b")),
    ("github_token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")),
    ("slack_token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("api_key", re.compile(r"\b(?:sk|pk|rk)-(?:[A-Za-z0-9]+-)?[A-Za-z0-9_]{16,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
    ("bearer_token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/-]{20,}=*")),
    (
        "password",
        re.compile(
            r"(?im)\b(pass(?:word|wd|phrase)?|pwd|secret|client_secret|api[_-]?key|token)\b(\s*[:=]\s*)(\S+)"
        ),
    ),
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("phone", re.compile(r"(?<![\w.])\+\d{1,3}[ .-]?\(?\d{1,4}\)?(?:[ .-]?\d{2,4}){2,4}(?![\w.])")),
    ("ipv4", re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")),
]

DEFAULT_KINDS = frozenset(name for name, _ in _PATTERNS) - {"ipv4"}
"""IPs are kept by default: runbooks need gateway and subnet addresses. Turn ``ipv4`` on for ticket text."""


@dataclass(slots=True)
class RedactionReport:
    counts: Counter[str] = field(default_factory=Counter)
    per_doc: dict[str, Counter[str]] = field(default_factory=dict)

    def add(self, doc_id: str, kind: str, n: int = 1) -> None:
        self.counts[kind] += n
        self.per_doc.setdefault(doc_id, Counter())[kind] += n

    @property
    def total(self) -> int:
        return sum(self.counts.values())


class Redactor:
    def __init__(self, kinds: frozenset[str] = DEFAULT_KINDS, keep_emails: list[str] | None = None) -> None:
        unknown = kinds - {n for n, _ in _PATTERNS}
        if unknown:
            raise ValueError(f"unknown redaction kinds: {sorted(unknown)}")
        self.kinds = kinds
        self._keep = [re.compile(p, re.IGNORECASE) for p in (keep_emails or [])]

    def redact(
        self,
        text: str,
        doc_id: str = "",
        report: RedactionReport | None = None,
        extra_kinds: frozenset[str] = frozenset(),
    ) -> str:
        kinds = self.kinds | extra_kinds
        for kind, pattern in _PATTERNS:
            if kind not in kinds:
                continue

            def _sub(m: re.Match[str], kind: str = kind) -> str:
                if kind == "email" and any(k.search(m.group(0)) for k in self._keep):
                    return m.group(0)
                if kind == "password":
                    value = m.group(3)
                    if value.startswith("[") and value.endswith("]"):
                        return m.group(0)  # already masked by an earlier, more specific pattern
                    if report is not None:
                        report.add(doc_id, kind)
                    return f"{m.group(1)}{m.group(2)}[REDACTED:{kind}]"
                if report is not None:
                    report.add(doc_id, kind)
                return f"[REDACTED:{kind}]"

            text = pattern.sub(_sub, text)
        return text
