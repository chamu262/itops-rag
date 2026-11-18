"""Price table, per-answer cost, and a JSONL ledger with a monthly budget cap.

Prices are USD per million tokens (first-party Claude API, November 2026). Cache reads bill at the listed read price
and cache writes (5-minute TTL) at 1.25x input. Update ``PRICES`` when list prices change; unknown models cost 0 and
log a warning instead of guessing.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from itops_rag.core.models import Usage

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Price:
    input: float
    output: float
    cache_read: float


PRICES: dict[str, Price] = {
    "claude-opus-5-5": Price(4.00, 20.00, 0.20),
    "claude-sonnet-5-5": Price(2.00, 10.00, 0.10),
    "claude-haiku-5-5": Price(0.10, 0.50, 0.01),
    "claude-fable-5-2": Price(8.00, 40.00, 0.20),
}


def cost_usd(
    model: str, input_tokens: int, output_tokens: int, cache_read: int = 0, cache_write: int = 0
) -> float:
    p = PRICES.get(model)
    if p is None:
        log.warning("no price for model %s; cost recorded as 0", model)
        return 0.0
    return (
        input_tokens * p.input
        + output_tokens * p.output
        + cache_read * p.cache_read
        + cache_write * p.input * 1.25
    ) / 1_000_000


class BudgetExceededError(RuntimeError):
    pass


class CostLedger:
    """Append-only JSONL of every model call. Small, greppable, and easy to ship to a log pipeline."""

    def __init__(self, path: Path, monthly_budget_usd: float) -> None:
        self.path = path
        self.budget = monthly_budget_usd

    def month_to_date(self, now: datetime | None = None) -> float:
        now = now or datetime.now(UTC)
        prefix = now.strftime("%Y-%m")
        total = 0.0
        if not self.path.exists():
            return 0.0
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(rec.get("ts", "")).startswith(prefix):
                total += float(rec.get("cost_usd", 0.0))
        return total

    def check(self) -> None:
        if self.budget > 0 and self.month_to_date() >= self.budget:
            raise BudgetExceededError(
                f"monthly budget of ${self.budget:.2f} reached; raise ITOPS_RAG_MONTHLY_BUDGET_USD or wait for next month"
            )

    def record(self, usage: Usage, purpose: str, prompt_id: str = "") -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        rec = {
            "ts": datetime.now(UTC).isoformat(timespec="seconds"),
            "purpose": purpose,
            "prompt_id": prompt_id,
            **asdict(usage),
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
