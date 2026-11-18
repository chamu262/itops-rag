# ADR 0002: Refuse locally before calling the model

**Status:** accepted · 2026-11

## Context
"Answer only from context or say I don't know" in a prompt works most of the time. It still costs a model call for
every out-of-scope question, and it can't be measured without an API key.

## Decision
After reranking, if the best cross-encoder score is below `min_rerank_score` (default -2.0, tuned on the golden
set), return a fixed "I don't know" answer naming the owning teams of the nearest docs. Make no API call. The prompt
rule stays as a second layer.

## Consequences
+ Out-of-scope questions cost $0, and refusal accuracy is part of the offline CI gate.
- A threshold that is too strict refuses borderline questions. It is a setting, and `itops-rag eval` reports false
  refusals.
