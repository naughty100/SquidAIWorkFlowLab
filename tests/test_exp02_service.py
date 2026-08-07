import json
from pathlib import Path

import pytest

from ai_workflow_lab.config import LabSettings
from ai_workflow_lab.exp02.budget import ExecutionBudget
from ai_workflow_lab.exp02.domain import ProposalDraft, ProposalItem, ResearchPack
from ai_workflow_lab.exp02.execution import Experiment02Mode, Experiment02Variant
from ai_workflow_lab.exp02.finalizer import ProposalBackend, finalize_proposal
from ai_workflow_lab.exp02.service import Experiment02Outcome, run_exp02
from ai_workflow_lab.run_recording import RunRecorder


class InvalidCitationBackend(ProposalBackend):
    def invoke(self, prompt: str, pack: ResearchPack) -> ProposalDraft:
        del prompt, pack
        return ProposalDraft(
            title="invalid",
            summary="invalid",
            recommendations=[
                ProposalItem(title="bad", rationale="bad", source_ids=["src-000000000000"])
            ],
        )


def make_run(tmp_path: Path, run_id: str) -> tuple[LabSettings, RunRecorder]:
    settings = LabSettings(lab_output_dir=tmp_path / "outputs")
    recorder = RunRecorder(settings, command="test", project_root=tmp_path, run_id=run_id)
    return settings, recorder


def test_both_fixture_variants_share_pack_and_finalizer_schema(tmp_path: Path) -> None:
    outcomes: list[Experiment02Outcome] = []
    for variant in Experiment02Variant:
        settings, recorder = make_run(tmp_path, variant.value)
        outcome = run_exp02(
            settings,
            recorder,
            case_id="career-ai-v1",
            mode=Experiment02Mode.FIXTURE,
            variant=variant,
            project_root=Path(__file__).parents[1],
        )
        recorder.finish("succeeded")
        outcomes.append(outcome)

    assert all(outcome.status == "succeeded" for outcome in outcomes)
    fixed_pack = outcomes[0].research_pack
    tool_pack = outcomes[1].research_pack
    fixed_proposal = outcomes[0].proposal
    tool_proposal = outcomes[1].proposal
    assert fixed_pack is not None and tool_pack is not None
    assert fixed_proposal is not None and tool_proposal is not None
    assert [source.url for source in fixed_pack.sources] == [
        source.url for source in tool_pack.sources
    ]
    assert fixed_proposal.title == tool_proposal.title


def test_web_body_is_only_in_artifact_and_excerpt_comes_from_it(tmp_path: Path) -> None:
    settings, recorder = make_run(tmp_path, "trace-safe")
    outcome = run_exp02(
        settings,
        recorder,
        case_id="career-ai-v1",
        mode=Experiment02Mode.FIXTURE,
        variant=Experiment02Variant.TOOL_CALL,
        project_root=Path(__file__).parents[1],
    )
    recorder.finish("succeeded")
    assert outcome.research_pack is not None

    events = recorder.events_path.read_text(encoding="utf-8")
    assert "WEB_ARTIFACT_ONLY_TAIL_MARKER" not in events
    first = outcome.research_pack.sources[0]
    body = recorder.artifacts.read_text(first.artifact)
    assert "WEB_ARTIFACT_ONLY_TAIL_MARKER" in body
    assert first.excerpt in body
    assert first.artifact.artifact_ref.startswith("artifacts/web/")

    tool_events = [
        json.loads(line)
        for line in events.splitlines()
        if json.loads(line)["type"] == "exp02.tool.result"
    ]
    encoded = json.dumps(tool_events, ensure_ascii=False)
    assert '"artifact_ref"' in encoded
    assert '"raw_content"' not in encoded


def test_finalizer_rejects_unknown_evidence_ids(tmp_path: Path) -> None:
    settings, recorder = make_run(tmp_path, "bad-citation")
    outcome = run_exp02(
        settings,
        recorder,
        case_id="career-ai-v1",
        mode=Experiment02Mode.FIXTURE,
        variant=Experiment02Variant.FIXED,
        project_root=Path(__file__).parents[1],
    )
    assert outcome.research_pack is not None

    with pytest.raises(ValueError, match="未知来源"):
        finalize_proposal(
            outcome.research_pack,
            backend=InvalidCitationBackend(),
            budget=ExecutionBudget(),
            recorder=recorder,
        )
