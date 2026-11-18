# Retrieval evaluation

65 questions, k=4

| Mode | hit@k | MRR | primary hit@k | primary MRR | recall@k | ticket share | refusal acc. | leaks | ms/q |
|---|---|---|---|---|---|---|---|---|---|
| vector | 0.94 | 0.84 | 0.93 | 0.77 | 0.70 | 0.17 | – | 0 | 3 |
| keyword | 0.96 | 0.80 | 0.89 | 0.72 | 0.70 | 0.18 | – | 0 | 0 |
| hybrid | 0.98 | 0.86 | 0.93 | 0.75 | 0.74 | 0.21 | – | 0 | 4 |
| hybrid_rerank | 0.98 | 0.91 | 0.98 | 0.85 | 0.75 | 0.10 | 0.95 | 0 | 271 |
