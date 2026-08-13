from pathlib import Path

import pytest

from ai_workflow_lab.config import ConfigurationError
from ai_workflow_lab.live_validation import (
    configured_live_env_file,
    live_env_file_cli_args,
    load_live_validation_settings,
)


def test_live_validation_uses_default_env_when_override_is_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LAB_LIVE_ENV_FILE", raising=False)

    assert configured_live_env_file() is None
    assert live_env_file_cli_args() == []


def test_live_validation_env_file_is_shared_with_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env.test-live"
    env_file.write_text("AI_MODEL=test-live-model\n", encoding="utf-8")
    monkeypatch.setenv("LAB_LIVE_ENV_FILE", str(env_file))

    settings = load_live_validation_settings()

    assert settings.ai_model == "test-live-model"
    assert settings.env_file_label == str(env_file.resolve())
    assert live_env_file_cli_args() == ["--env-file", str(env_file.resolve())]


def test_live_validation_rejects_missing_env_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = tmp_path / "missing.env"
    monkeypatch.setenv("LAB_LIVE_ENV_FILE", str(missing))

    with pytest.raises(ConfigurationError, match="不存在"):
        configured_live_env_file()
