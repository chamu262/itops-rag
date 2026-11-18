"""Settings, read from environment variables (prefix ``ITOPS_RAG_``), a ``.env`` file, or passed in code.

Every knob has a safe default, so ``Settings()`` works with no configuration at all.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

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
    max_chunks_per_doc: int = 1
    """Diversity cap: one hit per document; context expansion then brings in the rest of the section."""
    doc_type_boost: dict[str, float] = Field(
        default_factory=lambda: {
            t: 2.0 for t in ("runbook", "kb", "vendor", "standard", "oncall", "postmortem", "change", "doc")
        }
    )
    """Added to rerank scores for ordering. Tickets get 0 so authoritative docs win ties with near-duplicate tickets.
    Templates can override per type (``similar_tickets`` sets tickets high). Measured: primary-doc hit 0.81 -> 0.94
    on the hard golden questions."""
    context_char_budget: int = 24000
    """About 6k tokens of context per answer, after expanding hits to their section or whole document."""
    expand_whole_doc_chars: int = 4000
    """Documents shorter than this are given to the model whole; longer ones by section."""
    min_rerank_score: float = -2.0
    """Refuse locally (no API call) when the best cross-encoder score is below this. Tuned with ``itops-rag eval``."""
    min_vector_similarity: float = 0.30
    """Refusal gate used when reranking is off."""

    # Identity used in the system prompt (a personal agent would set its own name and audience).
    assistant_name: str = "IT Ops RAG"
    audience: str = "the IT operations team"

    # Access
    default_role: Literal["public", "it-staff", "security"] = "it-staff"
    """Role for the CLI, the library and the MCP server (fixed per process)."""
    default_access: Literal["public", "it-staff", "security"] = "it-staff"
    """Access tag for documents that don't declare one. Fail closed: not ``public``."""
    web_default_role: Literal["public", "it-staff", "security"] = "public"
    """Role for web requests that don't carry a verified role header."""
    role_header_secret: str = ""
    """If set, the web app trusts ``X-ITOPS-Role`` only when ``X-ITOPS-Proxy-Secret`` matches (your SSO proxy sets
    both and strips any client-sent copies). If empty, the role header is ignored entirely."""

    # Generation (Claude)
    answer_model: str = "claude-opus-5-5"
    fast_model: str = "claude-haiku-5-5"
    """Used for cheap steps: query rewriting, ticket triage labels, the faithfulness check."""
    effort: Effort = "medium"
    max_tokens: int = 8192
    """Includes thinking tokens (Opus 5.5 always thinks); you pay only for what is generated."""
    server_fallbacks: bool = True
    """Send ``fallbacks: "default"`` so a safety-classifier decline is retried on a fallback model in the same call."""
    rewrite_queries: bool = False
    verify_answers: bool = True
    """A Haiku faithfulness check per answer (about $0.0002). Off with ITOPS_RAG_VERIFY_ANSWERS=false."""

    # Cost control
    monthly_budget_usd: float = 25.0
    cost_ledger: Path = Field(default=Path(".itops-rag/costs.jsonl"))

    # Redaction at ingest
    redact: bool = True
    redact_keep_emails: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [r"^(servicedesk|it-oncall|security|noreply)@kestrelcloud\.example$"]
    )
    """Regexes for addresses that are functional mailboxes, not people. They are kept."""

    # Prompt packs
    prompt_dirs: Annotated[list[Path], NoDecode] = Field(default_factory=list)
    """Extra folders of prompt YAML files, loaded after the built-in packs (same id overrides)."""

    @field_validator("prompt_dirs", "redact_keep_emails", mode="before")
    @classmethod
    def _split_list(cls, value: Any) -> Any:
        """Accept a JSON list, or a comma-separated string, from environment variables."""
        if isinstance(value, str):
            text = value.strip()
            if text.startswith("["):
                import json

                return json.loads(text)
            return [part.strip() for part in text.split(",") if part.strip()]
        return value

    def resolved_store(self) -> Literal["sqlite", "chroma"]:
        if self.store != "auto":
            return self.store
        try:
            import chromadb  # noqa: F401
        except ImportError:
            return "sqlite"
        return "chroma"
