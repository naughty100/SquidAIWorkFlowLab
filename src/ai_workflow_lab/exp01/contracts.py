"""版本化案例、Prompt 与契约 hash。"""

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from ai_workflow_lab.exp01.domain import IdeaBrief, TopicOptionsDraft


class ExperimentCase(BaseModel):
    """版本化实验案例及其内容选题输入。"""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    case_version: str
    brief: IdeaBrief


class ContractBundle(BaseModel):
    """一次实验需要的已渲染 Prompt、案例和可复现 hash 集合。"""

    model_config = ConfigDict(extra="forbid")

    case: ExperimentCase
    prompt: str
    input_hash: str
    prompt_hash: str
    schema_hash: str


def _canonical_hash(value: object) -> str:
    """为 JSON 兼容值生成不受键顺序影响的 SHA-256 hash。"""
    # 规范化序列化可避免字典键顺序或空白差异造成误判。
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_contract(
    case_id: str,
    *,
    project_root: Path | None = None,
) -> ContractBundle:
    """读取案例和 Prompt 模板，并生成本次对照使用的固定契约。"""
    root = (project_root or Path.cwd()).resolve()
    experiment_root = root / "experiments" / "01-structured-output"
    case_path = experiment_root / "cases" / f"{case_id}.json"
    prompt_path = experiment_root / "prompts" / "topic-options-v1.txt"
    if not case_path.is_file():
        raise ValueError(f"未知实验案例：{case_id}")
    if not prompt_path.is_file():
        raise ValueError(f"实验 Prompt 不存在：{prompt_path}")

    case = ExperimentCase.model_validate_json(case_path.read_text(encoding="utf-8"))
    prompt_template = prompt_path.read_text(encoding="utf-8").strip()
    schema = TopicOptionsDraft.model_json_schema()
    prompt = prompt_template.format(
        brief_json=case.brief.model_dump_json(indent=2),
        schema_json=json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True),
    )
    # 三种 variant 都记录同一组 hash 用于事后确认对照条件没有漂移
    return ContractBundle(
        case=case,
        prompt=prompt,
        input_hash=_canonical_hash(case.brief.model_dump(mode="json")),
        prompt_hash=_canonical_hash(prompt),
        schema_hash=_canonical_hash(schema),
    )
