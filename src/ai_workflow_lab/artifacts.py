"""内容寻址的大文本 artifact 存储。"""

import gzip
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ai_workflow_lab.security import JSONValue, sanitize

_CATEGORY_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class ArtifactError(ValueError):
    """Artifact 引用不安全或内容校验失败。"""


class ArtifactRef(BaseModel):
    """可安全写入 Trace 的 artifact 描述。"""

    model_config = ConfigDict(extra="forbid")

    artifact_ref: str
    content_hash: str
    char_count: int = Field(ge=0)
    preview: str
    media_type: str = "text/plain"


class _StoredTextArtifact(BaseModel):
    """压缩文件内部的受校验结构。"""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    content_hash: str
    media_type: str
    text: str
    metadata: JSONValue


def normalize_text(value: str) -> str:
    """统一 Unicode 和换行，以稳定生成内容 hash。"""
    normalized = unicodedata.normalize("NFC", value)
    return normalized.replace("\r\n", "\n").replace("\r", "\n")


def text_hash(value: str) -> str:
    return hashlib.sha256(normalize_text(value).encode("utf-8")).hexdigest()


class ArtifactStore:
    """在单次运行目录下保存并读取 gzip JSON artifact。"""

    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir.resolve()
        self.artifacts_dir = self.run_dir / "artifacts"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def put_text(
        self,
        text: str,
        *,
        category: str = "trace",
        media_type: str = "text/plain",
        metadata: object | None = None,
    ) -> ArtifactRef:
        """按规范化正文 hash 保存文本，相同正文复用同一路径。"""
        if _CATEGORY_PATTERN.fullmatch(category) is None:
            raise ArtifactError(f"不安全的 artifact category: {category}")

        normalized = normalize_text(text)
        digest = text_hash(normalized)
        relative = Path("artifacts") / category / f"{digest}.json.gz"
        target = self.run_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)

        if not target.exists():
            payload: dict[str, JSONValue] = {
                "schema_version": 1,
                "content_hash": digest,
                "media_type": media_type,
                "text": normalized,
                "metadata": sanitize(metadata),
            }
            encoded = json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            compressed = gzip.compress(encoded, mtime=0)
            temporary = target.with_suffix(target.suffix + ".tmp")
            temporary.write_bytes(compressed)
            temporary.replace(target)

        return ArtifactRef(
            artifact_ref=relative.as_posix(),
            content_hash=digest,
            char_count=len(normalized),
            preview=normalized[:160],
            media_type=media_type,
        )

    def read_text(self, reference: ArtifactRef | str) -> str:
        """校验路径和 hash 后读取 artifact 正文。"""
        artifact_ref = reference.artifact_ref if isinstance(reference, ArtifactRef) else reference
        target = (self.run_dir / Path(artifact_ref)).resolve()
        if not target.is_relative_to(self.artifacts_dir):
            raise ArtifactError("artifact reference 超出当前运行目录")
        if not target.is_file():
            raise ArtifactError(f"artifact 不存在: {artifact_ref}")

        raw = gzip.decompress(target.read_bytes())
        try:
            payload = _StoredTextArtifact.model_validate_json(raw)
        except ValueError as exc:
            raise ArtifactError("artifact 内容格式无效") from exc
        text = payload.text
        expected = payload.content_hash
        if expected != text_hash(text):
            raise ArtifactError("artifact 内容 hash 校验失败")
        if isinstance(reference, ArtifactRef) and expected != reference.content_hash:
            raise ArtifactError("artifact reference hash 不匹配")
        return text


def externalize_large_text(
    value: JSONValue,
    *,
    store: ArtifactStore,
    threshold: int,
) -> JSONValue:
    """递归外置超过阈值的字符串。"""
    if isinstance(value, str):
        if len(value) <= threshold:
            return value
        reference = store.put_text(value, category="trace")
        return {"$artifact": reference.model_dump(mode="json")}
    if isinstance(value, list):
        return [externalize_large_text(item, store=store, threshold=threshold) for item in value]
    if isinstance(value, dict):
        return {
            key: externalize_large_text(item, store=store, threshold=threshold)
            for key, item in value.items()
        }
    return value


def reconstruct_externalized(value: JSONValue, *, store: ArtifactStore) -> JSONValue:
    """递归解析 `$artifact` 占位符并恢复正文。"""
    if isinstance(value, list):
        return [reconstruct_externalized(item, store=store) for item in value]
    if isinstance(value, dict):
        if set(value) == {"$artifact"} and isinstance(value["$artifact"], dict):
            reference = ArtifactRef.model_validate(value["$artifact"])
            return store.read_text(reference)
        return {key: reconstruct_externalized(item, store=store) for key, item in value.items()}
    return value
