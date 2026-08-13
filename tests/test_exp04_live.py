import os
from pathlib import Path

import pytest

from ai_workflow_lab.config import LabSettings
from ai_workflow_lab.exp04.domain import RetrievalProfile
from ai_workflow_lab.exp04.evaluation import evaluate_profile_gate
from ai_workflow_lab.exp04.indexing import (
    LocalSentenceTransformerEmbeddings,
    load_embedding_profile,
    resolve_profile_cache,
)


@pytest.mark.rag_live
@pytest.mark.skipif(os.getenv("RUN_RAG_LIVE") != "1", reason="set RUN_RAG_LIVE=1 explicitly")
def test_pinned_local_embedding_revision_dimension_gate_and_cache(tmp_path: Path) -> None:
    settings = LabSettings(lab_cache_dir=tmp_path / "cache")
    project_root = Path(__file__).parents[1]
    mini = load_embedding_profile("minilm-multilingual-v1", project_root)
    bge = load_embedding_profile("bge-small-zh-v1", project_root)
    retrieval = RetrievalProfile(
        profile_id="rag-live-baseline",
        chunk_size=800,
        overlap=120,
        top_k=8,
        profile_version="1",
    )

    selection = evaluate_profile_gate(
        settings,
        retrieval,
        project_root=project_root,
        requested_profile_id="auto",
        local=True,
    )

    assert len(mini.revision) == len(bge.revision) == 40
    assert selection.executed_profile_ids[0] == mini.profile_id
    mini_recall = selection.evaluations[0].metrics.recall_at_4
    assert (bge.profile_id in selection.executed_profile_ids) is (mini_recall < 5 / 6)
    assert (bge.profile_id in selection.skipped_profile_ids) is (mini_recall >= 5 / 6)
    bge_embeddings = LocalSentenceTransformerEmbeddings(settings, bge)
    assert len(bge_embeddings.embed_query("验证中文检索维度")) == bge.expected_dimensions
    mini_cache = resolve_profile_cache(settings, mini)
    bge_cache = resolve_profile_cache(settings, bge)
    assert mini_cache != bge_cache
    assert any(mini_cache.rglob("*"))
    assert any(bge_cache.rglob("*"))
