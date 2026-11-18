"""Trace one question through every retrieval stage, with real scores from your index.

    python scripts/trace_query.py "Autopilot fails with 0x80180014 on a new laptop" --prompt troubleshoot

Shows: the free prechecks, the top BM25 and vector candidates, Reciprocal Rank Fusion, the cross-encoder rerank
with the doc-type prior, the one-hit-per-document cut, the refusal gate, small-to-big expansion and the final prompt
size. Retrieval only: no API key needed. Used to produce the worked example in docs/how-it-works.md.
"""

from __future__ import annotations

import argparse

from itops_rag import Index, Settings
from itops_rag.core.generate import gate
from itops_rag.core.models import visible_access
from itops_rag.core.retriever import code_tokens, keyword_weight_for, rrf


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--prompt", default="qa")
    ap.add_argument("--role", default="it-staff")
    ap.add_argument("--show", type=int, default=6)
    args = ap.parse_args()

    with Index.open(Settings()) as ix:
        tpl = ix.prompts.get(args.prompt)
        k = tpl.top_k or ix.settings.top_k
        access = visible_access(args.role)
        boosts = ix.boosts_for(tpl.doc_type_boost)
        n = ix.settings.candidates
        q = args.question
        print(
            f"# Trace: {q!r}\nprompt={tpl.id} (doc types {tpl.doc_types or 'all'}, k={k}), role={args.role} -> {access}\n"
        )

        print("## 1. Free prechecks")
        print(f"- product check: {ix.precheck(q, args.role) or 'pass'}")
        print(f"- error codes in question: {sorted(code_tokens(q)) or 'none'}\n")

        kw = ix.docs.keyword_search(q, n, access, tpl.doc_types)
        vec = ix.vectors.search(ix.embedder.embed_query(q), n, access, tpl.doc_types)
        chunks = ix.docs.get_chunks(list({c for c, _ in kw} | {c for c, _ in vec}))

        def label(cid: str) -> str:
            c = chunks[cid]
            return f"{c.doc_id} [{c.meta['doc_type']}] {c.heading[:40] or '(top)'}"

        print(f"## 2a. Keyword (FTS5 BM25), top {args.show} of {len(kw)}")
        for i, (cid, s) in enumerate(kw[: args.show], 1):
            print(f"{i}. {label(cid)}  bm25={s:.2f}")
        print(f"\n## 2b. Vector (all-MiniLM-L6-v2 cosine), top {args.show} of {len(vec)}")
        for i, (cid, s) in enumerate(vec[: args.show], 1):
            print(f"{i}. {label(cid)}  cos={s:.3f}")

        kw_w = keyword_weight_for(q, ix.settings.keyword_weight)
        fused = rrf([[c for c, _ in vec], [c for c, _ in kw]], [ix.settings.vector_weight, kw_w])[:n]
        print(
            f"\n## 3. Reciprocal Rank Fusion (k=60, keyword weight {kw_w}), top {args.show} of {len(fused)}"
        )
        for i, (cid, s) in enumerate(fused[: args.show], 1):
            print(f"{i}. {label(cid)}  rrf={s:.4f}")

        hits = ix.search(q, k=k, role=args.role, doc_types=tpl.doc_types, doc_type_boost=boosts)
        print(f"\n## 4. Cross-encoder rerank + doc-type prior, then 1 hit per document -> top {k}")
        print("| # | Hit | raw rerank | prior | final |\n|---|---|---|---|---|")
        for i, h in enumerate(hits, 1):
            prior = boosts.get(str(h.chunk.meta.get("doc_type")), 0.0)
            print(
                f"| {i} | {h.doc_id} ({h.chunk.meta['doc_type']}) | {h.rerank_score:.2f} | +{prior:.0f} | {h.score:.2f} |"
            )

        expanded = ix.expand(hits)
        print(
            f"\n## 5. Refusal gate: {gate(expanded, ix.settings, q) or 'pass'} (threshold {ix.settings.min_rerank_score})"
        )
        print("\n## 6. Small-to-big expansion")
        for h, e in zip(hits, expanded, strict=False):
            what = (
                "whole document"
                if e.chunk.heading == "" and h.chunk.meta.get("doc_type") != "ticket"
                else (
                    "ticket chunk (not expanded)"
                    if h.chunk.meta.get("doc_type") == "ticket"
                    else f"section '{e.chunk.heading[:40]}'"
                )
            )
            print(f"- {h.doc_id}: {len(h.chunk.text)} -> {len(e.chunk.text)} chars ({what})")
        ctx = ix.context_for(q, prompt=tpl.id, role=args.role) if not tpl.needs_input else None
        if ctx:
            print(
                f"\n## 7. Prompt: {len(ctx['prompt'])} chars (~{len(ctx['prompt']) // 4} tokens) + system rules "
                f"{len(ctx['system'])} chars; refused={ctx['refused']}"
            )


if __name__ == "__main__":
    main()
