"""实验一的能力报告发现与冻结机制。"""

from pathlib import Path

from ai_workflow_lab.capabilities import (
    CapabilityReport,
    StructuredOutputMethod,
    StructuredOutputResolutionError,
    resolve_structured_output_method,
)
from ai_workflow_lab.config import LabSettings


def find_latest_capability_report(
    settings: LabSettings,
    *,
    project_root: Path | None = None,
) -> CapabilityReport:
    root = (project_root or Path.cwd()).resolve()
    output_root = settings.lab_output_dir
    if not output_root.is_absolute():
        output_root = root / output_root
    candidates = sorted(
        (output_root / "commands").glob("*/capabilities.json"),
        key=lambda path: path.stat().st_mtime_ns,
        reverse=True,
    )
    for path in candidates:
        try:
            report = CapabilityReport.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if (
            report.live
            and report.model == settings.ai_model
            and report.base_url_host == settings.base_url_host
        ):
            return report
    raise StructuredOutputResolutionError(
        "未找到当前模型与 Provider 的 live 能力报告；请先运行 lab doctor --live"
    )


def freeze_native_method(
    settings: LabSettings,
    *,
    project_root: Path | None = None,
) -> StructuredOutputMethod:
    """在模型调用前解析一次具体机制，后续运行不得自动切换。"""
    report = find_latest_capability_report(settings, project_root=project_root)
    return resolve_structured_output_method(report, settings.ai_structured_output_method)
