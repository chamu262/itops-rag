"""Typed records that flow through the pipeline: Document -> Chunk -> Hit -> Answer."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

ACCESS_LEVELS: tuple[str, ...] = ("public", "it-staff", "security")
"""Ordered from least to most privileged. A role sees its own level and every level below it."""


def visible_access(role: str) -> list[str]:
    """Access tags a caller with ``role`` may read.

    >>> visible_access("it-staff")
    ['public', 'it-staff']
    """
    if role not in ACCESS_LEVELS:
        raise ValueError(f"unknown role {role!r}; expected one of {ACCESS_LEVELS}")
    return list(ACCESS_LEVELS[: ACCESS_LEVELS.index(role) + 1])


@dataclass(slots=True)
class Document:
    """One source document after loading and before chunking."""

    id: str
    title: str
    text: str
    doc_type: str = "doc"
    system: str = "general"
    owner: str = ""
    access: str = "public"
    updated: str = ""
    tags: list[str] = field(default_factory=list)
    source: str = ""
    """Where it came from: a file path relative to the ingest root, or a URL."""
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.access not in ACCESS_LEVELS:
            raise ValueError(f"{self.id}: access must be one of {ACCESS_LEVELS}, got {self.access!r}")
        if not self.id:
            raise ValueError("document id must not be empty")

    @property
    def content_hash(self) -> str:
        h = hashlib.sha256()
        for part in (self.title, self.text, self.doc_type, self.system, self.access, self.updated, self.owner):
            h.update(part.encode())
            h.update(b"\x00")
        h.update(",".join(self.tags).encode())
        return h.hexdigest()[:16]

    def meta(self) -> dict[str, Any]:
        return {
            "doc_id": self.id,
            "title": self.title,
            "doc_type": self.doc_type,
            "system": self.system,
            "owner": self.owner,
            "access": self.access,
            "updated": self.updated,
            "tags": ",".join(self.tags),
            "source": self.source,
        }


@dataclass(slots=True)
class Chunk:
    id: str
    """``<doc_id>#<ordinal>``"""
    doc_id: str
    ordinal: int
    text: str
    """The chunk body shown to the model and to people."""
    heading: str = ""
    """Breadcrumb of section headings, e.g. ``Steps > Re-enrol``."""
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def embed_text(self) -> str:
        """Text that is embedded and keyword-indexed: title and heading on top give each chunk its context."""
        title = self.meta.get("title", "")
        head = f"{title} > {self.heading}" if self.heading else title
        return f"{head}\n{self.text}" if head else self.text


@dataclass(slots=True)
class Hit:
    chunk: Chunk
    score: float
    """Final score used for ordering (rerank score when reranking ran, else fused RRF score)."""
    vector_rank: int | None = None
    keyword_rank: int | None = None
    rerank_score: float | None = None

    @property
    def doc_id(self) -> str:
        return self.chunk.doc_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk.id,
            "doc_id": self.chunk.doc_id,
            "title": self.chunk.meta.get("title", ""),
            "heading": self.chunk.heading,
            "doc_type": self.chunk.meta.get("doc_type", ""),
            "system": self.chunk.meta.get("system", ""),
            "access": self.chunk.meta.get("access", ""),
            "owner": self.chunk.meta.get("owner", ""),
            "updated": self.chunk.meta.get("updated", ""),
            "source": self.chunk.meta.get("source", ""),
            "score": round(self.score, 4),
            "vector_rank": self.vector_rank,
            "keyword_rank": self.keyword_rank,
            "rerank_score": None if self.rerank_score is None else round(self.rerank_score, 4),
            "text": self.chunk.text,
        }


@dataclass(slots=True)
class Usage:
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: float = 0.0

    def __add__(self, other: Usage) -> Usage:
        return Usage(
            model=self.model or other.model,
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_read_tokens=self.cache_read_tokens + other.cache_read_tokens,
            cache_write_tokens=self.cache_write_tokens + other.cache_write_tokens,
            cost_usd=self.cost_usd + other.cost_usd,
        )


@dataclass(slots=True)
class Answer:
    question: str
    text: str
    hits: list[Hit]
    cited: list[int] = field(default_factory=list)
    """1-based chunk numbers the answer cites (validated against the context it was given)."""
    refused: bool = False
    reason: str = ""
    """Why it refused, or notes such as invalid citations or a suspicious chunk."""
    prompt_id: str = "qa"
    usage: Usage = field(default_factory=Usage)
    warnings: list[str] = field(default_factory=list)

    def sources(self) -> list[dict[str, Any]]:
        out = []
        for n in self.cited:
            if 1 <= n <= len(self.hits):
                h = self.hits[n - 1]
                out.append({"n": n, **{k: v for k, v in h.to_dict().items() if k != "text"}})
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "answer": self.text,
            "refused": self.refused,
            "reason": self.reason,
            "prompt_id": self.prompt_id,
            "cited": self.cited,
            "sources": self.sources(),
            "chunks": [h.to_dict() for h in self.hits],
            "warnings": self.warnings,
            "usage": {
                "model": self.usage.model,
                "input_tokens": self.usage.input_tokens,
                "output_tokens": self.usage.output_tokens,
                "cache_read_tokens": self.usage.cache_read_tokens,
                "cache_write_tokens": self.usage.cache_write_tokens,
                "cost_usd": round(self.usage.cost_usd, 6),
            },
        }
