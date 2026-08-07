"""实验二的模式冻结、路径编排与产物保存。"""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from ai_workflow_lab.capabilities import CapabilityStatus
from ai_workflow_lab.config import LabSettings
from ai_workflow_lab.exp01.capability import find_latest_capability_report, freeze_native_method
from ai_workflow_lab.exp02.budget import ExecutionBudget
from ai_workflow_lab.exp02.domain import ProposalBundle, ResearchPack
from ai_workflow_lab.exp02.execution import (
    Experiment02Mode,
    Experiment02Variant,
    FixtureResearchModel,
    OpenAIToolResearchModel,
    run_controlled_research,
    run_fixed_research,
)
from ai_workflow_lab.exp02.finalizer import (
    FixtureProposalBackend,
    OpenAIProposalBackend,
    finalize_proposal,
)
from ai_workflow_lab.exp02.tools import FixtureWebTools, TavilyWebTools, load_fixture
from ai_workflow_lab.run_recording import RunRecorder


class Experiment02Outcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    mode: Experiment02Mode
    variant: Experiment02Variant
    research_pack: ResearchPack | None = None
    proposal: ProposalBundle | None = None
    budget: dict[str, int | float] = Field(default_factory=dict)
    errors: list[dict[str, object]] = Field(default_factory=lambda: list[dict[str, object]]())


def run_exp02(
    settings: LabSettings,
    recorder: RunRecorder,
    *,
    case_id: str,
    mode: Experiment02Mode,
    variant: Experiment02Variant,
    project_root: Path | None = None,
) -> Experiment02Outcome:
    """在 run 开始时固定工具模式，然后执行研究和公共 finalizer。"""
    root = (project_root or Path.cwd()).resolve()
    fixture = load_fixture(root)
    if fixture.brief.case_id != case_id:
        raise ValueError(f"未知实验二 case：{case_id}")
    budget = ExecutionBudget()

    if mode is Experiment02Mode.FIXTURE:
        tools = FixtureWebTools(fixture, recorder.artifacts)
        proposal_backend = FixtureProposalBackend()
        research_model = FixtureResearchModel()
        resolved_method = "fixture-json-schema"
    else:
        settings.require_live_credentials()
        settings.require_tavily_credentials()
        tools = TavilyWebTools(settings, recorder.artifacts)
        method = freeze_native_method(settings, project_root=root)
        proposal_backend = OpenAIProposalBackend(settings, method)
        research_model = OpenAIToolResearchModel(settings)
        resolved_method = method.value
        if variant is Experiment02Variant.TOOL_CALL:
            report = find_latest_capability_report(settings, project_root=root)
            if report.tool_calling.status is not CapabilityStatus.SUPPORTED:
                raise ValueError(
                    "tool-call variant requires supported tool_calling; "
                    f"got {report.tool_calling.status.value}"
                )

    if variant is Experiment02Variant.FIXED:
        pack = run_fixed_research(
            fixture.brief,
            tools=tools,
            budget=budget,
            recorder=recorder,
        )
    else:
        pack = run_controlled_research(
            fixture.brief,
            model=research_model,
            tools=tools,
            budget=budget,
            recorder=recorder,
        )
    proposal = finalize_proposal(
        pack,
        backend=proposal_backend,
        budget=budget,
        recorder=recorder,
    )
    outcome = Experiment02Outcome(
        status="succeeded",
        mode=mode,
        variant=variant,
        research_pack=pack,
        proposal=proposal,
        budget=budget.snapshot(),
    )
    recorder.write_json("research-pack.json", pack)
    recorder.write_json("proposal.json", proposal)
    recorder.write_text("proposal.md", proposal.markdown)
    recorder.update_summary(
        {
            "case_id": case_id,
            "case_version": fixture.brief.case_version,
            "experiment_status": outcome.status,
            "mode": mode.value,
            "variant": variant.value,
            "resolved_method": resolved_method,
            "budget": outcome.budget,
            "source_count": len(pack.sources),
            "tool_error_count": len(pack.tool_errors),
        }
    )
    return outcome
