import json

import pytest

from ai_workflow_lab.capabilities import StructuredOutputMethod
from ai_workflow_lab.exp01.backends import (
    SequenceMockBackend,
    default_mock_payload,
    to_langchain_method,
)
from ai_workflow_lab.exp01.execution import (
    ExperimentMetrics,
    ExperimentOutcome,
    ExperimentVariant,
    aggregate_metrics,
    execute_variant,
)


@pytest.mark.parametrize("variant", list(ExperimentVariant))
def test_all_variants_validate_the_same_contract(variant: ExperimentVariant) -> None:
    payload: object = default_mock_payload()
    if variant is ExperimentVariant.PROMPT_PARSE:
        payload = f"结果如下：\n```json\n{json.dumps(payload, ensure_ascii=False)}\n```"
    backend = SequenceMockBackend([payload])

    outcome = execute_variant(
        variant,
        backend,
        "prompt",
        resolved_method=StructuredOutputMethod.TOOL_CALLING,
    )

    assert outcome.status == "succeeded"
    assert outcome.resolved_method is StructuredOutputMethod.TOOL_CALLING
    assert outcome.result is not None
    assert len(outcome.result.options) == 3


def test_langchain_method_is_always_a_concrete_equivalent() -> None:
    assert to_langchain_method(StructuredOutputMethod.JSON_SCHEMA) == "json_schema"
    assert to_langchain_method(StructuredOutputMethod.TOOL_CALLING) == "function_calling"
    assert to_langchain_method(StructuredOutputMethod.JSON_MODE) == "json_mode"


def test_invalid_json_gets_only_one_schema_retry() -> None:
    valid = json.dumps(default_mock_payload(), ensure_ascii=False)
    backend = SequenceMockBackend(["not-json", valid])

    outcome = execute_variant(
        ExperimentVariant.PROMPT_PARSE,
        backend,
        "prompt",
        resolved_method=None,
    )

    assert outcome.status == "succeeded"
    assert backend.calls == 2
    assert outcome.metrics.transport_successes == 2
    assert outcome.metrics.schema_validity_rate_among_successes == 0.5
    assert outcome.errors[0]["category"] == "schema"


def test_missing_fields_stop_after_schema_retry_limit() -> None:
    backend = SequenceMockBackend([{"options": [{"title": "不完整"}]}])

    outcome = execute_variant(
        ExperimentVariant.SDK_NATIVE,
        backend,
        "prompt",
        resolved_method=StructuredOutputMethod.JSON_SCHEMA,
    )

    assert outcome.status == "failed"
    assert backend.calls == 2
    assert len(outcome.errors) == 2
    assert all(error["category"] == "schema" for error in outcome.errors)


def test_transport_failure_is_not_in_schema_denominator() -> None:
    failed = execute_variant(
        ExperimentVariant.PROMPT_PARSE,
        SequenceMockBackend([TimeoutError("timeout")]),
        "prompt",
        resolved_method=None,
    )
    succeeded = [
        execute_variant(
            ExperimentVariant.PROMPT_PARSE,
            SequenceMockBackend([json.dumps(default_mock_payload(), ensure_ascii=False)]),
            "prompt",
            resolved_method=None,
        )
        for _ in range(4)
    ]

    metrics = aggregate_metrics([failed, *succeeded])

    assert metrics.transport_success_rate == 4 / 5
    assert metrics.schema_validity_rate_among_successes == 1.0


def test_unsupported_outcome_has_no_model_calls() -> None:
    outcome = ExperimentOutcome(
        status="unsupported",
        variant=ExperimentVariant.SDK_NATIVE,
        metrics=ExperimentMetrics(),
    )

    assert outcome.metrics.model_calls == 0
