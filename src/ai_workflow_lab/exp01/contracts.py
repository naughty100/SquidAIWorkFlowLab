"""版本化案例、Prompt 与契约 hash。"""

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from ai_workflow_lab.exp01.domain import IdeaBrief, TopicOptionsDraft


class ExperimentCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    case_version: str
    brief: IdeaBrief


class ContractBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case: ExperimentCase
    prompt: str
    input_hash: str
    prompt_hash: str
    schema_hash: str


def _canonical_hash(value: object) -> str:
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
    return ContractBundle(
        case=case,
        prompt=prompt,
        input_hash=_canonical_hash(case.brief.model_dump(mode="json")),
        prompt_hash=_canonical_hash(prompt),
        schema_hash=_canonical_hash(schema),
    )
