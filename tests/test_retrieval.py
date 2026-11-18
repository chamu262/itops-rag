from __future__ import annotations

from pathlib import Path

import pytest

from itops_rag import Document, Index, IndexMismatchError, Settings
from itops_rag.core.embeddings import HashEmbedder
from itops_rag.core.retriever import keyword_weight_for, rrf
from itops_rag.stores.docstore import fts_query


def test_rrf_rewards_agreement() -> None:
    fused = dict(rrf([["a", "b", "c"], ["c", "a", "d"]]))
    assert max(fused, key=fused.__getitem__) == "a"
    assert fused["d"] < fused["c"]


def test_codes_raise_keyword_weight() -> None:
    assert keyword_weight_for("why AADSTS53003?", 1.0) > keyword_weight_for("why can't I sign in?", 1.0)


def test_fts_query_is_safe() -> None:
    assert fts_query('") OR 1=1; DROP TABLE chunks; --') == '"1" OR "drop" OR "table" OR "chunks"'
    assert fts_query("the and of") == ""


@pytest.mark.parametrize("mode", ["vector", "keyword", "hybrid", "hybrid_rerank"])
def test_every_mode_finds_the_runbook(index: Index, mode: str) -> None:
    hits = index.search("MG-401 after macOS update", k=3, mode=mode)  # type: ignore[arg-type]
    assert hits and hits[0].doc_id == "RB-VPN-001"


def test_access_tags_filter_results(index: Index) -> None:
    q = "break-glass account sealed envelope"
    assert all(h.doc_id != "RB-ENTRA-009" for h in index.search(q, role="it-staff"))
    assert all(h.chunk.meta["access"] == "public" for h in index.search(q, role="public"))
    assert index.search(q, role="security")[0].doc_id == "RB-ENTRA-009"
    assert index.get_document("RB-ENTRA-009", role="it-staff") is None


def test_filters_by_doc_type_and_system(index: Index) -> None:
    hits = index.search("steps", k=10, doc_types=["kb"], role="security")
    assert hits and {h.chunk.meta["doc_type"] for h in hits} == {"kb"}
    hits = index.search("steps", k=10, systems=["entra"], role="security")
    assert {h.chunk.meta["system"] for h in hits} == {"entra"}


def test_reingest_is_incremental(index: Index) -> None:
    from tests.conftest import sample_docs

    report = index.ingest(sample_docs())
    assert report.unchanged == 4 and report.added == 0
    docs = sample_docs()
    docs[0].text += "\n\n## Note\nUpdated."
    report = index.ingest(docs)
    assert report.updated == 1
    assert index.stats()["documents"] == 4


def test_prune_and_delete(index: Index) -> None:
    from tests.conftest import sample_docs

    report = index.ingest(sample_docs()[:2], prune_missing=True)
    assert report.removed == 2
    assert index.stats()["documents"] == 2
    index.delete(["KB-0001"])
    assert index.search("Authenticator QR code", role="security", mode="keyword") == []


def test_ingest_redacts_before_storing(index: Index) -> None:
    doc = index.get_document("KB-0009", role="public")
    assert doc is not None
    assert "jane.doe" not in doc["text"]
    assert "servicedesk@kestrelcloud.example" in doc["text"]


def test_model_mismatch_is_refused(settings: Settings) -> None:
    Index.open(settings, embedder=HashEmbedder(64), reranker=False).close()
    with pytest.raises(IndexMismatchError):
        Index.open(settings, embedder=HashEmbedder(128), reranker=False)


def test_numpy_fallback_matches_sqlite_vec(tmp_path: Path) -> None:
    from itops_rag.stores.docstore import DocStore
    from itops_rag.stores.vectors import SqliteVectorStore

    emb = HashEmbedder(64)
    results = []
    for use_ext in (True, False):
        ds = DocStore(tmp_path / f"{use_ext}.sqlite")
        vs = SqliteVectorStore(ds, emb.dim, use_extension=use_ext)
        docs = [
            Document(id=f"D{i}", title=f"doc {i}", text=t)
            for i, t in enumerate(["vpn gateway error", "printer queue", "mfa reset phone"])
        ]
        for d in docs:
            from itops_rag.core.chunking import chunk_document

            chunks = chunk_document(d)
            rowids = ds.upsert(d, chunks)
            vs.add(
                [c.id for c in chunks],
                rowids,
                emb.embed_documents([c.embed_text for c in chunks]),
                [c.meta for c in chunks],
            )
        results.append([cid for cid, _ in vs.search(emb.embed_query("vpn error"), 3, ["public"])])
    assert results[0] == results[1]


def test_chroma_store_works(tmp_path: Path) -> None:
    pytest.importorskip("chromadb")
    from tests.conftest import sample_docs

    s = Settings(index_dir=tmp_path / "ix", store="chroma", cost_ledger=tmp_path / "c.jsonl", _env_file=None)  # type: ignore[call-arg]
    ix = Index.open(s, embedder=HashEmbedder(), reranker=False)
    ix.ingest(sample_docs())
    assert ix.stats()["store"] == "chroma"
    hits = ix.search("MG-401 macOS", role="it-staff", mode="vector")
    assert hits[0].doc_id == "RB-VPN-001"
    assert all(
        h.chunk.meta["access"] != "security"
        for h in ix.search("break-glass", role="it-staff", mode="vector", k=10)
    )


def test_concurrent_searches_are_safe(index: Index) -> None:
    from concurrent.futures import ThreadPoolExecutor

    def work(i: int) -> str:
        q = ["MG-401 macOS", "Authenticator QR code", "London printer"][i % 3]
        return index.search(q, k=2, role="security")[0].doc_id

    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(work, range(600)))
    assert set(results[0::3]) == {"RB-VPN-001"}
    assert set(results[1::3]) == {"KB-0001"}
    assert set(results[2::3]) == {"KB-0009"}


def test_prune_is_scoped_to_its_folder_and_keeps_failed_files(index: Index, tmp_path: Path) -> None:
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    (a / "one.md").write_text("---\nid: A-1\n---\n# One\nalpha text")
    (a / "two.md").write_text("---\nid: A-2\n---\n# Two\nbeta text")
    (b / "three.md").write_text("---\nid: B-1\n---\n# Three\ngamma text")
    index.ingest_path(a)
    index.ingest_path(b)
    # A-2's file breaks (bad front matter): it must not be pruned just because it failed to load this run.
    (a / "two.md").write_text("---\naccess: everyone\n---\nbroken")
    (a / "one.md").unlink()
    report = index.ingest_path(a, prune_missing=True)
    ids = index.docs.all_doc_ids()
    assert "A-1" not in ids and "A-2" in ids and "B-1" in ids and "RB-VPN-001" in ids
    assert report.removed == 1 and report.errors


def test_documents_without_access_tag_fail_closed(index: Index, tmp_path: Path) -> None:
    (tmp_path / "note.md").write_text("# Untagged\nsecret-ish internal procedure")
    index.ingest_path(tmp_path)
    assert index.get_document("NOTE", role="public") is None
    assert index.get_document("NOTE", role="it-staff") is not None


def test_pasted_input_drives_retrieval(index: Index) -> None:
    from itops_rag import Document

    index.ingest(
        [
            Document(
                id="HELP-9",
                title="HELP-9: London printer offline",
                doc_type="ticket",
                access="it-staff",
                text="Printer on the 3rd floor in London shows offline. Fix: re-add queue.",
            )
        ]
    )
    ctx = index.context_for(
        "Triage this",
        prompt="ticket_triage",
        input_text="Can't print in London since Monday, the 3rd floor printer shows offline",
    )
    assert not ctx["refused"]
    assert ctx["chunks"][0]["doc_id"] == "HELP-9"
