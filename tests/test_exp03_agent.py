from pathlib import Path
from typing import Any, cast

import pytest
from langchain.agents.middleware.tool_call_limit import (
    ToolCallLimitExceededError,
    ToolCallLimitMiddleware,
)

from ai_workflow_lab.config import LabSettings
from ai_workflow_lab.exp02.budget import ExecutionBudget
from ai_workflow_lab.exp02.tools import FixtureWebTools, load_fixture
from ai_workflow_lab.exp03.agent import (
    RepeatedToolCallError,
    TrackedAgentTools,
    canonical_tool_fingerprint,
    create_research_agent,
    invoke_agent,
    run_fixture_agent,
)
from ai_workflow_lab.exp03.domain import AgentTermination
from ai_workflow_lab.run_recording import RunRecorder


def make_tracked(
    tmp_path: Path, run_id: str, budget: ExecutionBudget | None = None
) -> TrackedAgentTools:
    settings = LabSettings(lab_output_dir=tmp_path / "outputs")
    recorder = RunRecorder(settings, command="test", project_root=tmp_path, run_id=run_id)
    fixture = load_fixture()
    return TrackedAgentTools(
        brief=fixture.brief,
        tools=FixtureWebTools(fixture, recorder.artifacts),
        budget=budget or ExecutionBudget(),
        recorder=recorder,
    )


def test_tool_fingerprint_is_order_independent() -> None:
    left = canonical_tool_fingerprint("search_web", {"query": "AI", "max_results": 3})
    right = canonical_tool_fingerprint("search_web", {"max_results": 3, "query": "AI"})

    assert left == right


def test_third_identical_tool_call_is_not_executed(tmp_path: Path) -> None:
    tracked = make_tracked(tmp_path, "repeat")

    tracked.search_web("career", 1)
    tracked.search_web("career", 1)
    with pytest.raises(RepeatedToolCallError, match="第三次"):
        tracked.search_web("career", 1)

    assert tracked.budget.search_calls == 2
    assert len(tracked.exchanges) == 2


def test_fixture_agent_preserves_partial_pack_when_budget_ends(tmp_path: Path) -> None:
    tracked = make_tracked(
        tmp_path,
        "partial",
        ExecutionBudget(max_tool_calls=1, max_search_calls=1, max_read_calls=0),
    )

    result = run_fixture_agent(tracked)

    assert result.termination.value == "budget_exhausted"
    assert result.pack.queries
    assert result.pack.sources == []


def test_agent_builder_explicitly_uses_tool_strategy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    def fake_create_agent(*args: object, **kwargs: object) -> str:
        captured.update(kwargs)
        return "agent"

    monkeypatch.setattr("langchain.agents.create_agent", fake_create_agent)
    tracked = make_tracked(tmp_path, "strategy")

    result = create_research_agent(LabSettings(), tracked, model=object())

    assert result == "agent"
    strategy = cast(Any, captured["response_format"])
    assert type(strategy).__name__ == "ToolStrategy"
    assert strategy.schema.__name__ == "ResearchPack"
    middleware = cast(list[object], captured["middleware"])
    assert len(middleware) == 4
    tool_limits = {
        (item.tool_name, item.run_limit)
        for item in middleware
        if isinstance(item, ToolCallLimitMiddleware)
    }
    assert tool_limits == {("search_web", 2), ("read_webpage", 4)}


def test_middleware_termination_keeps_previously_collected_evidence(tmp_path: Path) -> None:
    class EndedAgent:
        def invoke(self, payload: object) -> dict[str, object]:
            del payload
            return {"messages": []}

    tracked = make_tracked(tmp_path, "middleware")
    fixture = load_fixture()
    tracked.read_webpage(fixture.pages[0].url)

    result = invoke_agent(EndedAgent(), tracked)

    assert result.termination.value == "middleware_limit"
    assert len(result.pack.sources) == 1
    assert result.error is not None


def test_agent_pack_is_bound_to_actual_tool_evidence(tmp_path: Path) -> None:
    tracked = make_tracked(tmp_path, "bound-pack")
    fixture = load_fixture()
    tracked.read_webpage(fixture.pages[0].url)
    claimed = tracked.partial_pack().model_copy(deep=True)
    original_excerpt = claimed.sources[0].excerpt
    claimed.sources[0].excerpt = "模型试图替换的摘录"

    class StructuredAgent:
        def invoke(self, payload: object) -> dict[str, object]:
            del payload
            return {"structured_response": claimed}

    result = invoke_agent(StructuredAgent(), tracked)

    assert result.termination is AgentTermination.COMPLETED
    assert result.pack.sources[0].excerpt == original_excerpt


def test_agent_pack_rejects_source_not_returned_by_tools(tmp_path: Path) -> None:
    tracked = make_tracked(tmp_path, "invented-source")
    fixture = load_fixture()
    tracked.read_webpage(fixture.pages[0].url)
    claimed = tracked.partial_pack().model_copy(deep=True)
    claimed.sources[0].source_id = "src-aaaaaaaaaaaa"
    claimed.findings[0].source_ids = ["src-aaaaaaaaaaaa"]

    class StructuredAgent:
        def invoke(self, payload: object) -> dict[str, object]:
            del payload
            return {"structured_response": claimed}

    result = invoke_agent(StructuredAgent(), tracked)

    assert result.termination is AgentTermination.INVALID_RESPONSE
    assert result.error is not None
    assert "未由工具返回" in result.error
    assert result.pack.sources[0].source_id != "src-aaaaaaaaaaaa"


def test_tool_call_limit_exception_is_classified_as_middleware_limit(
    tmp_path: Path,
) -> None:
    class LimitedAgent:
        def invoke(self, payload: object) -> dict[str, object]:
            del payload
            raise ToolCallLimitExceededError(
                thread_count=7,
                run_count=7,
                thread_limit=None,
                run_limit=6,
            )

    result = invoke_agent(LimitedAgent(), make_tracked(tmp_path, "tool-limit"))

    assert result.termination is AgentTermination.MIDDLEWARE_LIMIT
    assert result.error is not None
    assert "ToolCallLimitExceededError" in result.error
