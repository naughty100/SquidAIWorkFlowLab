"""逐查询排名、Recall/MRR、Profile 门禁与检索矩阵。"""

from collections.abc import Callable
from pathlib import Path
from statistics import fmean

from langchain_core.embeddings import Embeddings
from pydantic import BaseModel, ConfigDict

from ai_workflow_lab.config import LabSettings

from .domain import (
    EmbeddingProfile,
    ProfileEvaluation,
    ProfileSelection,
    QueryRanking,
    RetrievalCase,
    RetrievalMetrics,
    RetrievalProfile,
)
from .indexing import (
    HashEmbeddings,
    LocalSentenceTransformerEmbeddings,
    RagIndex,
    experiment_root,
    load_documents,
    load_embedding_profile,
)

EmbeddingFactory = Callable[[EmbeddingProfile], Embeddings]


class _RetrievalCaseBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_version: str
    cases: list[RetrievalCase]


def load_retrieval_cases(project_root: Path | None = None) -> list[RetrievalCase]:
    path = experiment_root(project_root) / "evaluation" / "retrieval-cases.json"
    return _RetrievalCaseBundle.model_validate_json(
        path.read_text(encoding="utf-8")
    ).cases


def compute_metrics(rankings: list[QueryRanking]) -> RetrievalMetrics:
    if not rankings:
        raise ValueError("至少需要一个检索评估案例")

    def recall_at(k: int) -> float:
        return sum(
            ranking.first_relevant_rank is not None and ranking.first_relevant_rank <= k
            for ranking in rankings
        ) / len(rankings)

    reciprocal = [
        1.0 / ranking.first_relevant_rank if ranking.first_relevant_rank else 0.0
        for ranking in rankings
    ]
    return RetrievalMetrics(
        query_count=len(rankings),
        recall_at_2=recall_at(2),
        recall_at_4=recall_at(4),
        recall_at_8=recall_at(8),
        mrr=fmean(reciprocal),
    )


def evaluate_profile(
    embedding_profile: EmbeddingProfile,
    retrieval_profile: RetrievalProfile,
    embeddings: Embeddings,
    *,
    project_root: Path | None = None,
) -> ProfileEvaluation:
    documents = load_documents(project_root)
    cases = load_retrieval_cases(project_root)
    index, elapsed = RagIndex.rebuild(documents, retrieval_profile, embeddings)
    rankings: list[QueryRanking] = []
    for case in cases:
        entries = index.rank_documents(case.query, limit=8)
        expected = set(case.expected_document_ids)
        first = next((entry.rank for entry in entries if entry.document_id in expected), None)
        rankings.append(
            QueryRanking(
                query_id=case.query_id,
                query=case.query,
                expected_document_ids=case.expected_document_ids,
                entries=entries,
                first_relevant_rank=first,
            )
        )
    return ProfileEvaluation(
        embedding_profile_id=embedding_profile.profile_id,
        embedding_profile_hash=embedding_profile.config_hash,
        retrieval_profile_id=retrieval_profile.profile_id,
        retrieval_profile_hash=retrieval_profile.config_hash,
        index_elapsed_ms=elapsed,
        chunk_count=len(index.chunks),
        rankings=rankings,
        metrics=compute_metrics(rankings),
    )


def default_embedding_factory(
    settings: LabSettings, *, local: bool
) -> EmbeddingFactory:
    if local:
        return lambda profile: LocalSentenceTransformerEmbeddings(settings, profile)
    return lambda profile: HashEmbeddings(profile)


def evaluate_profile_gate(
    settings: LabSettings,
    retrieval_profile: RetrievalProfile,
    *,
    project_root: Path | None = None,
    embedding_factory: EmbeddingFactory | None = None,
    requested_profile_id: str = "auto",
    local: bool = False,
) -> ProfileSelection:
    factory = embedding_factory or default_embedding_factory(settings, local=local)
    mini = load_embedding_profile("minilm-multilingual-v1", project_root)
    bge = load_embedding_profile("bge-small-zh-v1", project_root)
    evaluations: list[ProfileEvaluation] = []
    skipped: list[str] = []

    if requested_profile_id != "auto":
        profile = load_embedding_profile(requested_profile_id, project_root)
        evaluations.append(
            evaluate_profile(
                profile, retrieval_profile, factory(profile), project_root=project_root
            )
        )
        skipped = [item.profile_id for item in (mini, bge) if item.profile_id != profile.profile_id]
    else:
        mini_evaluation = evaluate_profile(
            mini, retrieval_profile, factory(mini), project_root=project_root
        )
        evaluations.append(mini_evaluation)
        if mini_evaluation.metrics.recall_at_4 < 5 / 6:
            evaluations.append(
                evaluate_profile(bge, retrieval_profile, factory(bge), project_root=project_root)
            )
        else:
            skipped.append(bge.profile_id)

    selected = sorted(
        evaluations,
        key=lambda item: (
            -item.metrics.recall_at_4,
            -item.metrics.mrr,
            item.index_elapsed_ms,
            item.embedding_profile_id,
        ),
    )[0]
    return ProfileSelection(
        executed_profile_ids=[item.embedding_profile_id for item in evaluations],
        skipped_profile_ids=skipped,
        gate_threshold=5 / 6,
        selected_profile_id=selected.embedding_profile_id,
        reason=(
            "仅在已执行 Profile 间按 Recall@4、MRR、索引耗时依次排序；"
            "未执行 Profile 不参与优劣结论。"
        ),
        evaluations=evaluations,
    )


def evaluate_retrieval_matrix(
    settings: LabSettings,
    profile_ids: list[str],
    *,
    project_root: Path | None = None,
    embedding_factory: EmbeddingFactory | None = None,
    local: bool = False,
) -> list[ProfileEvaluation]:
    factory = embedding_factory or default_embedding_factory(settings, local=local)
    matrix: list[ProfileEvaluation] = []
    for profile_id in profile_ids:
        embedding_profile = load_embedding_profile(profile_id, project_root)
        embeddings = factory(embedding_profile)
        for chunk_size, overlap in ((400, 60), (800, 120), (1200, 180)):
            for top_k in (2, 4, 8):
                retrieval = RetrievalProfile(
                    profile_id=f"chars-{chunk_size}-{overlap}-k{top_k}",
                    chunk_size=chunk_size,
                    overlap=overlap,
                    top_k=top_k,
                    profile_version="1",
                )
                matrix.append(
                    evaluate_profile(
                        embedding_profile,
                        retrieval,
                        embeddings,
                        project_root=project_root,
                    )
                )
    return matrix
