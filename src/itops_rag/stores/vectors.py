"""Vector stores. Both implement the same small protocol, keyed by chunk id, so retrieval code never changes.

* ``SqliteVectorStore``: vectors in the same SQLite file as the docstore. Uses the sqlite-vec ``vec0`` table when the
  extension loads, and falls back to exact numpy search otherwise (fine up to tens of thousands of chunks).
* ``ChromaVectorStore``: a persistent Chroma collection with cosine HNSW and native ``where`` filters.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from itops_rag.core.embeddings import Vector
from itops_rag.stores.docstore import DocStore


class VectorStore(Protocol):
    kind: str

    def add(
        self,
        chunk_ids: Sequence[str],
        rowids: Sequence[int],
        vectors: Vector,
        metas: Sequence[dict[str, Any]],
    ) -> None: ...

    def delete(self, chunk_ids: Sequence[str], rowids: Sequence[int]) -> None: ...

    def search(
        self,
        query: Vector,
        k: int,
        access: Sequence[str],
        doc_types: Sequence[str] | None = None,
        systems: Sequence[str] | None = None,
    ) -> list[tuple[str, float]]:
        """Return ``(chunk_id, cosine_similarity)`` best first, already filtered."""
        ...


class SqliteVectorStore:
    def __init__(self, docstore: DocStore, dim: int, use_extension: bool = True) -> None:
        self.docs = docstore
        self.dim = dim
        self.conn = docstore.conn
        self.vec_enabled = use_extension and self._load_extension()
        self.kind = "sqlite-vec" if self.vec_enabled else "sqlite-numpy"
        if self.vec_enabled:
            self.conn.execute(
                f"CREATE VIRTUAL TABLE IF NOT EXISTS chunk_vec USING vec0(embedding float[{dim}] distance_metric=cosine)"
            )
        else:
            self.conn.execute(
                "CREATE TABLE IF NOT EXISTS chunk_vectors (rowid INTEGER PRIMARY KEY, vec BLOB NOT NULL)"
            )
        self._matrix: tuple[np.ndarray[Any, Any], np.ndarray[Any, Any]] | None = None

    def _load_extension(self) -> bool:
        try:
            import sqlite_vec

            self.conn.enable_load_extension(True)
            sqlite_vec.load(self.conn)
            self.conn.enable_load_extension(False)
            return True
        except (ImportError, AttributeError, Exception):
            return False

    def add(
        self,
        chunk_ids: Sequence[str],
        rowids: Sequence[int],
        vectors: Vector,
        metas: Sequence[dict[str, Any]],
    ) -> None:
        table = "chunk_vec(rowid, embedding)" if self.vec_enabled else "chunk_vectors(rowid, vec)"
        self.conn.executemany(
            f"INSERT OR REPLACE INTO {table} VALUES (?, ?)",  # noqa: S608
            [
                (int(r), np.asarray(v, dtype=np.float32).tobytes())
                for r, v in zip(rowids, vectors, strict=True)
            ],
        )
        self._matrix = None

    def delete(self, chunk_ids: Sequence[str], rowids: Sequence[int]) -> None:
        table = "chunk_vec" if self.vec_enabled else "chunk_vectors"
        self.conn.executemany(f"DELETE FROM {table} WHERE rowid = ?", [(int(r),) for r in rowids])  # noqa: S608
        self._matrix = None

    def _count(self) -> int:
        table = "chunk_vec" if self.vec_enabled else "chunk_vectors"
        return int(self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])  # noqa: S608

    def search(
        self,
        query: Vector,
        k: int,
        access: Sequence[str],
        doc_types: Sequence[str] | None = None,
        systems: Sequence[str] | None = None,
    ) -> list[tuple[str, float]]:
        total = self._count()
        if total == 0:
            return []
        # vec0 has no join-time filter here, so over-fetch and filter; widen until we have k or saw everything.
        fetch = min(total, max(k * 4, 50))
        while True:
            raw = self._raw_search(query, fetch)
            allowed = self.docs.allowed_rowids([r for r, _ in raw], access, doc_types, systems)
            hits = [(allowed[r], s) for r, s in raw if r in allowed]
            if len(hits) >= k or fetch >= total:
                return hits[:k]
            fetch = min(total, fetch * 4)

    def _raw_search(self, query: Vector, n: int) -> list[tuple[int, float]]:
        q = np.asarray(query, dtype=np.float32)
        if self.vec_enabled:
            rows = self.conn.execute(
                "SELECT rowid, distance FROM chunk_vec WHERE embedding MATCH ? AND k = ? ORDER BY distance",
                (q.tobytes(), n),
            ).fetchall()
            return [(int(r[0]), 1.0 - float(r[1])) for r in rows]
        if self._matrix is None:
            rows = self.conn.execute("SELECT rowid, vec FROM chunk_vectors").fetchall()
            ids = np.array([int(r[0]) for r in rows], dtype=np.int64)
            mat = np.vstack([np.frombuffer(r[1], dtype=np.float32) for r in rows])
            self._matrix = (ids, mat)
        ids, mat = self._matrix
        sims = mat @ q
        top = np.argsort(-sims)[:n]
        return [(int(ids[i]), float(sims[i])) for i in top]


class ChromaVectorStore:
    kind = "chroma"

    def __init__(self, path: Path, collection: str = "chunks") -> None:
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(path), settings=ChromaSettings(anonymized_telemetry=False)
        )
        self._col = self._client.get_or_create_collection(collection, metadata={"hnsw:space": "cosine"})

    def add(
        self,
        chunk_ids: Sequence[str],
        rowids: Sequence[int],
        vectors: Vector,
        metas: Sequence[dict[str, Any]],
    ) -> None:
        if not chunk_ids:
            return
        keep = ("doc_id", "access", "doc_type", "system")
        self._col.upsert(
            ids=list(chunk_ids),
            embeddings=[v.tolist() for v in vectors],
            metadatas=[{k: str(m.get(k, "")) for k in keep} for m in metas],
        )

    def delete(self, chunk_ids: Sequence[str], rowids: Sequence[int]) -> None:
        if chunk_ids:
            self._col.delete(ids=list(chunk_ids))

    def search(
        self,
        query: Vector,
        k: int,
        access: Sequence[str],
        doc_types: Sequence[str] | None = None,
        systems: Sequence[str] | None = None,
    ) -> list[tuple[str, float]]:
        n = self._col.count()
        if n == 0:
            return []
        conds: list[dict[str, Any]] = [{"access": {"$in": list(access)}}]
        if doc_types:
            conds.append({"doc_type": {"$in": list(doc_types)}})
        if systems:
            conds.append({"system": {"$in": list(systems)}})
        where: dict[str, Any] = conds[0] if len(conds) == 1 else {"$and": conds}
        res = self._col.query(
            query_embeddings=[query.tolist()], n_results=min(k, n), where=where, include=["distances"]
        )
        ids = res["ids"][0]
        dists = (res.get("distances") or [[]])[0]
        return [(str(i), 1.0 - float(d)) for i, d in zip(ids, dists, strict=True)]
