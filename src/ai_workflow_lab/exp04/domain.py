"""实验四 Profile、排名、证据与运行结果领域模型。"""

import hashlib
import json
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ai_workflow_lab.artifacts import ArtifactRef
from ai_workflow_lab.exp02.domain import ProposalBundle


class CanonicalProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    def canonical_json(self) -> str:
        return json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @property
    def config_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


class EmbeddingProfile(CanonicalProfile):
    profile_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    provider: Literal["sentence-transformers"]
    model_name: str = Field(min_length=3)
    revision: str = Field(pattern=r"^[a-f0-9]{40}$")
    device: Literal["cpu"]
    dtype: Literal["float32"]
    trust_remote_code: bool
    normalize: bool
    batch_size: int = Field(ge=1, le=256)
    query_prefix: str
    document_prefix: str
    distance_metric: Literal["cosine"]
    expected_dimensions: int = Field(gt=0)
    max_sequence_length: int = Field(gt=0)
    cache_dir: Path
    profile_version: str = Field(min_length=1)

    @field_validator("trust_remote_code")
    @classmethod
    def remote_code_must_be_disabled(cls, value: bool) -> bool:
        if value:
            raise ValueError("RAG profile 禁止 trust_remote_code")
        return value

    @field_validator("cache_dir")
    @classmethod
    def cache_dir_must_be_relative(cls, value: Path) -> Path:
        if value.is_absolute() or ".." in value.parts:
            raise ValueError("cache_dir 必须是 cache root 下的相对路径")
        return value


class RetrievalProfile(CanonicalProfile):
    profile_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    splitter: Literal["deterministic-character"] = "deterministic-character"
    chunk_size: int = Field(ge=100, le=4000)
    overlap: int = Field(ge=0)
    top_k: int = Field(ge=1, le=32)
    score_type: Literal["cosine_similarity"] = "cosine_similarity"
    profile_version: str = Field(min_length=1)

    @model_validator(mode="after")
    def overlap_is_smaller_than_chunk(self) -> "RetrievalProfile":
        if self.overlap >= self.chunk_size:
            raise ValueError("overlap 必须小于 chunk_size")
        return self


class LocalDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(pattern=r"^doc-[a-z0-9-]+$")
    version: str = Field(min_length=1)
    title: str = Field(min_length=1)
    path: str = Field(min_length=1)
    content: str = Field(min_length=1)
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class DocumentChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str = Field(pattern=r"^chunk-[a-f0-9]{16}$")
    document_id: str
    document_version: str
    title: str
    ordinal: int = Field(ge=0)
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    content: str = Field(min_length=1)
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class RetrievalCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_id: str = Field(pattern=r"^q-[a-z0-9-]+$")
    query: str = Field(min_length=4)
    expected_document_ids: list[str] = Field(min_length=1)
    required_question_id: str = Field(pattern=r"^rq-[a-z0-9-]+$")


class RankingEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rank: int = Field(ge=1)
    document_id: str
    chunk_id: str
    score: float


class QueryRanking(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_id: str
    query: str
    expected_document_ids: list[str]
    entries: list[RankingEntry]
    first_relevant_rank: int | None = Field(default=None, ge=1)


class RetrievalMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_count: int = Field(ge=1)
    recall_at_2: float = Field(ge=0, le=1)
    recall_at_4: float = Field(ge=0, le=1)
    recall_at_8: float = Field(ge=0, le=1)
    mrr: float = Field(ge=0, le=1)


class ProfileEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    embedding_profile_id: str
    embedding_profile_hash: str
    retrieval_profile_id: str
    retrieval_profile_hash: str
    index_elapsed_ms: float = Field(ge=0)
    chunk_count: int = Field(ge=0)
    rankings: list[QueryRanking]
    metrics: RetrievalMetrics


class ProfileSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    executed_profile_ids: list[str]
    skipped_profile_ids: list[str]
    gate_threshold: float
    selected_profile_id: str
    reason: str
    evaluations: list[ProfileEvaluation]


class RagSourceEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(pattern=r"^src-[a-f0-9]{12}$")
    document_id: str
    chunk_id: str
    title: str
    artifact: ArtifactRef
    supporting_excerpt: str = Field(min_length=1, max_length=600)
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    metadata: dict[str, str]


class SupportedFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str
    claim: str = Field(min_length=1)
    source_ids: list[str] = Field(min_length=1)


class EvidenceStatus(StrEnum):
    SUPPORTED = "supported"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class EvidenceAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: EvidenceStatus
    required_question_ids: list[str]
    sources: list[RagSourceEvidence]
    findings: list[SupportedFinding]
    missing_question_ids: list[str] = Field(default_factory=list)


class AutomaticEvidenceResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid_source_ids: list[str]
    invalid_source_ids: list[str]
    covered_question_ids: list[str]
    missing_question_ids: list[str]
    status: EvidenceStatus


class ManualEvidenceRubric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str
    semantically_supported: bool | None = None
    reviewer: str = "unassigned"
    notes: str = "待人工判断摘录是否真正支持结论"


class RagVariant(StrEnum):
    NO_RAG = "no-rag"
    FULL_CONTEXT = "full-context"
    VECTOR = "vector"


class Experiment04Outcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: EvidenceStatus
    variant: RagVariant
    embedding_profile_hash: str
    retrieval_profile_hash: str
    generation_control_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    context_char_count: int = Field(ge=0)
    source_count: int = Field(ge=0)
    token_count: int | None = Field(default=None, ge=0)
    evidence: EvidenceAnswer
    automatic_evaluation: AutomaticEvidenceResult
    manual_rubric: list[ManualEvidenceRubric]
    proposal: ProposalBundle | None = None


class RagEvaluationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    selection: ProfileSelection
    matrix: list[ProfileEvaluation]
