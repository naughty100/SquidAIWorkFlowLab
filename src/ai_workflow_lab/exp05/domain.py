"""实验五可持久化 state 与 CLI 结果模型。"""

from typing import Literal, TypedDict

from pydantic import BaseModel, ConfigDict


class WorkflowState(TypedDict):
    """只允许 JSON 领域数据；客户端、连接和网页全文不属于 state。"""

    schema_version: str
    case_id: str
    case_version: str
    mode: str
    input_question: str
    audience: str
    goal: str
    thread_id: str
    initial_run_id: str
    topic_options: list[dict[str, str]]
    selected_topic_id: str
    selected_topic_title: str
    research_questions: list[str]
    source_evidence: list[dict[str, object]]
    artifact_refs: list[dict[str, object]]
    research_pack: dict[str, object]
    proposal: dict[str, object]
    quality_result: dict[str, object]
    research_round: int
    revision_count: int
    evidence_warning: bool
    status: str


class GraphInterruptInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: object
    interrupt_id: str | None = None


class WorkflowInvocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    thread_id: str
    status: str
    next_nodes: list[str]
    interrupts: list[GraphInterruptInfo]
    state: dict[str, object]


class CheckpointHistoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    checkpoint_id: str | None
    created_at: str | None
    next_nodes: list[str]
    status: str | None
    research_round: int
    revision_count: int


class GraphStateView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: str
    checkpoint_id: str | None
    state_hash: str
    next_nodes: list[str]
    interrupts: list[GraphInterruptInfo]
    status: str | None
    state: dict[str, object]
    history: list[CheckpointHistoryItem]
    read_only: Literal[True] = True
