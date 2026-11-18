"""Local embeddings. No API key and no text leaves the machine.

``FastEmbedder`` runs sentence-transformers/all-MiniLM-L6-v2 (384 dimensions) through ONNX Runtime via fastembed,
which gives the same vectors as the HuggingFace model without installing torch. ``HashEmbedder`` is a deterministic,
model-free stand-in for tests and dry runs.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import numpy.typing as npt

Vector = npt.NDArray[np.float32]


class Embedder(Protocol):
    name: str
    dim: int

    def embed_documents(self, texts: Sequence[str]) -> Vector: ...

    def embed_query(self, text: str) -> Vector: ...


def _normalise(m: npt.NDArray[Any]) -> Vector:
    m = np.asarray(m, dtype=np.float32)
    norms = np.linalg.norm(m, axis=-1, keepdims=True)
    norms[norms == 0] = 1.0
    return (m / norms).astype(np.float32)


class FastEmbedder:
    def __init__(self, model: str = "sentence-transformers/all-MiniLM-L6-v2", cache_dir: Path | None = None,
                 batch_size: int = 64) -> None:
        self.name = model
        self._cache_dir = cache_dir
        self._batch_size = batch_size
        self._model: Any = None
        self.dim = self._lookup_dim(model)

    @staticmethod
    def _lookup_dim(model: str) -> int:
        from fastembed import TextEmbedding

        for m in TextEmbedding.list_supported_models():
            if m["model"].lower() == model.lower():
                return int(m["dim"])
        raise ValueError(f"fastembed does not support embedding model {model!r}")

    def _load(self) -> Any:
        if self._model is None:
            from fastembed import TextEmbedding

            self._model = TextEmbedding(self.name, cache_dir=str(self._cache_dir) if self._cache_dir else None)
        return self._model

    def embed_documents(self, texts: Sequence[str]) -> Vector:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        vecs = list(self._load().embed(list(texts), batch_size=self._batch_size))
        return _normalise(np.vstack(vecs))

    def embed_query(self, text: str) -> Vector:
        return _normalise(np.asarray(next(iter(self._load().query_embed(text))), dtype=np.float32))


_TOKEN = re.compile(r"[a-z0-9]+")


class HashEmbedder:
    """Bag of hashed word and character-trigram features. Deterministic, instant, good enough for unit tests."""

    def __init__(self, dim: int = 256) -> None:
        self.name = f"hash-{dim}"
        self.dim = dim

    def _features(self, text: str) -> Iterable[str]:
        words = _TOKEN.findall(text.lower())
        yield from words
        for w in words:
            padded = f"#{w}#"
            yield from (padded[i : i + 3] for i in range(len(padded) - 2))

    def _vec(self, text: str) -> Vector:
        v = np.zeros(self.dim, dtype=np.float32)
        for f in self._features(text):
            h = int.from_bytes(hashlib.blake2b(f.encode(), digest_size=8).digest(), "little")
            v[h % self.dim] += 1.0 if (h >> 63) & 1 else -1.0
        return v

    def embed_documents(self, texts: Sequence[str]) -> Vector:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        return _normalise(np.vstack([self._vec(t) for t in texts]))

    def embed_query(self, text: str) -> Vector:
        return _normalise(self._vec(text))
