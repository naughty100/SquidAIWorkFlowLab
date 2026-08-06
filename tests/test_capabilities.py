import pytest

from ai_workflow_lab.capabilities import (
    CapabilityReport,
    CapabilityResult,
    CapabilityStatus,
    StructuredOutputMethod,
    StructuredOutputResolutionError,
    resolve_structured_output_method,
)


def capability(status: CapabilityStatus) -> CapabilityResult:
    return CapabilityResult(status=status)


def report(
    *,
    json_schema: CapabilityStatus = CapabilityStatus.UNKNOWN,
    tool_calling: CapabilityStatus = CapabilityStatus.UNKNOWN,
    json_mode: CapabilityStatus = CapabilityStatus.UNKNOWN,
) -> CapabilityReport:
    return CapabilityReport(
        model="test-model",
        base_url_host="example.com",
        live=True,
        chat=capability(CapabilityStatus.SUPPORTED),
        streaming=capability(CapabilityStatus.SUPPORTED),
        tool_calling=capability(tool_calling),
        json_mode=capability(json_mode),
        json_schema=capability(json_schema),
    )


def test_auto_resolution_skips_unknown_and_uses_priority() -> None:
    result = resolve_structured_output_method(
        report(
            json_schema=CapabilityStatus.UNKNOWN,
            tool_calling=CapabilityStatus.SUPPORTED,
            json_mode=CapabilityStatus.SUPPORTED,
        )
    )

    assert result is StructuredOutputMethod.TOOL_CALLING


def test_explicit_unknown_method_is_rejected() -> None:
    with pytest.raises(StructuredOutputResolutionError, match="unknown"):
        resolve_structured_output_method(report(), "json_schema")


def test_no_supported_method_does_not_guess() -> None:
    with pytest.raises(StructuredOutputResolutionError, match="没有已确认支持"):
        resolve_structured_output_method(report())
