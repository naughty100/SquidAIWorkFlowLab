"""实验三的配对运行、扩展门禁和分级结论。"""

from collections import Counter
from pathlib import Path
from statistics import fmean
from uuid import uuid4

from ai_workflow_lab.config import LabSettings
from ai_workflow_lab.exp02.execution import Experiment02Mode
from ai_workflow_lab.exp02.tools import load_fixture
from ai_workflow_lab.run_recording import RunRecorder

from .domain import (
    Experiment03Comparison,
    Experiment03Outcome,
    Experiment03Variant,
    PairedRun,
    VariantAggregate,
)
from .service import experiment_control_hash, run_exp03


def _mean_optional(values: list[int | float | None]) -> float | None:
    known = [float(value) for value in values if value is not None]
    return fmean(known) if known else None


def _aggregate(
    variant: Experiment03Variant, outcomes: list[Experiment03Outcome]
) -> VariantAggregate:
    metrics = [outcome.metrics for outcome in outcomes]
    failures = Counter(
        metric.failure_type for metric in metrics if metric.failure_type is not None
    )
    return VariantAggregate(
        variant=variant,
        runs=len(outcomes),
        success_rate=(
            sum(outcome.status == "succeeded" for outcome in outcomes) / len(outcomes)
            if outcomes
            else 0.0
        ),
        mean_source_coverage=fmean(m.source_coverage for m in metrics) if metrics else 0.0,
        mean_proposal_rubric=_mean_optional(
            [m.proposal_rubric.total if m.proposal_rubric else None for m in metrics]
        ),
        mean_model_calls=fmean(m.model_calls for m in metrics) if metrics else 0.0,
        mean_tool_calls=fmean(m.tool_calls for m in metrics) if metrics else 0.0,
        mean_token_count=_mean_optional([m.token_count for m in metrics]),
        mean_elapsed_ms=fmean(m.elapsed_ms for m in metrics) if metrics else 0.0,
        failure_types=dict(failures),
        mean_diagnosability=fmean(m.diagnosability for m in metrics) if metrics else 0.0,
    )


def _relative_difference(fixed: float, agent: float) -> float:
    denominator = abs(fixed)
    if denominator == 0:
        return 0.0 if agent == 0 else 1.0
    return abs(agent - fixed) / denominator


def run_comparison(
    settings: LabSettings,
    recorder: RunRecorder,
    *,
    case_id: str,
    mode: Experiment02Mode,
    runs: int = 3,
    project_root: Path | None = None,
) -> Experiment03Comparison:
    if runs < 1:
        raise ValueError("runs 必须至少为 1")
    root = (project_root or Path.cwd()).resolve()
    fixture = load_fixture(root)
    comparison_id = uuid4().hex
    fixed_outcomes: list[Experiment03Outcome] = []
    agent_outcomes: list[Experiment03Outcome] = []
    pairs: list[PairedRun] = []

    for index in range(1, runs + 1):
        pair_id = f"{comparison_id}-pair-{index:02d}"
        fixed_recorder = RunRecorder(
            settings,
            command=f"compare exp03 fixed pair {index}",
            project_root=root,
        )
        agent_recorder = RunRecorder(
            settings,
            command=f"compare exp03 agent pair {index}",
            project_root=root,
        )
        try:
            fixed = run_exp03(
                settings,
                fixed_recorder,
                case_id=case_id,
                mode=mode,
                variant=Experiment03Variant.FIXED,
                project_root=root,
                comparison_id=comparison_id,
                pair_id=pair_id,
            )
            fixed_recorder.finish("succeeded" if fixed.status == "succeeded" else "failed")
            agent = run_exp03(
                settings,
                agent_recorder,
                case_id=case_id,
                mode=mode,
                variant=Experiment03Variant.AGENT,
                project_root=root,
                comparison_id=comparison_id,
                pair_id=pair_id,
            )
            agent_recorder.finish("succeeded" if agent.status == "succeeded" else "failed")
        except Exception:
            fixed_recorder.finish("failed")
            agent_recorder.finish("failed")
            raise
        fixed_outcomes.append(fixed)
        agent_outcomes.append(agent)
        pairs.append(
            PairedRun(
                pair_id=pair_id,
                fixed_run_id=fixed_recorder.run_id,
                agent_run_id=agent_recorder.run_id,
                fixed=fixed.metrics,
                agent=agent.metrics,
            )
        )

    fixed_aggregate = _aggregate(Experiment03Variant.FIXED, fixed_outcomes)
    agent_aggregate = _aggregate(Experiment03Variant.AGENT, agent_outcomes)
    differences = {
        "source_coverage": _relative_difference(
            fixed_aggregate.mean_source_coverage, agent_aggregate.mean_source_coverage
        ),
        "model_calls": _relative_difference(
            fixed_aggregate.mean_model_calls, agent_aggregate.mean_model_calls
        ),
        "tool_calls": _relative_difference(
            fixed_aggregate.mean_tool_calls, agent_aggregate.mean_tool_calls
        ),
        "elapsed_ms": _relative_difference(
            fixed_aggregate.mean_elapsed_ms, agent_aggregate.mean_elapsed_ms
        ),
    }
    if (
        fixed_aggregate.mean_token_count is not None
        and agent_aggregate.mean_token_count is not None
    ):
        differences["token_count"] = _relative_difference(
            fixed_aggregate.mean_token_count, agent_aggregate.mean_token_count
        )
    rubric_difference = abs(
        (agent_aggregate.mean_proposal_rubric or 0)
        - (fixed_aggregate.mean_proposal_rubric or 0)
    )
    differences["proposal_rubric_points"] = rubric_difference
    extension_triggered = any(
        value >= 0.20
        for key, value in differences.items()
        if key != "proposal_rubric_points"
    ) or rubric_difference >= 1.0

    if runs < 3:
        conclusion_status = "insufficient_sample"
    elif extension_triggered and runs < 10:
        conclusion_status = "extension_required"
    elif runs < 10:
        conclusion_status = "insufficient_sample"
    else:
        conclusion_status = "directional"
    directional = None
    if conclusion_status == "directional":
        fixed_score = fixed_aggregate.mean_proposal_rubric or 0
        agent_score = agent_aggregate.mean_proposal_rubric or 0
        if agent_score > fixed_score:
            directional = "Agent 最终质量方向性更高；仍需结合研究覆盖与成本判断。"
        elif fixed_score > agent_score:
            directional = "固定流程最终质量方向性更高；自主决策未抵消其额外复杂度。"
        else:
            directional = "最终质量接近；应优先比较来源覆盖、成本和可诊断性。"

    report = Experiment03Comparison(
        comparison_id=comparison_id,
        case_id=case_id,
        case_version=fixture.brief.case_version,
        fixture_version=fixture.fixture_version,
        control_hash=experiment_control_hash(),
        model=settings.ai_model,
        mode=mode.value,  # type: ignore[arg-type]
        requested_runs=runs,
        completed_pairs=len(pairs),
        smoke_comparison=runs == 3,
        paired_runs=pairs,
        fixed=fixed_aggregate,
        agent=agent_aggregate,
        threshold_differences=differences,
        extension_triggered=extension_triggered,
        minimum_required_runs=10 if extension_triggered else 3,
        conclusion_status=conclusion_status,  # type: ignore[arg-type]
        directional_conclusion=directional,
    )
    recorder.write_json("comparison.json", report)
    recorder.update_summary(
        {
            "experiment": "exp03",
            "comparison_id": comparison_id,
            "case_id": case_id,
            "mode": mode.value,
            "runs": runs,
            "smoke_comparison": runs == 3,
            "extension_triggered": extension_triggered,
            "conclusion_status": conclusion_status,
        }
    )
    return report
