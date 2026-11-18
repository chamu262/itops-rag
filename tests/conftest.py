from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from itops_rag import Document, Index, Settings
from itops_rag.core.embeddings import HashEmbedder
from itops_rag.core.rerank import OverlapReranker

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "data" / "demo" / "kestrel-cloud"


def sample_docs() -> list[Document]:
    return [
        Document(
            id="RB-VPN-001",
            title="MeshGate client cannot connect (MG-401 / MG-503)",
            doc_type="runbook",
            system="meshgate",
            owner="Workplace Network",
            access="it-staff",
            updated="2026-09-01",
            text="## Symptoms\nThe MeshGate client shows MG-401 after a macOS update.\n\n"
            "## Fix\n1. Run `meshgate reauth --force`.\n2. Re-approve the system extension in "
            "System Settings.\n\n## Escalate\nWorkplace Network on-call.",
        ),
        Document(
            id="KB-0001",
            title="Set up MFA in Microsoft Authenticator",
            doc_type="kb",
            system="entra",
            owner="Identity & Access",
            access="public",
            updated="2026-05-02",
            text="## Steps\n1. Open aka.ms/mysecurityinfo.\n2. Add the Authenticator app and scan the QR code.",
        ),
        Document(
            id="RB-ENTRA-009",
            title="Break-glass account use",
            doc_type="runbook",
            system="entra",
            owner="Security Operations",
            access="security",
            updated="2026-08-12",
            text="## When\nOnly when all admin sign-ins fail.\n\n## Steps\nRetrieve the sealed envelope from the "
            "safe and sign in at the admin portal.",
        ),
        Document(
            id="KB-0009",
            title="Office printers",
            doc_type="kb",
            system="general",
            owner="Service Desk",
            access="public",
            text="Add the London printer from Self Service. Contact "
            "servicedesk@kestrelcloud.example or jane.doe@kestrelcloud.example.",
        ),
    ]


class FakeMessages:
    def __init__(self, text: str, model: str) -> None:
        self.text = text
        self.model = model
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        usage = SimpleNamespace(
            input_tokens=1200, output_tokens=150, cache_read_input_tokens=0, cache_creation_input_tokens=0
        )
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=self.text)],
            stop_reason="end_turn",
            usage=usage,
            model=kwargs.get("model", self.model),
        )


class FakeClient:
    """Stands in for anthropic.Anthropic: records calls, returns a canned answer."""

    def __init__(self, text: str = "Run `meshgate reauth --force` [1].") -> None:
        self.messages = FakeMessages(text, "claude-haiku-5-5")
        self.beta = SimpleNamespace(messages=FakeMessages(text, "claude-opus-5-5"))


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        index_dir=tmp_path / "index",
        store="sqlite",
        cost_ledger=tmp_path / "costs.jsonl",
        min_rerank_score=-4.0,
        _env_file=None,
    )  # type: ignore[call-arg]


@pytest.fixture
def fake_client() -> FakeClient:
    return FakeClient()


@pytest.fixture
def index(settings: Settings, fake_client: FakeClient) -> Iterator[Index]:
    ix = Index.open(settings, embedder=HashEmbedder(), reranker=OverlapReranker(), client=fake_client)
    ix.ingest(sample_docs())
    yield ix
    ix.close()
