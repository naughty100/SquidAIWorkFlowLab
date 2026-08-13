import json
from pathlib import Path

import pytest

from ai_workflow_lab.config import LabSettings
from ai_workflow_lab.exp02.execution import Experiment02Mode
from ai_workflow_lab.exp05.graph import GraphDependencies
from ai_workflow_lab.exp05.runtime import GraphRuntime, graph_config, inspect_graph_state
from ai_workflow_lab.exp05.service import (
    get_workflow_state,
    resume_workflow,
    start_workflow,
)
from ai_workflow_lab.run_recording import RunRecorder

PROJECT_ROOT = Path(__file__).parents[1]


def make_run(
    tmp_path: Path, run_id: str
) -> tuple[LabSettings, RunRecorder]:
    settings = LabSettings(
        lab_output_dir=tmp_path / "outputs",
        lab_runtime_dir=tmp_path / "runtime",
        lab_cache_dir=tmp_path / "cache",
    )
    return settings, RunRecorder(
        settings, command="test", project_root=tmp_path, run_id=run_id
    )


def test_interrupt_survives_new_runtime_and_resume_uses_new_run(tmp_path: Path) -> None:
    settings, first_run = make_run(tmp_path, "start-run")
    started = start_workflow(
        settings, first_run, project_root=PROJECT_ROOT, thread_id="thread-resume"
    )

    assert started.status == "awaiting_topic_selection"
    assert started.next_nodes == ["wait_for_topic_selection"]
    assert started.interrupts[0].value["topic_ids"]  # type: ignore[index]
    assert not list(first_run.artifacts.artifacts_dir.rglob("*.json.gz"))

    settings, second_run = make_run(tmp_path, "resume-run")
    resumed = resume_workflow(
        settings,
        second_run,
        thread_id=started.thread_id,
        topic_id="topic-career-roadmap",
        project_root=PROJECT_ROOT,
    )

    assert resumed.run_id != started.run_id
    assert resumed.thread_id == started.thread_id
    assert resumed.status == "succeeded"
    assert resumed.next_nodes == []
    assert (second_run.run_dir / "proposal.md").is_file()
    persisted = json.loads(
        (second_run.run_dir / "workflow-state.json").read_text(encoding="utf-8")
    )
    assert persisted["status"] == "succeeded"
    assert resumed.state["mode"] == "fixture"
    assert all(
        item["run_id"] == second_run.run_id
        for item in resumed.state["artifact_refs"]  # type: ignore[union-attr]
    )


def test_invalid_topic_does_not_advance_checkpoint(tmp_path: Path) -> None:
    settings, first_run = make_run(tmp_path, "invalid-start")
    started = start_workflow(
        settings, first_run, project_root=PROJECT_ROOT, thread_id="thread-invalid"
    )
    settings, view_run = make_run(tmp_path, "view-before")
    before = get_workflow_state(
        settings, view_run, thread_id=started.thread_id, project_root=PROJECT_ROOT
    )
    settings, invalid_run = make_run(tmp_path, "invalid-resume")

    with pytest.raises(ValueError, match="非法 topic ID"):
        resume_workflow(
            settings,
            invalid_run,
            thread_id=started.thread_id,
            topic_id="topic-does-not-exist",
            project_root=PROJECT_ROOT,
        )

    settings, after_run = make_run(tmp_path, "view-after")
    after = get_workflow_state(
        settings, after_run, thread_id=started.thread_id, project_root=PROJECT_ROOT
    )
    assert after.checkpoint_id == before.checkpoint_id
    assert after.state_hash == before.state_hash
    assert after.next_nodes == ["wait_for_topic_selection"]


def test_resume_mode_mismatch_does_not_advance_checkpoint(tmp_path: Path) -> None:
    settings, start_run = make_run(tmp_path, "mode-start")
    started = start_workflow(
        settings, start_run, project_root=PROJECT_ROOT, thread_id="thread-mode"
    )
    settings, view_run = make_run(tmp_path, "mode-before")
    before = get_workflow_state(
        settings, view_run, thread_id=started.thread_id, project_root=PROJECT_ROOT
    )
    settings, resume_run = make_run(tmp_path, "mode-resume")

    with pytest.raises(ValueError, match="mode 与 thread"):
        resume_workflow(
            settings,
            resume_run,
            thread_id=started.thread_id,
            topic_id="topic-career-roadmap",
            mode=Experiment02Mode.LIVE,
            project_root=PROJECT_ROOT,
        )

    settings, after_run = make_run(tmp_path, "mode-after")
    after = get_workflow_state(
        settings, after_run, thread_id=started.thread_id, project_root=PROJECT_ROOT
    )
    assert after.checkpoint_id == before.checkpoint_id
    assert after.state_hash == before.state_hash


def test_research_and_revision_loops_are_strictly_capped(tmp_path: Path) -> None:
    settings, first_run = make_run(tmp_path, "loops-start")
    started = start_workflow(
        settings, first_run, project_root=PROJECT_ROOT, thread_id="thread-loops"
    )
    settings, second_run = make_run(tmp_path, "loops-resume")
    dependencies = GraphDependencies(
        settings=settings,
        recorder=second_run,
        project_root=PROJECT_ROOT,
        sufficiency_evaluator=lambda _: False,
        quality_evaluator=lambda _: False,
    )

    resumed = resume_workflow(
        settings,
        second_run,
        thread_id=started.thread_id,
        topic_id="topic-rag-graph",
        project_root=PROJECT_ROOT,
        dependencies_override=dependencies,
    )

    assert resumed.status == "needs_review"
    assert resumed.state["research_round"] == 2
    assert resumed.state["revision_count"] == 2
    assert resumed.state["evidence_warning"] is True
    persisted = json.loads(
        (second_run.run_dir / "workflow-state.json").read_text(encoding="utf-8")
    )
    assert persisted["status"] == "needs_review"


def test_failed_node_can_continue_from_official_checkpoint_without_retry_command(
    tmp_path: Path,
) -> None:
    settings, first_run = make_run(tmp_path, "failure-start")
    started = start_workflow(
        settings, first_run, project_root=PROJECT_ROOT, thread_id="thread-failure"
    )
    settings, failing_run = make_run(tmp_path, "failure-resume")
    failing_dependencies = GraphDependencies(
        settings=settings,
        recorder=failing_run,
        project_root=PROJECT_ROOT,
        fail_once_node="collect_evidence",
    )
    with pytest.raises(RuntimeError, match="one-shot failure"):
        resume_workflow(
            settings,
            failing_run,
            thread_id=started.thread_id,
            topic_id="topic-agent-boundaries",
            project_root=PROJECT_ROOT,
            dependencies_override=failing_dependencies,
        )

    settings, recovery_run = make_run(tmp_path, "failure-recovery")
    recovery_dependencies = GraphDependencies(
        settings=settings, recorder=recovery_run, project_root=PROJECT_ROOT
    )
    with GraphRuntime(recovery_dependencies) as runtime:
        runtime.graph.invoke(None, graph_config(started.thread_id))
        recovered = inspect_graph_state(runtime.graph, started.thread_id)

    assert recovered.status == "succeeded"
    assert recovered.next_nodes == []
    failing_events = failing_run.events_path.read_text(encoding="utf-8")
    recovery_events = recovery_run.events_path.read_text(encoding="utf-8")
    assert '"type": "exp05.graph.checkpoint.pending_writes"' in failing_events
    assert '"node": "collect_evidence"' in recovery_events


def test_checkpoint_contains_references_but_not_full_web_body_or_agent_event(
    tmp_path: Path,
) -> None:
    settings, start_run = make_run(tmp_path, "compact-start")
    started = start_workflow(
        settings, start_run, project_root=PROJECT_ROOT, thread_id="thread-compact"
    )
    settings, resume_run = make_run(tmp_path, "compact-resume")
    resumed = resume_workflow(
        settings,
        resume_run,
        thread_id=started.thread_id,
        topic_id="topic-career-roadmap",
        project_root=PROJECT_ROOT,
    )

    encoded = json.dumps(resumed.state, ensure_ascii=False)
    events = resume_run.events_path.read_text(encoding="utf-8")
    assert "artifact_ref" in encoded
    assert "WEB_ARTIFACT_ONLY_TAIL_MARKER" not in encoded
    assert "create_agent" not in events
