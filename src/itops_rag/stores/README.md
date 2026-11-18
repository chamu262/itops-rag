# stores

Storage. `docstore.py` is the SQLite file (documents, chunks, FTS5 keyword index, manifest, access filters). `vectors.py` holds the interchangeable vector stores: sqlite-vec, a numpy fallback, and Chroma.
