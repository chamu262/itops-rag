"""``Index``: the one object callers use. Ingest, search and ask against one index folder.

    from itops_rag import Index, Settings
    ix = Index.open(Settings(index_dir=Path("~/.nova/rag").expanduser(), store="sqlite"))
    ix.ingest_path(Path("~/notes"))
    for hit in ix.search("which backup schedule did I pick?", role="public"):
        print(hit.doc_id, hit.score)

Each app (IT Ops, Nova, Agentic OS, Godfather) opens its own index folder; the engine is shared, the data is not.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from itops_rag.config import SearchMode, Settings
from itops_rag.core.chunking import chunk_document
from itops_rag.core.embeddings import Embedder, FastEmbedder
from itops_rag.core.generate import Generator, MessagesClient
from itops_rag.core.models import Answer, Document, Hit, visible_access
from itops_rag.core.redact import RedactionReport, Redactor
from itops_rag.core.rerank import CrossEncoderReranker, Reranker
from itops_rag.core.retriever import HybridRetriever, SearchFilters
from itops_rag.loaders import load_path
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
        self, documents: Iterable[Document], *, prune_missing: bool = False, batch_size: int = 64
    ) -> IngestReport:
        """Redact, chunk, embed and store documents. Unchanged documents (same content hash) are skipped."""
        report = IngestReport()
        seen: set[str] = set()
        pending: list[tuple[Document, list[Any]]] = []

        for doc in documents:
            seen.add(doc.id)
            if self.settings.redact:
                extra = frozenset({"ipv4"}) if doc.extra.get("redact_ip") else frozenset()
                doc.text = self.redactor.redact(doc.text, doc.id, report.redaction, extra)
                doc.title = self.redactor.redact(doc.title, doc.id, report.redaction, extra)
            existing = self.docs.doc_hash(doc.id)
            if existing == doc.content_hash:
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
            stale = self.docs.all_doc_ids() - seen
            self.delete(stale)
            report.removed = len(stale)
        self.docs.commit()
        return report

    def _flush(self, pending: list[tuple[Document, list[Any]]]) -> int:
        all_chunks = [c for _, chunks in pending for c in chunks]
        vectors = self.embedder.embed_documents([c.embed_text for c in all_chunks])
        offset = 0
        for doc, chunks in pending:
            old = self.docs.conn.execute(
                "SELECT id, rowid FROM chunks WHERE doc_id = ?", (doc.id,)
            ).fetchall()
            if old:
                self.vectors.delete([r[0] for r in old], [int(r[1]) for r in old])
            rowids = self.docs.upsert(doc, chunks)
            self.vectors.add(
                [c.id for c in chunks],
                rowids,
                vectors[offset : offset + len(chunks)],
                [c.meta for c in chunks],
            )
            offset += len(chunks)
        return len(all_chunks)

    def ingest_path(self, path: Path, *, prune_missing: bool = False) -> IngestReport:
        documents, errors = load_path(path.expanduser())
        report = self.ingest(documents, prune_missing=prune_missing)
        report.errors.extend(errors)
        return report

    def delete(self, doc_ids: Iterable[str]) -> None:
        for doc_id in list(doc_ids):
            chunk_rows = self.docs.conn.execute(
                "SELECT id, rowid FROM chunks WHERE doc_id = ?", (doc_id,)
            ).fetchall()
            self.vectors.delete([r[0] for r in chunk_rows], [int(r[1]) for r in chunk_rows])
            self.docs.delete([doc_id])
        self.docs.commit()

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
    ) -> list[Hit]:
        filters = SearchFilters(
            access=visible_access(role or self.settings.default_role),
            doc_types=list(doc_types) if doc_types else None,
            systems=list(systems) if systems else None,
        )
        mode = mode or self.settings.mode
        if mode == "hybrid_rerank" and self.reranker is None:
            mode = "hybrid"
        return self.retriever.search(query, k or self.settings.top_k, filters, mode)

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
        assistant_name: str = "IT Ops RAG",
        audience: str = "the IT operations team",
    ) -> Answer:
        template = self.prompts.get(prompt)
        if template.needs_input and not input_text.strip():
            raise ValueError(f"prompt {template.id!r} needs {template.input_label!r} text (use --input)")
        query = question
        if self.settings.rewrite_queries and not dry_run:
            query = self.generator.rewrite_query(question)
        hits = self.search(
            query,
            k=k or template.top_k or self.settings.top_k,
            role=role,
            doc_types=template.doc_types,
            systems=systems,
        )
        return self.generator.answer(
            question,
            hits,
            template,
            input_text=input_text,
            dry_run=dry_run,
            assistant_name=assistant_name,
            audience=audience,
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
        hits = self.search(
            question, k=k or template.top_k or self.settings.top_k, role=role, doc_types=template.doc_types
        )
        ans = self.generator.answer(question, hits, template, input_text=input_text, dry_run=True)
        return {
            "refused": ans.refused,
            "reason": ans.reason,
            "warnings": ans.warnings,
            "system": self.generator.system_prompt("IT Ops RAG", "the IT operations team"),
            "prompt": ans.text.split("--- user ---\n", 1)[-1] if not ans.refused else ans.text,
            "chunks": [h.to_dict() for h in hits],
        }

    def get_document(self, doc_id: str, role: str | None = None) -> dict[str, Any] | None:
        d = self.docs.get_document(doc_id)
        if d is None or d["access"] not in visible_access(role or self.settings.default_role):
            return None
        return d

    def stats(self) -> dict[str, Any]:
        return {
            **self.docs.stats(),
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
