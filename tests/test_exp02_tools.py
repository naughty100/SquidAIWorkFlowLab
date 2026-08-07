from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from ai_workflow_lab.artifacts import ArtifactStore
from ai_workflow_lab.config import LabSettings
from ai_workflow_lab.exp02.tools import (
    FixtureWebTools,
    ReadWebpageArgs,
    SearchWebArgs,
    TavilyWebTools,
    load_fixture,
)


def test_tool_argument_limits_are_enforced() -> None:
    with pytest.raises(ValidationError):
        SearchWebArgs(query="AI", max_results=6)
    with pytest.raises(ValidationError):
        ReadWebpageArgs(url="file:///etc/passwd", max_chars=10)
    with pytest.raises(ValidationError):
        ReadWebpageArgs(url="https://example.com", max_chars=12001)


def test_fixture_mode_never_uses_network(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def forbidden_network(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("fixture mode accessed network")

    monkeypatch.setattr("ai_workflow_lab.exp02.tools.urlopen", forbidden_network)
    fixture = load_fixture()
    tools = FixtureWebTools(fixture, ArtifactStore(tmp_path))

    search = tools.search_web(SearchWebArgs(query="career", max_results=2))
    page = tools.read_webpage(ReadWebpageArgs(url=search.results[0].url, max_chars=12000))

    assert len(search.results) == 2
    assert page.error is None
    assert page.artifact is not None
    assert page.artifact.artifact_ref.startswith("artifacts/web/")


def test_tavily_adapter_caps_results_content_and_uses_fixed_endpoints(tmp_path: Path) -> None:
    calls: list[tuple[str, dict[str, object], str, float]] = []

    def transport(
        url: str,
        payload: dict[str, object],
        key: SecretStr,
        timeout: float,
    ) -> dict[str, object]:
        calls.append((url, payload, key.get_secret_value(), timeout))
        if url.endswith("/search"):
            return {
                "results": [
                    {
                        "title": f"result-{index}",
                        "url": f"https://example.com/{index}",
                        "content": "snippet",
                    }
                    for index in range(8)
                ]
            }
        return {
            "results": [
                {
                    "url": "https://example.com/1",
                    "title": "page",
                    "raw_content": "x" * 13000,
                }
            ]
        }

    settings = LabSettings(
        tavily_api_key=SecretStr("tvly-test-secret"),
        tavily_timeout_seconds=12,
    )
    tools = TavilyWebTools(settings, ArtifactStore(tmp_path), transport=transport)

    search = tools.search_web(SearchWebArgs(query="career", max_results=5))
    page = tools.read_webpage(ReadWebpageArgs(url=search.results[0].url, max_chars=12000))

    assert len(search.results) == 5
    assert page.content is not None and len(page.content) == 12000
    assert [call[0] for call in calls] == [
        "https://api.tavily.com/search",
        "https://api.tavily.com/extract",
    ]
    assert all(call[2] == "tvly-test-secret" for call in calls)
    assert all(call[3] == 12 for call in calls)


def test_tavily_timeout_is_normalized_without_secret(tmp_path: Path) -> None:
    def timeout_transport(
        _url: str,
        _payload: dict[str, object],
        _key: SecretStr,
        _timeout: float,
    ) -> dict[str, object]:
        raise TimeoutError("tvly-secret-value")

    settings = LabSettings(tavily_api_key=SecretStr("tvly-secret-value"))
    tools = TavilyWebTools(settings, ArtifactStore(tmp_path), transport=timeout_transport)

    result = tools.search_web(SearchWebArgs(query="career"))

    assert result.error is not None
    assert result.error.code == "timeout"
    assert "tvly-secret-value" not in result.model_dump_json()
