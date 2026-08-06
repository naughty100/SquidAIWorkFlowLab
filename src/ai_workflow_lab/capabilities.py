"""Provider 能力模型及结构化机制解析。"""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class CapabilityStatus(StrEnum):
    """能力探测的三态结果。"""

    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


class StructuredOutputMethod(StrEnum):
    """允许显式交给 SDK/LangChain 的结构化机制。"""

    JSON_SCHEMA = "json_schema"
    TOOL_CALLING = "tool_calling"
    JSON_MODE = "json_mode"


class CapabilityResult(BaseModel):
    """单项能力结果。"""

    model_config = ConfigDict(extra="forbid")

    status: CapabilityStatus
    reason: str | None = None
    error: dict[str, object] | None = None


def unknown_capability(reason: str) -> CapabilityResult:
    return CapabilityResult(status=CapabilityStatus.UNKNOWN, reason=reason)


class CapabilityReport(BaseModel):
    """一次 Provider 能力探测报告。"""

    model_config = ConfigDict(extra="forbid")

    model: str | None
    base_url_host: str
    probed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    live: bool
    chat: CapabilityResult
    streaming: CapabilityResult
    tool_calling: CapabilityResult
    json_mode: CapabilityResult
    json_schema: CapabilityResult

    def for_method(self, method: StructuredOutputMethod) -> CapabilityResult:
        return {
            StructuredOutputMethod.JSON_SCHEMA: self.json_schema,
            StructuredOutputMethod.TOOL_CALLING: self.tool_calling,
            StructuredOutputMethod.JSON_MODE: self.json_mode,
        }[method]


class StructuredOutputResolutionError(ValueError):
    """请求的结构化机制无法安全解析。"""


_METHOD_PRIORITY = (
    StructuredOutputMethod.JSON_SCHEMA,
    StructuredOutputMethod.TOOL_CALLING,
    StructuredOutputMethod.JSON_MODE,
)


def resolve_structured_output_method(
    report: CapabilityReport,
    requested: str = "auto",
) -> StructuredOutputMethod:
    """只从明确 supported 的能力中解析一个具体机制。"""
    normalized = requested.strip().casefold()
    if normalized == "auto":
        for method in _METHOD_PRIORITY:
            if report.for_method(method).status is CapabilityStatus.SUPPORTED:
                return method
        raise StructuredOutputResolutionError("没有已确认支持的结构化输出机制")

    try:
        method = StructuredOutputMethod(normalized)
    except ValueError as exc:
        allowed = ", ".join(method.value for method in _METHOD_PRIORITY)
        raise StructuredOutputResolutionError(
            f"未知结构化输出机制：{requested}；可选值：auto, {allowed}"
        ) from exc

    result = report.for_method(method)
    if result.status is not CapabilityStatus.SUPPORTED:
        raise StructuredOutputResolutionError(
            f"结构化输出机制 {method.value} 当前状态为 {result.status.value}"
        )
    return method
