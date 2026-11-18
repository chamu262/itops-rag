# Deploying on Google Cloud Run (outline)

A small, cheap way to host it for a team. The web app scales to zero, and ingest runs as a scheduled Job.

1. Build and push the image: `gcloud builds submit --tag REGION-docker.pkg.dev/PROJECT/itops/itops-rag:0.1.0`
2. The ingest Job builds the index and uploads `docstore.sqlite` to a Cloud Storage bucket. Each web instance copies
   it to local disk at start-up and opens it read-only. Don't run SQLite in WAL mode directly on a GCS FUSE mount:
   it doesn't support the locking SQLite needs.
3. **Ingest Job** (nightly, from Cloud Scheduler): `itops-rag ingest /exports --prune`, with exports synced into
   the bucket by your connectors.
4. **Web service**: `itops-rag serve --host 0.0.0.0 --port 8080`, with `--no-allow-unauthenticated` behind IAP. IAP
   passes client headers through, so a thin proxy must verify the IAP JWT, map the user's groups to a role, strip any
   client-sent `X-ITOPS-*` headers, and send `X-ITOPS-Role` plus `X-ITOPS-Proxy-Secret`
   (`ITOPS_RAG_ROLE_HEADER_SECRET` from Secret Manager).
5. `ANTHROPIC_API_KEY` from Secret Manager (`--set-secrets`), never in the image or env files.
6. Set `ITOPS_RAG_MONTHLY_BUDGET_USD` per environment.

The private repo has a concrete Cloud Run Job template wired to real exports.
