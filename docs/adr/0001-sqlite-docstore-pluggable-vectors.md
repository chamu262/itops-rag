# ADR 0001: SQLite docstore with pluggable vector stores

**Status:** accepted · 2026-11

## Context
The brief started from LangChain + Chroma. IT ops search needs exact-token matches (error codes, ticket keys) as
much as semantic ones, plus access filtering that can't be bypassed. Chroma has no BM25. Other apps (personal agents)
need the lightest possible install.

## Decision
Documents, chunks, FTS5 (BM25) and metadata always live in one SQLite file. Vectors sit behind a three-method
`VectorStore` protocol: sqlite-vec (default for the light install), a numpy fallback, and Chroma (`[chroma]` extra,
chosen automatically when installed).

## Consequences
+ Hybrid search works the same with any vector store, and access filters are part of every query.
+ The base install has no server and no torch, and fits in a personal agent.
- Two stores to keep consistent on delete. `Index` owns both writes, and tests cover delete and prune.
