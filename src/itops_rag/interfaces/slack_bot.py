"""Slack bot stub (Bolt, Socket Mode): ``/itops <question>`` and @mentions answer in a thread with sources.

This is a working stub, not a hardened bot. Before a real workspace: map Slack users or channels to roles from your
IdP groups (``CHANNEL_ROLES`` below is a placeholder), add rate limits, and log to your SIEM.
Manifest: ``deploy/slack-manifest.yaml``. Needs the [slack] extra plus SLACK_BOT_TOKEN and SLACK_APP_TOKEN.
"""

from __future__ import annotations

import os
from typing import Any

from itops_rag.config import Settings
from itops_rag.core.index import Index
from itops_rag.core.models import Answer

# channel id -> role. Anything not listed gets "public".
CHANNEL_ROLES: dict[str, str] = {}


def format_answer(ans: Answer) -> list[dict[str, Any]]:
    """Slack Block Kit blocks for an answer: text, then a compact sources line."""
    blocks: list[dict[str, Any]] = [{"type": "section", "text": {"type": "mrkdwn", "text": ans.text[:2900]}}]
    srcs = ans.sources()
    if srcs:
        line = "  ".join(f"[{s['n']}] *{s['doc_id']}* {s['title'][:60]}" for s in srcs)
        blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": line[:2900]}]})
    if ans.warnings:
        blocks.append(
            {"type": "context", "elements": [{"type": "mrkdwn", "text": "⚠ " + "; ".join(ans.warnings)}]}
        )
    return blocks


def build_app(settings: Settings | None = None) -> Any:
    from slack_bolt import App

    settings = settings or Settings()
    index = Index.open(settings)
    app = App(token=os.environ["SLACK_BOT_TOKEN"], signing_secret=os.environ.get("SLACK_SIGNING_SECRET"))

    def respond_to(question: str, channel: str) -> list[dict[str, Any]]:
        role = CHANNEL_ROLES.get(channel, "public")
        return format_answer(index.ask(question, role=role))

    @app.command("/itops")
    def slash(ack: Any, command: dict[str, Any], respond: Any) -> None:
        ack()
        respond(
            blocks=respond_to(command.get("text", ""), command.get("channel_id", "")),
            response_type="ephemeral",
        )

    @app.event("app_mention")
    def mention(event: dict[str, Any], say: Any) -> None:
        text = " ".join(w for w in event.get("text", "").split() if not w.startswith("<@"))
        say(blocks=respond_to(text, event.get("channel", "")), thread_ts=event.get("ts"))

    return app


def main() -> None:
    from slack_bolt.adapter.socket_mode import SocketModeHandler

    SocketModeHandler(build_app(), os.environ["SLACK_APP_TOKEN"]).start()  # type: ignore[no-untyped-call]


if __name__ == "__main__":
    main()
