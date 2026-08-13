"""实验三 fixed/agent 公平执行与统一 finalizer。"""

import hashlib
import time
from pathlib import Path

from ai_workflow_lab.capabilities import CapabilityStatus
from ai_workflow_lab.config import LabSettings
from ai_workflow_lab.exp01.capability import find_latest_capability_report, freeze_native_method
from ai_workflow_lab.exp02.budget import ExecutionBudget
from ai_workflow_lab.exp02.execution import Experiment02Mode, run_fixed_research
from ai_workflow_lab.exp02.finalizer import (
    FixtureProposalBackend,
    OpenAIProposalBackend,
    finalize_proposal,
)
from ai_workflow_lab.exp02.tools import FixtureWebTools, TavilyWebTools, load_fixture
from ai_workflow_lab.run_recording import RunRecorder

from .agent import (
    AGENT_SYSTEM_PROMPT_VERSION,
    TrackedAgentTools,
    invoke_live_agent,
    run_fixture_agent,
)
from .domain import (
    AgentTermination,
    Experiment03Metrics,
    Experiment03Outcome,
    Experiment03Variant,
    ProposalRubric,
)


def experiment_control_hash() -> str:
    """比较双方共享的研究指令版本、预算和 finalizer 契约 hash。"""
    payload = (
        f"{AGENT_SYSTEM_PROMPT_VERSION}|ExecutionBudget-v1|"
        "finalize_proposal:build_final_prompt:v1|ProposalDraft:v1"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def score_proposal(source_count: int, recommendation_count: int) -> ProposalRubric:
    return ProposalRubric(
        evidence_traceability=5 if source_count > 0 else 0,
        evidence_specificity=min(5, source_count + 2) if source_count > 0 else 0,
        actionability=min(5, recommendation_count + 2) if recommendation_count > 0 else 0,
    )


def run_exp03(
    settings: LabSettings,
    recorder: RunRecorder,
    *,
    case_id: str,
    mode: Experiment02Mode,
    variant: Experiment03Variant,
    project_root: Path | None = None,
    comparison_id: str | None = None,
    pair_id: str | None = None,
) -> Experiment03Outcome:
    root = (project_root or Path.cwd()).resolve()
    fixture = load_fixture(root)
    if fixture.brief.case_id != case_id:
        raise ValueError(f"未知实验三 case：{case_id}")
    budget = ExecutionBudget()
    started = time.perf_counter()
    token_count: int | None = None
    termination: AgentTermination | None = None
    error: str | None = None

    if mode is Experiment02Mode.FIXTURE:
        tools = FixtureWebTools(fixture, recorder.artifacts)
        proposal_backend = FixtureProposalBackend()
        resolved_method = "fixture-json-schema"
    else:
        settings.require_live_credentials()
        settings.require_tavily_credentials()
        tools = TavilyWebTools(settings, recorder.artifacts)
        method = freeze_native_method(settings, project_root=root)
        report = find_latest_capability_report(settings, project_root=root)
        if report.tool_calling.status is not CapabilityStatus.SUPPORTED:
            raise ValueError(
                "agent variant requires supported tool_calling; "
                f"got {report.tool_calling.status.value}"
            )
        proposal_backend = OpenAIProposalBackend(settings, method)
        resolved_method = method.value

    if variant is Experiment03Variant.FIXED:
        pack = run_fixed_research(
            fixture.brief, tools=tools, budget=budget, recorder=recorder
        )
    else:
        tracked = TrackedAgentTools(
            brief=fixture.brief,
            tools=tools,
            budget=budget,
            recorder=recorder,
        )
        agent_result = (
            run_fixture_agent(tracked)
            if mode is Experiment02Mode.FIXTURE
            else invoke_live_agent(settings, tracked)
        )
        pack = agent_result.pack
        token_count = agent_result.token_count
        termination = agent_result.termination
        error = agent_result.error

    proposal = None
    status: str = (
        "partial"
        if variant is Experiment03Variant.AGENT
        and termination not in {None, AgentTermination.COMPLETED}
        else "succeeded"
    )
    if pack.sources:
        try:
            proposal = finalize_proposal(
                pack,
                backend=proposal_backend,
                budget=budget,
                recorder=recorder,
            )
        except Exception as exc:  # noqa: BLE001 - preserve partial research evidence.
            status = "partial"
            error = error or f"{type(exc).__name__}: {exc}"
    else:
        status = "partial" if variant is Experiment03Variant.AGENT else "failed"
        error = error or "没有可用于公共 finalizer 的真实来源"

    elapsed_ms = (time.perf_counter() - started) * 1000
    token_count = budget.total_tokens or token_count
    rubric = (
        score_proposal(len(pack.sources), len(proposal.recommendations))
        if proposal is not None
        else None
    )
    metrics = Experiment03Metrics(
        source_coverage=min(1.0, len(pack.sources) / max(1, len(fixture.pages))),
        proposal_rubric=rubric,
        model_calls=budget.model_calls,
        tool_calls=budget.tool_calls,
        token_count=token_count,
        elapsed_ms=elapsed_ms,
        failure_type=(
            None if status == "succeeded" else (termination.value if termination else error)
        ),
        diagnosability=5 if error is None or pack.tool_errors or termination is not None else 4,
    )
    outcome = Experiment03Outcome(
        status=status,  # type: ignore[arg-type]
        mode=mode.value,  # type: ignore[arg-type]
        variant=variant,
        research_pack=pack,
        proposal=proposal,
        budget=budget.snapshot(),
        metrics=metrics,
        termination=termination,
        error=error,
    )
    recorder.write_json("research-pack.json", pack)
    if proposal is not None:
        recorder.write_json("proposal.json", proposal)
        recorder.write_text("proposal.md", proposal.markdown)
    recorder.update_summary(
        {
            "case_id": case_id,
            "case_version": fixture.brief.case_version,
            "fixture_version": fixture.fixture_version,
            "experiment_status": status,
            "mode": mode.value,
            "variant": variant.value,
            "resolved_method": resolved_method,
            "control_hash": experiment_control_hash(),
            "comparison_id": comparison_id,
            "pair_id": pair_id,
            "budget": budget.snapshot(),
            "metrics": metrics,
            "termination": termination.value if termination else None,
        }
    )
    return outcome
