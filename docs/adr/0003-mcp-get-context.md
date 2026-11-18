# ADR 0003: MCP exposes context, not only answers

**Status:** accepted · 2026-11

## Context
The agents that use this index (Claude Code, personal agent systems) already run on Claude. If the MCP server
answered with its own API key, every agent question would be paid for twice.

## Decision
The MCP server's main tool is `get_context`: retrieval plus the fully rendered grounded prompt and system rules. The
calling agent answers with its own model. `answer_question` exists but is off unless
`ITOPS_RAG_MCP_ALLOW_ANSWERS=true`. Every tool is read-only, and the caller's role is fixed by the server's
configuration.

## Consequences
+ No second bill. The grounding rules travel with the context.
- The quality of the final answer depends on the calling agent following the rules. Answers from the server's own
  path stay available for clients that can't.
