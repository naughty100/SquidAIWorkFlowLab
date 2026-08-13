"""版本化文档、embedding profile 与确定性 InMemoryVectorStore。"""

import hashlib
import importlib
import math
import re
import time
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Protocol, cast

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore
from pydantic import BaseModel, ConfigDict

from ai_workflow_lab.artifacts import normalize_text, text_hash
from ai_workflow_lab.config import LabSettings

from .domain import (
    DocumentChunk,
    EmbeddingProfile,
    LocalDocument,
    RankingEntry,
    RetrievalProfile,
)

_TOKEN_PATTERN = re.compile(r"[a-z0-9_]+|[\u3400-\u9fff]", re.IGNORECASE)


class _ManifestItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    version: str
    title: str
    path: str


class _DocumentManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: str
    dataset_version: str
    documents: list[_ManifestItem]


class _EncodedArray(Protocol):
    def tolist(self) -> list[list[float]]: ...


class _SentenceTransformerModel(Protocol):
    max_seq_length: int

    def get_sentence_embedding_dimension(self) -> int | None: ...

    def encode(self, sentences: list[str], **kwargs: object) -> _EncodedArray: ...


def experiment_root(project_root: Path | None = None) -> Path:
    root = (project_root or Path.cwd()).resolve()
    return root / "experiments" / "04-rag-evaluation"


def load_embedding_profile(
    profile_id: str, project_root: Path | None = None
) -> EmbeddingProfile:
    path = experiment_root(project_root) / "profiles" / f"{profile_id}.json"
    if not path.is_file():
        raise ValueError(f"未知 embedding profile：{profile_id}")
    return EmbeddingProfile.model_validate_json(path.read_text(encoding="utf-8"))


def load_retrieval_profile(
    profile_id: str, project_root: Path | None = None
) -> RetrievalProfile:
    path = experiment_root(project_root) / "retrieval-profiles" / f"{profile_id}.json"
    if not path.is_file():
        raise ValueError(f"未知 retrieval profile：{profile_id}")
    return RetrievalProfile.model_validate_json(path.read_text(encoding="utf-8"))


def resolve_profile_cache(settings: LabSettings, profile: EmbeddingProfile) -> Path:
    root = settings.lab_cache_dir
    if not root.is_absolute():
        root = Path.cwd() / root
    root = root.resolve()
    target = (root / profile.cache_dir).resolve()
    if not target.is_relative_to(root):
        raise ValueError("embedding cache path 超出 LAB_CACHE_DIR")
    target.mkdir(parents=True, exist_ok=True)
    return target


def load_documents(project_root: Path | None = None) -> list[LocalDocument]:
    root = experiment_root(project_root)
    manifest_path = root / "documents" / "manifest.json"
    manifest = _DocumentManifest.model_validate_json(
        manifest_path.read_text(encoding="utf-8")
    )
    documents: list[LocalDocument] = []
    for item in manifest.documents:
        document_id = item.document_id
        relative = item.path
        path = (root / "documents" / relative).resolve()
        document_root = (root / "documents").resolve()
        if not path.is_relative_to(document_root) or not path.is_file():
            raise ValueError(f"RAG 文档路径无效：{relative}")
        content = normalize_text(path.read_text(encoding="utf-8")).strip() + "\n"
        documents.append(
            LocalDocument(
                document_id=document_id,
                version=item.version,
                title=item.title,
                path=relative,
                content=content,
                content_hash=text_hash(content),
            )
        )
    return sorted(documents, key=lambda document: document.document_id)


def chunk_documents(
    documents: list[LocalDocument], profile: RetrievalProfile
) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    step = profile.chunk_size - profile.overlap
    for document in sorted(documents, key=lambda item: item.document_id):
        start = 0
        ordinal = 0
        while start < len(document.content):
            end = min(len(document.content), start + profile.chunk_size)
            content = document.content[start:end]
            seed = (
                f"{document.document_id}|{document.version}|{ordinal}|{start}|{end}|"
                f"{text_hash(content)}"
            )
            chunk_id = "chunk-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
            chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=document.document_id,
                    document_version=document.version,
                    title=document.title,
                    ordinal=ordinal,
                    start=start,
                    end=end,
                    content=content,
                    content_hash=text_hash(content),
                )
            )
            if end >= len(document.content):
                break
            start += step
            ordinal += 1
    return chunks


class HashEmbeddings(Embeddings):
    """完全离线、确定性的测试 embedding，不代表真实模型质量。"""

    def __init__(self, profile: EmbeddingProfile) -> None:
        self.profile = profile

    def _embed(self, value: str, *, query: bool) -> list[float]:
        prefix = self.profile.query_prefix if query else self.profile.document_prefix
        text = normalize_text(prefix + value).lower()
        tokens = _TOKEN_PATTERN.findall(text)
        vector = [0.0] * self.profile.expected_dimensions
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % len(vector)
            vector[index] += -1.0 if digest[4] & 1 else 1.0
        norm = math.sqrt(sum(component * component for component in vector))
        if norm and self.profile.normalize:
            vector = [component / norm for component in vector]
        return vector

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text, query=False) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text, query=True)


class LocalSentenceTransformerEmbeddings(Embeddings):
    """固定 revision、CPU/float32 且禁用 remote code 的本地 backend。"""

    def __init__(self, settings: LabSettings, profile: EmbeddingProfile) -> None:
        try:
            sentence_transformers = importlib.import_module("sentence_transformers")
            torch = importlib.import_module("torch")
        except ImportError as exc:
            raise RuntimeError("请先安装 RAG extra：uv sync --extra rag") from exc
        cache = resolve_profile_cache(settings, profile)
        self.profile = profile
        model_factory = cast(
            Callable[..., _SentenceTransformerModel],
            sentence_transformers.SentenceTransformer,
        )
        self.model = model_factory(
            profile.model_name,
            revision=profile.revision,
            device=profile.device,
            cache_folder=str(cache),
            trust_remote_code=False,
            model_kwargs={"torch_dtype": getattr(torch, profile.dtype)},
        )
        dimensions = self.model.get_sentence_embedding_dimension()
        if dimensions != profile.expected_dimensions:
            raise ValueError(
                f"embedding dimensions 不匹配：profile={profile.expected_dimensions}, "
                f"actual={dimensions}"
            )
        actual_length = int(self.model.max_seq_length)
        if actual_length != profile.max_sequence_length:
            raise ValueError(
                f"max sequence length 不匹配：profile={profile.max_sequence_length}, "
                f"actual={actual_length}"
            )

    def _encode(self, texts: list[str], *, query: bool) -> list[list[float]]:
        prefix = self.profile.query_prefix if query else self.profile.document_prefix
        encoded = self.model.encode(
            [prefix + text for text in texts],
            batch_size=self.profile.batch_size,
            normalize_embeddings=self.profile.normalize,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return encoded.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._encode(texts, query=False)

    def embed_query(self, text: str) -> list[float]:
        return self._encode([text], query=True)[0]


class RagIndex:
    """每次从 chunks 确定性重建的 LangChain InMemoryVectorStore。"""

    def __init__(self, embeddings: Embeddings, chunks: list[DocumentChunk]) -> None:
        self.chunks = list(chunks)
        self.by_id = {chunk.chunk_id: chunk for chunk in chunks}
        self.store = InMemoryVectorStore(embeddings)
        documents = [
            Document(
                page_content=chunk.content,
                metadata={
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "document_version": chunk.document_version,
                    "title": chunk.title,
                    "content_hash": chunk.content_hash,
                    "ordinal": chunk.ordinal,
                },
            )
            for chunk in chunks
        ]
        self.store.add_documents(documents, ids=[chunk.chunk_id for chunk in chunks])

    @classmethod
    def rebuild(
        cls,
        documents: list[LocalDocument],
        retrieval_profile: RetrievalProfile,
        embeddings: Embeddings,
    ) -> tuple["RagIndex", float]:
        started = time.perf_counter()
        chunks = chunk_documents(documents, retrieval_profile)
        index = cls(embeddings, chunks)
        return index, (time.perf_counter() - started) * 1000

    def rank_documents(self, query: str, *, limit: int = 8) -> list[RankingEntry]:
        if not self.chunks:
            return []
        results = self.store.similarity_search_with_score(query, k=len(self.chunks))
        best: dict[str, tuple[Document, float]] = {}
        for document, score in results:
            document_id = str(document.metadata["document_id"])
            if document_id not in best or score > best[document_id][1]:
                best[document_id] = (document, float(score))
        ordered = sorted(best.values(), key=lambda pair: (-pair[1], str(pair[0].metadata)))
        return [
            RankingEntry(
                rank=rank,
                document_id=str(document.metadata["document_id"]),
                chunk_id=str(document.metadata["chunk_id"]),
                score=score,
            )
            for rank, (document, score) in enumerate(ordered[:limit], start=1)
        ]

    def retrieve_chunks(self, query: str, *, top_k: int) -> list[DocumentChunk]:
        results = self.store.similarity_search_with_score(query, k=min(top_k, len(self.chunks)))
        return [self.by_id[str(document.metadata["chunk_id"])] for document, _ in results]


def group_chunks(chunks: list[DocumentChunk]) -> dict[str, list[DocumentChunk]]:
    grouped: defaultdict[str, list[DocumentChunk]] = defaultdict(list)
    for chunk in chunks:
        grouped[chunk.document_id].append(chunk)
    return {key: sorted(value, key=lambda item: item.ordinal) for key, value in grouped.items()}
