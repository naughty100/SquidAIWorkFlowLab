import os
from pathlib import Path

import pytest

from ai_workflow_lab.capabilities import CapabilityStatus
from ai_workflow_lab.exp01.capability import find_latest_capability_report
from ai_workflow_lab.exp02.execution import Experiment02Mode
from ai_workflow_lab.exp03.comparison import run_comparison
from ai_workflow_lab.exp03.domain import Experiment03Comparison
from ai_workflow_lab.live_validation import load_live_validation_settings
from ai_workflow_lab.run_recording import RunRecorder

PROJECT_ROOT = Path(__file__).parents[1]


def _execute_live_comparison(runs: int) -> Experiment03Comparison:
    settings = load_live_validation_settings()
    recorder = RunRecorder(
        settings,
        command=f"pytest live exp03 comparison --runs {runs}",
        project_root=PROJECT_ROOT,
    )
    try:
        report = run_comparison(
            settings,
            recorder,
            case_id="career-ai-v1",
            mode=Experiment02Mode.LIVE,
            runs=runs,
            project_root=PROJECT_ROOT,
        )
    except Exception as exc:
        recorder.finish("failed", details=exc)
        raise
    recorder.finish("succeeded")
    return report


@pytest.mark.live
@pytest.mark.skipif(
    os.getenv("RUN_LIVE_TESTS") != "1",
    reason="set RUN_LIVE_TESTS=1 to run billable exp03 comparisons",
)
def test_live_agent_smoke_and_required_extension_are_persisted() -> None:
    settings = load_live_validation_settings()
    settings.require_live_credentials()
    settings.require_tavily_credentials()
    capability = find_latest_capability_report(settings, project_root=PROJECT_ROOT)
    assert capability.tool_calling.status is CapabilityStatus.SUPPORTED

    smoke = _execute_live_comparison(3)

    assert smoke.mode == "live"
    assert smoke.smoke_comparison is True
    assert smoke.completed_pairs == 3
    assert smoke.fixed.success_rate > 0
    assert smoke.agent.success_rate > 0
    assert smoke.conclusion_status != "directional"

    if smoke.extension_triggered:
        expanded = _execute_live_comparison(10)
        assert expanded.completed_pairs == 10
        assert expanded.conclusion_status == "directional"
        assert expanded.directional_conclusion is not None
