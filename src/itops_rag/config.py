"""Settings, read from environment variables (prefix ``ITOPS_RAG_``), a ``.env`` file, or passed in code.

Every knob has a safe default, so ``Settings()`` works with no configuration at all.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

StoreKind = Literal["auto", "sqlite", "chroma"]
SearchMode = Literal["vector", "keyword", "hybrid", "hybrid_rerank"]
Effort = Literal["low", "medium", "high", "xhigh", "max"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ITOPS_RAG_", env_file=".env", extra="ignore")

    # Where the index lives. One folder per index: docstore.sqlite (+ chroma/ when that store is used).
    index_dir: Path = Field(default=Path(".itops-rag/index"))
    store: StoreKind = "auto"
    """``auto`` uses Chroma when it is installed, else SQLite (sqlite-vec, or numpy when the extension can't load)."""

    # Local models (downloaded once to the fastembed cache, then fully offline).
    embed_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    rerank_model: str = "Xenova/ms-marco-MiniLM-L-6-v2"
    model_cache_dir: Path | None = None

    # Chunking
    chunk_size: int = 800
    chunk_overlap: int = 100

    # Retrieval
    mode: SearchMode = "hybrid_rerank"
    top_k: int = 4
    candidates: int = 30
    """How many chunks each retriever returns before fusion, and how many go to the reranker."""
    keyword_weight: float = 1.0
    vector_weight: float = 1.0
    max_chunks_per_doc: int = 2
    """Diversity cap: stops one long document from filling the whole context."""
    min_rerank_score: float = -2.0
    """Refuse locally (no API call) when the best cross-encoder score is below this. Tuned with ``itops-rag eval``."""
    min_vector_similarity: float = 0.30
    """Refusal gate used when reranking is off."""

    # Identity used in the system prompt (a personal agent would set its own name and audience).
    assistant_name: str = "IT Ops RAG"
    audience: str = "the IT operations team"

    # Access
    default_role: str = "it-staff"

    # Generation (Claude)
    answer_model: str = "claude-opus-5-5"
    fast_model: str = "claude-haiku-5-5"
    """Used for cheap steps: query rewriting, ticket triage labels, the faithfulness check."""
    effort: Effort = "medium"
    max_tokens: int = 4096
    server_fallbacks: bool = True
    """Send ``fallbacks: "default"`` so a safety-classifier decline is retried on a fallback model in the same call."""
    rewrite_queries: bool = False
    verify_answers: bool = False

    # Cost control
    monthly_budget_usd: float = 25.0
    cost_ledger: Path = Field(default=Path(".itops-rag/costs.jsonl"))

    # Redaction at ingest
    redact: bool = True
    redact_keep_emails: list[str] = Field(
        default_factory=lambda: [r"^(servicedesk|it-oncall|security|noreply)@"]
    )
    """Regexes for addresses that are functional mailboxes, not people. They are kept."""

    # Prompt packs
    prompt_dirs: list[Path] = Field(default_factory=list)
    """Extra folders of prompt YAML files, loaded after the built-in packs (same id overrides)."""

    def resolved_store(self) -> Literal["sqlite", "chroma"]:
        if self.store != "auto":
            return self.store
        try:
            import chromadb  # noqa: F401
        except ImportError:
            return "sqlite"
        return "chroma"
