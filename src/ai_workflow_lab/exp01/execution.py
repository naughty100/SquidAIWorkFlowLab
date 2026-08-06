"""结构化输出实验的统一执行、校验与指标。"""

import json
from enum import StrEnum
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ai_workflow_lab.capabilities import StructuredOutputMethod
from ai_workflow_lab.exp01.backends import BackendResponse, StructuredBackend
from ai_workflow_lab.exp01.domain import (
    TopicOptions,
    TopicOptionsDraft,
    finalize_topic_options,
)
from ai_workflow_lab.security import sanitize


class ExperimentVariant(StrEnum):
    PROMPT_PARSE = "prompt-parse"
    SDK_NATIVE = "sdk-native"
    LANGCHAIN_NATIVE = "langchain-native"


class ExperimentMode(StrEnum):
    MOCK = "mock"
    LIVE = "live"


class ExperimentMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_calls: int = 0
    transport_successes: int = 0
    schema_valid_responses: int = 0
    transport_success_rate: float = 0.0
    schema_validity_rate_among_successes: float | None = None


class ExperimentOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    variant: ExperimentVariant
    resolved_method: StructuredOutputMethod | None = None
    result: TopicOptions | None = None
    metrics: ExperimentMetrics
    errors: list[dict[str, object]] = Field(default_factory=lambda: list[dict[str, object]]())


def extract_json_object(text: str) -> object:
    """从普通文本或 Markdown fence 中提取第一个可解码 JSON 对象。"""
    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, _end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return cast(dict[str, object], value)
    raise ValueError("响应中不存在合法 JSON 对象")


def _validate_response(response: BackendResponse, *, parse_text: bool) -> TopicOptionsDraft:
    if response.parser_error is not None:
        raise ValueError(f"LangChain 结构化解析失败：{response.parser_error}")
    payload: Any = response.payload
    if isinstance(payload, TopicOptionsDraft):
        return payload
    if isinstance(payload, BaseModel):
        payload = payload.model_dump(mode="json")
    if isinstance(payload, str):
        payload = extract_json_object(payload) if parse_text else json.loads(payload)
    return TopicOptionsDraft.model_validate(payload)


def _metrics(calls: int, transports: int, schema_valid: int) -> ExperimentMetrics:
    return ExperimentMetrics(
        model_calls=calls,
        transport_successes=transports,
        schema_valid_responses=schema_valid,
        transport_success_rate=transports / calls if calls else 0.0,
        schema_validity_rate_among_successes=(schema_valid / transports if transports else None),
    )


def aggregate_metrics(outcomes: list[ExperimentOutcome]) -> ExperimentMetrics:
    """跨多次运行聚合指标，传输失败不会进入 Schema 分母。"""
    calls = sum(outcome.metrics.model_calls for outcome in outcomes)
    transports = sum(outcome.metrics.transport_successes for outcome in outcomes)
    schema_valid = sum(outcome.metrics.schema_valid_responses for outcome in outcomes)
    return _metrics(calls, transports, schema_valid)


def execute_variant(
    variant: ExperimentVariant,
    backend: StructuredBackend,
    prompt: str,
    *,
    resolved_method: StructuredOutputMethod | None,
    schema_retries: int = 1,
) -> ExperimentOutcome:
    """执行初次生成及最多一次 Schema 修复请求。"""
    calls = 0
    transports = 0
    errors: list[dict[str, object]] = []
    current_prompt = prompt
    for schema_attempt in range(schema_retries + 1):
        calls += 1
        try:
            response = backend.invoke(current_prompt)
        except Exception as exc:  # noqa: BLE001 - Provider transports are normalized.
            error = sanitize(exc)
            assert isinstance(error, dict)
            errors.append({"category": "transport", **cast(dict[str, object], error)})
            return ExperimentOutcome(
                status="failed",
                variant=variant,
                resolved_method=resolved_method,
                metrics=_metrics(calls, transports, 0),
                errors=errors,
            )

        transports += 1
        try:
            draft = _validate_response(
                response,
                parse_text=variant is ExperimentVariant.PROMPT_PARSE,
            )
        except (json.JSONDecodeError, ValidationError, ValueError, TypeError) as exc:
            error = sanitize(exc)
            assert isinstance(error, dict)
            errors.append({"category": "schema", **cast(dict[str, object], error)})
            if schema_attempt < schema_retries:
                current_prompt = (
                    f"{prompt}\n\n上一次响应未通过 Schema 校验：{exc}\n"
                    "请修正全部错误，只返回完整 JSON。"
                )
                continue
            return ExperimentOutcome(
                status="failed",
                variant=variant,
                resolved_method=resolved_method,
                metrics=_metrics(calls, transports, 0),
                errors=errors,
            )

        return ExperimentOutcome(
            status="succeeded",
            variant=variant,
            resolved_method=resolved_method,
            result=finalize_topic_options(draft),
            metrics=_metrics(calls, transports, 1),
            errors=errors,
        )

    raise AssertionError("unreachable")


def unsupported_outcome(
    variant: ExperimentVariant,
    reason: str,
) -> ExperimentOutcome:
    return ExperimentOutcome(
        status="unsupported",
        variant=variant,
        metrics=ExperimentMetrics(),
        errors=[{"category": "capability", "type": "unsupported", "message": reason}],
    )
