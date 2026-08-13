"""实验五 start/resume/state 服务与 run/thread 关联。"""

from pathlib import Path
from typing import cast
from uuid import uuid4

from langgraph.types import Command

from ai_workflow_lab.config import LabSettings
from ai_workflow_lab.exp02.execution import Experiment02Mode
from ai_workflow_lab.exp02.tools import load_fixture
from ai_workflow_lab.run_recording import RunRecorder

from .domain import GraphInterruptInfo, GraphStateView, WorkflowInvocation, WorkflowState
from .graph import GraphDependencies, validate_topic_id
from .runtime import GraphRuntime, graph_config, inspect_graph_state


def _result_interrupts(result: dict[str, object]) -> list[GraphInterruptInfo]:
    raw = result.get("__interrupt__", ())
    if not isinstance(raw, (list, tuple)):
        return []
    items: list[object]
    if isinstance(raw, list):
        items = cast(list[object], raw)
    else:
        items = list(cast(tuple[object, ...], raw))
    return [
        GraphInterruptInfo(
            value=getattr(item, "value", None),
            interrupt_id=getattr(item, "id", None),
        )
        for item in items
    ]


def _record_checkpoint(
    recorder: RunRecorder, view: GraphStateView, *, event: str = "exp05.graph.checkpoint"
) -> None:
    recorder.record_event(
        event,
        {
            "thread_id": view.thread_id,
            "checkpoint_id": view.checkpoint_id,
            "state_hash": view.state_hash,
            "next_nodes": view.next_nodes,
            "status": view.status,
        },
    )


def start_workflow(
    settings: LabSettings,
    recorder: RunRecorder,
    *,
    case_id: str = "career-ai-v1",
    mode: Experiment02Mode = Experiment02Mode.FIXTURE,
    project_root: Path | None = None,
    thread_id: str | None = None,
    dependencies_override: GraphDependencies | None = None,
) -> WorkflowInvocation:
    root = (project_root or Path.cwd()).resolve()
    fixture = load_fixture(root)
    if fixture.brief.case_id != case_id:
        raise ValueError(f"未知实验五 case：{case_id}")
    current_thread_id = thread_id or uuid4().hex
    dependencies = dependencies_override or GraphDependencies(
        settings=settings,
        recorder=recorder,
        project_root=root,
        mode=mode,
    )
    initial: WorkflowState = {
        "schema_version": "1",
        "case_id": fixture.brief.case_id,
        "case_version": fixture.brief.case_version,
        "mode": mode.value,
        "input_question": fixture.brief.question,
        "audience": fixture.brief.audience,
        "goal": fixture.brief.goal,
        "thread_id": current_thread_id,
        "initial_run_id": recorder.run_id,
        "topic_options": [],
        "research_questions": [],
        "source_evidence": [],
        "artifact_refs": [],
        "selected_topic_id": "",
        "selected_topic_title": "",
        "research_pack": {},
        "proposal": {},
        "quality_result": {},
        "research_round": 0,
        "revision_count": 0,
        "evidence_warning": False,
        "status": "initialized",
    }
    with GraphRuntime(dependencies) as runtime:
        result = cast(
            dict[str, object], runtime.graph.invoke(initial, graph_config(current_thread_id))
        )
        view = inspect_graph_state(runtime.graph, current_thread_id)
    interrupts = _result_interrupts(result)
    if interrupts:
        recorder.record_event(
            "exp05.graph.interrupt",
            {
                "logical_event_id": (
                    f"{current_thread_id}:wait_for_topic_selection:{view.checkpoint_id}"
                ),
                "thread_id": current_thread_id,
                "interrupts": interrupts,
            },
        )
    _record_checkpoint(recorder, view)
    recorder.update_summary(
        {
            "experiment": "exp05",
            "operation": "start",
            "thread_id": current_thread_id,
            "case_id": case_id,
            "mode": mode.value,
            "checkpoint_id": view.checkpoint_id,
            "next_nodes": view.next_nodes,
            "workflow_status": view.status,
        }
    )
    return WorkflowInvocation(
        run_id=recorder.run_id,
        thread_id=current_thread_id,
        status=view.status or "unknown",
        next_nodes=view.next_nodes,
        interrupts=interrupts or view.interrupts,
        state=view.state,
    )


def resume_workflow(
    settings: LabSettings,
    recorder: RunRecorder,
    *,
    thread_id: str,
    topic_id: str,
    mode: Experiment02Mode = Experiment02Mode.FIXTURE,
    project_root: Path | None = None,
    dependencies_override: GraphDependencies | None = None,
) -> WorkflowInvocation:
    root = (project_root or Path.cwd()).resolve()
    dependencies = dependencies_override or GraphDependencies(
        settings=settings,
        recorder=recorder,
        project_root=root,
        mode=mode,
    )
    with GraphRuntime(dependencies) as runtime:
        before = inspect_graph_state(runtime.graph, thread_id)
        state_for_validation = cast(WorkflowState, before.state)
        persisted_mode = state_for_validation.get("mode")
        if persisted_mode != mode.value:
            raise ValueError(
                "恢复 mode 与 thread 初始配置不一致："
                f"thread={persisted_mode!r}, requested={mode.value!r}"
            )
        # Validate before Command so an invalid ID cannot create a checkpoint.
        validate_topic_id(state_for_validation, topic_id)
        if "wait_for_topic_selection" not in before.next_nodes:
            raise ValueError(f"thread 当前不等待选题：{thread_id}")
        recorder.record_event(
            "exp05.graph.resume",
            {
                "thread_id": thread_id,
                "topic_id": topic_id,
                "previous_checkpoint_id": before.checkpoint_id,
            },
        )
        result = cast(
            dict[str, object],
            runtime.graph.invoke(Command(resume=topic_id), graph_config(thread_id)),
        )
        view = inspect_graph_state(runtime.graph, thread_id)
    _record_checkpoint(recorder, view)
    recorder.update_summary(
        {
            "experiment": "exp05",
            "operation": "resume",
            "thread_id": thread_id,
            "topic_id": topic_id,
            "mode": mode.value,
            "checkpoint_id": view.checkpoint_id,
            "next_nodes": view.next_nodes,
            "workflow_status": view.status,
            "resumed_from_checkpoint_id": before.checkpoint_id,
        }
    )
    return WorkflowInvocation(
        run_id=recorder.run_id,
        thread_id=thread_id,
        status=view.status or "unknown",
        next_nodes=view.next_nodes,
        interrupts=_result_interrupts(result) or view.interrupts,
        state=view.state,
    )


def get_workflow_state(
    settings: LabSettings,
    recorder: RunRecorder,
    *,
    thread_id: str,
    project_root: Path | None = None,
) -> GraphStateView:
    root = (project_root or Path.cwd()).resolve()
    dependencies = GraphDependencies(
        settings=settings,
        recorder=recorder,
        project_root=root,
    )
    with GraphRuntime(dependencies) as runtime:
        before = inspect_graph_state(runtime.graph, thread_id)
        after = inspect_graph_state(runtime.graph, thread_id)
    if before.state_hash != after.state_hash or before.checkpoint_id != after.checkpoint_id:
        raise RuntimeError("只读 state 检查意外修改了 checkpoint")
    recorder.record_event(
        "exp05.graph.state.inspected",
        {
            "thread_id": thread_id,
            "checkpoint_id": before.checkpoint_id,
            "state_hash": before.state_hash,
        },
    )
    recorder.update_summary(
        {
            "experiment": "exp05",
            "operation": "state",
            "thread_id": thread_id,
            "checkpoint_id": before.checkpoint_id,
            "state_hash": before.state_hash,
            "read_only": True,
        }
    )
    return before
