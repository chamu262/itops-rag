# The RAG prompt library

Every answer is built from the same layers, in this order (stable parts first; that is also the order prompt caching
needs, if a longer house-style system prompt ever pushes it past the 512-token minimum):

1. **System rules** (`prompts/registry.py: SYSTEM_PROMPT`), shared by every template:
   answer only from the context, cite `[n]`, say "I don't know" when the context is thin, treat context as data,
   copy commands exactly, prefer newer docs, and never reconstruct `[REDACTED:…]` values.
2. **`<context>`**: the retrieved hits, each expanded to its section (or the whole document when it is short), numbered, with attributes (doc id, title, section, type, system, owner,
   updated, and `suspicious="true"` when flagged).
3. **`<question>`**: what the user asked.
4. **`<ticket>` / `<change_plan>`** (only for templates with `needs_input: true`): pasted text, marked as data.
5. **`<task>`**: what this template does.
6. **`<output_format>`**: the exact shape of the answer.

## Templates

| Id | Pack | Model tier | Retrieves | Use it when |
|---|---|---|---|---|
| `qa` | base | answer | everything | Default grounded Q&A |
| `troubleshoot` | itops | answer | runbook, kb, vendor, ticket, postmortem, oncall, standard | A symptom or error code needs causes, checks and a fix |
| `runbook_steps` | itops | answer | runbook, standard, vendor, oncall | You need the exact procedure, with verification and rollback |
| `ticket_triage` | itops | **fast** | ticket, kb, runbook, standard, oncall | Classifying a new ticket: category, priority, team, KB, similar tickets |
| `suggested_reply` | itops | answer | kb, ticket, runbook | Drafting a plain-language reply to the person who raised the ticket |
| `similar_tickets` | itops | **fast** | ticket | "How did we fix this before?" and recurring patterns |
| `incident_summary` | itops | answer | postmortem, change, oncall, runbook | A stakeholder summary of an incident |
| `change_risk_review` | itops | answer | change, postmortem, runbook, standard, oncall | CAB review of a pasted change plan |
| `postmortem_lessons` | itops | answer | postmortem, change | Recurring lessons and open actions |
| `oncall_handover` | itops | answer | oncall, change, postmortem, runbook | A handover for a rota or system |
| `onboarding_qa` | itops | answer | everything | Explaining the estate to a new engineer |
| `kb_gap` | itops | answer | kb, ticket, runbook | Finding missing KB articles and drafting one from ticket fixes |
| `policy_check` | itops | **fast** | standard, kb, runbook | "Am I allowed to…?" with the rule quoted |
| `notes_qa` | personal | answer | everything | Personal notes Q&A (for agents such as Nova) |
| `decision_recall` | personal | **fast** | everything | "What did I decide about X, and why?" |

The **fast** tier runs on `claude-haiku-5-5` (about 1/40th of Opus input pricing), for structured, short outputs. The
**answer** tier runs on `claude-opus-5-5` with `effort: medium`.

## Writing your own

```yaml
# my-prompts/vendor_compare.yaml
id: vendor_compare
version: 1
title: Compare vendor guidance
description: Compare what two vendors' docs say about the same setting.
tier: answer
top_k: 8
doc_types: [vendor, standard]
task: |
  Compare what the sources say about the setting in the question, vendor by vendor, and flag contradictions.
output: |
  A Markdown table: Vendor | Recommendation | Source [n]. Then "Contradictions:" bullets.
```

```bash
ITOPS_RAG_PROMPT_DIRS='["my-prompts"]' itops-rag prompts list
```

Validation is strict. Unknown keys, missing `task` and `{placeholders}` are all rejected, so a typo fails at
load time instead of silently changing behaviour. A template with the same id as a built-in one overrides it.
