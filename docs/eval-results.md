# Retrieval evaluation

66 questions, k=4

| Mode | hit@k | MRR | primary hit@k | primary MRR | recall@k | ticket share | refusal acc. | leaks | ms/q |
|---|---|---|---|---|---|---|---|---|---|
| vector | 0.93 | 0.83 | 0.89 | 0.72 | 0.68 | 0.18 | – | 0 | 3 |
| keyword | 0.96 | 0.79 | 0.84 | 0.69 | 0.69 | 0.21 | – | 0 | 0 |
| hybrid | 0.95 | 0.84 | 0.87 | 0.73 | 0.71 | 0.22 | – | 0 | 2 |
| hybrid_rerank | 0.98 | 0.90 | 0.98 | 0.84 | 0.73 | 0.09 | 1.00 | 0 | 217 |
