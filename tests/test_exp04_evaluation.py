from pathlib import Path

import pytest
from langchain_core.embeddings import Embeddings

from ai_workflow_lab.config import LabSettings
from ai_workflow_lab.exp04.domain import (
    EmbeddingProfile,
    ProfileEvaluation,
    QueryRanking,
    RankingEntry,
    RetrievalMetrics,
    RetrievalProfile,
)
from ai_workflow_lab.exp04.evaluation import compute_metrics, evaluate_profile_gate

PROJECT_ROOT = Path(__file__).parents[1]


class UnusedEmbedding(Embeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.0]


def test_metrics_count_rank_four_as_recall_four_and_quarter_mrr() -> None:
    rankings = [
        QueryRanking(
            query_id="q-1",
            query="question",
            expected_document_ids=["doc-right"],
            entries=[
                RankingEntry(
                    rank=index,
                    document_id=f"doc-{index}",
                    chunk_id=f"c-{index}",
                    score=1 / index,
                )
                for index in range(1, 4)
            ]
            + [RankingEntry(rank=4, document_id="doc-right", chunk_id="c-4", score=0.2)],
            first_relevant_rank=4,
        )
    ]

    metrics = compute_metrics(rankings)

    assert metrics.recall_at_2 == 0
    assert metrics.recall_at_4 == 1
    assert metrics.mrr == 0.25


def test_low_minilm_recall_executes_bge_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_evaluate(
        profile: EmbeddingProfile,
        retrieval: object,
        embeddings: object,
        **_: object,
    ) -> ProfileEvaluation:
        del retrieval, embeddings
        profile_id = profile.profile_id
        recall = 0.5 if profile_id == "minilm-multilingual-v1" else 1.0
        return ProfileEvaluation(
            embedding_profile_id=profile_id,
            embedding_profile_hash="a" * 64,
            retrieval_profile_id="test",
            retrieval_profile_hash="b" * 64,
            index_elapsed_ms=2 if recall == 0.5 else 3,
            chunk_count=6,
            rankings=[],
            metrics=RetrievalMetrics(
                query_count=6,
                recall_at_2=recall,
                recall_at_4=recall,
                recall_at_8=recall,
                mrr=recall,
            ),
        )

    monkeypatch.setattr("ai_workflow_lab.exp04.evaluation.evaluate_profile", fake_evaluate)
    retrieval = RetrievalProfile(
        profile_id="test", chunk_size=800, overlap=120, top_k=8, profile_version="1"
    )

    selection = evaluate_profile_gate(
        LabSettings(),
        retrieval,
        project_root=PROJECT_ROOT,
        embedding_factory=lambda _: UnusedEmbedding(),
    )

    assert selection.executed_profile_ids == ["minilm-multilingual-v1", "bge-small-zh-v1"]
    assert selection.selected_profile_id == "bge-small-zh-v1"
    assert selection.skipped_profile_ids == []


def test_high_minilm_recall_skips_bge_without_ranking_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_evaluate(
        profile: EmbeddingProfile,
        retrieval: object,
        embeddings: object,
        **_: object,
    ) -> ProfileEvaluation:
        del retrieval, embeddings
        assert profile.profile_id == "minilm-multilingual-v1"
        return ProfileEvaluation(
            embedding_profile_id=profile.profile_id,
            embedding_profile_hash="a" * 64,
            retrieval_profile_id="test",
            retrieval_profile_hash="b" * 64,
            index_elapsed_ms=1,
            chunk_count=6,
            rankings=[],
            metrics=RetrievalMetrics(
                query_count=6,
                recall_at_2=1,
                recall_at_4=1,
                recall_at_8=1,
                mrr=1,
            ),
        )

    monkeypatch.setattr("ai_workflow_lab.exp04.evaluation.evaluate_profile", fake_evaluate)
    retrieval = RetrievalProfile(
        profile_id="test", chunk_size=800, overlap=120, top_k=8, profile_version="1"
    )

    selection = evaluate_profile_gate(
        LabSettings(),
        retrieval,
        project_root=PROJECT_ROOT,
        embedding_factory=lambda _: UnusedEmbedding(),
    )

    assert selection.executed_profile_ids == ["minilm-multilingual-v1"]
    assert selection.skipped_profile_ids == ["bge-small-zh-v1"]
    assert selection.selected_profile_id == "minilm-multilingual-v1"
    assert "未执行 Profile 不参与" in selection.reason
