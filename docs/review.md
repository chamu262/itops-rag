# Pre-release review (November 2026)

Before the first public release, two reviewers who had not built the project went through it. One fact-checked the
code and every claim in the docs. The other reviewed the retrieval architecture and measured alternatives. This page
records what they found and what changed, including ideas that were tested and rejected.

## Fact-check: bugs found and fixed

| Finding | Severity | Fix |
|---|---|---|
| `ticket_triage` and `change_risk_review` searched only the short question ("Triage this"), so the pasted ticket or change plan never reached retrieval. The triage example was refused, and the change review retrieved unrelated docs. | Critical | Templates with pasted input now search on the input. Tested. |
| One SQLite connection was shared across FastAPI worker threads. 148 of 3,000 concurrent searches failed. | Critical | Every index operation takes a lock, and lazy start-up in the web and MCP servers is locked too. A 600-search, 16-thread test now passes. |
| Redaction missed `aws_secret_access_key = …` (because `_` counts as a word character), quoted values, Anthropic and Azure keys, Basic auth, unsigned JWTs, keys without an END line, and national phone numbers. The keep-list matched `security@` at any domain. | Critical | Patterns rewritten, keep-list anchored to the domain. A test ingests the adversarial fixtures and asserts no planted secret survives. |
| The web UI trusted an `X-ITOPS-Role` header from any client. | Important | Requests default to `public`. The header is accepted only with a proxy shared secret, and is otherwise ignored or rejected with a 403. |
| Files without an access tag became `public`. | Important | Fail closed: the default is `it-staff`, and it is configurable. |
| `--prune` deleted documents from other folders in the same index, and documents whose file failed to load. | Important | Pruning is scoped to the ingested folder, and documents from failed files are kept. |
| Changing chunk size or redaction patterns didn't re-chunk: documents were skipped as "unchanged". | Important | An ingest fingerprint (chunker, size, overlap, redaction version) is folded into each stored hash. |
| The refusal gate without the reranker almost never refused. | Important | It now uses vector similarity only. |
| "Prompt caching" was listed as a cost control, but the system prompt is below the 512-token minimum. | Claim | The claim is removed (see the cost row in the README). |
| Fallback-served answers were priced at $0. | Important | Fallback models are priced, and unknown models are charged at the highest listed price. |
| Smaller items: list settings from env crashed unless given as JSON, chunk overlap was dropped near the size limit, `[1-3]` citation ranges were ignored, the SDK pin was too low for `fallbacks`, and the `[web]` text in `--help` was swallowed by Rich markup. | Minor | All fixed. |

## Architecture: measured changes

All retrieval was measured offline on the golden set, extended with 21 harder questions (paraphrases and near-miss
unanswerables). "Primary" means the single document that should answer the question.

| Change | Result | Kept? |
|---|---|---|
| Doc-type prior (+2 to the rerank score of non-ticket docs, for ordering only) and 1 hit per document | Primary hit@4 0.93 → 0.98, primary MRR 0.80 → 0.85, recall 0.68 → 0.74, ticket share 0.14 → 0.09 | Yes |
| Evaluate on the same path `ask()` uses (template doc types and top-k), and add primary-doc metrics | The old eval overstated recall | Yes |
| Small-to-big context: expand each hit to its section, or the whole doc under 4k chars; ~6k-token budget; tickets stay as chunks | Heading-split chunks averaged ~330 chars, and step lists were split from their "see step 3" references. The context was ~600 tokens; it is now complete sections. | Yes |
| Refuse when the question names an error code that no retrieved doc mentions | Refuses "MG-777" and passes every answerable code question | Yes |
| Faithfulness check on Haiku by default | About $0.0002 per answer | Yes |
| Other embedding models: bge-small, arctic-embed-s, nomic-v1.5, bge-base | No better after reranking (primary hit 0.75–0.81 vs 0.81 on the hard set), and 2–8× slower to build | No: kept all-MiniLM-L6-v2 |
| Other rerankers: ms-marco-L12, jina tiny/turbo, bge-reranker-base | L12 and jina-turbo were slightly better on hard questions at 2× latency. bge-base was 7× slower and worse. | No: kept ms-marco-L6 |
| Candidate pool 20/30/50, RRF k 20/60, FTS5 column weights, contextual chunk headers, 500 or 1200-char chunks, a synonym glossary | Neutral, mixed or worse | No |

## Still open

- One hard question ("Who is on call for Jamf problems?") misses its escalation-matrix table. Splitting tables by
  row is untested.
- Near-miss unanswerables (another vendor's SAML rotation, a Chromebook in Intune) score as high as real questions.
  Only the model's "I don't know" catches them. An answer-level eval (`itops-rag eval --llm`) needs an API key and
  hasn't been run yet.
- Triage could return structured JSON (`output_config.format`) instead of fixed text lines.
