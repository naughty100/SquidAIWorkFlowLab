from pathlib import Path

import pytest

from ai_workflow_lab.exp04.domain import RetrievalProfile
from ai_workflow_lab.exp04.indexing import (
    HashEmbeddings,
    RagIndex,
    chunk_documents,
    load_documents,
    load_embedding_profile,
)

PROJECT_ROOT = Path(__file__).parents[1]


def test_embedding_and_retrieval_hashes_are_independent() -> None:
    embedding = load_embedding_profile("minilm-multilingual-v1", PROJECT_ROOT)
    first = RetrievalProfile(
        profile_id="test-k4", chunk_size=800, overlap=120, top_k=4, profile_version="1"
    )
    second = first.model_copy(update={"top_k": 8})

    assert len(embedding.config_hash) == 64
    assert first.config_hash != second.config_hash
    assert embedding.config_hash == embedding.model_copy().config_hash
    assert embedding.revision != "main"
    assert embedding.trust_remote_code is False


def test_retrieval_profile_rejects_invalid_overlap() -> None:
    with pytest.raises(ValueError, match="overlap"):
        RetrievalProfile(
            profile_id="bad", chunk_size=400, overlap=400, top_k=4, profile_version="1"
        )


def test_chunk_and_index_rebuild_are_deterministic() -> None:
    documents = load_documents(PROJECT_ROOT)
    retrieval = RetrievalProfile(
        profile_id="test", chunk_size=400, overlap=60, top_k=4, profile_version="1"
    )
    profile = load_embedding_profile("minilm-multilingual-v1", PROJECT_ROOT)

    first_chunks = chunk_documents(documents, retrieval)
    second_chunks = chunk_documents(documents, retrieval)
    first_index, _ = RagIndex.rebuild(documents, retrieval, HashEmbeddings(profile))
    second_index, _ = RagIndex.rebuild(documents, retrieval, HashEmbeddings(profile))

    assert [item.chunk_id for item in first_chunks] == [item.chunk_id for item in second_chunks]
    assert [item.model_dump() for item in first_index.chunks] == [
        item.model_dump() for item in second_index.chunks
    ]
    assert [item.document_id for item in documents] == sorted(
        item.document_id for item in documents
    )
