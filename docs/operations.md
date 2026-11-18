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
| One long doc crowds out others | `ITOPS_RAG_MAX_CHUNKS_PER_DOC` (default 1) |
| Tickets crowd out runbooks (or the reverse) | `ITOPS_RAG_DOC_TYPE_BOOST` (JSON, default +2 for non-ticket types), or `doc_type_boost` in a template |
| Answers miss steps from long runbooks | `ITOPS_RAG_CONTEXT_CHAR_BUDGET` (default 24000) and `ITOPS_RAG_EXPAND_WHOLE_DOC_CHARS` (default 4000) |
| Error-code lookups miss | Check `itops-rag search --mode keyword "<code>"`; codes need to be in the text, not only in images |
| Answers too long or short | Edit the template's `output` block; effort barely changes length |
| Cost creeping up | `ITOPS_RAG_EFFORT=low`, move templates to `tier: fast`, or point agents at `get_context` over MCP |

## Costs (Opus 5.5 at $4 / $20 per million tokens)

A typical `troubleshoot` answer reads about 4–7k input tokens (system rules + expanded sections + task) and generates
a few hundred to a few thousand output tokens, including thinking (Opus 5.5 always thinks; `effort: medium` keeps it
moderate). That is roughly **$0.03–0.08 per answer**, plus about $0.0002 for the Haiku faithfulness check. These are
estimates, not measurements: check the cost line on your first answers. The same question through `ticket_triage` on Haiku costs a fraction
of a cent. Refusals, searches, ingest and evals cost nothing. Every call is logged to `.itops-rag/costs.jsonl`, and
calls stop once `ITOPS_RAG_MONTHLY_BUDGET_USD` is reached.

## Security checklist before real data

- [ ] Run behind SSO (the web app has no auth of its own). Set `ITOPS_RAG_ROLE_HEADER_SECRET`; have the proxy send
      `X-ITOPS-Role` (from IdP groups) and `X-ITOPS-Proxy-Secret`, and strip any client-sent copies. Without the
      secret, every web caller is `public`.
- [ ] Give the MCP server the lowest role its users need. Start one server per role if needed.
- [ ] Keep the index folder on encrypted disk, and exclude it from backups that leave your boundary.
- [ ] Check `itops-rag ingest` redaction counts on the first run. Add patterns for your own token formats.
- [ ] Decide on retention for `.itops-rag/costs.jsonl` (it holds prompt ids and token counts, not text).
- [ ] Review which `security` documents exist and who can reach a `security`-role interface.
