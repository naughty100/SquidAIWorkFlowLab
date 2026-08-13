"""实验四三种上下文策略、证据规范化与 CLI 服务。"""

import hashlib
import json
import re
from pathlib import Path

from ai_workflow_lab.config import LabSettings
from ai_workflow_lab.exp02.budget import ExecutionBudget
from ai_workflow_lab.exp02.domain import (
    ResearchFinding,
    ResearchPack,
    SourceEvidence,
)
from ai_workflow_lab.exp02.finalizer import FixtureProposalBackend, finalize_proposal
from ai_workflow_lab.exp02.tools import load_fixture
from ai_workflow_lab.run_recording import RunRecorder

from .domain import (
    AutomaticEvidenceResult,
    DocumentChunk,
    EvidenceAnswer,
    EvidenceStatus,
    Experiment04Outcome,
    ManualEvidenceRubric,
    RagEvaluationReport,
    RagSourceEvidence,
    RagVariant,
    RetrievalCase,
    RetrievalProfile,
    SupportedFinding,
)
from .evaluation import (
    evaluate_profile_gate,
    evaluate_retrieval_matrix,
    load_retrieval_cases,
)
from .indexing import (
    HashEmbeddings,
    LocalSentenceTransformerEmbeddings,
    RagIndex,
    chunk_documents,
    load_documents,
    load_embedding_profile,
)

FULL_CONTEXT_MAX_CHARS = 50_000
RAG_GENERATION_PROMPT_VERSION = "exp04-context-answer-v1"
_TOKEN_PATTERN = re.compile(r"[a-z0-9_]+|[\u3400-\u9fff]", re.IGNORECASE)


def rag_generation_control_hash() -> str:
    """三种 variant 共用的答案契约与 finalizer 控制 hash。"""
    payload = {
        "answer_schema": EvidenceAnswer.model_json_schema(),
        "answer_prompt_version": RAG_GENERATION_PROMPT_VERSION,
        "finalizer": "finalize_proposal:FixtureProposalBackend:v1",
    }
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _source_from_chunk(chunk: DocumentChunk, recorder: RunRecorder) -> RagSourceEvidence:
    artifact = recorder.artifacts.put_text(
        chunk.content,
        category="local",
        media_type="text/markdown",
        metadata={
            "document_id": chunk.document_id,
            "document_version": chunk.document_version,
            "chunk_id": chunk.chunk_id,
        },
    )
    return RagSourceEvidence(
        source_id=f"src-{chunk.content_hash[:12]}",
        document_id=chunk.document_id,
        chunk_id=chunk.chunk_id,
        title=chunk.title,
        artifact=artifact,
        supporting_excerpt=chunk.content[:500],
        content_hash=chunk.content_hash,
        metadata={
            "document_version": chunk.document_version,
            "ordinal": str(chunk.ordinal),
            "source_type": "local_markdown",
        },
    )


def validate_evidence(
    answer: EvidenceAnswer,
    chunks_by_id: dict[str, DocumentChunk],
) -> AutomaticEvidenceResult:
    valid: set[str] = set()
    invalid: set[str] = set()
    for source in answer.sources:
        chunk = chunks_by_id.get(source.chunk_id)
        is_valid = (
            chunk is not None
            and source.document_id == chunk.document_id
            and source.source_id == f"src-{chunk.content_hash[:12]}"
            and source.supporting_excerpt in chunk.content
            and source.content_hash == chunk.content_hash
            and source.artifact.content_hash == chunk.content_hash
        )
        (valid if is_valid else invalid).add(source.source_id)
    covered = {
        finding.question_id
        for finding in answer.findings
        if finding.source_ids and all(source_id in valid for source_id in finding.source_ids)
    }
    required = set(answer.required_question_ids)
    missing = sorted(required - covered)
    status = (
        EvidenceStatus.SUPPORTED
        if valid and not invalid and not missing
        else EvidenceStatus.INSUFFICIENT_EVIDENCE
    )
    return AutomaticEvidenceResult(
        valid_source_ids=sorted(valid),
        invalid_source_ids=sorted(invalid),
        covered_question_ids=sorted(covered),
        missing_question_ids=missing,
        status=status,
    )


def _context_score(case: RetrievalCase, chunk: DocumentChunk) -> int:
    query_tokens = set(_TOKEN_PATTERN.findall(case.query.lower()))
    title_tokens = set(_TOKEN_PATTERN.findall(chunk.title.lower()))
    content_tokens = set(_TOKEN_PATTERN.findall(chunk.content.lower()))
    return 3 * len(query_tokens & title_tokens) + len(query_tokens & content_tokens)


def _select_context_chunk(
    case: RetrievalCase, chunks: list[DocumentChunk]
) -> DocumentChunk | None:
    if not chunks:
        return None
    return sorted(
        chunks,
        key=lambda chunk: (
            -_context_score(case, chunk),
            chunk.document_id,
            chunk.ordinal,
            chunk.chunk_id,
        ),
    )[0]


def _build_answer(
    context_by_question: dict[str, list[DocumentChunk]],
    recorder: RunRecorder,
    *,
    project_root: Path,
) -> tuple[EvidenceAnswer, dict[str, DocumentChunk]]:
    cases = load_retrieval_cases(project_root)
    sources_by_chunk: dict[str, RagSourceEvidence] = {}
    findings: list[SupportedFinding] = []
    all_chunks: dict[str, DocumentChunk] = {}
    for chunks in context_by_question.values():
        all_chunks.update({chunk.chunk_id: chunk for chunk in chunks})
    for case in cases:
        candidate = _select_context_chunk(
            case, context_by_question.get(case.required_question_id, [])
        )
        if candidate is None:
            continue
        source = sources_by_chunk.get(candidate.chunk_id)
        if source is None:
            source = _source_from_chunk(candidate, recorder)
            sources_by_chunk[candidate.chunk_id] = source
        findings.append(
            SupportedFinding(
                question_id=case.required_question_id,
                claim=source.supporting_excerpt[:260],
                source_ids=[source.source_id],
            )
        )
    required = [case.required_question_id for case in cases]
    missing = sorted(set(required) - {finding.question_id for finding in findings})
    sources = list(sources_by_chunk.values())
    answer = EvidenceAnswer(
        status=(
            EvidenceStatus.SUPPORTED
            if sources and not missing
            else EvidenceStatus.INSUFFICIENT_EVIDENCE
        ),
        required_question_ids=required,
        sources=sources,
        findings=findings,
        missing_question_ids=missing,
    )
    return answer, all_chunks


def _to_research_pack(answer: EvidenceAnswer, project_root: Path) -> ResearchPack:
    fixture = load_fixture(project_root)
    sources = [
        SourceEvidence(
            source_id=source.source_id,
            title=source.title,
            url=f"https://local.invalid/{source.document_id}/{source.chunk_id}",
            artifact=source.artifact,
            excerpt=source.supporting_excerpt,
        )
        for source in answer.sources
    ]
    return ResearchPack(
        brief=fixture.brief,
        queries=[case.query for case in load_retrieval_cases(project_root)],
        sources=sources,
        findings=[
            ResearchFinding(claim=finding.claim, source_ids=finding.source_ids)
            for finding in answer.findings
        ],
    )


def run_exp04(
    settings: LabSettings,
    recorder: RunRecorder,
    *,
    variant: RagVariant,
    embedding_profile_id: str = "minilm-multilingual-v1",
    retrieval_profile: RetrievalProfile | None = None,
    local_embeddings: bool = False,
    project_root: Path | None = None,
) -> Experiment04Outcome:
    root = (project_root or Path.cwd()).resolve()
    embedding_profile = load_embedding_profile(embedding_profile_id, root)
    retrieval = retrieval_profile or RetrievalProfile(
        profile_id="chars-800-120-k4",
        chunk_size=800,
        overlap=120,
        top_k=4,
        profile_version="1",
    )
    documents = load_documents(root)
    chunks = chunk_documents(documents, retrieval)
    cases = load_retrieval_cases(root)
    context_char_count = 0

    if variant is RagVariant.NO_RAG:
        context_by_question: dict[str, list[DocumentChunk]] = {
            case.required_question_id: [] for case in cases
        }
    elif variant is RagVariant.FULL_CONTEXT:
        context_char_count = sum(len(document.content) for document in documents)
        if context_char_count > FULL_CONTEXT_MAX_CHARS:
            raise ValueError(
                f"full-context 超过长度上限：{context_char_count}>{FULL_CONTEXT_MAX_CHARS}"
            )
        context_by_question = {
            case.required_question_id: list(chunks) for case in cases
        }
    else:
        embeddings = (
            LocalSentenceTransformerEmbeddings(settings, embedding_profile)
            if local_embeddings
            else HashEmbeddings(embedding_profile)
        )
        index, _ = RagIndex.rebuild(documents, retrieval, embeddings)
        context_by_question = {
            case.required_question_id: index.retrieve_chunks(
                case.query, top_k=retrieval.top_k
            )
            for case in cases
        }
        deduplicated = {
            chunk.chunk_id: chunk
            for selected in context_by_question.values()
            for chunk in selected
        }
        context_char_count = sum(len(chunk.content) for chunk in deduplicated.values())

    answer, known_chunks = _build_answer(
        context_by_question, recorder, project_root=root
    )
    automatic = validate_evidence(answer, known_chunks)
    answer.status = automatic.status
    answer.missing_question_ids = automatic.missing_question_ids
    proposal = None
    if automatic.status is EvidenceStatus.SUPPORTED:
        pack = _to_research_pack(answer, root)
        proposal = finalize_proposal(
            pack,
            backend=FixtureProposalBackend(),
            budget=ExecutionBudget(),
            recorder=recorder,
        )
        recorder.write_json("research-pack.json", pack)
        recorder.write_json("proposal.json", proposal)
        recorder.write_text("proposal.md", proposal.markdown)
    manual = [
        ManualEvidenceRubric(question_id=question_id)
        for question_id in answer.required_question_ids
    ]
    outcome = Experiment04Outcome(
        status=automatic.status,
        variant=variant,
        embedding_profile_hash=embedding_profile.config_hash,
        retrieval_profile_hash=retrieval.config_hash,
        generation_control_hash=rag_generation_control_hash(),
        context_char_count=context_char_count,
        source_count=len(answer.sources),
        token_count=None,
        evidence=answer,
        automatic_evaluation=automatic,
        manual_rubric=manual,
        proposal=proposal,
    )
    recorder.write_json("evidence.json", answer)
    recorder.write_json("automatic-evaluation.json", automatic)
    recorder.write_json("manual-rubric.json", manual)
    recorder.update_summary(
        {
            "experiment": "exp04",
            "variant": variant.value,
            "context_strategy": variant.value,
            "embedding_profile_id": embedding_profile.profile_id,
            "embedding_profile_hash": embedding_profile.config_hash,
            "retrieval_profile_hash": retrieval.config_hash,
            "generation_control_hash": rag_generation_control_hash(),
            "source_count": len(answer.sources),
            "token_count": None,
            "evidence_status": automatic.status.value,
            "context_char_count": context_char_count,
        }
    )
    return outcome


def run_rag_evaluation(
    settings: LabSettings,
    recorder: RunRecorder,
    *,
    embedding_profile_id: str = "auto",
    local_embeddings: bool = False,
    project_root: Path | None = None,
) -> RagEvaluationReport:
    root = (project_root or Path.cwd()).resolve()
    baseline = RetrievalProfile(
        profile_id="chars-800-120-k8",
        chunk_size=800,
        overlap=120,
        top_k=8,
        profile_version="1",
    )
    selection = evaluate_profile_gate(
        settings,
        baseline,
        project_root=root,
        requested_profile_id=embedding_profile_id,
        local=local_embeddings,
    )
    matrix = evaluate_retrieval_matrix(
        settings,
        selection.executed_profile_ids,
        project_root=root,
        local=local_embeddings,
    )
    report = RagEvaluationReport(selection=selection, matrix=matrix)
    embedding_hashes = {
        evaluation.embedding_profile_id: evaluation.embedding_profile_hash
        for evaluation in selection.evaluations
    }
    recorder.write_json("rag-evaluation.json", report)
    recorder.update_summary(
        {
            "experiment": "exp04-rag-evaluate",
            "requested_embedding_profile": embedding_profile_id,
            "local_embeddings": local_embeddings,
            "selected_profile_id": selection.selected_profile_id,
            "executed_profile_ids": selection.executed_profile_ids,
            "embedding_profile_hashes": embedding_hashes,
            "baseline_retrieval_profile_hash": baseline.config_hash,
            "skipped_profile_ids": selection.skipped_profile_ids,
            "matrix_runs": len(matrix),
        }
    )
    return report
