# eval

`golden.jsonl` holds 65 questions:
- 54 answerable, across the public, it-staff and security roles, including 16 deliberately hard paraphrases (the `h*` ids)
- 11 that should be refused, 5 of them near-misses such as another vendor's SAML rotation or an unknown error code

The first id in `expected` is the **primary** document, the one that should answer the question. `baseline.json` holds the metrics CI must not drop below (`itops-rag eval --baseline eval/baseline.json`, tolerance 0.03). Questions are searched the way `ask()` searches them: their prompt template's doc types and top-k.

The questions were written with knowledge of the corpus, so treat the numbers as regression checks, not a benchmark. See docs/review.md for the experiments behind the current settings.
