"""``Index``: the one object callers use. Ingest, search and ask against one index folder.

    from itops_rag import Index, Settings
    ix = Index.open(Settings(index_dir=Path("~/.nova/rag").expanduser(), store="sqlite"))
    ix.ingest_path(Path("~/notes"))
    for hit in ix.search("which backup schedule did I pick?", role="public"):
        print(hit.doc_id, hit.score)

Each app (IT Ops, Nova, Agentic OS, Godfather) opens its own index folder; the engine is shared, the data is not.
"""

from __future__ import annotations

import hashlib
import logging
import threading
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from itops_rag.config import SearchMode, Settings
from itops_rag.core.chunking import CHUNKER_VERSION, chunk_document, join_overlapping
from itops_rag.core.embeddings import Embedder, FastEmbedder
from itops_rag.core.generate import Generator, MessagesClient, gate
from itops_rag.core.models import Answer, Chunk, Document, Hit, visible_access
from itops_rag.core.redact import REDACTION_VERSION, RedactionReport, Redactor
from itops_rag.core.rerank import CrossEncoderReranker, Reranker
from itops_rag.core.retriever import HybridRetriever, SearchFilters
from itops_rag.loaders import load_tree
from itops_rag.prompts.registry import PromptRegistry
from itops_rag.stores.docstore import DocStore
from itops_rag.stores.vectors import ChromaVectorStore, SqliteVectorStore, VectorStore

log = logging.getLogger(__name__)


class IndexMismatchError(RuntimeError):
    """The index was built with a different embedding model, dimension or store."""


@dataclass(slots=True)
class IngestReport:
    added: int = 0
    updated: int = 0
    unchanged: int = 0
    removed: int = 0
    chunks: int = 0
    errors: list[str] = field(default_factory=list)
    redaction: RedactionReport = field(default_factory=RedactionReport)

    def to_dict(self) -> dict[str, Any]:
        return {
            "added": self.added,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "removed": self.removed,
            "chunks": self.chunks,
            "errors": self.errors,
            "redacted": dict(self.redaction.counts),
        }


class Index:
    def __init__(
        self,
        settings: Settings,
        docs: DocStore,
        vectors: VectorStore,
        embedder: Embedder,
        reranker: Reranker | None,
        prompts: PromptRegistry,
        generator: Generator,
    ) -> None:
        self.settings = settings
        self.docs = docs
        self.vectors = vectors
        self.embedder = embedder
        self.reranker = reranker
        self.prompts = prompts
        self.generator = generator
        self.redactor = Redactor(keep_emails=settings.redact_keep_emails)
        # One SQLite connection is shared by the docstore and sqlite-vec, and FastAPI/MCP call in from worker
        # threads. Every index operation takes this lock; the Claude call in ask() runs outside it.
        self._lock = threading.RLock()
        # Anything that changes what gets stored for the same source text. It is folded into every stored document
        # hash, so changing chunk size or redaction patterns re-processes documents instead of silently skipping them.
        self.fingerprint = (
            f"chunker={CHUNKER_VERSION};size={settings.chunk_size};overlap={settings.chunk_overlap};"
            f"redaction={REDACTION_VERSION};redact={settings.redact};keep={','.join(settings.redact_keep_emails)}"
        )
        self.retriever = HybridRetriever(
            docs,
            vectors,
            embedder,
            reranker,
            candidates=settings.candidates,
            keyword_weight=settings.keyword_weight,
            vector_weight=settings.vector_weight,
            max_chunks_per_doc=settings.max_chunks_per_doc,
        )

    # ----- construction ---------------------------------------------------------------------------------------
    @classmethod
    def open(
        cls,
        settings: Settings | None = None,
        *,
        embedder: Embedder | None = None,
        reranker: Reranker | bool | None = True,
        client: MessagesClient | None = None,
        prompts: PromptRegistry | None = None,
    ) -> Index:
        """Open (or create) the index in ``settings.index_dir``.

        ``reranker=True`` loads the local cross-encoder, ``False``/``None`` disables reranking, or pass your own.
        """
        settings = settings or Settings()
        index_dir = settings.index_dir.expanduser()
        docs = DocStore(index_dir / "docstore.sqlite")
        embedder = embedder or FastEmbedder(settings.embed_model, settings.model_cache_dir)

        store_kind = docs.get_meta("store") or settings.resolved_store()
        for key, want in (("embed_model", embedder.name), ("embed_dim", str(embedder.dim))):
            have = docs.get_meta(key)
            if have is not None and have != want:
                raise IndexMismatchError(
                    f"index at {index_dir} was built with {key}={have}, not {want}. Rebuild it with --rebuild."
                )
        if settings.store != "auto" and docs.get_meta("store") not in (None, settings.store):
            raise IndexMismatchError(
                f"index at {index_dir} uses store {docs.get_meta('store')}, not {settings.store}"
            )

        vectors: VectorStore
        if store_kind == "chroma":
            vectors = ChromaVectorStore(index_dir / "chroma")
        else:
            vectors = SqliteVectorStore(docs, embedder.dim)
        docs.set_meta("store", store_kind)
        docs.set_meta("embed_model", embedder.name)
        docs.set_meta("embed_dim", str(embedder.dim))
        docs.commit()

        rr: Reranker | None
        if reranker is True:
            rr = CrossEncoderReranker(settings.rerank_model, settings.model_cache_dir)
        elif reranker is False or reranker is None:
            rr = None
        else:
            rr = reranker
        if rr is not None:
            # The refusal threshold is calibrated on one reranker's score scale; switching rerankers needs re-tuning.
            previous = docs.get_meta("rerank_model")
            if previous and previous != rr.name:
                log.warning(
                    "index was tuned with reranker %s, now using %s: re-check min_rerank_score with `itops-rag eval`",
                    previous,
                    rr.name,
                )
            docs.set_meta("rerank_model", rr.name)
            docs.commit()
        prompts = prompts or PromptRegistry.default(settings.prompt_dirs)
        return cls(settings, docs, vectors, embedder, rr, prompts, Generator(settings, client))

    @staticmethod
    def wipe(settings: Settings) -> None:
        """Delete an index folder's contents (used by ``--rebuild``)."""
        import shutil

        d = settings.index_dir.expanduser()
        if d.exists():
            shutil.rmtree(d)

    # ----- ingest ---------------------------------------------------------------------------------------------
    def ingest(
        self,
        documents: Iterable[Document],
        *,
        prune_missing: bool = False,
        prune_root: str | None = None,
        keep_ids: Iterable[str] = (),
        batch_size: int = 64,
    ) -> IngestReport:
        """Redact, chunk, embed and store documents. Unchanged documents (same content hash) are skipped.

        ``prune_missing`` deletes indexed documents that are not in this batch. With ``prune_root`` it only considers
        documents previously ingested from that root (so pruning one folder never touches another folder's docs).
        ``keep_ids`` are never pruned (``ingest_path`` passes documents whose files failed to load this run).
        """
        with self._lock:
            report = IngestReport()
            seen: set[str] = set(keep_ids)
            pending: list[tuple[Document, list[Any]]] = []

            for doc in documents:
                seen.add(doc.id)
                if prune_root is not None:
                    doc.extra["ingest_root"] = prune_root
                if self.settings.redact:
                    extra = frozenset({"ipv4"}) if doc.extra.get("redact_ip") else frozenset()
                    doc.text = self.redactor.redact(doc.text, doc.id, report.redaction, extra)
                    doc.title = self.redactor.redact(doc.title, doc.id, report.redaction, extra)
                stored_hash = hashlib.sha256(f"{doc.content_hash}|{self.fingerprint}".encode()).hexdigest()[
                    :16
                ]
                doc.extra["_stored_hash"] = stored_hash
                existing = self.docs.doc_hash(doc.id)
                if existing == stored_hash:
                    report.unchanged += 1
                    continue
                if existing is None:
                    report.added += 1
                else:
                    report.updated += 1
                chunks = chunk_document(doc, self.settings.chunk_size, self.settings.chunk_overlap)
                pending.append((doc, chunks))
                if sum(len(c) for _, c in pending) >= batch_size:
                    report.chunks += self._flush(pending)
                    pending = []
            if pending:
                report.chunks += self._flush(pending)

            if prune_missing:
                candidates = (
                    self.docs.doc_ids_for_root(prune_root)
                    if prune_root is not None
                    else self.docs.all_doc_ids()
                )
                stale = candidates - seen
                self._delete(stale)
                report.removed = len(stale)
            self.docs.commit()
            return report

    def _flush(self, pending: list[tuple[Document, list[Any]]]) -> int:
        all_chunks = [c for _, chunks in pending for c in chunks]
        vectors = self.embedder.embed_documents([c.embed_text for c in all_chunks])
        offset = 0
        for doc, chunks in pending:
            old = self.docs.chunk_rows(doc.id)
            if old:
                self.vectors.delete([cid for cid, _ in old], [rid for _, rid in old])
            rowids = self.docs.upsert(
                doc, chunks, content_hash=str(doc.extra.pop("_stored_hash", "")) or None
            )
            self.vectors.add(
                [c.id for c in chunks],
                rowids,
                vectors[offset : offset + len(chunks)],
                [c.meta for c in chunks],
            )
            offset += len(chunks)
        return len(all_chunks)

    def ingest_path(self, path: Path, *, prune_missing: bool = False) -> IngestReport:
        """Ingest a file or folder. Pruning is scoped to documents that came from this same path."""
        root = path.expanduser().resolve()
        documents, errors, failed_sources = load_tree(root, default_access=self.settings.default_access)
        keep = self.docs.doc_ids_for_sources(root.as_posix(), failed_sources) if prune_missing else set()
        report = self.ingest(
            documents, prune_missing=prune_missing, prune_root=root.as_posix(), keep_ids=keep
        )
        report.errors.extend(errors)
        return report

    def delete(self, doc_ids: Iterable[str]) -> None:
        with self._lock:
            self._delete(doc_ids)
            self.docs.commit()

    def _delete(self, doc_ids: Iterable[str]) -> None:
        for doc_id in list(doc_ids):
            rows = self.docs.chunk_rows(doc_id)
            self.vectors.delete([cid for cid, _ in rows], [rid for _, rid in rows])
            self.docs.delete([doc_id])

    # ----- query ----------------------------------------------------------------------------------------------
    def search(
        self,
        query: str,
        *,
        k: int | None = None,
        role: str | None = None,
        doc_types: Sequence[str] | None = None,
        systems: Sequence[str] | None = None,
        mode: SearchMode | None = None,
        doc_type_boost: dict[str, float] | None = None,
    ) -> list[Hit]:
        filters = SearchFilters(
            access=visible_access(role or self.settings.default_role),
            doc_types=list(doc_types) if doc_types else None,
            systems=list(systems) if systems else None,
        )
        mode = mode or self.settings.mode
        if mode == "hybrid_rerank" and self.reranker is None:
            mode = "hybrid"
        with self._lock:
            return self.retriever.search(
                query,
                k or self.settings.top_k,
                filters,
                mode,
                self.settings.doc_type_boost if doc_type_boost is None else doc_type_boost,
            )

    def boosts_for(self, template_boost: dict[str, float] | None) -> dict[str, float]:
        return {**self.settings.doc_type_boost, **(template_boost or {})}

    def expand(self, hits: list[Hit]) -> list[Hit]:
        """Small-to-big: give the model each hit's whole section (or the whole document when it is short), not the
        800-character chunk that happened to match. Heading-split chunks are often a few hundred characters, and a
        step list split across chunks ("fix: see step 3") is useless without its neighbours. Tickets stay as they
        are. Stops at ``context_char_budget``."""
        out: list[Hit] = []
        used = 0
        seen: set[tuple[str, str]] = set()
        with self._lock:
            for h in hits:
                text, heading = h.chunk.text, h.chunk.heading
                if h.chunk.meta.get("doc_type") != "ticket":
                    doc = self.docs.get_document(h.doc_id)
                    if doc and len(doc["text"]) <= self.settings.expand_whole_doc_chars:
                        text, heading = doc["text"], ""
                    else:
                        parts = self.docs.section_texts(h.doc_id, h.chunk.heading)
                        if parts:
                            text = join_overlapping(parts, self.settings.chunk_overlap + 50)
                key = (h.doc_id, heading if text != h.chunk.text else h.chunk.id)
                if key in seen or (h.doc_id, "") in seen:
                    continue
                remaining = self.settings.context_char_budget - used
                if remaining < 300:
                    break
                if len(text) > remaining:
                    text = text[:remaining].rstrip() + "\n[... truncated to fit the context budget]"
                seen.add(key)
                used += len(text)
                chunk = Chunk(
                    id=h.chunk.id,
                    doc_id=h.doc_id,
                    ordinal=h.chunk.ordinal,
                    text=text,
                    heading=heading,
                    meta=dict(h.chunk.meta),
                )
                out.append(
                    Hit(
                        chunk=chunk,
                        score=h.score,
                        vector_rank=h.vector_rank,
                        keyword_rank=h.keyword_rank,
                        rerank_score=h.rerank_score,
                    )
                )
        return out

    @staticmethod
    def retrieval_query(question: str, input_text: str, needs_input: bool, limit: int = 1500) -> str:
        """What to search for. For templates that take pasted text (a ticket, a change plan) the pasted text is the
        real subject, and a question like "Triage this" carries no signal, so the input leads the query."""
        if not needs_input or not input_text.strip():
            return question
        return f"{input_text.strip()[:limit]}\n{question}"

    def ask(
        self,
        question: str,
        *,
        prompt: str = "qa",
        input_text: str = "",
        role: str | None = None,
        k: int | None = None,
        systems: Sequence[str] | None = None,
        dry_run: bool = False,
        assistant_name: str | None = None,
        audience: str | None = None,
    ) -> Answer:
        template = self.prompts.get(prompt)
        if template.needs_input and not input_text.strip():
            raise ValueError(f"prompt {template.id!r} needs {template.input_label!r} text (use --input)")
        k = k or template.top_k or self.settings.top_k
        query = self.retrieval_query(question, input_text, template.needs_input)
        boosts = self.boosts_for(template.doc_type_boost)
        hits = self.search(
            query, k=k, role=role, doc_types=template.doc_types, systems=systems, doc_type_boost=boosts
        )
        # Query rewriting costs a fast-model call, so it only runs once the free gate has passed.
        if self.settings.rewrite_queries and not dry_run and gate(hits, self.settings, question) is None:
            rewritten = self.generator.rewrite_query(query)
            if rewritten.strip() and rewritten.strip() != query.strip():
                better = self.search(
                    rewritten,
                    k=k,
                    role=role,
                    doc_types=template.doc_types,
                    systems=systems,
                    doc_type_boost=boosts,
                )
                if better and gate(better, self.settings, question) is None:
                    hits = better
        return self.generator.answer(
            question,
            self.expand(hits),
            template,
            input_text=input_text,
            dry_run=dry_run,
            assistant_name=assistant_name or self.settings.assistant_name,
            audience=audience or self.settings.audience,
        )

    def context_for(
        self,
        question: str,
        *,
        prompt: str = "qa",
        input_text: str = "",
        role: str | None = None,
        k: int | None = None,
    ) -> dict[str, Any]:
        """Retrieval plus the fully rendered prompt, *without* calling a model.

        This is the cheapest way for an agent that already runs on Claude (Claude Code, an MCP client) to use the
        index: it gets grounded, fenced context and answers with its own model, so there is no second API bill.
        """
        template = self.prompts.get(prompt)
        if template.needs_input and not input_text.strip():
            raise ValueError(f"prompt {template.id!r} needs {template.input_label!r} text")
        query = self.retrieval_query(question, input_text, template.needs_input)
        hits = self.expand(
            self.search(
                query,
                k=k or template.top_k or self.settings.top_k,
                role=role,
                doc_types=template.doc_types,
                doc_type_boost=self.boosts_for(template.doc_type_boost),
            )
        )
        ans = self.generator.answer(
            question,
            hits,
            template,
            input_text=input_text,
            dry_run=True,
            assistant_name=self.settings.assistant_name,
            audience=self.settings.audience,
        )
        return {
            "refused": ans.refused,
            "reason": ans.reason,
            "warnings": ans.warnings,
            "system": self.generator.system_prompt(self.settings.assistant_name, self.settings.audience),
            "prompt": ans.text.split("--- user ---\n", 1)[-1] if not ans.refused else ans.text,
            "chunks": [h.to_dict() for h in hits],
        }

    def get_document(self, doc_id: str, role: str | None = None) -> dict[str, Any] | None:
        with self._lock:
            d = self.docs.get_document(doc_id)
        if d is None or d["access"] not in visible_access(role or self.settings.default_role):
            return None
        return d

    def stats(self) -> dict[str, Any]:
        with self._lock:
            base = self.docs.stats()
        return {
            **base,
            "store": self.vectors.kind,
            "embed_model": self.embedder.name,
            "reranker": getattr(self.reranker, "name", None),
            "index_dir": str(self.settings.index_dir),
        }

    def close(self) -> None:
        self.docs.close()

    def __enter__(self) -> Index:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
