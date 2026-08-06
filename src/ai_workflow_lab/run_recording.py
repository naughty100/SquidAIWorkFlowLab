"""单次命令运行的本地 Trace 与摘要记录。"""

import hashlib
import json
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from ai_workflow_lab.artifacts import ArtifactStore, externalize_large_text
from ai_workflow_lab.config import LabSettings
from ai_workflow_lab.security import JSONValue, sanitize

TRACE_SCHEMA_VERSION = "1"
RunStatus = Literal["running", "succeeded", "failed"]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_commit(project_root: Path) -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    return completed.stdout.strip() if completed.returncode == 0 else None


def _write_json(path: Path, value: JSONValue) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(encoded, encoding="utf-8")
    temporary.replace(path)


class RunRecorder:
    """负责一个 run 目录、事件和 summary 的生命周期。"""

    def __init__(
        self,
        settings: LabSettings,
        *,
        command: str,
        project_root: Path | None = None,
        run_id: str | None = None,
    ) -> None:
        self.settings = settings
        self.project_root = (project_root or Path.cwd()).resolve()
        self.run_id = run_id or uuid4().hex
        output_root = settings.lab_output_dir
        if not output_root.is_absolute():
            output_root = self.project_root / output_root
        self.run_dir = (output_root / "commands" / self.run_id).resolve()
        self.run_dir.mkdir(parents=True, exist_ok=False)
        self.artifacts = ArtifactStore(self.run_dir)
        self.events_path = self.run_dir / "events.jsonl"
        self.summary_path = self.run_dir / "summary.json"
        self._started_at = _utc_now()
        self._finished = False
        self._summary: dict[str, JSONValue] = {
            "run_id": self.run_id,
            "command": command,
            "status": "running",
            "started_at": self._started_at,
            "finished_at": None,
            "git_commit": _git_commit(self.project_root),
            "python_version": platform.python_version(),
            "dependency_lock_hash": _sha256_file(self.project_root / "uv.lock"),
            "env_file": settings.env_file_label,
            "model": settings.ai_model,
            "base_url_host": settings.base_url_host,
            "trace_schema_version": TRACE_SCHEMA_VERSION,
        }
        self._persist_summary()
        self.record_event("run.started", {"command": command})

    def _persist_summary(self) -> None:
        """将当前运行摘要脱敏后原子写入磁盘。"""
        sanitized = sanitize(self._summary, secrets=self.settings.secret_values)
        _write_json(self.summary_path, sanitized)

    def record_event(self, event_type: str, payload: object) -> dict[str, JSONValue]:
        """脱敏、外置大文本后追加一个事件。"""
        sanitized = sanitize(payload, secrets=self.settings.secret_values)
        externalized = externalize_large_text(
            sanitized,
            store=self.artifacts,
            threshold=self.settings.lab_artifact_inline_threshold,
        )
        event: dict[str, JSONValue] = {
            "event_id": uuid4().hex,
            "occurred_at": _utc_now(),
            "type": event_type,
            "trace_schema_version": TRACE_SCHEMA_VERSION,
            "payload": externalized,
        }
        with self.events_path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        return event

    def write_json(self, relative_path: str, value: object) -> Path:
        """在 run 目录内写入经过脱敏的 JSON 文件。"""
        target = (self.run_dir / relative_path).resolve()
        if not target.is_relative_to(self.run_dir):
            raise ValueError("运行产物路径超出 run 目录")
        sanitized = sanitize(value, secrets=self.settings.secret_values)
        _write_json(target, sanitized)
        return target

    def update_summary(self, values: dict[str, object]) -> None:
        """在结束前补充命令专属的可复现摘要字段。"""
        if self._finished:
            raise RuntimeError("已结束的 run 不可再更新摘要")
        # 先脱敏再合并 避免调用方直接把敏感字段写进 summary
        sanitized = sanitize(values, secrets=self.settings.secret_values)
        assert isinstance(sanitized, dict)
        self._summary.update(sanitized)
        self._persist_summary()

    def finish(self, status: Literal["succeeded", "failed"], *, details: object = None) -> None:
        """完成 run；重复调用不会写入第二个结束事件。"""
        if self._finished:
            return
        self.record_event("run.finished", {"status": status, "details": details})
        self._summary["status"] = status
        self._summary["finished_at"] = _utc_now()
        self._persist_summary()
        self._finished = True
