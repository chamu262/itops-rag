"""The document store: one SQLite file that holds documents, chunks, the FTS5 keyword index and the index manifest.

It is always SQLite, whichever vector store is used. Keyword search (BM25) and metadata filters live here, so Chroma
and sqlite-vec are interchangeable for the vector half of hybrid search.
"""

from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from itops_rag.core.models import Chunk, Document

SCHEMA_VERSION = 1

# Words that carry no signal for keyword search. Error codes, ticket keys and product names are untouched.
_STOP = frozenset(
    "a an and are as at be but by can do does for from has have how i if in into is it its me my no not of on or "
    "our so than that the their them then there these they this to was we what when where which who why will with "
    "you your should would could i'm get got need".split()
)
_QUERY_TOKEN = re.compile(r"[\w][\w\-]*", re.UNICODE)


def fts_query(text: str) -> str:
    """Turn free text into a safe FTS5 query: quoted terms joined with OR, stop words dropped.

    >>> fts_query('Why does MG-401 happen after the "upgrade"?')
    '"mg-401" OR "happen" OR "after" OR "upgrade"'
    """
    terms: list[str] = []
    for tok in _QUERY_TOKEN.findall(text.lower()):
        tok = tok.strip("-_")
        if tok and tok not in _STOP and tok not in terms:
            terms.append(tok)
    return " OR ".join(f'"{t}"' for t in terms)


class DocStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._migrate()

    def _migrate(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS manifest (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY, title TEXT, doc_type TEXT, system TEXT, owner TEXT, access TEXT,
                updated TEXT, tags TEXT, source TEXT, content_hash TEXT, text TEXT, extra TEXT
            );
            CREATE TABLE IF NOT EXISTS chunks (
                rowid INTEGER PRIMARY KEY AUTOINCREMENT,
                id TEXT UNIQUE NOT NULL,
                doc_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                ordinal INTEGER NOT NULL, heading TEXT, text TEXT NOT NULL,
                access TEXT NOT NULL, doc_type TEXT, system TEXT
            );
            CREATE INDEX IF NOT EXISTS chunks_doc ON chunks(doc_id);
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                embed_text, content='', contentless_delete=1,
                tokenize="porter unicode61 remove_diacritics 2 tokenchars '-_'"
            );
            """
        )
        self.set_meta("schema_version", str(SCHEMA_VERSION))
        self.conn.commit()

    # ----- manifest -------------------------------------------------------------------------------------------
    def get_meta(self, key: str) -> str | None:
        row = self.conn.execute("SELECT value FROM manifest WHERE key = ?", (key,)).fetchone()
        return None if row is None else str(row[0])

    def set_meta(self, key: str, value: str) -> None:
        self.conn.execute("INSERT OR REPLACE INTO manifest(key, value) VALUES (?, ?)", (key, value))

    # ----- writes ---------------------------------------------------------------------------------------------
    def doc_hash(self, doc_id: str) -> str | None:
        row = self.conn.execute("SELECT content_hash FROM documents WHERE id = ?", (doc_id,)).fetchone()
        return None if row is None else str(row[0])

    def upsert(self, doc: Document, chunks: Sequence[Chunk]) -> list[int]:
        """Replace a document and its chunks. Returns the chunk rowids (used by sqlite-vec)."""
        self.delete([doc.id])
        self.conn.execute(
            "INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (doc.id, doc.title, doc.doc_type, doc.system, doc.owner, doc.access, doc.updated,
             ",".join(doc.tags), doc.source, doc.content_hash, doc.text, json.dumps(doc.extra, default=str)),
        )
        rowids: list[int] = []
        for c in chunks:
            cur = self.conn.execute(
                "INSERT INTO chunks(id, doc_id, ordinal, heading, text, access, doc_type, system) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (c.id, c.doc_id, c.ordinal, c.heading, c.text, doc.access, doc.doc_type, doc.system),
            )
            rowid = int(cur.lastrowid or 0)
            self.conn.execute("INSERT INTO chunks_fts(rowid, embed_text) VALUES (?, ?)", (rowid, c.embed_text))
            rowids.append(rowid)
        return rowids

    def delete(self, doc_ids: Iterable[str]) -> list[int]:
        removed: list[int] = []
        for doc_id in doc_ids:
            rows = self.conn.execute("SELECT rowid FROM chunks WHERE doc_id = ?", (doc_id,)).fetchall()
            for (rowid,) in rows:
                self.conn.execute("DELETE FROM chunks_fts WHERE rowid = ?", (rowid,))
                removed.append(int(rowid))
            self.conn.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
            self.conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        return removed

    def commit(self) -> None:
        self.conn.commit()

    # ----- reads ----------------------------------------------------------------------------------------------
    @staticmethod
    def _filters(access: Sequence[str], doc_types: Sequence[str] | None,
                 systems: Sequence[str] | None) -> tuple[str, list[Any]]:
        clauses = [f"c.access IN ({','.join('?' * len(access))})"]
        params: list[Any] = list(access)
        if doc_types:
            clauses.append(f"c.doc_type IN ({','.join('?' * len(doc_types))})")
            params.extend(doc_types)
        if systems:
            clauses.append(f"c.system IN ({','.join('?' * len(systems))})")
            params.extend(systems)
        return " AND ".join(clauses), params

    def keyword_search(self, query: str, k: int, access: Sequence[str], doc_types: Sequence[str] | None = None,
                       systems: Sequence[str] | None = None) -> list[tuple[str, float]]:
        """BM25 over title + heading + chunk text. Returns ``(chunk_id, score)``, higher is better."""
        q = fts_query(query)
        if not q:
            return []
        where, params = self._filters(access, doc_types, systems)
        rows = self.conn.execute(
            f"SELECT c.id, bm25(chunks_fts) AS s FROM chunks_fts JOIN chunks c ON c.rowid = chunks_fts.rowid "  # noqa: S608
            f"WHERE chunks_fts MATCH ? AND {where} ORDER BY s LIMIT ?",
            [q, *params, k],
        ).fetchall()
        return [(str(r[0]), -float(r[1])) for r in rows]

    def allowed_rowids(self, rowids: Sequence[int], access: Sequence[str], doc_types: Sequence[str] | None = None,
                       systems: Sequence[str] | None = None) -> dict[int, str]:
        """Filter rowids by access and metadata, returning ``rowid -> chunk_id`` for the ones that pass."""
        if not rowids:
            return {}
        where, params = self._filters(access, doc_types, systems)
        rows = self.conn.execute(
            f"SELECT c.rowid, c.id FROM chunks c WHERE c.rowid IN ({','.join('?' * len(rowids))}) AND {where}",  # noqa: S608
            [*rowids, *params],
        ).fetchall()
        return {int(r[0]): str(r[1]) for r in rows}

    def rowids_for(self, chunk_ids: Sequence[str]) -> dict[str, int]:
        if not chunk_ids:
            return {}
        rows = self.conn.execute(
            f"SELECT id, rowid FROM chunks WHERE id IN ({','.join('?' * len(chunk_ids))})", list(chunk_ids)  # noqa: S608
        ).fetchall()
        return {str(r[0]): int(r[1]) for r in rows}

    def get_chunks(self, chunk_ids: Sequence[str]) -> dict[str, Chunk]:
        if not chunk_ids:
            return {}
        rows = self.conn.execute(
            "SELECT c.id, c.doc_id, c.ordinal, c.heading, c.text, d.title, d.doc_type, d.system, d.owner, d.access, "
            f"d.updated, d.tags, d.source FROM chunks c JOIN documents d ON d.id = c.doc_id "  # noqa: S608
            f"WHERE c.id IN ({','.join('?' * len(chunk_ids))})",
            list(chunk_ids),
        ).fetchall()
        out: dict[str, Chunk] = {}
        for r in rows:
            meta = {"doc_id": r["doc_id"], "title": r["title"], "doc_type": r["doc_type"], "system": r["system"],
                    "owner": r["owner"], "access": r["access"], "updated": r["updated"], "tags": r["tags"],
                    "source": r["source"]}
            out[r["id"]] = Chunk(id=r["id"], doc_id=r["doc_id"], ordinal=r["ordinal"], text=r["text"],
                                 heading=r["heading"] or "", meta=meta)
        return out

    def get_document(self, doc_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["tags"] = [t for t in (d.get("tags") or "").split(",") if t]
        d["extra"] = json.loads(d.get("extra") or "{}")
        return d

    def list_documents(self, access: Sequence[str]) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            f"SELECT id, title, doc_type, system, owner, access, updated, source FROM documents "  # noqa: S608
            f"WHERE access IN ({','.join('?' * len(access))}) ORDER BY id",
            list(access),
        ).fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> dict[str, Any]:
        docs = self.conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        chunks = self.conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        by_type = dict(self.conn.execute("SELECT doc_type, COUNT(*) FROM documents GROUP BY doc_type").fetchall())
        by_access = dict(self.conn.execute("SELECT access, COUNT(*) FROM documents GROUP BY access").fetchall())
        return {"documents": docs, "chunks": chunks, "by_doc_type": by_type, "by_access": by_access}

    def all_doc_ids(self) -> set[str]:
        return {str(r[0]) for r in self.conn.execute("SELECT id FROM documents").fetchall()}

    def close(self) -> None:
        self.conn.close()
