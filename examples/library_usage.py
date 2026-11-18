"""Using itops-rag as a library: the same engine, a separate index per app.

This is how Nova OS, Agentic OS or Godfather would embed it: their own index folder, their own documents and their own
prompt pack, with the light SQLite store.

    pip install itops-rag
    python examples/library_usage.py ~/notes
"""

from __future__ import annotations

import sys
from pathlib import Path

from itops_rag import Document, Index, Settings


def main() -> None:
    notes = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else None
    settings = Settings(
        index_dir=Path("~/.my-agent/rag").expanduser(),  # one folder per app; never shared between apps
        store="sqlite",  # no server, one file
        default_role="public",
        assistant_name="Nova",
        audience="one person's private notes and documents",
        answer_model="claude-opus-5-5",
        monthly_budget_usd=5.0,
    )
    with Index.open(settings) as ix:
        if notes:
            report = ix.ingest_path(notes, prune_missing=True)
            print("ingest:", report.to_dict())
        else:
            ix.ingest(
                [
                    Document(
                        id="note-backup",
                        title="Home lab backups",
                        updated="2026-10-02",
                        text="Decided: nightly restic backup to the NAS at 02:00, weekly copy to cloud storage.",
                    )
                ]
            )

        # Free: search only, no API call.
        for hit in ix.search("when do backups run?", k=3):
            print(f"{hit.score:6.2f}  {hit.doc_id}  {hit.chunk.text[:70]!r}")

        # Free: the grounded prompt, for an agent that answers with its own model.
        ctx = ix.context_for("when do backups run?", prompt="notes_qa")
        print("prompt chars:", len(ctx["prompt"]), "refused:", ctx["refused"])

        # Paid: a cited answer from Claude (needs ANTHROPIC_API_KEY). dry_run=True shows the prompt instead.
        answer = ix.ask("When do my backups run?", prompt="notes_qa", dry_run=True)
        print(answer.text[:400])


if __name__ == "__main__":
    main()
