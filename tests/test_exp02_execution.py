from collections.abc import Sequence
from pathlib import Path

from ai_workflow_lab.config import LabSettings
from ai_workflow_lab.exp02.budget import ExecutionBudget
from ai_workflow_lab.exp02.execution import (
    ResearchModel,
    ResearchTurn,
    ToolCall,
    execute_tool_batch,
    run_controlled_research,
)
from ai_workflow_lab.exp02.tools import FixtureWebTools, load_fixture
from ai_workflow_lab.run_recording import RunRecorder


class SequenceResearchModel(ResearchModel):
    def __init__(self, turns: Sequence[ResearchTurn]) -> None:
        self.turns = list(turns)
        self.calls = 0

    def invoke(self, messages: Sequence[dict[str, object]]) -> ResearchTurn:
        del messages
        turn = self.turns[min(self.calls, len(self.turns) - 1)]
        self.calls += 1
        return turn


def make_recorder(tmp_path: Path, run_id: str) -> RunRecorder:
    settings = LabSettings(lab_output_dir=tmp_path / "outputs")
    return RunRecorder(settings, command="test", project_root=tmp_path, run_id=run_id)


def test_controlled_loop_searches_reads_and_stops_early(tmp_path: Path) -> None:
    fixture = load_fixture()
    recorder = make_recorder(tmp_path, "early-stop")
    tools = FixtureWebTools(fixture, recorder.artifacts)
    model = SequenceResearchModel(
        [
            ResearchTurn(
                tool_calls=[
                    ToolCall(
                        call_id="search-1",
                        name="search_web",
                        arguments={"query": "career", "max_results": 1},
                    )
                ]
            ),
            ResearchTurn(
                tool_calls=[
                    ToolCall(
                        call_id="read-1",
                        name="read_webpage",
                        arguments={"url": fixture.pages[0].url},
                    )
                ]
            ),
            ResearchTurn(content="done"),
        ]
    )
    budget = ExecutionBudget()

    pack = run_controlled_research(
        fixture.brief,
        model=model,
        tools=tools,
        budget=budget,
        recorder=recorder,
    )

    assert model.calls == 3
    assert budget.research_model_calls == 3
    assert [source.url for source in pack.sources] == [fixture.pages[0].url]


def test_controlled_loop_stops_after_three_rounds(tmp_path: Path) -> None:
    fixture = load_fixture()
    recorder = make_recorder(tmp_path, "round-limit")
    model = SequenceResearchModel(
        [
            ResearchTurn(
                tool_calls=[
                    ToolCall(
                        call_id=f"search-{index}",
                        name="search_web",
                        arguments={"query": "career", "max_results": 1},
                    )
                ]
            )
            for index in range(1, 4)
        ]
    )
    budget = ExecutionBudget()

    run_controlled_research(
        fixture.brief,
        model=model,
        tools=FixtureWebTools(fixture, recorder.artifacts),
        budget=budget,
        recorder=recorder,
    )

    assert model.calls == 3
    assert budget.research_model_calls == 3


def test_multi_call_batch_preserves_order_and_continues_after_failure(tmp_path: Path) -> None:
    fixture = load_fixture()
    recorder = make_recorder(tmp_path, "batch-order")
    calls = [
        ToolCall(
            call_id="read-1",
            name="read_webpage",
            arguments={"url": fixture.pages[0].url},
        ),
        ToolCall(
            call_id="read-2",
            name="read_webpage",
            arguments={"url": "https://fixture.example/missing"},
        ),
        ToolCall(
            call_id="read-3",
            name="read_webpage",
            arguments={"url": fixture.pages[2].url},
        ),
    ]

    exchanges = execute_tool_batch(
        calls,
        tools=FixtureWebTools(fixture, recorder.artifacts),
        budget=ExecutionBudget(),
        recorder=recorder,
    )

    assert [exchange.call.call_id for exchange in exchanges] == ["read-1", "read-2", "read-3"]
    assert exchanges[0].result.error is None
    assert exchanges[1].result.error is not None
    assert exchanges[2].result.error is None


def test_budget_rejection_returns_message_for_every_remaining_call(tmp_path: Path) -> None:
    fixture = load_fixture()
    recorder = make_recorder(tmp_path, "batch-budget")
    calls = [
        ToolCall(
            call_id=f"search-{index}",
            name="search_web",
            arguments={"query": "career", "max_results": 1},
        )
        for index in range(1, 4)
    ]
    budget = ExecutionBudget(max_tool_calls=1, max_search_calls=1)

    exchanges = execute_tool_batch(
        calls,
        tools=FixtureWebTools(fixture, recorder.artifacts),
        budget=budget,
        recorder=recorder,
    )

    assert len(exchanges) == 3
    assert exchanges[0].result.error is None
    assert [exchange.result.error.code for exchange in exchanges[1:] if exchange.result.error] == [
        "budget_exceeded",
        "budget_exceeded",
    ]
