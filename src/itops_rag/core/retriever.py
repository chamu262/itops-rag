"""Hybrid retrieval: BM25 + vector search, fused with Reciprocal Rank Fusion, then a cross-encoder rerank.

Why hybrid for IT ops: people search with exact strings ("AADSTS53003", "0x80180014", "MG-401", "HELP-1042") that
embeddings blur, *and* with paraphrases ("the VPN says I'm not authorised") that keywords miss. RRF needs no score
calibration between the two lists: each list contributes ``weight / (k + rank)``.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from itops_rag.config import SearchMode
from itops_rag.core.embeddings import Embedder
from itops_rag.core.models import Hit
from itops_rag.core.rerank import Reranker
from itops_rag.stores.docstore import DocStore
from itops_rag.stores.vectors import VectorStore

RRF_K = 60
CODE_LIKE = re.compile(r"\b(?:[A-Z]{2,}[-_]?\d{2,}|0x[0-9a-fA-F]{6,}|[A-Z]+-\d+)\b")


def rrf(
    rankings: Sequence[Sequence[str]], weights: Sequence[float] | None = None, k: int = RRF_K
) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion. ``rankings`` are lists of ids, best first."""
    weights = weights or [1.0] * len(rankings)
    scores: dict[str, float] = defaultdict(float)
    for ranking, w in zip(rankings, weights, strict=True):
        for rank, item in enumerate(ranking, start=1):
            scores[item] += w / (k + rank)
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))


def keyword_weight_for(query: str, base: float) -> float:
    """Exact identifiers in the query (error codes, ticket keys) make keyword matches worth more."""
    return base * 1.5 if CODE_LIKE.search(query) else base


def code_tokens(text: str) -> set[str]:
    """Exact identifiers in a question: error codes, ticket keys (``AADSTS53003``, ``0x80180014``, ``MG-401``)."""
    return {m.group(0).lower() for m in CODE_LIKE.finditer(text)} | {
        m.group(0).lower() for m in _CODE_LIKE_ANY_CASE.finditer(text)
    }


# Lower-case forms people type ("mg-777", "0X80180014", "aadsts53003"); narrower than CODE_LIKE so ordinary words
# with a number ("windows11", "office365") are not treated as codes.
_CODE_LIKE_ANY_CASE = re.compile(r"(?i)\b(?:[a-z]{1,8}-\d{2,}|0x[0-9a-f]{6,}|[a-z]{2,}\d{4,})\b")


@dataclass(slots=True)
class SearchFilters:
    access: list[str]
    doc_types: list[str] | None = None
    systems: list[str] | None = None


class HybridRetriever:
    def __init__(
        self,
        docs: DocStore,
        vectors: VectorStore,
        embedder: Embedder,
        reranker: Reranker | None,
        candidates: int = 30,
        keyword_weight: float = 1.0,
        vector_weight: float = 1.0,
        max_chunks_per_doc: int = 2,
        pool_chunks_per_doc: int = 0,
    ) -> None:
        self.docs = docs
        self.vectors = vectors
        self.embedder = embedder
        self.reranker = reranker
        self.candidates = candidates
        self.keyword_weight = keyword_weight
        self.vector_weight = vector_weight
        self.max_chunks_per_doc = max_chunks_per_doc
        self.pool_chunks_per_doc = pool_chunks_per_doc

    def search(
        self,
        query: str,
        k: int,
        filters: SearchFilters,
        mode: SearchMode = "hybrid_rerank",
        doc_type_boost: dict[str, float] | None = None,
    ) -> list[Hit]:
        """Hybrid search. ``doc_type_boost`` is added to the rerank score for *ordering only* (``rerank_score`` keeps
        the raw cross-encoder score, which the refusal gate uses). It lets authoritative sources (runbooks, KB,
        standards) outrank the many near-duplicate tickets that match the same symptom."""
        query = query.strip()
        if not query:
            return []
        n = max(self.candidates, k)
        vec: list[tuple[str, float]] = []
        kw: list[tuple[str, float]] = []
        if mode != "keyword":
            vec = self.vectors.search(
                self.embedder.embed_query(query), n, filters.access, filters.doc_types, filters.systems
            )
        if mode != "vector":
            kw = self.docs.keyword_search(query, n, filters.access, filters.doc_types, filters.systems)

        vec_rank = {cid: i for i, (cid, _) in enumerate(vec, start=1)}
        kw_rank = {cid: i for i, (cid, _) in enumerate(kw, start=1)}
        vec_sim = dict(vec)

        if mode == "vector":
            fused = [(cid, s) for cid, s in vec]
        elif mode == "keyword":
            fused = [(cid, s) for cid, s in kw]
        else:
            fused = rrf(
                [[c for c, _ in vec], [c for c, _ in kw]],
                [self.vector_weight, keyword_weight_for(query, self.keyword_weight)],
            )

        limit = n if mode == "hybrid_rerank" else max(k * 3, k)
        if self.pool_chunks_per_doc > 0:
            # Spread the candidate pool across documents: without this, a few long tickets (core + comments
            # chunks, each matching the same error code) can fill every slot and push the runbook out unseen.
            per_doc: dict[str, int] = defaultdict(int)
            spread: list[tuple[str, float]] = []
            for cid, score in fused:
                doc = cid.rsplit("#", 1)[0]
                if per_doc[doc] < self.pool_chunks_per_doc:
                    per_doc[doc] += 1
                    spread.append((cid, score))
            fused = spread
        pool = fused[:limit]
        chunks = self.docs.get_chunks([cid for cid, _ in pool])
        hits = [
            Hit(chunk=chunks[cid], score=score, vector_rank=vec_rank.get(cid), keyword_rank=kw_rank.get(cid))
            for cid, score in pool
            if cid in chunks
        ]
        for h in hits:
            h.chunk.meta["vector_similarity"] = vec_sim.get(h.chunk.id)

        if mode == "hybrid_rerank" and self.reranker is not None and hits:
            scores = self.reranker.score(query, [h.chunk.embed_text for h in hits])
            boost = doc_type_boost or {}
            for h, s in zip(hits, scores, strict=True):
                h.rerank_score = s
                h.score = s + boost.get(str(h.chunk.meta.get("doc_type", "")), 0.0)
            hits.sort(key=lambda h: -h.score)

        return self._diversify(hits, k)

    def _diversify(self, hits: list[Hit], k: int) -> list[Hit]:
        per_doc: dict[str, int] = defaultdict(int)
        out: list[Hit] = []
        for h in hits:
            if per_doc[h.doc_id] >= self.max_chunks_per_doc:
                continue
            per_doc[h.doc_id] += 1
            out.append(h)
            if len(out) == k:
                break
        return out
