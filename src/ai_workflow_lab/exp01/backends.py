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
    """一次已成功完成传输的模型响应及可选的框架解析错误。"""

    payload: object
    parser_error: object | None = None


class StructuredBackend(Protocol):
    """统一三种实验路径的单次模型调用边界。"""

    def invoke(self, prompt: str) -> BackendResponse:
        """发送完整 Prompt，并在收到 Provider 响应后返回标准包装对象。"""
        ...


def _openai_client(settings: LabSettings) -> tuple[Any, str]:
    """按实验统一参数创建底层 OpenAI-compatible SDK 客户端。"""
    from openai import OpenAI

    settings.require_live_credentials()
    assert settings.ai_api_key is not None
    assert settings.ai_model is not None
    client: Any = OpenAI(
        api_key=settings.ai_api_key.get_secret_value(),
        base_url=settings.ai_base_url,
        timeout=settings.ai_timeout_seconds,
        # 实验协议要求传输重试最多两次 即使全局配置更大也要截断
        max_retries=min(settings.ai_max_retries, 2),
    )
    return client, settings.ai_model


class OpenAIPromptParseBackend:
    """通过普通 SDK 文本响应实现 Prompt 约束的结构化输出路径。"""

    def __init__(self, settings: LabSettings) -> None:
        """保存共享 SDK 客户端、模型名与输出 token 上限。"""
        self._client, self._model = _openai_client(settings)
        self._max_tokens = settings.ai_max_output_tokens

    def invoke(self, prompt: str) -> BackendResponse:
        """请求普通 Chat Completions，并将原始文本交给应用层提取 JSON。"""
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=self._max_tokens,
        )
        content = response.choices[0].message.content if response.choices else None
        return BackendResponse(payload=content or "")


class OpenAINativeBackend:
    """通过 SDK 的 JSON Schema、JSON Mode 或强制 Tool Calling 请求结构化响应。"""

    def __init__(self, settings: LabSettings, method: StructuredOutputMethod) -> None:
        """固定本次运行已解析的 native 机制和公共响应 Schema。"""
        self._client, self._model = _openai_client(settings)
        self._method = method
        self._max_tokens = settings.ai_max_output_tokens
        self._schema = TopicOptionsDraft.model_json_schema()

    def invoke(self, prompt: str) -> BackendResponse:
        """按固定机制调用 SDK，并统一返回文本或 Tool 参数中的业务对象。"""
        common: dict[str, object] = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self._max_tokens,
        }
        if self._method is StructuredOutputMethod.JSON_SCHEMA:
            # 服务端按完整 JSON Schema 约束输出 是最强的 native 路径
            common["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "topic_options",
                    "strict": True,
                    "schema": self._schema,
                },
            }
        elif self._method is StructuredOutputMethod.JSON_MODE:
            # JSON Mode 只保证 JSON 形态 字段约束仍由本地 Pydantic 负责
            common["response_format"] = {"type": "json_object"}
        else:
            # 强制指定函数 避免模型把 Tool Calling 当成可选行为
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
            # Tool Calling 的业务对象位于函数参数 而不是普通文本 content
            calls = message.tool_calls if message is not None else None
            arguments = calls[0].function.arguments if calls else ""
            return BackendResponse(payload=arguments)
        return BackendResponse(payload=message.content if message is not None else "")


class LangChainNativeBackend:
    """通过 LangChain 显式结构化 API 执行与 SDK native 等价的调用。"""

    def __init__(self, settings: LabSettings, method: StructuredOutputMethod) -> None:
        """构建已强制指定方法的 LangChain structured runnable。"""
        from langchain_openai import ChatOpenAI

        settings.require_live_credentials()
        assert settings.ai_api_key is not None
        assert settings.ai_model is not None
        model = ChatOpenAI(
            api_key=settings.ai_api_key,
            base_url=settings.ai_base_url,
            model=settings.ai_model,
            timeout=settings.ai_timeout_seconds,
            # 与 SDK variant 使用完全相同的传输重试上限。
            max_retries=min(settings.ai_max_retries, 2),
            max_completion_tokens=settings.ai_max_output_tokens,
        )
        langchain_method = to_langchain_method(method)
        model_with_structure: Any = model
        self._structured: Any = model_with_structure.with_structured_output(
            TopicOptionsDraft,
            # 必须传具体 method 不允许 LangChain 根据 Provider 自行猜测
            method=langchain_method,
            include_raw=True,
        )

    def invoke(self, prompt: str) -> BackendResponse:
        """执行 runnable，并保留 LangChain 原始响应以区分传输与解析失败。"""
        result: object = self._structured.invoke(prompt)
        if not isinstance(result, dict):
            return BackendResponse(payload=result)
        typed_result = cast(dict[str, object], result)
        return BackendResponse(
            # include_raw=True 让解析失败仍能区分“传输成功”与“Schema 失败”。
            payload=typed_result.get("parsed") or typed_result.get("raw"),
            parser_error=typed_result.get("parsing_error"),
        )


def to_langchain_method(
    method: StructuredOutputMethod,
) -> Literal["json_schema", "function_calling", "json_mode"]:
    """将项目机制名映射为 LangChain API 接受的具体 method 值。"""
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
        """消费下一项 mock 响应，用于模拟成功、格式错误和传输失败。"""
        del prompt
        # 最后一项会重复返回 便于用一个坏响应测试重试上限
        index = min(self.calls, len(self.responses) - 1)
        self.calls += 1
        value = self.responses[index]
        if isinstance(value, BaseException):
            raise value
        if isinstance(value, BackendResponse):
            return value
        return BackendResponse(payload=value)


def default_mock_payload() -> dict[str, object]:
    """返回满足三个选题契约的固定离线响应。"""
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
    """创建适配指定 variant 载荷形态的默认离线 Backend。"""
    payload = default_mock_payload()
    response = json.dumps(payload, ensure_ascii=False) if as_json_text else payload
    return SequenceMockBackend([response])


def as_mapping(value: BaseModel) -> dict[str, object]:
    """将 Pydantic 对象转换为 JSON 兼容字典。"""
    return cast(dict[str, object], value.model_dump(mode="json"))
