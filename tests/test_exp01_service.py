import json
from pathlib import Path

from ai_workflow_lab.capabilities import StructuredOutputMethod
from ai_workflow_lab.config import LabSettings
from ai_workflow_lab.exp01.backends import SequenceMockBackend, default_mock_payload
from ai_workflow_lab.exp01.execution import ExperimentMode, ExperimentVariant
from ai_workflow_lab.exp01.service import run_exp01
from ai_workflow_lab.run_recording import RunRecorder


def test_native_without_supported_capability_never_constructs_backend(tmp_path: Path) -> None:
    settings = LabSettings(
        ai_model="model-without-report",
        lab_output_dir=tmp_path / "outputs",
    )
    recorder = RunRecorder(settings, command="test", run_id="unsupported")

    def forbidden_factory(
        _settings: LabSettings,
        _mode: ExperimentMode,
        _variant: ExperimentVariant,
        _method: StructuredOutputMethod | None,
    ) -> SequenceMockBackend:
        raise AssertionError("unsupported native variant must not construct a backend")

    outcome = run_exp01(
        settings,
        recorder,
        case_id="career-transition-v1",
        mode=ExperimentMode.LIVE,
        variant=ExperimentVariant.SDK_NATIVE,
        project_root=Path(__file__).parents[1],
        backend_factory=forbidden_factory,
    )
    recorder.finish("succeeded")

    assert outcome.status == "unsupported"
    assert outcome.metrics.model_calls == 0


def test_mock_run_saves_contract_metrics_and_result(tmp_path: Path) -> None:
    settings = LabSettings(lab_output_dir=tmp_path / "outputs")
    recorder = RunRecorder(settings, command="test", run_id="mock-run")

    def factory(
        _settings: LabSettings,
        _mode: ExperimentMode,
        _variant: ExperimentVariant,
        _method: StructuredOutputMethod | None,
    ) -> SequenceMockBackend:
        return SequenceMockBackend([default_mock_payload()])

    outcome = run_exp01(
        settings,
        recorder,
        case_id="career-transition-v1",
        mode=ExperimentMode.MOCK,
        variant=ExperimentVariant.LANGCHAIN_NATIVE,
        project_root=Path(__file__).parents[1],
        backend_factory=factory,
    )
    recorder.finish("succeeded")

    summary = json.loads(recorder.summary_path.read_text(encoding="utf-8"))
    result = json.loads((recorder.run_dir / "exp01.json").read_text(encoding="utf-8"))
    assert outcome.status == "succeeded"
    assert summary["resolved_method"] == "json_schema"
    assert summary["prompt_hash"]
    assert summary["schema_hash"]
    assert result["metrics"]["schema_validity_rate_among_successes"] == 1.0
