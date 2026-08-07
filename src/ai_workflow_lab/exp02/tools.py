"""实验二的只读网页工具、fixture 与 Tavily live 适配器。"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Literal, Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError

from ai_workflow_lab.artifacts import ArtifactRef, ArtifactStore, normalize_text
from ai_workflow_lab.config import LabSettings
from ai_workflow_lab.exp02.domain import ResearchBrief


class ToolError(BaseModel):
    """所有工具失败共享的模型可读错误。"""

    model_config = ConfigDict(extra="forbid")

    code: Literal[
        "invalid_arguments",
        "empty_result",
        "not_found",
        "timeout",
        "rate_limited",
        "server_error",
        "budget_exceeded",
        "unknown_tool",
    ]
    message: str
    retryable: bool


class SearchWebArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=2, max_length=500)
    max_results: int = Field(default=5, ge=1, le=5)


class SearchHit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    url: str = Field(pattern=r"^https?://")
    snippet: str = Field(default="", max_length=1000)


class SearchWebResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    results: list[SearchHit] = Field(default_factory=lambda: list[SearchHit](), max_length=5)
    error: ToolError | None = None


class ReadWebpageArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = Field(pattern=r"^https?://")
    max_chars: int = Field(default=12000, ge=1, le=12000)


class ReadWebpageResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    title: str = ""
    content: str | None = None
    artifact: ArtifactRef | None = None
    error: ToolError | None = None


class WebTools(Protocol):
    def search_web(self, args: SearchWebArgs) -> SearchWebResult: ...

    def read_webpage(self, args: ReadWebpageArgs) -> ReadWebpageResult: ...


class FixturePage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    url: str
    content: str


class FixtureBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fixture_version: str
    brief: ResearchBrief
    search_results: list[SearchHit]
    pages: list[FixturePage]


def default_fixture_path(project_root: Path | None = None) -> Path:
    root = (project_root or Path.cwd()).resolve()
    return root / "experiments" / "02-controlled-tool-calling" / "fixtures" / "career-ai-v1.json"


def load_fixture(project_root: Path | None = None) -> FixtureBundle:
    return FixtureBundle.model_validate_json(
        default_fixture_path(project_root).read_text(encoding="utf-8")
    )


def _clean_content(value: str, max_chars: int) -> str:
    lines = (line.strip() for line in normalize_text(value).splitlines())
    return "\n".join(line for line in lines if line)[:max_chars]


class FixtureWebTools:
    """只读版本化 JSON fixture，不包含任何网络代码路径。"""

    def __init__(self, fixture: FixtureBundle, store: ArtifactStore) -> None:
        self.fixture = fixture
        self.store = store
        self._pages = {page.url: page for page in fixture.pages}

    def search_web(self, args: SearchWebArgs) -> SearchWebResult:
        del args.query
        results = self.fixture.search_results[: args.max_results]
        if not results:
            return SearchWebResult(
                error=ToolError(
                    code="empty_result",
                    message="fixture search returned no results",
                    retryable=False,
                )
            )
        return SearchWebResult(results=results)

    def read_webpage(self, args: ReadWebpageArgs) -> ReadWebpageResult:
        page = self._pages.get(args.url)
        if page is None:
            return ReadWebpageResult(
                url=args.url,
                error=ToolError(
                    code="not_found", message="fixture page not found", retryable=False
                ),
            )
        content = _clean_content(page.content, args.max_chars)
        reference = self.store.put_text(
            content,
            category="web",
            media_type="text/markdown",
            metadata={
                "url": page.url,
                "title": page.title,
                "fixture_version": self.fixture.fixture_version,
            },
        )
        return ReadWebpageResult(
            url=page.url,
            title=page.title,
            content=content,
            artifact=reference,
        )


JSONTransport = Callable[[str, dict[str, object], SecretStr, float], dict[str, object]]


def _http_post_json(
    url: str,
    payload: dict[str, object],
    api_key: SecretStr,
    timeout: float,
) -> dict[str, object]:
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key.get_secret_value()}",
            "Content-Type": "application/json",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        decoded: object = json.loads(response.read().decode("utf-8"))
    if not isinstance(decoded, dict):
        raise ValueError("Tavily response must be a JSON object")
    return cast(dict[str, object], decoded)


def _http_error(exc: BaseException) -> ToolError:
    if isinstance(exc, HTTPError) and exc.code == 429:
        return ToolError(
            code="rate_limited", message="Tavily rate limited the request", retryable=True
        )
    if isinstance(exc, HTTPError):
        return ToolError(
            code="server_error", message=f"Tavily HTTP {exc.code}", retryable=exc.code >= 500
        )
    if isinstance(exc, TimeoutError):
        return ToolError(code="timeout", message="Tavily request timed out", retryable=True)
    if isinstance(exc, URLError) and isinstance(exc.reason, TimeoutError):
        return ToolError(code="timeout", message="Tavily request timed out", retryable=True)
    return ToolError(
        code="server_error", message=f"Tavily request failed: {type(exc).__name__}", retryable=True
    )


class TavilyWebTools:
    """使用 Tavily Search/Extract API 的受限 live 实现。"""

    def __init__(
        self,
        settings: LabSettings,
        store: ArtifactStore,
        *,
        transport: JSONTransport = _http_post_json,
    ) -> None:
        settings.require_tavily_credentials()
        assert settings.tavily_api_key is not None
        self._api_key = settings.tavily_api_key
        self._timeout = settings.tavily_timeout_seconds
        self._store = store
        self._transport = transport

    def search_web(self, args: SearchWebArgs) -> SearchWebResult:
        try:
            payload = self._transport(
                "https://api.tavily.com/search",
                {
                    "query": args.query,
                    "max_results": args.max_results,
                    "search_depth": "basic",
                    "include_answer": False,
                    "include_raw_content": False,
                },
                self._api_key,
                self._timeout,
            )
            raw_results_value = payload.get("results", [])
            if not isinstance(raw_results_value, list):
                raise ValueError("Tavily search results must be a list")
            raw_results = cast(list[object], raw_results_value)
            hits: list[SearchHit] = []
            for item in raw_results[: args.max_results]:
                if not isinstance(item, dict):
                    continue
                mapped = cast(dict[str, object], item)
                try:
                    hits.append(
                        SearchHit(
                            title=str(mapped.get("title") or mapped.get("url") or "Untitled"),
                            url=str(mapped.get("url") or ""),
                            snippet=str(mapped.get("content") or "")[:1000],
                        )
                    )
                except ValidationError:
                    continue
            if not hits:
                return SearchWebResult(
                    error=ToolError(
                        code="empty_result",
                        message="Tavily search returned no usable results",
                        retryable=False,
                    )
                )
            return SearchWebResult(results=hits)
        except Exception as exc:  # noqa: BLE001 - normalize the external Tool boundary.
            return SearchWebResult(error=_http_error(exc))

    def read_webpage(self, args: ReadWebpageArgs) -> ReadWebpageResult:
        parsed = urlsplit(args.url)
        if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
            return ReadWebpageResult(
                url=args.url,
                error=ToolError(
                    code="invalid_arguments", message="url must be HTTP(S)", retryable=False
                ),
            )
        try:
            payload = self._transport(
                "https://api.tavily.com/extract",
                {
                    "urls": [args.url],
                    "extract_depth": "basic",
                    "format": "markdown",
                    "include_images": False,
                    "timeout": self._timeout,
                },
                self._api_key,
                self._timeout,
            )
            raw_results = payload.get("results", [])
            if (
                not isinstance(raw_results, list)
                or not raw_results
                or not isinstance(raw_results[0], dict)
            ):
                return ReadWebpageResult(
                    url=args.url,
                    error=ToolError(
                        code="empty_result",
                        message="Tavily extract returned no content",
                        retryable=False,
                    ),
                )
            first = cast(dict[str, object], raw_results[0])
            content = _clean_content(str(first.get("raw_content") or ""), args.max_chars)
            if not content:
                return ReadWebpageResult(
                    url=args.url,
                    error=ToolError(
                        code="empty_result",
                        message="Tavily extract returned empty content",
                        retryable=False,
                    ),
                )
            title = str(first.get("title") or parsed.hostname)
            reference = self._store.put_text(
                content,
                category="web",
                media_type="text/markdown",
                metadata={"url": args.url, "title": title},
            )
            return ReadWebpageResult(
                url=args.url,
                title=title,
                content=content,
                artifact=reference,
            )
        except Exception as exc:  # noqa: BLE001 - normalize the external Tool boundary.
            return ReadWebpageResult(url=args.url, error=_http_error(exc))
