# eval

`golden.jsonl` holds 66 questions:
- 55 answerable, across the public, it-staff and security roles, including 17 deliberately hard paraphrases (the `h*` ids; h17 is a regression question found by tracing)
- 11 that should be refused, 5 of them near-misses such as another vendor's SAML rotation or an unknown error code

Each question has a `split`: tune settings on `dev` (46) and only report `test` (20): `itops-rag eval --split dev`. `scripts/calibrate.py` builds one index per variant and scores both.

The first id in `expected` is the **primary** document, the one that should answer the question. `baseline.json` holds the metrics CI must not drop below (`itops-rag eval --baseline eval/baseline.json`, tolerance 0.03). Questions are searched the way `ask()` searches them: their prompt template's doc types and top-k.

The questions were written with knowledge of the corpus, so treat the numbers as regression checks, not a benchmark. See docs/review.md for the experiments behind the current settings.
