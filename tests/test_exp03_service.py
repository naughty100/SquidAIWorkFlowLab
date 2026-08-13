from pathlib import Path

import pytest

from ai_workflow_lab.config import LabSettings
from ai_workflow_lab.exp02.execution import Experiment02Mode
from ai_workflow_lab.exp03.agent import run_fixture_agent
from ai_workflow_lab.exp03.comparison import run_comparison
from ai_workflow_lab.exp03.domain import (
    AgentTermination,
    Experiment03Outcome,
    Experiment03Variant,
)
from ai_workflow_lab.exp03.service import experiment_control_hash, run_exp03
from ai_workflow_lab.run_recording import RunRecorder

PROJECT_ROOT = Path(__file__).parents[1]


def recorder(tmp_path: Path, run_id: str) -> tuple[LabSettings, RunRecorder]:
    settings = LabSettings(lab_output_dir=tmp_path / "outputs")
    return settings, RunRecorder(
        settings, command="test", project_root=tmp_path, run_id=run_id
    )


def test_fixed_and_agent_share_finalizer_and_controls(tmp_path: Path) -> None:
    outcomes: list[Experiment03Outcome] = []
    for variant in Experiment03Variant:
        settings, run = recorder(tmp_path, variant.value)
        outcomes.append(
            run_exp03(
                settings,
                run,
                case_id="career-ai-v1",
                mode=Experiment02Mode.FIXTURE,
                variant=variant,
                project_root=PROJECT_ROOT,
            )
        )

    assert all(item.status == "succeeded" for item in outcomes)
    assert all(item.proposal is not None for item in outcomes)
    assert outcomes[0].proposal.title == outcomes[1].proposal.title  # type: ignore[union-attr]
    assert outcomes[0].metrics.source_coverage == outcomes[1].metrics.source_coverage
    assert len(experiment_control_hash()) == 64


def test_three_run_report_never_claims_a_winner(tmp_path: Path) -> None:
    settings, parent = recorder(tmp_path, "comparison")

    report = run_comparison(
        settings,
        parent,
        case_id="career-ai-v1",
        mode=Experiment02Mode.FIXTURE,
        runs=3,
        project_root=PROJECT_ROOT,
    )

    assert report.smoke_comparison is True
    assert report.completed_pairs == 3
    assert report.case_version == "1.0.0"
    assert len(report.control_hash) == 64
    assert report.conclusion_status in {"insufficient_sample", "extension_required"}
    assert report.directional_conclusion is None


def test_terminated_agent_with_preserved_sources_is_partial_not_succeeded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def terminated_after_research(tracked: object) -> object:
        result = run_fixture_agent(tracked)  # type: ignore[arg-type]
        return result.model_copy(
            update={
                "termination": AgentTermination.MIDDLEWARE_LIMIT,
                "error": "controlled middleware stop",
            }
        )

    monkeypatch.setattr(
        "ai_workflow_lab.exp03.service.run_fixture_agent", terminated_after_research
    )
    settings, run = recorder(tmp_path, "partial-agent")

    outcome = run_exp03(
        settings,
        run,
        case_id="career-ai-v1",
        mode=Experiment02Mode.FIXTURE,
        variant=Experiment03Variant.AGENT,
        project_root=PROJECT_ROOT,
    )

    assert outcome.status == "partial"
    assert outcome.proposal is not None
    assert outcome.termination is AgentTermination.MIDDLEWARE_LIMIT
