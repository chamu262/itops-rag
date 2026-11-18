# Changelog

## 0.2.1 (2026-11-18)

- **The rerank candidate pool is back at 30, after being 20 in 0.2.0.** Tracing a wordier Autopilot question showed
  the runbook dropping out of a 20-candidate pool once tickets were split into core and comment chunks. It is now a
  regression question in the eval (h17). This costs about 90 ms per query.
- `pool_chunks_per_doc` setting (off by default): capping chunks per document in the pool was measured and hurt.
- `scripts/trace_query.py` shows a question's path through every stage with real scores.
- `docs/how-it-works.md` is a visual guide to the database, chunking, embedding and retrieval.

## 0.2.0 (2026-11-18)

Calibration round 2. Settings were chosen on a dev split of the golden set and reported on a held-out test split.
The details are in [docs/review.md](docs/review.md).

**Retrieval and refusals**
- Product refusal gate. A question that names an IT product no visible document mentions (Okta, Chromebook,
  Linux…) is refused locally at no cost. Refusal accuracy went from 0.95 to 1.00, with no false refusals.
- Candidate pool cut from 30 to 20. Quality is the same and reranking dropped from about 235 to about 150 ms per query.
- `ticket_triage` weighs similar tickets as heavily as KB articles.

**Ingest and chunking**
- Ticket comments are chunked separately from summary, resolution and description.
- System names are canonical at ingest, for example "Entra ID" → `entra` and "Intune / Autopilot" → `intune`.
- Hyphenated words can be searched by their parts ("on call" finds "on-call"). Error codes stay whole.
- PDF sections come from font sizes instead of "Page N".
- Opt-in settings: `ITOPS_RAG_TABLE_ROWS` (one chunk per table row) and `ITOPS_RAG_MIN_SECTION_CHARS` (merge small
  sections). Both were measured and are not defaults.
- `ITOPS_RAG_DOC2QUERY`: Haiku writes likely questions for each chunk at ingest, cached by chunk content. Off by
  default and not yet measured.

**Evaluation**
- Stratified dev/test split, with `itops-rag eval --split dev|test`.
- `scripts/calibrate.py` builds one index per variant and scores both splits.

Upgrading: the ingest fingerprint changed, so the next `itops-rag ingest` re-processes every document. No `--rebuild`
is needed.

## 0.1.0 (2026-11-18)

First public release. Hybrid BM25 + vector search with a local cross-encoder rerank, cited answers from Claude, a
local refusal gate, redaction at ingest, access tags, CLI, web UI, MCP server, Slack stub and a prompt library.
