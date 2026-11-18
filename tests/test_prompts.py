from pathlib import Path

import pytest

from itops_rag.prompts.registry import PromptRegistry

EXPECTED_ITOPS = {
    "troubleshoot",
    "runbook_steps",
    "ticket_triage",
    "suggested_reply",
    "similar_tickets",
    "incident_summary",
    "change_risk_review",
    "postmortem_lessons",
    "oncall_handover",
    "onboarding_qa",
    "kb_gap",
    "policy_check",
}


def test_all_packs_load() -> None:
    reg = PromptRegistry.default()
    ids = {p.id for p in reg.list()}
    assert ids >= EXPECTED_ITOPS
    assert {"qa", "notes_qa", "decision_recall"} <= ids


def test_pack_selection() -> None:
    reg = PromptRegistry.default(packs=["base", "personal"])
    assert "qa" in reg and "notes_qa" in reg and "troubleshoot" not in reg


def test_render_puts_task_after_context() -> None:
    p = PromptRegistry.default().get("change_risk_review")
    out = p.render("Review this", "<context>\n</context>", input_text="Rotate the cert on Thursday")
    assert out.index("<context>") < out.index("<question>") < out.index("<change_plan>") < out.index("<task>")


def test_user_prompt_dirs_override(tmp_path: Path) -> None:
    (tmp_path / "qa.yaml").write_text("id: qa\ntitle: Mine\ndescription: d\ntask: t\n")
    reg = PromptRegistry.default([tmp_path])
    assert reg.get("qa").title == "Mine"


@pytest.mark.parametrize(
    "bad",
    [
        "id: x\ntitle: t\ndescription: d\n",
        "id: x\ntitle: t\ndescription: d\ntask: use {question}\n",
        "id: x\ntitle: t\ndescription: d\ntask: t\nsurprise: 1\n",
    ],
)
def test_bad_templates_are_rejected(tmp_path: Path, bad: str) -> None:
    (tmp_path / "x.yaml").write_text(bad)
    with pytest.raises(ValueError):
        PromptRegistry().load_dir(tmp_path)


def test_unknown_prompt_lists_available() -> None:
    with pytest.raises(KeyError, match="troubleshoot"):
        PromptRegistry.default().get("nope")
