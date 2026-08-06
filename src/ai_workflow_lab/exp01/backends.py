"""实验一的 SDK、LangChain 与离线 Mock 调用适配器。"""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal, Protocol, cast

from pydantic import BaseModel

from ai_workflow_lab.capabilities import StructuredOutputMethod
from ai_workflow_lab.config import LabSettings
from ai_workflow_lab.exp01.domain import TopicOptionsDraft


@dataclass(frozen=True, slots=True)
class BackendResponse:
    """一次已成功完成传输的模型响应。"""

    payload: object
    parser_error: object | None = None


class StructuredBackend(Protocol):
    def invoke(self, prompt: str) -> BackendResponse: ...


def _openai_client(settings: LabSettings) -> tuple[Any, str]:
    from openai import OpenAI

    settings.require_live_credentials()
    assert settings.ai_api_key is not None
    assert settings.ai_model is not None
    client: Any = OpenAI(
        api_key=settings.ai_api_key.get_secret_value(),
        base_url=settings.ai_base_url,
        timeout=settings.ai_timeout_seconds,
        max_retries=min(settings.ai_max_retries, 2),
    )
    return client, settings.ai_model


class OpenAIPromptParseBackend:
    def __init__(self, settings: LabSettings) -> None:
        self._client, self._model = _openai_client(settings)
        self._max_tokens = settings.ai_max_output_tokens

    def invoke(self, prompt: str) -> BackendResponse:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=self._max_tokens,
        )
        content = response.choices[0].message.content if response.choices else None
        return BackendResponse(payload=content or "")


class OpenAINativeBackend:
    def __init__(self, settings: LabSettings, method: StructuredOutputMethod) -> None:
        self._client, self._model = _openai_client(settings)
        self._method = method
        self._max_tokens = settings.ai_max_output_tokens
        self._schema = TopicOptionsDraft.model_json_schema()

    def invoke(self, prompt: str) -> BackendResponse:
        common: dict[str, object] = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self._max_tokens,
        }
        if self._method is StructuredOutputMethod.JSON_SCHEMA:
            common["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "topic_options",
                    "strict": True,
                    "schema": self._schema,
                },
            }
        elif self._method is StructuredOutputMethod.JSON_MODE:
            common["response_format"] = {"type": "json_object"}
        else:
            common["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": "return_topic_options",
                        "description": "返回三个内容选题。",
                        "parameters": self._schema,
                    },
                }
            ]
            common["tool_choice"] = {
                "type": "function",
                "function": {"name": "return_topic_options"},
            }

        response = self._client.chat.completions.create(**common)
        message = response.choices[0].message if response.choices else None
        if self._method is StructuredOutputMethod.TOOL_CALLING:
            calls = message.tool_calls if message is not None else None
            arguments = calls[0].function.arguments if calls else ""
            return BackendResponse(payload=arguments)
        return BackendResponse(payload=message.content if message is not None else "")


class LangChainNativeBackend:
    def __init__(self, settings: LabSettings, method: StructuredOutputMethod) -> None:
        from langchain_openai import ChatOpenAI

        settings.require_live_credentials()
        assert settings.ai_api_key is not None
        assert settings.ai_model is not None
        model = ChatOpenAI(
            api_key=settings.ai_api_key,
            base_url=settings.ai_base_url,
            model=settings.ai_model,
            timeout=settings.ai_timeout_seconds,
            max_retries=min(settings.ai_max_retries, 2),
            max_completion_tokens=settings.ai_max_output_tokens,
        )
        langchain_method = to_langchain_method(method)
        model_with_structure: Any = model
        self._structured: Any = model_with_structure.with_structured_output(
            TopicOptionsDraft,
            method=langchain_method,
            include_raw=True,
        )

    def invoke(self, prompt: str) -> BackendResponse:
        result: object = self._structured.invoke(prompt)
        if not isinstance(result, dict):
            return BackendResponse(payload=result)
        typed_result = cast(dict[str, object], result)
        return BackendResponse(
            payload=typed_result.get("parsed") or typed_result.get("raw"),
            parser_error=typed_result.get("parsing_error"),
        )


def to_langchain_method(
    method: StructuredOutputMethod,
) -> Literal["json_schema", "function_calling", "json_mode"]:
    """显式映射项目机制名，禁止把 `auto` 交给 LangChain。"""
    if method is StructuredOutputMethod.JSON_SCHEMA:
        return "json_schema"
    if method is StructuredOutputMethod.TOOL_CALLING:
        return "function_calling"
    return "json_mode"


@dataclass(slots=True)
class SequenceMockBackend:
    """按序返回值或抛出异常的离线 Backend。"""

    responses: Sequence[object]
    calls: int = 0

    def invoke(self, prompt: str) -> BackendResponse:
        del prompt
        index = min(self.calls, len(self.responses) - 1)
        self.calls += 1
        value = self.responses[index]
        if isinstance(value, BaseException):
            raise value
        if isinstance(value, BackendResponse):
            return value
        return BackendResponse(payload=value)


def default_mock_payload() -> dict[str, object]:
    return {
        "options": [
            {
                "title": "技术专家还是管理者：转型前先识别你的优势",
                "angle": "用真实工作偏好拆解两条常见路线",
                "target_audience": "考虑晋升或转岗的中高级程序员",
                "core_question": "怎样判断自己更适合继续深耕技术还是转向管理？",
                "reason": "决策具体，且能引出可操作的自我评估方法",
            },
            {
                "title": "从全职开发到独立职业：先验证最小收入闭环",
                "angle": "从副业验证、获客和交付能力讨论转型",
                "target_audience": "希望尝试自由职业或独立产品的程序员",
                "core_question": "辞职以前应验证哪些收入和客户信号？",
                "reason": "避开冲动辞职叙事，强调低风险实验",
            },
            {
                "title": "AI 时代的程序员转型：重构能力组合而非追逐岗位名",
                "angle": "把编码、业务理解和 AI 协作组合成新能力模型",
                "target_audience": "担心 AI 影响职业前景的开发者",
                "core_question": "哪些能力组合能让程序员在 AI 时代持续增值？",
                "reason": "回应现实焦虑，同时能形成清晰的学习路径",
            },
        ]
    }


def mock_backend(*, as_json_text: bool) -> SequenceMockBackend:
    payload = default_mock_payload()
    response = json.dumps(payload, ensure_ascii=False) if as_json_text else payload
    return SequenceMockBackend([response])


def as_mapping(value: BaseModel) -> dict[str, object]:
    return cast(dict[str, object], value.model_dump(mode="json"))
