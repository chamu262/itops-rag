# Deploying on Google Cloud Run (outline)

A small, cheap way to host it for a team. The web app scales to zero, and ingest runs as a scheduled Job.

1. Build and push the image: `gcloud builds submit --tag REGION-docker.pkg.dev/PROJECT/itops/itops-rag:0.1.0`
2. Store the index on a Cloud Storage bucket mounted as a volume (Cloud Run volume mounts), at `/data`.
3. **Ingest Job** (nightly, from Cloud Scheduler): `itops-rag ingest /exports --prune`, with exports synced into
   the bucket by your connectors.
4. **Web service**: `itops-rag serve --host 0.0.0.0 --port 8080`, with `--no-allow-unauthenticated` behind IAP, and
   IAP group membership mapped to the `X-ITOPS-Role` header by a thin proxy.
5. `ANTHROPIC_API_KEY` from Secret Manager (`--set-secrets`), never in the image or env files.
6. Set `ITOPS_RAG_MONTHLY_BUDGET_USD` per environment.

The private repo has a concrete Cloud Run Job template wired to real exports.
