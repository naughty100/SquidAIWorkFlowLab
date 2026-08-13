"""实验三的运行、质量与比较领域模型。"""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ai_workflow_lab.exp02.domain import ProposalBundle, ResearchPack


class Experiment03Variant(StrEnum):
    FIXED = "fixed"
    AGENT = "agent"


class AgentTermination(StrEnum):
    COMPLETED = "completed"
    BUDGET_EXHAUSTED = "budget_exhausted"
    MIDDLEWARE_LIMIT = "middleware_limit"
    REPEATED_TOOL_CALL = "repeated_tool_call"
    INVALID_RESPONSE = "invalid_response"
    FAILED = "failed"


class AgentResearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pack: ResearchPack
    termination: AgentTermination
    structured_strategy: Literal["ToolStrategy[ResearchPack]"] = "ToolStrategy[ResearchPack]"
    error: str | None = None
    token_count: int | None = Field(default=None, ge=0)


class ProposalRubric(BaseModel):
    """固定 15 分 Rubric；自动填充仅用于可重复实验，允许人工覆盖。"""

    model_config = ConfigDict(extra="forbid")

    evidence_traceability: int = Field(ge=0, le=5)
    evidence_specificity: int = Field(ge=0, le=5)
    actionability: int = Field(ge=0, le=5)
    reviewer: str = "deterministic-baseline"
    notes: str = "等待人工复核"

    @property
    def total(self) -> int:
        return self.evidence_traceability + self.evidence_specificity + self.actionability


class Experiment03Metrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_coverage: float = Field(ge=0, le=1)
    proposal_rubric: ProposalRubric | None = None
    model_calls: int = Field(ge=0)
    tool_calls: int = Field(ge=0)
    token_count: int | None = Field(default=None, ge=0)
    elapsed_ms: float = Field(ge=0)
    failure_type: str | None = None
    diagnosability: int = Field(ge=0, le=5)


class Experiment03Outcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["succeeded", "partial", "failed"]
    mode: Literal["fixture", "live"]
    variant: Experiment03Variant
    research_pack: ResearchPack
    proposal: ProposalBundle | None = None
    budget: dict[str, int | float]
    metrics: Experiment03Metrics
    termination: AgentTermination | None = None
    error: str | None = None


class VariantAggregate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variant: Experiment03Variant
    runs: int = Field(ge=0)
    success_rate: float = Field(ge=0, le=1)
    mean_source_coverage: float = Field(ge=0, le=1)
    mean_proposal_rubric: float | None = None
    mean_model_calls: float = Field(ge=0)
    mean_tool_calls: float = Field(ge=0)
    mean_token_count: float | None = None
    mean_elapsed_ms: float = Field(ge=0)
    failure_types: dict[str, int] = Field(default_factory=dict)
    mean_diagnosability: float = Field(ge=0, le=5)


class PairedRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pair_id: str
    fixed_run_id: str
    agent_run_id: str
    fixed: Experiment03Metrics
    agent: Experiment03Metrics


class Experiment03Comparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    comparison_id: str
    case_id: str
    case_version: str
    fixture_version: str
    control_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    model: str | None = None
    mode: Literal["fixture", "live"]
    requested_runs: int = Field(ge=1)
    completed_pairs: int = Field(ge=0)
    smoke_comparison: bool
    paired_runs: list[PairedRun]
    fixed: VariantAggregate
    agent: VariantAggregate
    threshold_differences: dict[str, float]
    extension_triggered: bool
    minimum_required_runs: int
    conclusion_status: Literal["insufficient_sample", "extension_required", "directional"]
    directional_conclusion: str | None = None
