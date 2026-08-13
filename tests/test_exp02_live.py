import os
from pathlib import Path

import pytest

from ai_workflow_lab.exp02.execution import Experiment02Mode, Experiment02Variant
from ai_workflow_lab.exp02.service import Experiment02Outcome, run_exp02
from ai_workflow_lab.live_validation import load_live_validation_settings
from ai_workflow_lab.run_recording import RunRecorder


@pytest.mark.live
def test_live_fixed_and_tool_call_use_the_same_case() -> None:
    """显式启用后执行会产生模型与 Tavily 费用的真实对照。"""
    if os.environ.get("RUN_LIVE_TESTS") != "1":
        pytest.skip("set RUN_LIVE_TESTS=1 to make billable Provider and Tavily requests")
    settings = load_live_validation_settings()
    outcomes: list[Experiment02Outcome] = []
    for variant in Experiment02Variant:
        recorder = RunRecorder(settings, command=f"live-test-exp02-{variant.value}")
        outcome = run_exp02(
            settings,
            recorder,
            case_id="career-ai-v1",
            mode=Experiment02Mode.LIVE,
            variant=variant,
            project_root=Path(__file__).parents[1],
        )
        recorder.finish("succeeded")
        outcomes.append(outcome)

    assert all(outcome.status == "succeeded" for outcome in outcomes)
    assert all(outcome.research_pack is not None for outcome in outcomes)
    assert all(outcome.proposal is not None for outcome in outcomes)
