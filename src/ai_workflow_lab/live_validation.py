"""统一 live 验收所用的可选 dotenv 配置档案。"""

import os
from pathlib import Path

from ai_workflow_lab.config import ConfigurationError, LabSettings

LIVE_ENV_FILE_VARIABLE = "LAB_LIVE_ENV_FILE"


def configured_live_env_file() -> Path | None:
    """解析验收专用 dotenv 路径；未设置时沿用项目默认 `.env`。"""
    raw = os.environ.get(LIVE_ENV_FILE_VARIABLE, "").strip()
    if not raw:
        return None
    resolved = Path(raw).expanduser().resolve()
    if not resolved.is_file():
        raise ConfigurationError(
            f"{LIVE_ENV_FILE_VARIABLE} 指向的配置文件不存在：{resolved}"
        )
    return resolved


def load_live_validation_settings() -> LabSettings:
    """让 pytest live 验收与 CLI 使用同一配置档案语义。"""
    return LabSettings.from_env_file(configured_live_env_file())


def live_env_file_cli_args() -> list[str]:
    """为子进程 CLI 生成不含秘密值的 `--env-file` 参数。"""
    env_file = configured_live_env_file()
    return [] if env_file is None else ["--env-file", str(env_file)]
