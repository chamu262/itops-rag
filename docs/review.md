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
| Faithfulness check on Haiku by default | Under $0.001 per answer (it reads the ~4–7k-token context at $0.10/M) | Yes |
| Other embedding models: bge-small, arctic-embed-s, nomic-v1.5, bge-base | No better after reranking (primary hit 0.75–0.81 vs 0.81 on the hard set), and 2–8× slower to build | No: kept all-MiniLM-L6-v2 |
| Other rerankers: ms-marco-L12, jina tiny/turbo, bge-reranker-base | L12 and jina-turbo were slightly better on hard questions at 2× latency. bge-base was 7× slower and worse. | No: kept ms-marco-L6 |
| Candidate pool 20/30/50, RRF k 20/60, FTS5 column weights, contextual chunk headers, 500 or 1200-char chunks, a synonym glossary | Neutral, mixed or worse | No |

## Round 2: chunking, embedding and retrieval calibration

**Method.** The golden set was split into dev (45 questions) and held-out test (20), stratified by kind. Each
variant got its own index build (`scripts/calibrate.py`) and was scored on both splits. Decisions used dev only;
test is reported to show whether a change holds up on questions it wasn't tuned on. n is small: one question moves
dev by about 0.03 and test by about 0.06.

| Variant | Chunks | Dev primary hit | Dev primary MRR | Dev refusal | Test primary hit | Test primary MRR | Test refusal | ms/query | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| Round-1 settings | 657 | 0.97 | 0.84 | 0.98 | 1.00 | 0.86 | 0.95 | 248 | baseline |
| + product gate | 657 | 0.97 | 0.84 | **1.00** | 1.00 | 0.86 | **1.00** | 244 | **kept** |
| + ticket comments in their own chunks | 696 | 0.97 | 0.84 | 0.98 | 1.00 | 0.86 | 0.95 | 242 | **kept** (neutral; cleaner ticket context) |
| + candidate pool 20 (was 30) | 657 | 0.97 | 0.84 | 0.98 | 1.00 | 0.87 | 0.95 | **159** | **kept** |
| Table rows as chunks | 759 | 1.00 | 0.85 | 0.98 | 0.94 | 0.84 | 0.95 | 237 | opt-in only: +1 dev, −1 test |
| Merge sections < 300 chars | 416 | 0.97 | 0.83 | 0.96 | 0.94 | 0.81 | 0.95 | 258 | rejected |
| Merge sections < 500 chars | 405 | 0.97 | 0.82 | 0.96 | 0.94 | 0.84 | 0.95 | 264 | rejected |
| **Final** (gate + ticket split + pool 20) | 696 | 0.97 | 0.84 | **1.00** | **1.00** | **0.86** | **1.00** | **170** | **shipped** |
| Final + ms-marco-L12 reranker | 696 | 0.97 | 0.80 | 1.00 | 1.00 | 0.87 | 1.00 | 367 | rejected |
| Final + jina-reranker-v1-turbo | 696 | 0.97 | 0.86 | 0.96 | 1.00 | 0.92 | 1.00 | 223 | follow-up: needs its own refusal threshold |

Also shipped in this round, because they fix correctness rather than tune a number:
- **System names are normalised at ingest.** The demo tickets used ~30 spellings, such as "Entra ID" vs "entra" or
  "Intune / Autopilot"; there are now 13 canonical names, so `--system` filters work.
- **Hyphenated words are searchable by their parts.** "On call" now finds "on-call". Error codes such as MG-401 stay
  whole tokens. This is what let the table-row variant answer "who is on call for Jamf?" at all.
- **PDF sections come from font sizes**, for example "MG-4xx authentication (p. 1)", instead of "Page 1".
- **doc2query enrichment** is built and cached per chunk content, but off by default. It needs an API key, so it
  hasn't been measured yet.

## Still open

- One hard question ("Who is on call for Jamf problems?") still misses its escalation-matrix row by default. Table
  rows fix it but cost a held-out question, so they are opt-in.
- Near-miss unanswerables that name no product or error code would still score like real questions. The product
  and code checks catch the ones in the golden set. An answer-level eval (`itops-rag eval --llm`) needs an API key and
  hasn't been run yet. The same goes for doc2query and query rewriting.
- Triage could return structured JSON (`output_config.format`) instead of fixed text lines.
