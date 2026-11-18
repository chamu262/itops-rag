"""Second-stage reranking with a local cross-encoder.

Hybrid retrieval is good at recall; a cross-encoder reads the query and each candidate together and is much better at
precision. ms-marco-MiniLM-L-6-v2 is ~80 MB, runs on CPU in a few milliseconds per pair, and costs nothing per query.
Scores are logits: above 0 is a likely match, below about -2 is usually unrelated (that is what the refusal gate uses).
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol


class Reranker(Protocol):
    name: str

    def score(self, query: str, texts: Sequence[str]) -> list[float]: ...


class CrossEncoderReranker:
    def __init__(self, model: str = "Xenova/ms-marco-MiniLM-L-6-v2", cache_dir: Path | None = None) -> None:
        self.name = model
        self._cache_dir = cache_dir
        self._model: Any = None

    def _load(self) -> Any:
        if self._model is None:
            from fastembed.rerank.cross_encoder import TextCrossEncoder

            self._model = TextCrossEncoder(
                self.name, cache_dir=str(self._cache_dir) if self._cache_dir else None
            )
        return self._model

    def score(self, query: str, texts: Sequence[str]) -> list[float]:
        if not texts:
            return []
        return [float(s) for s in self._load().rerank(query, list(texts))]


class OverlapReranker:
    """Model-free reranker for tests: fraction of query words present in the text, mapped to a logit-like range."""

    name = "overlap"

    def score(self, query: str, texts: Sequence[str]) -> list[float]:
        q = {w for w in query.lower().split() if len(w) > 2}
        out = []
        for t in texts:
            words = set(t.lower().split())
            frac = len(q & words) / len(q) if q else 0.0
            out.append(frac * 10 - 5)
        return out
