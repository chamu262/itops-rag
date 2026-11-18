"""itops-rag: retrieval-augmented answers for IT operations, and a small reusable RAG engine.

Public API (stable within a minor version):

    Index, Settings, Document, Chunk, Hit, Answer, PromptRegistry, PromptTemplate, visible_access
"""

from itops_rag.config import Settings
from itops_rag.core.index import Index, IndexMismatchError, IngestReport
from itops_rag.core.models import ACCESS_LEVELS, Answer, Chunk, Document, Hit, Usage, visible_access
from itops_rag.prompts.registry import PromptRegistry, PromptTemplate

__version__ = "0.2.1"

__all__ = [
    "ACCESS_LEVELS",
    "Answer",
    "Chunk",
    "Document",
    "Hit",
    "Index",
    "IndexMismatchError",
    "IngestReport",
    "PromptRegistry",
    "PromptTemplate",
    "Settings",
    "Usage",
    "__version__",
    "visible_access",
]
