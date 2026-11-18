"""FastAPI app: a one-page chat UI with citations, plus a JSON API.

Auth is out of scope for the demo: run it on localhost or behind your SSO proxy. Requests get
``web_default_role`` (``public``). A higher role is accepted only from ``X-ITOPS-Role`` when the request also carries
``X-ITOPS-Proxy-Secret`` equal to ``ITOPS_RAG_ROLE_HEADER_SECRET``: your proxy sets both after authenticating the user,
and must strip any copies the client sent. With no secret configured, the role header is ignored.
"""

import hmac
import threading
from importlib import resources
from typing import Any

from itops_rag.config import Settings
from itops_rag.core.index import Index
from itops_rag.core.models import ACCESS_LEVELS


def create_app(settings: Settings | None = None, index: Index | None = None) -> Any:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import HTMLResponse
    from pydantic import BaseModel, Field

    from itops_rag import __version__

    settings = settings or Settings()
    state: dict[str, Index] = {}
    init_lock = threading.Lock()

    def ix() -> Index:
        if index is not None:
            return index
        with init_lock:  # FastAPI runs sync endpoints in a threadpool: open the index exactly once
            if "ix" not in state:
                state["ix"] = Index.open(settings)
        return state["ix"]

    def role_of(request: Request) -> str:
        secret = settings.role_header_secret
        claimed = request.headers.get("x-itops-role")
        if not secret or claimed is None:
            return settings.web_default_role
        presented = request.headers.get("x-itops-proxy-secret", "")
        if not hmac.compare_digest(presented.encode(), secret.encode()):
            raise HTTPException(403, "role header without a valid proxy secret")
        if claimed not in ACCESS_LEVELS:
            raise HTTPException(400, f"unknown role {claimed!r}")
        return claimed

    class AskBody(BaseModel):
        question: str = Field(min_length=3, max_length=2000)
        prompt: str = "qa"
        input_text: str = Field(default="", max_length=20000)
        dry_run: bool = False

    app = FastAPI(title="itops-rag", version=__version__, docs_url="/api/docs")
    page = (resources.files("itops_rag.interfaces") / "static" / "index.html").read_text(encoding="utf-8")

    @app.get("/", response_class=HTMLResponse)
    def home() -> str:
        return page

    @app.get("/healthz")
    def healthz() -> dict[str, Any]:
        return {"ok": True}

    @app.get("/api/stats")
    def api_stats() -> dict[str, Any]:
        s = ix().stats()  # no paths or per-access counts for unauthenticated callers
        return {k: s[k] for k in ("documents", "chunks", "store", "reranker", "embed_model")}

    @app.get("/api/prompts")
    def api_prompts() -> list[dict[str, Any]]:
        return [p.to_dict() for p in ix().prompts.list()]

    @app.get("/api/search")
    def api_search(request: Request, q: str, k: int = 5) -> list[dict[str, Any]]:
        return [h.to_dict() for h in ix().search(q, k=min(k, 20), role=role_of(request))]

    @app.post("/api/ask")
    def api_ask(request: Request, body: AskBody) -> dict[str, Any]:
        try:
            ans = ix().ask(
                body.question,
                prompt=body.prompt,
                input_text=body.input_text,
                role=role_of(request),
                dry_run=body.dry_run,
            )
        except (KeyError, ValueError) as e:
            raise HTTPException(400, str(e)) from None
        return ans.to_dict()

    @app.get("/api/documents/{doc_id}")
    def api_document(request: Request, doc_id: str) -> dict[str, Any]:
        d = ix().get_document(doc_id, role=role_of(request))
        if d is None:
            raise HTTPException(404, "not found")
        return d

    return app
