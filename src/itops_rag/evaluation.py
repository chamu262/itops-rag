"""Evaluation: measure retrieval offline (free, runs in CI) and answers online (optional, costs tokens).

Golden set format (JSON Lines), one question per line:

    {"id": "q01", "question": "...", "expected": ["RB-MAC-001"], "answerable": true, "role": "it-staff",
     "prompt": "qa", "tags": ["jamf"]}

Retrieval metrics per mode (vector, keyword, hybrid, hybrid_rerank):
* hit@k - share of answerable questions with at least one expected document in the top k
* recall@k - share of expected documents found in the top k, averaged
* MRR - mean reciprocal rank of the first expected document
* refusal accuracy - unanswerable questions the local gate refuses, and answerable ones it lets through
* access leaks - hits above the caller's role (must be zero)
"""

from __future__ import annotations

import json
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from itops_rag.config import SearchMode
from itops_rag.core.generate import gate
from itops_rag.core.index import Index
from itops_rag.core.models import Hit, visible_access

MODES: tuple[SearchMode, ...] = ("vector", "keyword", "hybrid", "hybrid_rerank")


@dataclass(slots=True)
class GoldenItem:
    id: str
    question: str
    expected: list[str]
    answerable: bool = True
    role: str = "it-staff"
    prompt: str = "qa"
    tags: list[str] = field(default_factory=list)


def load_golden(path: Path) -> list[GoldenItem]:
    items = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        d = json.loads(line)
        try:
            items.append(GoldenItem(**d))
        except TypeError as e:
            raise ValueError(f"{path}:{n}: {e}") from None
    ids = [i.id for i in items]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path}: duplicate question ids")
    return items


def _first_rank(hits: Sequence[Hit], expected: set[str]) -> int | None:
    for rank, h in enumerate(hits, start=1):
        if h.doc_id in expected:
            return rank
    return None


@dataclass(slots=True)
class ModeResult:
    mode: str
    k: int
    hit_at_k: float
    recall_at_k: float
    mrr: float
    refusal_accuracy: float | None
    false_refusals: int
    access_leaks: int
    ms_per_query: float
    misses: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "k": self.k,
            "hit_at_k": round(self.hit_at_k, 3),
            "recall_at_k": round(self.recall_at_k, 3),
            "mrr": round(self.mrr, 3),
            "refusal_accuracy": None if self.refusal_accuracy is None else round(self.refusal_accuracy, 3),
            "false_refusals": self.false_refusals,
            "access_leaks": self.access_leaks,
            "ms_per_query": round(self.ms_per_query, 1),
            "misses": self.misses,
        }


def evaluate_retrieval(
    index: Index, items: Sequence[GoldenItem], k: int = 4, modes: Sequence[SearchMode] = MODES
) -> list[ModeResult]:
    results = []
    answerable = [i for i in items if i.answerable]
    unanswerable = [i for i in items if not i.answerable]
    for mode in modes:
        if mode == "hybrid_rerank" and index.reranker is None:
            continue
        hits_at, recalls, rrs, misses = [], [], [], []
        leaks = 0
        false_refusals = 0
        correct_refusals = 0
        t0 = time.perf_counter()
        for item in items:
            hits = index.search(item.question, k=k, role=item.role, mode=mode)
            allowed = set(visible_access(item.role))
            leaks += sum(1 for h in hits if h.chunk.meta.get("access") not in allowed)
            refused = gate(hits, index.settings) is not None if mode == "hybrid_rerank" else None
            if item.answerable:
                expected = set(item.expected)
                rank = _first_rank(hits, expected)
                hits_at.append(1.0 if rank else 0.0)
                rrs.append(1.0 / rank if rank else 0.0)
                recalls.append(len(expected & {h.doc_id for h in hits}) / len(expected))
                if not rank:
                    misses.append(item.id)
                if refused:
                    false_refusals += 1
            elif refused:
                correct_refusals += 1
        elapsed = (time.perf_counter() - t0) * 1000 / max(len(items), 1)
        refusal_acc = None
        if mode == "hybrid_rerank" and items:
            refusal_acc = (correct_refusals + len(answerable) - false_refusals) / len(items)
        n = max(len(answerable), 1)
        results.append(
            ModeResult(
                mode=mode,
                k=k,
                hit_at_k=sum(hits_at) / n,
                recall_at_k=sum(recalls) / n,
                mrr=sum(rrs) / n,
                refusal_accuracy=refusal_acc,
                false_refusals=false_refusals,
                access_leaks=leaks,
                ms_per_query=elapsed,
                misses=misses,
            )
        )
        _ = unanswerable
    return results


def evaluate_answers(index: Index, items: Sequence[GoldenItem], limit: int | None = None) -> dict[str, Any]:
    """Run the full ask() pipeline (calls Claude). Measures refusal correctness and citation precision."""
    rows: list[dict[str, Any]] = []
    total_cost = 0.0
    for item in list(items)[:limit]:
        ans = index.ask(
            item.question, prompt=item.prompt if item.prompt in index.prompts else "qa", role=item.role
        )
        total_cost += ans.usage.cost_usd
        cited_docs = [ans.hits[n - 1].doc_id for n in ans.cited]
        precision = (
            (sum(1 for d in cited_docs if d in item.expected) / len(cited_docs)) if cited_docs else None
        )
        rows.append(
            {
                "id": item.id,
                "answerable": item.answerable,
                "refused": ans.refused,
                "correct_refusal": ans.refused == (not item.answerable),
                "citation_precision": precision,
                "warnings": ans.warnings,
                "cost_usd": round(ans.usage.cost_usd, 5),
            }
        )
    precisions = [r["citation_precision"] for r in rows if r["citation_precision"] is not None]
    return {
        "questions": len(rows),
        "refusal_correct": sum(r["correct_refusal"] for r in rows) / max(len(rows), 1),
        "citation_precision": sum(precisions) / len(precisions) if precisions else None,
        "answers_with_warnings": sum(1 for r in rows if r["warnings"]),
        "total_cost_usd": round(total_cost, 4),
        "rows": rows,
    }


def markdown_table(results: Sequence[ModeResult]) -> str:
    lines = [
        "| Mode | hit@k | recall@k | MRR | Refusal accuracy | Access leaks | ms/query |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        ra = "–" if r.refusal_accuracy is None else f"{r.refusal_accuracy:.2f}"
        lines.append(
            f"| {r.mode} | {r.hit_at_k:.2f} | {r.recall_at_k:.2f} | {r.mrr:.2f} | {ra} | "
            f"{r.access_leaks} | {r.ms_per_query:.0f} |"
        )
    return "\n".join(lines)


def check_gate(results: Sequence[ModeResult], baseline: dict[str, Any], tolerance: float = 0.02) -> list[str]:
    """Compare against a stored baseline. Returns failure messages (empty means pass)."""
    failures = []
    by_mode = {r.mode: r for r in results}
    for mode, base in baseline.get("modes", {}).items():
        r = by_mode.get(mode)
        if r is None:
            continue
        for metric in ("hit_at_k", "mrr", "refusal_accuracy"):
            b = base.get(metric)
            v = getattr(r, metric)
            if b is not None and v is not None and v < b - tolerance:
                failures.append(
                    f"{mode} {metric} dropped: {v:.3f} < baseline {b:.3f} (tolerance {tolerance})"
                )
    for r in results:
        if r.access_leaks:
            failures.append(f"{r.mode}: {r.access_leaks} access leaks")
    return failures
