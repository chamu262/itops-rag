import itertools

from itops_rag import Document
from itops_rag.core.chunking import chunk_document, split_sections, split_text


def test_sections_keep_heading_breadcrumbs_and_skip_h1() -> None:
    text = "# Title\nintro\n## Steps\none\n### Detail\ntwo\n## Rollback\nthree"
    secs = split_sections(text)
    assert [(s.heading, s.text) for s in secs] == [
        ("", "intro"),
        ("Steps", "one"),
        ("Steps > Detail", "two"),
        ("Rollback", "three"),
    ]


def test_headings_inside_code_fences_are_ignored() -> None:
    secs = split_sections("## A\n```bash\n# not a heading\necho hi\n```\n")
    assert len(secs) == 1 and "# not a heading" in secs[0].text


def test_split_text_respects_size_and_overlap() -> None:
    text = " ".join(f"word{i}" for i in range(400))
    chunks = split_text(text, size=200, overlap=40)
    assert all(len(c) <= 200 for c in chunks)
    assert len(chunks) > 5
    # overlap: the start of each chunk appeared at the end of the previous one
    for a, b in itertools.pairwise(chunks):
        assert b.split()[0] in a


def test_short_documents_stay_whole() -> None:
    doc = Document(id="D1", title="t", text="short text")
    chunks = chunk_document(doc, 800, 100)
    assert len(chunks) == 1 and chunks[0].id == "D1#0"


def test_embed_text_has_title_and_heading() -> None:
    doc = Document(id="D2", title="Re-enrol a Mac", text="## Steps\nRun profiles renew.")
    (c,) = chunk_document(doc)
    assert c.embed_text.startswith("Re-enrol a Mac > Steps\n")


def test_invalid_split_arguments() -> None:
    import pytest

    with pytest.raises(ValueError):
        split_text("abc", 10, 10)


def test_overlap_survives_long_paragraphs() -> None:
    para = " ".join(["word"] * 150)  # ~750 chars, close to the chunk size
    chunks = split_text(f"{para}\n\n{para}\n\n{para}", size=800, overlap=100)
    assert len(chunks) == 3
    assert all(c.startswith("word") for c in chunks)
    assert len(chunks[1]) > len(para)  # carries some overlap from the previous paragraph


def test_table_rows_become_their_own_chunks() -> None:
    from itops_rag.core.chunking import ChunkOptions

    text = (
        "## Matrix\nIntro line.\n\n| System | Team |\n|---|---|\n| Jamf | Endpoint |\n| Entra | Identity |\n"
    )
    doc = Document(id="OC", title="Escalation", text=text)
    chunks = chunk_document(doc, options=ChunkOptions(table_rows=True))
    rows = [c for c in chunks if c.heading.endswith("table")]
    assert len(rows) == 2 and all(c.text.startswith("| System | Team |") for c in rows)
    assert any("Intro line." in c.text for c in chunks)


def test_small_sections_merge_under_their_common_heading() -> None:
    from itops_rag.core.chunking import ChunkOptions

    text = "## Steps\n### One\nshort a\n### Two\nshort b\n## Rollback\n" + "long " * 100
    chunks = chunk_document(
        Document(id="R", title="T", text=text), options=ChunkOptions(min_section_chars=300)
    )
    assert chunks[0].heading == "Steps" and "short a" in chunks[0].text and "short b" in chunks[0].text


def test_ticket_comments_are_kept_apart() -> None:
    from itops_rag.core.chunking import ChunkOptions

    text = "Ticket HELP-1: VPN\nStatus: Resolved\n\n## Resolution\nReauth fixed it\n\n## Comments\n2026-01-01 noise"
    doc = Document(id="HELP-1", title="HELP-1: VPN", text=text, doc_type="ticket")
    split = chunk_document(doc, options=ChunkOptions(split_ticket_comments=True))
    assert [c.heading for c in split] == ["", "Comments"] and "Reauth fixed it" in split[0].text
    whole = chunk_document(doc, options=ChunkOptions(split_ticket_comments=False))
    assert len(whole) == 1 and "noise" in whole[0].text
