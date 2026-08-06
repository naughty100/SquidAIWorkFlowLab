"""本地环境检查与显式 live Provider 能力探测。"""

import importlib.util
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, Protocol, cast

from pydantic import BaseModel, ConfigDict, Field

from ai_workflow_lab.capabilities import (
    CapabilityReport,
    CapabilityResult,
    CapabilityStatus,
    unknown_capability,
)
from ai_workflow_lab.config import ConfigurationError, LabSettings
from ai_workflow_lab.security import sanitize


class LocalCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    ok: bool
    detail: str


class DoctorReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    run_id: str | None = None
    mode: str
    checks: list[LocalCheck]
    capabilities: CapabilityReport
    warnings: list[str] = Field(default_factory=list)


class LiveProbeBackend(Protocol):
    """隔离 OpenAI SDK，便于完全离线测试。"""

    def probe_chat(self) -> bool: ...

    def probe_streaming(self) -> bool: ...

    def probe_tool_calling(self) -> bool: ...

    def probe_json_mode(self) -> bool: ...

    def probe_json_schema(self) -> bool: ...


class OpenAIProbeBackend:
    """使用 OpenAI Chat Completions 兼容接口执行最小能力探测。"""

    def __init__(self, settings: LabSettings) -> None:
        from openai import OpenAI

        settings.require_live_credentials()
        assert settings.ai_api_key is not None
        assert settings.ai_model is not None
        self._model = settings.ai_model
        self._client: Any = OpenAI(
            api_key=settings.ai_api_key.get_secret_value(),
            base_url=settings.ai_base_url,
            timeout=settings.ai_timeout_seconds,
            max_retries=settings.ai_max_retries,
        )

    def probe_chat(self) -> bool:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": "Reply with exactly: pong"}],
            max_tokens=8,
        )
        return bool(response.choices and response.choices[0].message.content)

    def probe_streaming(self) -> bool:
        stream: Iterator[Any] = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": "Reply with exactly: pong"}],
            max_tokens=8,
            stream=True,
        )
        return any(True for _chunk in stream)

    def probe_tool_calling(self) -> bool:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": "Call capability_probe with value pong."}],
            max_tokens=32,
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "capability_probe",
                        "description": "Return the requested probe value.",
                        "parameters": {
                            "type": "object",
                            "properties": {"value": {"type": "string"}},
                            "required": ["value"],
                            "additionalProperties": False,
                        },
                    },
                }
            ],
            tool_choice={"type": "function", "function": {"name": "capability_probe"}},
        )
        return bool(response.choices and response.choices[0].message.tool_calls)

    def probe_json_mode(self) -> bool:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": 'Return JSON only: {"value":"pong"}'}],
            max_tokens=32,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content if response.choices else None
        return bool(content and '"value"' in content)

    def probe_json_schema(self) -> bool:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": "Return the value pong."}],
            max_tokens=32,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "capability_probe",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {"value": {"type": "string"}},
                        "required": ["value"],
                        "additionalProperties": False,
                    },
                },
            },
        )
        content = response.choices[0].message.content if response.choices else None
        return bool(content and '"value"' in content)


ProbeFactory = Callable[[LabSettings], LiveProbeBackend]


def _probe_feature(
    probe: Callable[[], bool],
    *,
    chat_supported: bool,
    secrets: tuple[str, ...],
) -> CapabilityResult:
    try:
        if probe():
            return CapabilityResult(status=CapabilityStatus.SUPPORTED)
        return unknown_capability("inconclusive_response")
    except Exception as exc:  # noqa: BLE001 - Provider SDK exceptions are intentionally normalized.
        status_code = getattr(exc, "status_code", None)
        if chat_supported and status_code in {400, 422}:
            status = CapabilityStatus.UNSUPPORTED
            reason = "feature_rejected"
        else:
            status = CapabilityStatus.UNKNOWN
            reason = "transport_or_auth_error"
        error = sanitize(exc, secrets=secrets)
        assert isinstance(error, dict)
        return CapabilityResult(
            status=status,
            reason=reason,
            error=cast(dict[str, object], error),
        )


def offline_capability_report(settings: LabSettings) -> CapabilityReport:
    skipped = unknown_capability("live_probe_not_requested")
    return CapabilityReport(
        model=settings.ai_model,
        base_url_host=settings.base_url_host,
        live=False,
        chat=skipped.model_copy(deep=True),
        streaming=skipped.model_copy(deep=True),
        tool_calling=skipped.model_copy(deep=True),
        json_mode=skipped.model_copy(deep=True),
        json_schema=skipped.model_copy(deep=True),
    )


def unknown_live_capability_report(
    settings: LabSettings,
    *,
    reason: str,
    error: dict[str, object] | None = None,
) -> CapabilityReport:
    """表示用户请求了 live，但尚未获得任何可靠能力结论。"""
    chat = CapabilityResult(status=CapabilityStatus.UNKNOWN, reason=reason, error=error)
    blocked = unknown_capability("chat_unavailable")
    return CapabilityReport(
        model=settings.ai_model,
        base_url_host=settings.base_url_host,
        live=True,
        chat=chat,
        streaming=blocked.model_copy(deep=True),
        tool_calling=blocked.model_copy(deep=True),
        json_mode=blocked.model_copy(deep=True),
        json_schema=blocked.model_copy(deep=True),
    )


def live_capability_report(
    settings: LabSettings,
    *,
    backend_factory: ProbeFactory = OpenAIProbeBackend,
) -> CapabilityReport:
    settings.require_live_credentials()
    backend = backend_factory(settings)
    chat = _probe_feature(
        backend.probe_chat,
        chat_supported=False,
        secrets=settings.secret_values,
    )
    chat_supported = chat.status is CapabilityStatus.SUPPORTED

    if not chat_supported:
        blocked = unknown_capability("chat_unavailable")
        return CapabilityReport(
            model=settings.ai_model,
            base_url_host=settings.base_url_host,
            live=True,
            chat=chat,
            streaming=blocked.model_copy(deep=True),
            tool_calling=blocked.model_copy(deep=True),
            json_mode=blocked.model_copy(deep=True),
            json_schema=blocked.model_copy(deep=True),
        )

    return CapabilityReport(
        model=settings.ai_model,
        base_url_host=settings.base_url_host,
        live=True,
        chat=chat,
        streaming=_probe_feature(
            backend.probe_streaming,
            chat_supported=True,
            secrets=settings.secret_values,
        ),
        tool_calling=_probe_feature(
            backend.probe_tool_calling,
            chat_supported=True,
            secrets=settings.secret_values,
        ),
        json_mode=_probe_feature(
            backend.probe_json_mode,
            chat_supported=True,
            secrets=settings.secret_values,
        ),
        json_schema=_probe_feature(
            backend.probe_json_schema,
            chat_supported=True,
            secrets=settings.secret_values,
        ),
    )


def local_checks(settings: LabSettings, *, project_root: Path | None = None) -> list[LocalCheck]:
    root = project_root or Path.cwd()
    checks = [
        LocalCheck(
            name="python",
            ok=sys.version_info[:2] == (3, 12),
            detail=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        ),
        LocalCheck(
            name="lockfile",
            ok=(root / "uv.lock").is_file(),
            detail="uv.lock" if (root / "uv.lock").is_file() else "uv.lock 不存在",
        ),
    ]
    for module in ("openai", "langchain_openai", "pydantic", "typer"):
        checks.append(
            LocalCheck(
                name=f"dependency:{module}",
                ok=importlib.util.find_spec(module) is not None,
                detail="available" if importlib.util.find_spec(module) is not None else "missing",
            )
        )
    for name, directory in (
        ("output_dir", settings.lab_output_dir),
        ("runtime_dir", settings.lab_runtime_dir),
        ("cache_dir", settings.lab_cache_dir),
    ):
        resolved = directory if directory.is_absolute() else root / directory
        checks.append(LocalCheck(name=name, ok=resolved.is_dir(), detail=str(resolved)))
    return checks


def run_doctor(
    settings: LabSettings,
    *,
    live: bool,
    project_root: Path | None = None,
    backend_factory: ProbeFactory = OpenAIProbeBackend,
) -> DoctorReport:
    checks = local_checks(settings, project_root=project_root)
    warnings: list[str] = []
    capabilities = offline_capability_report(settings)

    if live:
        capabilities = unknown_live_capability_report(
            settings,
            reason="live_probe_initializing",
        )
        try:
            capabilities = live_capability_report(settings, backend_factory=backend_factory)
            checks.append(
                LocalCheck(
                    name="live_probe",
                    ok=capabilities.chat.status is CapabilityStatus.SUPPORTED,
                    detail=capabilities.chat.status.value,
                )
            )
        except ConfigurationError as exc:
            checks.append(LocalCheck(name="live_config", ok=False, detail=str(exc)))
            capabilities = unknown_live_capability_report(
                settings,
                reason="live_configuration_invalid",
            )
        except Exception as exc:  # noqa: BLE001 - Factory failures become an unknown probe.
            error = sanitize(exc, secrets=settings.secret_values)
            warnings.append(f"无法创建 live probe backend：{error}")
            checks.append(LocalCheck(name="live_probe", ok=False, detail="backend_error"))
            assert isinstance(error, dict)
            capabilities = unknown_live_capability_report(
                settings,
                reason="backend_error",
                error=cast(dict[str, object], error),
            )

    return DoctorReport(
        ok=all(check.ok for check in checks),
        mode="live" if live else "offline",
        checks=checks,
        capabilities=capabilities,
        warnings=warnings,
    )
