"""Calibration harness: build one index per variant and score it on the golden dev and test splits.

    python scripts/calibrate.py                 # all variants
    python scripts/calibrate.py baseline merge  # some variants

Variants that only change query-time settings reuse an index; variants that change chunking get their own build.
Tune on dev, then read test once. Results are printed as a Markdown table. Retrieval only: no API key needed.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from itops_rag import Index, Settings
from itops_rag.evaluation import evaluate_retrieval, load_golden

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data" / "demo" / "kestrel-cloud"
GOLDEN = ROOT / "eval" / "golden.jsonl"

ROUND1 = {"product_gate": False}
FINAL = {"split_ticket_comments": True, "candidates": 30}  # shipped: product gate + ticket split, pool 30
VARIANTS: dict[str, dict[str, Any]] = {
    "round1": dict(ROUND1),
    "product_gate": {},
    "tickets_split": {"product_gate": False, "split_ticket_comments": True},
    "table_rows": {"product_gate": False, "table_rows": True},
    "merge_300": {"product_gate": False, "min_section_chars": 300},
    "merge_500": {"product_gate": False, "min_section_chars": 500},
    "pool20": {"product_gate": False, "candidates": 20},
    "final": dict(FINAL),
    "final+table_rows": {**FINAL, "table_rows": True},
    "final+merge_300": {**FINAL, "min_section_chars": 300},
    "final+L12": {**FINAL, "rerank_model": "Xenova/ms-marco-MiniLM-L-12-v2"},
    "final+jina_turbo": {**FINAL, "rerank_model": "jinaai/jina-reranker-v1-turbo-en"},
    # round 2b: pool spread across documents (found by tracing a realistic Autopilot question)
    "final_pool20": {**FINAL, "candidates": 20},
    "final_spread1": {**FINAL, "pool_chunks_per_doc": 1},
    "final_spread2": {**FINAL, "pool_chunks_per_doc": 2},
}
BUILD_KEYS = ("chunk_size", "chunk_overlap", "min_section_chars", "table_rows", "split_ticket_comments")


def run(names: list[str]) -> list[dict[str, Any]]:
    dev, test = load_golden(GOLDEN, "dev"), load_golden(GOLDEN, "test")
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for name in names:
            settings = Settings(
                _env_file=None, store="sqlite", cost_ledger=Path(tmp) / "c.jsonl", **VARIANTS[name]
            )  # type: ignore[call-arg]
            build = {k: getattr(settings, k) for k in BUILD_KEYS}
            settings.index_dir = (
                Path(tmp) / hashlib.sha256(json.dumps(build, sort_keys=True).encode()).hexdigest()[:10]
            )
            t0 = time.perf_counter()
            with Index.open(settings) as ix:
                ix.ingest_path(CORPUS)
                build_s = time.perf_counter() - t0
                chunks = ix.stats()["chunks"]
                r_dev = evaluate_retrieval(ix, dev, modes=["hybrid_rerank"])[0]
                r_test = evaluate_retrieval(ix, test, modes=["hybrid_rerank"])[0]
            rows.append(
                {
                    "variant": name,
                    "chunks": chunks,
                    "build_s": round(build_s, 1),
                    "dev": r_dev,
                    "test": r_test,
                }
            )
            print(f"done {name}", file=sys.stderr)
    return rows


def table(rows: list[dict[str, Any]]) -> str:
    head = (
        "| Variant | chunks | dev P-hit | dev P-MRR | dev recall | dev refusal | test P-hit | test P-MRR | "
        "test recall | test refusal | ms/q |\n|---|---|---|---|---|---|---|---|---|---|---|"
    )
    lines = [head]
    for r in rows:
        d, t = r["dev"], r["test"]
        lines.append(
            f"| {r['variant']} | {r['chunks']} | {d.primary_hit_at_k:.2f} | {d.primary_mrr:.2f} | {d.recall_at_k:.2f} | "
            f"{d.refusal_accuracy:.2f} | {t.primary_hit_at_k:.2f} | {t.primary_mrr:.2f} | {t.recall_at_k:.2f} | "
            f"{t.refusal_accuracy:.2f} | {d.ms_per_query:.0f} |"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    selected = sys.argv[1:] or list(VARIANTS)
    results = run(selected)
    print(table(results))
    for r in results:
        print(
            f"{r['variant']}: dev misses {r['dev'].misses}, test misses {r['test'].misses}, "
            f"missed refusals dev {r['dev'].missed_refusals} test {r['test'].missed_refusals}, "
            f"false refusals dev {r['dev'].false_refusals} test {r['test'].false_refusals}"
        )
