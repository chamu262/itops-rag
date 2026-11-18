"""LangChain adapter: use an itops-rag ``Index`` as a LangChain ``BaseRetriever``.

    from itops_rag import Index
    from itops_rag.integrations.langchain import ItopsRetriever
    retriever = ItopsRetriever(index=Index.open(), k=4, role="it-staff")
    docs = retriever.invoke("MG-401 after macOS update")

You get hybrid search, reranking, redaction and access tags inside any LangChain chain.
"""

from __future__ import annotations

from typing import Any

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document as LCDocument
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict

from itops_rag.core.index import Index


class ItopsRetriever(BaseRetriever):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    index: Index
    k: int = 4
    role: str | None = None
    doc_types: list[str] | None = None

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun, **kwargs: Any
    ) -> list[LCDocument]:
        hits = self.index.search(query, k=self.k, role=self.role, doc_types=self.doc_types)
        return [
            LCDocument(
                page_content=h.chunk.text, metadata={k: v for k, v in h.to_dict().items() if k != "text"}
            )
            for h in hits
        ]
