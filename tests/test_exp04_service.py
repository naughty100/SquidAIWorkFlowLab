import json
from pathlib import Path

from ai_workflow_lab.config import LabSettings
from ai_workflow_lab.exp04.domain import (
    DocumentChunk,
    EvidenceStatus,
    RagVariant,
    RetrievalProfile,
)
from ai_workflow_lab.exp04.indexing import chunk_documents, load_documents
from ai_workflow_lab.exp04.service import (
    run_exp04,
    run_rag_evaluation,
    validate_evidence,
)
from ai_workflow_lab.run_recording import RunRecorder

PROJECT_ROOT = Path(__file__).parents[1]


def make_run(tmp_path: Path, run_id: str) -> tuple[LabSettings, RunRecorder]:
    settings = LabSettings(lab_output_dir=tmp_path / "outputs")
    return settings, RunRecorder(
        settings, command="test", project_root=tmp_path, run_id=run_id
    )


def default_chunks() -> dict[str, DocumentChunk]:
    retrieval = RetrievalProfile(
        profile_id="chars-800-120-k4",
        chunk_size=800,
        overlap=120,
        top_k=4,
        profile_version="1",
    )
    return {
        chunk.chunk_id: chunk
        for chunk in chunk_documents(load_documents(PROJECT_ROOT), retrieval)
    }


def test_no_rag_refuses_but_full_context_is_structurally_supported(tmp_path: Path) -> None:
    settings, no_rag_run = make_run(tmp_path, "no-rag")
    no_rag = run_exp04(
        settings, no_rag_run, variant=RagVariant.NO_RAG, project_root=PROJECT_ROOT
    )
    settings, full_run = make_run(tmp_path, "full")
    full = run_exp04(
        settings, full_run, variant=RagVariant.FULL_CONTEXT, project_root=PROJECT_ROOT
    )

    assert no_rag.status is EvidenceStatus.INSUFFICIENT_EVIDENCE
    assert no_rag.proposal is None
    assert full.status is EvidenceStatus.SUPPORTED
    assert full.proposal is not None
    assert full.context_char_count > 0
    assert no_rag.generation_control_hash == full.generation_control_hash
    assert all(item.semantically_supported is None for item in full.manual_rubric)

    full.manual_rubric[0].semantically_supported = False
    assert full.automatic_evaluation.status is EvidenceStatus.SUPPORTED


def test_vector_evidence_excerpt_and_hash_are_verifiable(tmp_path: Path) -> None:
    settings, run = make_run(tmp_path, "vector")
    outcome = run_exp04(
        settings, run, variant=RagVariant.VECTOR, project_root=PROJECT_ROOT
    )

    assert outcome.status in {EvidenceStatus.SUPPORTED, EvidenceStatus.INSUFFICIENT_EVIDENCE}
    for source in outcome.evidence.sources:
        body = run.artifacts.read_text(source.artifact)
        assert source.supporting_excerpt in body
        assert source.content_hash == source.artifact.content_hash

    if outcome.evidence.sources:
        invalid = outcome.evidence.model_copy(deep=True)
        invalid.sources[0].supporting_excerpt = "不存在的伪造摘录"
        result = validate_evidence(invalid, default_chunks())
        assert result.status is EvidenceStatus.INSUFFICIENT_EVIDENCE

        forged_id = outcome.evidence.model_copy(deep=True)
        forged_id.sources[0].source_id = "src-aaaaaaaaaaaa"
        forged_id.findings[0].source_ids = ["src-aaaaaaaaaaaa"]
        result = validate_evidence(forged_id, default_chunks())
        assert result.status is EvidenceStatus.INSUFFICIENT_EVIDENCE


def test_nonempty_context_still_refuses_when_a_required_question_is_missing(
    tmp_path: Path,
) -> None:
    settings, run = make_run(tmp_path, "missing-question")
    outcome = run_exp04(
        settings, run, variant=RagVariant.FULL_CONTEXT, project_root=PROJECT_ROOT
    )
    incomplete = outcome.evidence.model_copy(deep=True)
    removed = incomplete.findings.pop()

    result = validate_evidence(incomplete, default_chunks())

    assert incomplete.sources
    assert result.status is EvidenceStatus.INSUFFICIENT_EVIDENCE
    assert removed.question_id in result.missing_question_ids


def test_rag_evaluation_summary_records_profile_and_retrieval_hashes(
    tmp_path: Path,
) -> None:
    settings, run = make_run(tmp_path, "evaluation-summary")

    report = run_rag_evaluation(settings, run, project_root=PROJECT_ROOT)
    summary = json.loads(run.summary_path.read_text(encoding="utf-8"))

    selected = report.selection.selected_profile_id
    assert len(summary["embedding_profile_hashes"][selected]) == 64
    assert len(summary["baseline_retrieval_profile_hash"]) == 64
