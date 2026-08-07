"""实验二的研究输入、证据和提案领域契约。"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ai_workflow_lab.artifacts import ArtifactRef


class ResearchBrief(BaseModel):
    """一个版本化研究案例。"""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    case_version: str = Field(min_length=1)
    question: str = Field(min_length=8)
    audience: str = Field(min_length=1)
    goal: str = Field(min_length=1)


class SourceEvidence(BaseModel):
    """由网页 artifact 支撑的规范化证据。"""

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(pattern=r"^src-[a-f0-9]{12}$")
    title: str = Field(min_length=1)
    url: str = Field(pattern=r"^https?://")
    artifact: ArtifactRef
    excerpt: str = Field(min_length=1, max_length=600)


class ResearchFinding(BaseModel):
    """引用一个或多个来源的研究发现。"""

    model_config = ConfigDict(extra="forbid")

    claim: str = Field(min_length=1)
    source_ids: list[str] = Field(min_length=1)


class ResearchPack(BaseModel):
    """固定流程和受控循环共享的研究结果。"""

    model_config = ConfigDict(extra="forbid")

    brief: ResearchBrief
    queries: list[str]
    sources: list[SourceEvidence]
    findings: list[ResearchFinding]
    tool_errors: list[dict[str, object]] = Field(default_factory=lambda: list[dict[str, object]]())

    @model_validator(mode="after")
    def validate_finding_sources(self) -> "ResearchPack":
        known = {source.source_id for source in self.sources}
        missing = {
            source_id
            for finding in self.findings
            for source_id in finding.source_ids
            if source_id not in known
        }
        if missing:
            raise ValueError(f"发现引用了未知来源：{', '.join(sorted(missing))}")
        return self


class ProposalItem(BaseModel):
    """一项由研究证据支撑的提案建议。"""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    source_ids: list[str] = Field(min_length=1)


class ProposalDraft(BaseModel):
    """模型生成、尚未渲染 Markdown 的提案。"""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    recommendations: list[ProposalItem] = Field(min_length=1, max_length=5)


class ProposalBundle(ProposalDraft):
    """校验证据并确定性渲染后的最终提案。"""

    markdown: str = Field(min_length=1)
