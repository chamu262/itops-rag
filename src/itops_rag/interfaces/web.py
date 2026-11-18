"""FastAPI app: a one-page chat UI with citations, plus a JSON API.

Auth is out of scope for the demo: run it on localhost or behind your SSO proxy. The role comes from a trusted
header set by that proxy (``X-ITOPS-Role``) and falls back to the server's default role; it is never read from the
request body.
"""

from importlib import resources
from typing import Any

from itops_rag.config import Settings
from itops_rag.core.index import Index
from itops_rag.core.models import ACCESS_LEVELS


def create_app(settings: Settings | None = None, index: Index | None = None) -> Any:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import HTMLResponse
    from pydantic import BaseModel, Field

    settings = settings or Settings()
    state: dict[str, Index] = {}

    def ix() -> Index:
        if index is not None:
            return index
        if "ix" not in state:
            state["ix"] = Index.open(settings)
        return state["ix"]

    def role_of(request: Request) -> str:
        role = request.headers.get("x-itops-role", settings.default_role)
        if role not in ACCESS_LEVELS:
            raise HTTPException(400, f"unknown role {role!r}")
        return role

    class AskBody(BaseModel):
        question: str = Field(min_length=3, max_length=2000)
        prompt: str = "qa"
        input_text: str = Field(default="", max_length=20000)
        dry_run: bool = False

    app = FastAPI(title="itops-rag", version="0.1.0", docs_url="/api/docs")
    page = (resources.files("itops_rag.interfaces") / "static" / "index.html").read_text(encoding="utf-8")

    @app.get("/", response_class=HTMLResponse)
    def home() -> str:
        return page

    @app.get("/healthz")
    def healthz() -> dict[str, Any]:
        return {"ok": True}

    @app.get("/api/stats")
    def api_stats() -> dict[str, Any]:
        return ix().stats()

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
