# itops-rag: web UI + JSON API (and the MCP server via `itops-rag mcp`).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ITOPS_RAG_MODEL_CACHE_DIR=/models \
    ITOPS_RAG_INDEX_DIR=/data/index \
    ITOPS_RAG_COST_LEDGER=/data/costs.jsonl

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir ".[web,mcp]"

# Bake the local models into the image so the container runs fully offline.
RUN python -c "from itops_rag.core.embeddings import FastEmbedder; from itops_rag.core.rerank import CrossEncoderReranker; \
FastEmbedder(cache_dir='/models').embed_query('warm up'); CrossEncoderReranker(cache_dir='/models').score('a', ['b'])"

COPY data/demo/kestrel-cloud /app/demo
RUN useradd --create-home --uid 10001 app && mkdir -p /data && chown -R app /data /models
USER app

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz')"
CMD ["sh", "-c", "itops-rag ingest /app/demo --store sqlite && itops-rag serve --host 0.0.0.0 --port 8080"]
