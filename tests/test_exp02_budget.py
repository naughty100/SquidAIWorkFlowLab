from dataclasses import dataclass

import pytest

from ai_workflow_lab.exp02.budget import BudgetExceeded, ExecutionBudget


@dataclass
class FakeClock:
    now: float = 10.0

    def __call__(self) -> float:
        return self.now


def test_budget_tracks_model_and_tool_categories() -> None:
    clock = FakeClock()
    budget = ExecutionBudget(clock=clock)

    for _ in range(4):
        budget.consume_model(finalizer=False)
    with pytest.raises(BudgetExceeded, match="reserved"):
        budget.consume_model(finalizer=False)
    budget.consume_model(finalizer=True)

    for _ in range(2):
        budget.consume_tool("search_web")
    with pytest.raises(BudgetExceeded, match="search_web"):
        budget.consume_tool("search_web")
    for _ in range(4):
        budget.consume_tool("read_webpage")

    snapshot = budget.snapshot()
    assert snapshot["model_calls"] == 5
    assert snapshot["tool_calls"] == 6
    assert snapshot["finalizer_calls"] == 1


def test_deadline_rejects_every_call_without_consuming_counts() -> None:
    clock = FakeClock()
    budget = ExecutionBudget(duration_seconds=5, clock=clock)
    clock.now = 15

    with pytest.raises(BudgetExceeded, match="deadline"):
        budget.consume_model()
    with pytest.raises(BudgetExceeded, match="deadline"):
        budget.consume_tool("search_web")

    assert budget.model_calls == 0
    assert budget.tool_calls == 0
