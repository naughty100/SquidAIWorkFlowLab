from pathlib import Path

from ai_workflow_lab.exp01.contracts import load_contract
from ai_workflow_lab.exp01.domain import TopicOptionsDraft, finalize_topic_options


def valid_payload() -> dict[str, object]:
    return {
        "options": [
            {
                "title": f"选题 {index}",
                "angle": f"角度 {index}",
                "target_audience": "程序员",
                "core_question": f"问题 {index} 是什么？",
                "reason": f"理由 {index}",
            }
            for index in range(1, 4)
        ]
    }


def test_topic_ids_are_added_by_code_and_are_deterministic() -> None:
    draft = TopicOptionsDraft.model_validate(valid_payload())

    first = finalize_topic_options(draft)
    second = finalize_topic_options(draft)

    assert first == second
    assert len({option.topic_id for option in first.options}) == 3
    assert all(option.topic_id.startswith("topic-") for option in first.options)


def test_versioned_contract_hashes_are_stable() -> None:
    project_root = Path(__file__).parents[1]

    first = load_contract("career-transition-v1", project_root=project_root)
    second = load_contract("career-transition-v1", project_root=project_root)

    assert first.case.case_version == "1.0.0"
    assert first.input_hash == second.input_hash
    assert first.prompt_hash == second.prompt_hash
    assert first.schema_hash == second.schema_hash
    assert "topic_id" not in first.prompt
