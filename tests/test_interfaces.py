from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from itops_rag import Index


def test_web_api(index: Index) -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from itops_rag.interfaces.web import create_app

    client = TestClient(create_app(index.settings, index=index))
    assert client.get("/healthz").json() == {"ok": True}
    assert "IT Ops RAG" in client.get("/").text
    assert any(p["id"] == "troubleshoot" for p in client.get("/api/prompts").json())

    hits = client.get("/api/search", params={"q": "break-glass envelope"}).json()
    assert all(h["access"] != "security" for h in hits)
    hits = client.get(
        "/api/search", params={"q": "break-glass envelope"}, headers={"x-itops-role": "security"}
    ).json()
    assert hits[0]["doc_id"] == "RB-ENTRA-009"
    assert client.get("/api/search", params={"q": "x"}, headers={"x-itops-role": "root"}).status_code == 400

    r = client.post("/api/ask", json={"question": "MG-401 after macOS update"})
    body = r.json()
    assert r.status_code == 200 and body["cited"] == [1] and body["sources"][0]["doc_id"] == "RB-VPN-001"
    assert client.post("/api/ask", json={"question": "hello", "prompt": "nope"}).status_code == 400
    assert client.get("/api/documents/RB-ENTRA-009").status_code == 404


def _call(server: Any, name: str, args: dict[str, Any]) -> Any:
    result = asyncio.run(server.call_tool(name, args))
    # MCPServer.call_tool returns content blocks and/or structured output depending on the SDK version.
    if isinstance(result, tuple):
        result = result[1] if result[1] is not None else result[0]
    if isinstance(result, dict) and "result" in result:
        return result["result"]
    if isinstance(result, list) and result and hasattr(result[0], "text"):
        return json.loads(result[0].text) if len(result) == 1 else [json.loads(b.text) for b in result]
    content = getattr(result, "structured_content", None) or getattr(result, "structuredContent", None)
    if content is not None:
        return content.get("result", content)
    return result


def test_mcp_tools(index: Index) -> None:
    pytest.importorskip("mcp")
    from itops_rag.interfaces.mcp_server import build_server

    server = build_server(index.settings, index=index)
    tools = {t.name: t for t in asyncio.run(server.list_tools())}
    assert {"search_kb", "get_context", "similar_tickets", "get_document", "list_prompts"} <= set(tools)
    assert "answer_question" not in tools  # off unless explicitly enabled
    assert all(t.annotations and t.annotations.read_only_hint for t in tools.values())

    hits = _call(server, "search_kb", {"query": "MG-401 macOS", "k": 2})
    assert hits[0]["doc_id"] == "RB-VPN-001"
    ctx = _call(server, "get_context", {"question": "MG-401 macOS", "prompt": "troubleshoot"})
    assert "<context>" in ctx["prompt"] and "Grounding rules" in ctx["system"]
    assert "error" in _call(server, "get_document", {"doc_id": "RB-ENTRA-009"})


def test_cli_offline_commands(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from typer.testing import CliRunner

    from itops_rag.core.embeddings import HashEmbedder
    from itops_rag.core.rerank import OverlapReranker
    from itops_rag.interfaces import cli

    real_open = Index.open

    def fake_open(settings, **kw):  # type: ignore[no-untyped-def]
        kw.pop("reranker", None)
        return real_open(settings, embedder=HashEmbedder(), reranker=OverlapReranker(), **kw)

    monkeypatch.setattr(Index, "open", staticmethod(fake_open))
    monkeypatch.setenv("ITOPS_RAG_COST_LEDGER", str(tmp_path / "c.jsonl"))
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "rb.md").write_text(
        "---\nid: RB-1\ntitle: Fix MG-401\naccess: it-staff\n---\n## Steps\nRun reauth.\n"
    )
    runner = CliRunner()
    ix = ["--index", str(tmp_path / "ix")]
    r = runner.invoke(cli.app, ["ingest", str(docs), *ix, "--store", "sqlite", "--json"])
    assert r.exit_code == 0, r.output
    assert json.loads(r.output)["report"]["added"] == 1
    r = runner.invoke(cli.app, ["search", "MG-401", *ix, "--json"])
    assert r.exit_code == 0 and json.loads(r.output)[0]["doc_id"] == "RB-1"
    r = runner.invoke(cli.app, ["ask", "How to fix MG-401?", *ix, "--dry-run"])
    assert r.exit_code == 0 and "<context>" in r.output
    r = runner.invoke(cli.app, ["prompts", "list", "--json"])
    assert r.exit_code == 0 and len(json.loads(r.output)) >= 15


def test_slack_formatting(index: Index) -> None:
    from itops_rag.interfaces.slack_bot import format_answer

    blocks = format_answer(index.ask("MG-401 macOS"))
    assert blocks[0]["type"] == "section" and "RB-VPN-001" in blocks[1]["elements"][0]["text"]


def test_langchain_retriever(index: Index) -> None:
    pytest.importorskip("langchain_core")
    from itops_rag.integrations.langchain import ItopsRetriever

    docs = ItopsRetriever(index=index, k=2).invoke("MG-401 macOS")
    assert docs[0].metadata["doc_id"] == "RB-VPN-001"
