"""Evaluation: measure retrieval offline (free, runs in CI) and answers online (optional, costs tokens).

Golden set format (JSON Lines), one question per line:

    {"id": "q01", "question": "...", "expected": ["RB-MAC-001"], "answerable": true, "role": "it-staff",
     "prompt": "qa", "tags": ["jamf"]}

The first id in ``expected`` is the *primary* document: the runbook, KB article or standard that should answer the
question. The rest are supporting sources (often similar tickets).

Retrieval metrics per mode (vector, keyword, hybrid, hybrid_rerank), measured on the same path ``ask()`` uses
(each question's prompt template sets doc types, top-k and doc-type boosts):
* hit@k / MRR - any expected document in the top k / reciprocal rank of the first one
* primary hit@k / primary MRR - the same for the primary document only (the stricter, more honest number)
* recall@k - share of expected documents found in the top k, averaged
* ticket share - share of returned hits that are tickets (tickets crowding out runbooks is the classic failure)
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
    mrr: float
    primary_hit_at_k: float
    primary_mrr: float
    recall_at_k: float
    ticket_share: float
    refusal_accuracy: float | None
    false_refusals: int
    missed_refusals: int
    access_leaks: int
    ms_per_query: float
    misses: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "k": self.k,
            "hit_at_k": round(self.hit_at_k, 3),
            "mrr": round(self.mrr, 3),
            "primary_hit_at_k": round(self.primary_hit_at_k, 3),
            "primary_mrr": round(self.primary_mrr, 3),
            "recall_at_k": round(self.recall_at_k, 3),
            "ticket_share": round(self.ticket_share, 3),
            "refusal_accuracy": None if self.refusal_accuracy is None else round(self.refusal_accuracy, 3),
            "false_refusals": self.false_refusals,
            "missed_refusals": self.missed_refusals,
            "access_leaks": self.access_leaks,
            "ms_per_query": round(self.ms_per_query, 1),
            "misses": self.misses,
        }


def evaluate_retrieval(
    index: Index,
    items: Sequence[GoldenItem],
    k: int = 4,
    modes: Sequence[SearchMode] = MODES,
    template_path: bool = True,
) -> list[ModeResult]:
    """Retrieval metrics per mode. With ``template_path`` (default) each question is searched exactly the way
    ``ask()`` would: its template's doc types, top-k (capped at ``k``), and doc-type boosts. The refusal gate is applied to
    expanded hits, as in ``ask()``."""
    results = []
    answerable = [i for i in items if i.answerable]
    for mode in modes:
        if mode == "hybrid_rerank" and index.reranker is None:
            continue
        hits_at, rrs, p_hits, p_rrs, recalls, misses = [], [], [], [], [], []
        leaks = tickets = returned = false_refusals = missed_refusals = correct_refusals = 0
        t0 = time.perf_counter()
        for item in items:
            doc_types = None
            boosts = None
            kk = k
            if template_path and item.prompt in index.prompts:
                tpl = index.prompts.get(item.prompt)
                doc_types = tpl.doc_types
                boosts = index.boosts_for(tpl.doc_type_boost)
                kk = min(k, tpl.top_k or k)
            hits = index.search(
                item.question, k=kk, role=item.role, mode=mode, doc_types=doc_types, doc_type_boost=boosts
            )
            allowed = set(visible_access(item.role))
            leaks += sum(1 for h in hits if h.chunk.meta.get("access") not in allowed)
            tickets += sum(1 for h in hits if h.chunk.meta.get("doc_type") == "ticket")
            returned += len(hits)
            refused = (
                gate(index.expand(hits), index.settings, item.question) is not None
                if mode == "hybrid_rerank"
                else None
            )
            if item.answerable:
                expected = set(item.expected)
                rank = _first_rank(hits, expected)
                p_rank = _first_rank(hits, {item.expected[0]})
                hits_at.append(1.0 if rank else 0.0)
                rrs.append(1.0 / rank if rank else 0.0)
                p_hits.append(1.0 if p_rank else 0.0)
                p_rrs.append(1.0 / p_rank if p_rank else 0.0)
                recalls.append(len(expected & {h.doc_id for h in hits}) / len(expected))
                if not p_rank:
                    misses.append(item.id)
                if refused:
                    false_refusals += 1
            elif refused:
                correct_refusals += 1
            elif refused is False:
                missed_refusals += 1
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
                mrr=sum(rrs) / n,
                primary_hit_at_k=sum(p_hits) / n,
                primary_mrr=sum(p_rrs) / n,
                recall_at_k=sum(recalls) / n,
                ticket_share=tickets / max(returned, 1),
                refusal_accuracy=refusal_acc,
                false_refusals=false_refusals,
                missed_refusals=missed_refusals,
                access_leaks=leaks,
                ms_per_query=elapsed,
                misses=misses,
            )
        )
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
        "| Mode | hit@k | MRR | primary hit@k | primary MRR | recall@k | ticket share | refusal acc. | leaks | ms/q |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        ra = "–" if r.refusal_accuracy is None else f"{r.refusal_accuracy:.2f}"
        lines.append(
            f"| {r.mode} | {r.hit_at_k:.2f} | {r.mrr:.2f} | {r.primary_hit_at_k:.2f} | {r.primary_mrr:.2f} | "
            f"{r.recall_at_k:.2f} | {r.ticket_share:.2f} | {ra} | {r.access_leaks} | {r.ms_per_query:.0f} |"
        )
    return "\n".join(lines)


def check_gate(results: Sequence[ModeResult], baseline: dict[str, Any], tolerance: float = 0.03) -> list[str]:
    """Compare against a stored baseline. Returns failure messages (empty means pass)."""
    failures = []
    by_mode = {r.mode: r for r in results}
    for mode, base in baseline.get("modes", {}).items():
        r = by_mode.get(mode)
        if r is None:
            continue
        for metric in ("hit_at_k", "mrr", "primary_hit_at_k", "primary_mrr", "refusal_accuracy"):
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
