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
# Name boundaries use (?<![A-Za-z0-9]) rather than \b, because "_" is a word character and names like
# aws_secret_access_key or DB_PASSWORD must still match.
_KEY_NAME_PATTERN = (
    r"[A-Za-z0-9_.-]*(?:pass(?:word|wd|phrase)?|pwd|secret|token|api[_-]?key|access[_-]?key|"
    r"private[_-]?key|client[_-]?secret|credentials?)[A-Za-z0-9_.-]*"
)
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "private_key",
        # With or without an END line (pasted keys are often truncated): stop at END, a blank line or end of text.
        re.compile(
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----(?:.*?-----END [A-Z ]*PRIVATE KEY-----|.*?(?=\n\s*\n|\Z))",
            re.DOTALL,
        ),
    ),
    ("aws_access_key", re.compile(r"(?<![A-Za-z0-9])(?:AKIA|ASIA)[A-Z0-9]{12,20}(?![A-Za-z0-9])")),
    (
        "github_token",
        re.compile(r"(?<![A-Za-z0-9])(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
    ),
    ("slack_token", re.compile(r"(?<![A-Za-z0-9])xox[abprs]-[A-Za-z0-9-]{10,}")),
    ("anthropic_key", re.compile(r"(?<![A-Za-z0-9])sk-ant-[A-Za-z0-9_-]{20,}")),
    ("api_key", re.compile(r"(?<![A-Za-z0-9])(?:sk|pk|rk)-[A-Za-z0-9_-]{16,}")),
    ("azure_client_secret", re.compile(r"(?<![A-Za-z0-9])[A-Za-z0-9_~.-]{3}\dQ~[A-Za-z0-9_~.-]{30,}")),
    ("google_api_key", re.compile(r"(?<![A-Za-z0-9])AIza[0-9A-Za-z_-]{30,}")),
    ("jwt", re.compile(r"(?<![A-Za-z0-9])eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]*")),
    ("auth_header", re.compile(r"(?i)(?<![A-Za-z0-9])(?:bearer|basic)\s+[A-Za-z0-9._~+/-]{12,}=*")),
    (
        "password",
        # name, separator, value (quoted values may contain spaces). The value must not itself be another
        # "name =" so that "secret: aws_secret_access_key = KEY" masks KEY, not the key's name.
        re.compile(
            rf"(?i)(?<![A-Za-z0-9])({_KEY_NAME_PATTERN})(\s*[:=]\s*)"
            r"""(?![A-Za-z0-9_.-]*\s*[:=])("[^"\n]*"|'[^'\n]*'|\S+)"""
        ),
    ),
    ("email", re.compile(r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![A-Za-z])")),
    ("phone", re.compile(r"(?<![\w.])\+\d{1,3}[ .-]?\(?\d{1,4}\)?(?:[ .-]?\d{2,4}){2,4}(?!\d)")),
    ("phone_national", re.compile(r"(?<![\w.+-])0\d{1,4}[ -]\d{2,4}(?:[ -]?\d{2,4}){1,3}(?![\d-])")),
    (
        "ipv4",
        re.compile(r"(?<![\d.])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?![\d.]\d)"),
    ),
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
                    if value.lstrip("\"'").startswith("[REDACTED"):
                        return m.group(0)  # already masked by an earlier, more specific pattern
                    if report is not None:
                        report.add(doc_id, kind)
                    return f"{m.group(1)}{m.group(2)}[REDACTED:{kind}]"
                if report is not None:
                    report.add(doc_id, kind)
                return f"[REDACTED:{kind}]"

            text = pattern.sub(_sub, text)
        return text
