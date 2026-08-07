"""实验二的单调时钟执行预算。"""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

BudgetTool = Literal["search_web", "read_webpage"]


class BudgetExceeded(RuntimeError):
    """调用会突破 deadline 或分类配额。"""


@dataclass(slots=True)
class ExecutionBudget:
    """集中维护模型、工具和 deadline 的硬上限。"""

    max_model_calls: int = 5
    max_research_model_calls: int = 4
    max_tool_calls: int = 6
    max_search_calls: int = 2
    max_read_calls: int = 4
    duration_seconds: float = 120.0
    clock: Callable[[], float] = time.monotonic
    model_calls: int = 0
    research_model_calls: int = 0
    finalizer_calls: int = 0
    tool_calls: int = 0
    search_calls: int = 0
    read_calls: int = 0
    _deadline: float = field(init=False)

    def __post_init__(self) -> None:
        self._deadline = self.clock() + self.duration_seconds

    def _check_deadline(self) -> None:
        if self.clock() >= self._deadline:
            raise BudgetExceeded("execution deadline exceeded")

    def consume_model(self, *, finalizer: bool = False) -> None:
        """消费一次模型调用，并为 finalizer 强制保留最后一次配额。"""
        self._check_deadline()
        if self.model_calls >= self.max_model_calls:
            raise BudgetExceeded("model call budget exceeded")
        if finalizer:
            if self.finalizer_calls >= 1:
                raise BudgetExceeded("finalizer call budget exceeded")
            self.finalizer_calls += 1
        else:
            if self.research_model_calls >= self.max_research_model_calls:
                raise BudgetExceeded("research model budget exceeded; finalizer call is reserved")
            if self.model_calls >= self.max_model_calls - 1:
                raise BudgetExceeded("research model budget exceeded; finalizer call is reserved")
            self.research_model_calls += 1
        self.model_calls += 1

    def consume_tool(self, tool: BudgetTool) -> None:
        """消费一次工具调用并同时检查总量与分类上限。"""
        self._check_deadline()
        if self.tool_calls >= self.max_tool_calls:
            raise BudgetExceeded("tool call budget exceeded")
        if tool == "search_web" and self.search_calls >= self.max_search_calls:
            raise BudgetExceeded("search_web budget exceeded")
        if tool == "read_webpage" and self.read_calls >= self.max_read_calls:
            raise BudgetExceeded("read_webpage budget exceeded")
        self.tool_calls += 1
        if tool == "search_web":
            self.search_calls += 1
        else:
            self.read_calls += 1

    def snapshot(self) -> dict[str, int | float]:
        return {
            "model_calls": self.model_calls,
            "research_model_calls": self.research_model_calls,
            "finalizer_calls": self.finalizer_calls,
            "tool_calls": self.tool_calls,
            "search_calls": self.search_calls,
            "read_calls": self.read_calls,
            "remaining_seconds": max(0.0, self._deadline - self.clock()),
        }
