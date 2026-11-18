# Running it for real

## Keeping the index fresh

```bash
# nightly, from cron, a CI schedule or a Cloud Run Job
itops-rag ingest /srv/kb-exports --prune
```

- Unchanged documents are skipped by content hash, so a nightly run over thousands of docs re-embeds only what
  changed.
- `--prune` removes documents that disappeared from the source folder (a retired runbook stops being retrievable).
- One writer at a time: run ingest from one job. Readers (web, MCP, Slack) can keep serving during it (SQLite WAL).

## Exporting sources

| Source | How to get files | Notes |
|---|---|---|
| Confluence | Space → Export → HTML | Add `<meta name="itops:access">` per page, or set access per folder with a small wrapper |
| Jira | Filter → Export CSV (all fields) | Keep `key, summary, description, resolution, comments, component, assignee_team` |
| ServiceNow | List → Export → JSON | `{"records": [...]}` is accepted as is |
| Runbooks in Git | Clone the repo | Markdown with front matter is the best-supported format |
| Vendor PDFs | Download | Add a `<name>.meta.yaml` sidecar for access and system |

Live API connectors (Confluence and Jira REST, Google Drive) are kept in the private repo. They write the same files
these loaders read, so the public engine has no credentials code in it.

## Tuning

| Symptom | Knob |
|---|---|
| Refuses questions it should answer | Lower `ITOPS_RAG_MIN_RERANK_SCORE` (default -2.0), then re-run `itops-rag eval` |
| Answers questions it should refuse | Raise it |
| One long doc crowds out others | `ITOPS_RAG_MAX_CHUNKS_PER_DOC` (default 2) |
| Error-code lookups miss | Check `itops-rag search --mode keyword "<code>"`; codes need to be in the text, not only in images |
| Answers too long or short | Edit the template's `output` block; effort barely changes length |
| Cost creeping up | `ITOPS_RAG_EFFORT=low`, move templates to `tier: fast`, or point agents at `get_context` over MCP |

## Costs (Opus 5.5 at $4 / $20 per million tokens)

A typical `troubleshoot` answer reads about 3–4k input tokens (system rules + 6 chunks + task) and writes 300–600,
which comes to roughly **$0.02–0.03 per answer**. The same question through `ticket_triage` on Haiku costs a fraction
of a cent. Refusals, searches, ingest and evals cost nothing. Every call is logged to `.itops-rag/costs.jsonl`, and
calls stop once `ITOPS_RAG_MONTHLY_BUDGET_USD` is reached.

## Security checklist before real data

- [ ] Run behind SSO (the web app has no auth of its own) and set `X-ITOPS-Role` from IdP groups at the proxy.
- [ ] Give the MCP server the lowest role its users need. Start one server per role if needed.
- [ ] Keep the index folder on encrypted disk, and exclude it from backups that leave your boundary.
- [ ] Check `itops-rag ingest` redaction counts on the first run. Add patterns for your own token formats.
- [ ] Decide on retention for `.itops-rag/costs.jsonl` (it holds prompt ids and token counts, not text).
- [ ] Review which `security` documents exist and who can reach a `security`-role interface.
