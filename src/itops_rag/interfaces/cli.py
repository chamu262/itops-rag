"""Command line: ``itops-rag ingest | search | ask | prompts | eval | stats | serve | mcp``."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from itops_rag import __version__
from itops_rag.config import SearchMode, Settings
from itops_rag.core.index import Index

app = typer.Typer(
    help="Retrieval-augmented answers for IT operations.", no_args_is_help=True, add_completion=False
)
prompts_app = typer.Typer(help="Browse the RAG prompt library.", no_args_is_help=True)
app.add_typer(prompts_app, name="prompts")
console = Console()

IndexOpt = Annotated[Path | None, typer.Option("--index", "-i", help="Index folder (default from settings).")]
RoleOpt = Annotated[str | None, typer.Option("--role", "-r", help="public | it-staff | security")]
JsonOpt = Annotated[bool, typer.Option("--json", help="Print JSON instead of formatted output.")]


def _settings(index: Path | None, **overrides: Any) -> Settings:
    s = Settings()
    if index is not None:
        s.index_dir = index
    for k, v in overrides.items():
        if v is not None:
            setattr(s, k, v)
    return s


def _open(settings: Settings, rerank: bool = True) -> Index:
    with console.status("Loading index and local models…", spinner="dots"):
        return Index.open(settings, reranker=rerank)


@app.command()
def version() -> None:
    """Print the version."""
    console.print(__version__)


@app.command()
def ingest(
    path: Annotated[Path, typer.Argument(help="File or folder to ingest.", exists=True)],
    index: IndexOpt = None,
    store: Annotated[str | None, typer.Option(help="auto | sqlite | chroma")] = None,
    rebuild: Annotated[bool, typer.Option(help="Delete the index first.")] = False,
    prune: Annotated[
        bool, typer.Option(help="Remove indexed documents that are no longer under PATH.")
    ] = False,
    as_json: JsonOpt = False,
) -> None:
    """Load, redact, chunk, embed and index documents. Unchanged documents are skipped."""
    s = _settings(index, store=store)
    if rebuild:
        Index.wipe(s)
    with _open(s, rerank=False) as ix, console.status("Ingesting…"):
        report = ix.ingest_path(path, prune_missing=prune)
        stats = ix.stats()
    if as_json:
        print(json.dumps({"report": report.to_dict(), "stats": stats}, indent=2))
        return
    console.print(
        f"[bold green]Indexed[/] {report.added} new, {report.updated} updated, {report.unchanged} unchanged, "
        f"{report.removed} removed → {report.chunks} chunks embedded "
        f"([dim]{stats['store']}, {stats['documents']} docs / {stats['chunks']} chunks total[/])"
    )
    if report.redaction.total:
        console.print(
            "[yellow]Redacted:[/] " + ", ".join(f"{k} ×{v}" for k, v in report.redaction.counts.items())
        )
    for err in report.errors:
        console.print(f"[red]skipped[/] {err}")


@app.command()
def search(
    query: Annotated[str, typer.Argument(help="What to search for.")],
    k: Annotated[int, typer.Option("-k", help="Number of results.")] = 5,
    mode: Annotated[str, typer.Option(help="vector | keyword | hybrid | hybrid_rerank")] = "hybrid_rerank",
    role: RoleOpt = None,
    system: Annotated[list[str] | None, typer.Option(help="Filter by system (repeatable).")] = None,
    doc_type: Annotated[list[str] | None, typer.Option(help="Filter by doc type (repeatable).")] = None,
    index: IndexOpt = None,
    as_json: JsonOpt = False,
) -> None:
    """Search only: no model call, no cost."""
    s = _settings(index)
    m: SearchMode = mode  # type: ignore[assignment]
    with _open(s, rerank=mode == "hybrid_rerank") as ix:
        hits = ix.search(query, k=k, role=role, systems=system, doc_types=doc_type, mode=m)
    if as_json:
        print(json.dumps([h.to_dict() for h in hits], indent=2))
        return
    if not hits:
        console.print("[yellow]No matches for your access level.[/]")
        return
    table = Table(show_lines=False, header_style="bold")
    for col in ("#", "Doc", "Title / section", "Type", "Score", "Vec", "Kw"):
        table.add_column(col)
    for n, h in enumerate(hits, start=1):
        title = h.chunk.meta.get("title", "") + (f" › {h.chunk.heading}" if h.chunk.heading else "")
        table.add_row(
            str(n),
            h.doc_id,
            title[:70],
            str(h.chunk.meta.get("doc_type", "")),
            f"{h.score:.3f}",
            str(h.vector_rank or "–"),
            str(h.keyword_rank or "–"),
        )
    console.print(table)


@app.command()
def ask(
    question: Annotated[str, typer.Argument(help="The question.")],
    prompt: Annotated[
        str, typer.Option("--prompt", "-p", help="Prompt id (see `itops-rag prompts list`).")
    ] = "qa",
    input_file: Annotated[
        Path | None, typer.Option("--input", help="File with ticket text / change plan ('-' for stdin).")
    ] = None,
    role: RoleOpt = None,
    k: Annotated[int | None, typer.Option("-k", help="Chunks of context (default from the prompt).")] = None,
    model: Annotated[str | None, typer.Option(help="Override the answer model.")] = None,
    verify: Annotated[bool, typer.Option(help="Add a cheap faithfulness check on the fast model.")] = False,
    dry_run: Annotated[bool, typer.Option(help="Show the exact prompt and do not call the API.")] = False,
    show_chunks: Annotated[bool, typer.Option(help="Print the retrieved chunks too.")] = False,
    index: IndexOpt = None,
    as_json: JsonOpt = False,
) -> None:
    """Answer a question from the index with Claude, citing chunk numbers."""
    s = _settings(index, answer_model=model)
    if verify:
        s.verify_answers = True
    input_text = ""
    if input_file is not None:
        input_text = sys.stdin.read() if str(input_file) == "-" else input_file.read_text(encoding="utf-8")
    with _open(s) as ix:
        try:
            ans = ix.ask(question, prompt=prompt, input_text=input_text, role=role, k=k, dry_run=dry_run)
        except (KeyError, ValueError) as e:
            console.print(f"[red]{e}[/]")
            raise typer.Exit(2) from None
    if as_json:
        print(json.dumps(ans.to_dict(), indent=2))
        return
    if dry_run:
        console.print(ans.text, markup=False, highlight=False)
        return
    style = "yellow" if ans.refused else "green"
    console.print(Panel(Markdown(ans.text), title=f"[bold]{ans.prompt_id}[/]", border_style=style))
    for src in ans.sources():
        console.print(
            f"  [{src['n']}] [bold]{src['doc_id']}[/] {src['title']}"
            + (f" › {src['heading']}" if src["heading"] else "")
            + f"  [dim]{src['source']}[/]"
        )
    for w in ans.warnings:
        console.print(f"[yellow]⚠ {w}[/]")
    if show_chunks:
        for n, h in enumerate(ans.hits, start=1):
            console.print(
                Panel(h.chunk.text, title=f"[{n}] {h.doc_id} › {h.chunk.heading}", border_style="dim")
            )
    u = ans.usage
    if u.model:
        console.print(
            f"[dim]{u.model} · in {u.input_tokens} (cache read {u.cache_read_tokens}) · out "
            f"{u.output_tokens} · ${u.cost_usd:.4f}[/]"
        )
    else:
        console.print("[dim]No model call (refused locally) · $0.0000[/]")


@prompts_app.command("list")
def prompts_list(as_json: JsonOpt = False) -> None:
    """List available prompt templates."""
    from itops_rag.prompts.registry import PromptRegistry

    reg = PromptRegistry.default(Settings().prompt_dirs)
    if as_json:
        print(json.dumps([p.to_dict() for p in reg.list()], indent=2))
        return
    table = Table(header_style="bold")
    for col in ("Id", "Pack", "Tier", "Needs input", "Description"):
        table.add_column(col)
    for p in reg.list():
        table.add_row(p.id, p.pack, p.tier, p.input_label if p.needs_input else "", p.description)
    console.print(table)


@prompts_app.command("show")
def prompts_show(prompt_id: str) -> None:
    """Show one template: retrieval settings, task and output format."""
    from itops_rag.prompts.registry import PromptRegistry

    p = PromptRegistry.default(Settings().prompt_dirs).get(prompt_id)
    console.print(
        Panel(
            f"[bold]{p.title}[/] (v{p.version}, {p.pack}, tier={p.tier}, top_k={p.top_k}, "
            f"doc_types={p.doc_types})\n\n{p.description}\n\n[bold]Task[/]\n{p.task}\n"
            f"[bold]Output[/]\n{p.output}",
            title=p.id,
        )
    )


@app.command("eval")
def eval_cmd(
    golden: Annotated[Path, typer.Option(help="Golden set (JSONL).")] = Path("eval/golden.jsonl"),
    k: Annotated[int, typer.Option("-k")] = 4,
    baseline: Annotated[
        Path | None, typer.Option(help="Fail if metrics drop below this baseline JSON.")
    ] = None,
    write_baseline: Annotated[Path | None, typer.Option(help="Save results as the new baseline.")] = None,
    report: Annotated[Path | None, typer.Option(help="Write a Markdown report here.")] = None,
    llm: Annotated[bool, typer.Option(help="Also run full answers through Claude (costs tokens).")] = False,
    llm_limit: Annotated[int | None, typer.Option(help="Max questions for --llm.")] = None,
    index: IndexOpt = None,
) -> None:
    """Measure retrieval quality per mode (offline, free) and optionally answer quality (--llm)."""
    from itops_rag.evaluation import (
        check_gate,
        evaluate_answers,
        evaluate_retrieval,
        load_golden,
        markdown_table,
    )

    items = load_golden(golden)
    s = _settings(index)
    with _open(s) as ix:
        results = evaluate_retrieval(ix, items, k=k)
        answers = evaluate_answers(ix, items, limit=llm_limit) if llm else None
    table = markdown_table(results)
    console.print(
        Markdown(
            f"**{len(items)} questions** ({sum(i.answerable for i in items)} answerable), k={k}\n\n" + table
        )
    )
    for r in results:
        if r.misses:
            console.print(f"[dim]{r.mode} misses: {', '.join(r.misses)}[/]")
    payload = {"k": k, "questions": len(items), "modes": {r.mode: r.to_dict() for r in results}}
    if answers:
        payload["answers"] = answers
        console.print(
            f"Answers: refusal correct {answers['refusal_correct']:.2f}, citation precision "
            f"{answers['citation_precision']}, cost ${answers['total_cost_usd']}"
        )
    if report:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(
            f"# Retrieval evaluation\n\n{len(items)} questions, k={k}\n\n{table}\n", encoding="utf-8"
        )
    if write_baseline:
        write_baseline.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        console.print(f"Baseline written to {write_baseline}")
    if baseline:
        failures = check_gate(results, json.loads(baseline.read_text(encoding="utf-8")))
        if failures:
            for f in failures:
                console.print(f"[red]FAIL[/] {f}")
            raise typer.Exit(1)
        console.print("[green]Eval gate passed.[/]")


@app.command()
def stats(index: IndexOpt = None) -> None:
    """Show what is in the index."""
    with _open(_settings(index), rerank=False) as ix:
        print(json.dumps(ix.stats(), indent=2))


@app.command()
def serve(
    host: Annotated[str, typer.Option()] = "127.0.0.1",
    port: Annotated[int, typer.Option()] = 8080,
    index: IndexOpt = None,
) -> None:
    """Run the web UI and JSON API (needs the [web] extra)."""
    import uvicorn

    from itops_rag.interfaces.web import create_app

    uvicorn.run(create_app(_settings(index)), host=host, port=port)


@app.command()
def mcp(index: IndexOpt = None) -> None:
    """Run the read-only MCP server on stdio (needs the [mcp] extra)."""
    from itops_rag.interfaces.mcp_server import build_server

    build_server(_settings(index)).run("stdio")


if __name__ == "__main__":
    app()
