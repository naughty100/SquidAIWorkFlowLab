import os

import pytest

from ai_workflow_lab.config import LabSettings
from ai_workflow_lab.exp01.backends import OpenAIPromptParseBackend
from ai_workflow_lab.exp01.contracts import load_contract
from ai_workflow_lab.exp01.execution import ExperimentVariant, execute_variant


@pytest.mark.live
def test_live_prompt_parse_transport_and_schema_metrics_are_separate() -> None:
    if os.environ.get("RUN_LIVE_TESTS") != "1":
        pytest.skip("set RUN_LIVE_TESTS=1 to make a billable Provider request")
    settings = LabSettings()
    contract = load_contract("career-transition-v1")

    outcome = execute_variant(
        ExperimentVariant.PROMPT_PARSE,
        OpenAIPromptParseBackend(settings),
        contract.prompt,
        resolved_method=None,
    )

    assert outcome.metrics.transport_successes <= outcome.metrics.model_calls
    if outcome.metrics.transport_successes == 0:
        assert outcome.metrics.schema_validity_rate_among_successes is None
