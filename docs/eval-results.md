# Retrieval evaluation

44 questions, k=4

| Mode | hit@k | recall@k | MRR | Refusal accuracy | Access leaks | ms/query |
|---|---|---|---|---|---|---|
| vector | 0.97 | 0.73 | 0.94 | – | 0 | 3 |
| keyword | 0.97 | 0.71 | 0.90 | – | 0 | 0 |
| hybrid | 1.00 | 0.77 | 0.94 | – | 0 | 2 |
| hybrid_rerank | 1.00 | 0.77 | 0.96 | 1.00 | 0 | 228 |
