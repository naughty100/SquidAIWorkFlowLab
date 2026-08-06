"""应用配置及运行前校验。"""

from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field, PrivateAttr, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigurationError(ValueError):
    """配置不足或不合法。"""


class LabSettings(BaseSettings):
    """从环境变量和本地 `.env` 读取的实验配置。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    ai_base_url: str = "https://api.openai.com/v1"
    ai_api_key: SecretStr | None = None
    ai_model: str | None = None
    ai_timeout_seconds: float = Field(default=60.0, gt=0, le=600)
    ai_max_retries: int = Field(default=2, ge=0, le=10)
    ai_max_output_tokens: int = Field(default=1200, ge=64, le=32000)
    ai_structured_output_method: str = "auto"

    lab_output_dir: Path = Path("data/outputs")
    lab_runtime_dir: Path = Path("data/runtime")
    lab_cache_dir: Path = Path("data/cache")
    lab_artifact_inline_threshold: int = Field(default=2048, ge=256, le=1_000_000)

    _loaded_env_file: Path | None = PrivateAttr(default=None)

    @classmethod
    def from_env_file(cls, env_file: Path | None = None) -> "LabSettings":
        """从指定的 dotenv 配置档案加载设置；未指定时沿用默认 `.env`。"""
        if env_file is None:
            return cls()

        resolved = env_file.expanduser().resolve()
        if not resolved.is_file():
            raise ConfigurationError(f"环境配置文件不存在或不是文件：{resolved}")
        settings = cls(_env_file=resolved)  # type: ignore[call-arg]
        settings._loaded_env_file = resolved
        return settings

    @property
    def env_file_label(self) -> str:
        """返回可安全写入运行摘要的配置档案标识，不包含任何配置值。"""
        return str(self._loaded_env_file) if self._loaded_env_file is not None else ".env"

    @field_validator("ai_base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        """只接受具有 host 的 HTTP(S) URL，并移除结尾斜杠。"""
        stripped = value.strip().rstrip("/")
        parsed = urlsplit(stripped)
        if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
            msg = "AI_BASE_URL 必须是包含主机名的 HTTP(S) URL"
            raise ValueError(msg)
        return stripped

    @field_validator("ai_model", mode="before")
    @classmethod
    def normalize_optional_model(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    @property
    def base_url_host(self) -> str:
        """返回不含路径、查询串和凭据的 host[:port]。"""
        parsed = urlsplit(self.ai_base_url)
        host = parsed.hostname or ""
        return f"{host}:{parsed.port}" if parsed.port is not None else host

    @property
    def secret_values(self) -> tuple[str, ...]:
        """返回需要从持久化内容中二次替换的实际秘密值。"""
        if self.ai_api_key is None:
            return ()
        value = self.ai_api_key.get_secret_value()
        return (value,) if value else ()

    def require_live_credentials(self) -> None:
        """确认 live probe 所需配置齐全。"""
        missing: list[str] = []
        if self.ai_api_key is None or not self.ai_api_key.get_secret_value():
            missing.append("AI_API_KEY")
        if self.ai_model is None:
            missing.append("AI_MODEL")
        if missing:
            joined = ", ".join(missing)
            raise ConfigurationError(f"live 模式缺少配置：{joined}")
