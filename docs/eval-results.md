# Retrieval evaluation

65 questions, k=4

| Mode | hit@k | MRR | primary hit@k | primary MRR | recall@k | ticket share | refusal acc. | leaks | ms/q |
|---|---|---|---|---|---|---|---|---|---|
| vector | 0.93 | 0.82 | 0.91 | 0.74 | 0.68 | 0.17 | – | 0 | 3 |
| keyword | 0.96 | 0.79 | 0.85 | 0.70 | 0.69 | 0.20 | – | 0 | 0 |
| hybrid | 0.94 | 0.84 | 0.89 | 0.74 | 0.70 | 0.20 | – | 0 | 2 |
| hybrid_rerank | 0.98 | 0.90 | 0.98 | 0.85 | 0.74 | 0.11 | 1.00 | 0 | 149 |
