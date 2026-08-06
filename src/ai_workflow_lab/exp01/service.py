"""实验一用例编排与运行产物保存。"""

from collections.abc import Callable
from pathlib import Path

from ai_workflow_lab.capabilities import (
    StructuredOutputMethod,
    StructuredOutputResolutionError,
)
from ai_workflow_lab.config import LabSettings
from ai_workflow_lab.exp01.backends import (
    LangChainNativeBackend,
    OpenAINativeBackend,
    OpenAIPromptParseBackend,
    StructuredBackend,
    mock_backend,
)
from ai_workflow_lab.exp01.capability import freeze_native_method
from ai_workflow_lab.exp01.contracts import ContractBundle, load_contract
from ai_workflow_lab.exp01.execution import (
    ExperimentMode,
    ExperimentOutcome,
    ExperimentVariant,
    execute_variant,
    unsupported_outcome,
)
from ai_workflow_lab.run_recording import RunRecorder

BackendFactory = Callable[
    [LabSettings, ExperimentMode, ExperimentVariant, StructuredOutputMethod | None],
    StructuredBackend,
]


def resolve_method_for_run(
    settings: LabSettings,
    mode: ExperimentMode,
    variant: ExperimentVariant,
    *,
    project_root: Path | None = None,
) -> StructuredOutputMethod | None:
    if variant is ExperimentVariant.PROMPT_PARSE:
        return None
    if mode is ExperimentMode.MOCK:
        requested = settings.ai_structured_output_method.strip().casefold()
        if requested == "auto":
            return StructuredOutputMethod.JSON_SCHEMA
        try:
            return StructuredOutputMethod(requested)
        except ValueError as exc:
            raise StructuredOutputResolutionError(
                f"未知结构化输出机制：{settings.ai_structured_output_method}"
            ) from exc
    return freeze_native_method(settings, project_root=project_root)


def default_backend_factory(
    settings: LabSettings,
    mode: ExperimentMode,
    variant: ExperimentVariant,
    method: StructuredOutputMethod | None,
) -> StructuredBackend:
    if mode is ExperimentMode.MOCK:
        return mock_backend(as_json_text=variant is ExperimentVariant.PROMPT_PARSE)
    if variant is ExperimentVariant.PROMPT_PARSE:
        return OpenAIPromptParseBackend(settings)
    assert method is not None
    if variant is ExperimentVariant.SDK_NATIVE:
        return OpenAINativeBackend(settings, method)
    return LangChainNativeBackend(settings, method)


def _record_outcome(
    recorder: RunRecorder,
    contract: ContractBundle,
    outcome: ExperimentOutcome,
) -> None:
    contract_metadata = {
        "case_id": contract.case.case_id,
        "case_version": contract.case.case_version,
        "input_hash": contract.input_hash,
        "prompt_hash": contract.prompt_hash,
        "schema_hash": contract.schema_hash,
    }
    recorder.record_event(
        "exp01.input",
        {
            **contract_metadata,
            "brief": contract.case.brief,
            "prompt": contract.prompt,
        },
    )
    recorder.record_event("exp01.outcome", outcome)
    recorder.write_json(
        "input.json",
        {**contract_metadata, "brief": contract.case.brief},
    )
    recorder.write_json("exp01.json", outcome)
    recorder.update_summary(
        {
            **contract_metadata,
            "variant": outcome.variant.value,
            "resolved_method": (
                outcome.resolved_method.value if outcome.resolved_method is not None else None
            ),
            "experiment_status": outcome.status,
            "metrics": outcome.metrics,
            "errors": outcome.errors,
        }
    )


def run_exp01(
    settings: LabSettings,
    recorder: RunRecorder,
    *,
    case_id: str,
    mode: ExperimentMode,
    variant: ExperimentVariant,
    project_root: Path | None = None,
    backend_factory: BackendFactory = default_backend_factory,
) -> ExperimentOutcome:
    contract = load_contract(case_id, project_root=project_root)
    try:
        method = resolve_method_for_run(
            settings,
            mode,
            variant,
            project_root=project_root,
        )
    except StructuredOutputResolutionError as exc:
        if variant is ExperimentVariant.PROMPT_PARSE:
            raise
        outcome = unsupported_outcome(variant, str(exc))
        _record_outcome(recorder, contract, outcome)
        return outcome

    backend = backend_factory(settings, mode, variant, method)
    outcome = execute_variant(
        variant,
        backend,
        contract.prompt,
        resolved_method=method,
    )
    _record_outcome(recorder, contract, outcome)
    return outcome
