from pathlib import Path

from pydantic import SecretStr

from ai_workflow_lab.capabilities import CapabilityStatus
from ai_workflow_lab.config import LabSettings
from ai_workflow_lab.doctor import LiveProbeBackend, run_doctor


class SuccessfulBackend:
    def probe_chat(self) -> bool:
        return True

    def probe_streaming(self) -> bool:
        return True

    def probe_tool_calling(self) -> bool:
        return True

    def probe_json_mode(self) -> bool:
        return True

    def probe_json_schema(self) -> bool:
        return True


class FeatureRejectedError(RuntimeError):
    status_code = 400


class PartiallySupportedBackend(SuccessfulBackend):
    def probe_json_schema(self) -> bool:
        raise FeatureRejectedError("json_schema rejected")


def create_project(tmp_path: Path) -> LabSettings:
    (tmp_path / "uv.lock").write_text("lock", encoding="utf-8")
    for name in ("outputs", "runtime", "cache"):
        (tmp_path / name).mkdir()
    return LabSettings(
        ai_base_url="https://example.com/v1",
        ai_api_key=SecretStr("sk-unit-test"),
        ai_model="test-model",
        lab_output_dir=tmp_path / "outputs",
        lab_runtime_dir=tmp_path / "runtime",
        lab_cache_dir=tmp_path / "cache",
    )


def test_offline_doctor_does_not_construct_live_backend(tmp_path: Path) -> None:
    settings = create_project(tmp_path)

    def forbidden_factory(_settings: LabSettings) -> LiveProbeBackend:
        raise AssertionError("offline doctor must not construct a live backend")

    result = run_doctor(
        settings,
        live=False,
        project_root=tmp_path,
        backend_factory=forbidden_factory,
    )

    assert result.ok
    assert result.capabilities.chat.status is CapabilityStatus.UNKNOWN
    assert result.capabilities.chat.reason == "live_probe_not_requested"


def test_live_doctor_reports_supported_capabilities(tmp_path: Path) -> None:
    settings = create_project(tmp_path)

    result = run_doctor(
        settings,
        live=True,
        project_root=tmp_path,
        backend_factory=lambda _settings: SuccessfulBackend(),
    )

    assert result.ok
    assert result.capabilities.chat.status is CapabilityStatus.SUPPORTED
    assert result.capabilities.json_schema.status is CapabilityStatus.SUPPORTED


def test_feature_rejection_is_unsupported_only_after_chat_succeeds(tmp_path: Path) -> None:
    settings = create_project(tmp_path)

    result = run_doctor(
        settings,
        live=True,
        project_root=tmp_path,
        backend_factory=lambda _settings: PartiallySupportedBackend(),
    )

    assert result.ok
    assert result.capabilities.json_schema.status is CapabilityStatus.UNSUPPORTED
    assert result.capabilities.json_schema.reason == "feature_rejected"


def test_requested_live_with_missing_credentials_remains_unknown(tmp_path: Path) -> None:
    settings = create_project(tmp_path).model_copy(update={"ai_api_key": None, "ai_model": None})

    result = run_doctor(settings, live=True, project_root=tmp_path)

    assert not result.ok
    assert result.capabilities.live
    assert result.capabilities.chat.status is CapabilityStatus.UNKNOWN
    assert result.capabilities.chat.reason == "live_configuration_invalid"
