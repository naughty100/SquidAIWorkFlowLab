from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from ai_workflow_lab.config import ConfigurationError, LabSettings


def test_base_url_host_excludes_path_query_and_credentials() -> None:
    settings = LabSettings(
        ai_base_url="https://example.com:8443/v1/?trace=secret",
    )

    assert settings.ai_base_url == "https://example.com:8443/v1/?trace=secret"
    assert settings.base_url_host == "example.com:8443"


def test_invalid_base_url_is_rejected() -> None:
    with pytest.raises(ValidationError, match="HTTP"):
        LabSettings(ai_base_url="file:///tmp/model")


def test_live_credentials_are_required() -> None:
    settings = LabSettings(ai_api_key=None, ai_model=None)

    with pytest.raises(ConfigurationError, match="AI_API_KEY, AI_MODEL"):
        settings.require_live_credentials()


def test_secret_values_only_contains_non_empty_keys(tmp_path: Path) -> None:
    settings = LabSettings(
        ai_api_key=SecretStr("secret-value"),
        ai_model="model",
        lab_output_dir=tmp_path / "outputs",
    )

    assert settings.secret_values == ("secret-value",)
