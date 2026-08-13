# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""SQLite checkpointer 生命周期与只读状态提取。"""

import hashlib
import json
import sqlite3
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

from langgraph.checkpoint.sqlite import SqliteSaver

from ai_workflow_lab.config import LabSettings
from ai_workflow_lab.run_recording import RunRecorder

from .domain import CheckpointHistoryItem, GraphInterruptInfo, GraphStateView
from .graph import GraphDependencies, build_workflow


class TracingSqliteSaver(SqliteSaver):
    """Emit compact trace events for checkpoint commits and pending writes."""

    def __init__(self, connection: sqlite3.Connection, recorder: RunRecorder) -> None:
        super().__init__(connection)
        self._recorder = recorder

    def put(
        self,
        config: Any,
        checkpoint: Any,
        metadata: Any,
        new_versions: Any,
    ) -> Any:
        saved = super().put(config, checkpoint, metadata, new_versions)
        configurable = saved.get("configurable", {})
        safe_metadata = metadata if isinstance(metadata, dict) else {}
        self._recorder.record_event(
            "exp05.graph.checkpoint.written",
            {
                "thread_id": configurable.get("thread_id"),
                "checkpoint_id": configurable.get("checkpoint_id"),
                "step": safe_metadata.get("step"),
                "source": safe_metadata.get("source"),
            },
        )
        return saved

    def put_writes(
        self,
        config: Any,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        super().put_writes(config, writes, task_id, task_path)
        configurable = config.get("configurable", {})
        self._recorder.record_event(
            "exp05.graph.checkpoint.pending_writes",
            {
                "thread_id": configurable.get("thread_id"),
                "checkpoint_id": configurable.get("checkpoint_id"),
                "task_id": task_id,
                "task_path": task_path,
                "channels": [channel for channel, _ in writes],
                "write_count": len(writes),
            },
        )


def checkpoint_path(settings: LabSettings, project_root: Path | None = None) -> Path:
    root = settings.lab_runtime_dir
    if not root.is_absolute():
        root = (project_root or Path.cwd()).resolve() / root
    target = (root.resolve() / "graph" / "exp05.sqlite3").resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


class GraphRuntime:
    """应用启动层拥有连接；节点和 state 永远看不到连接对象。"""

    def __init__(self, dependencies: GraphDependencies) -> None:
        self.dependencies = dependencies
        path = checkpoint_path(dependencies.settings, dependencies.project_root)
        self.connection = sqlite3.connect(str(path), check_same_thread=False)
        self.checkpointer = TracingSqliteSaver(self.connection, dependencies.recorder)
        self.checkpointer.setup()
        self.graph = build_workflow(dependencies, self.checkpointer)

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "GraphRuntime":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def graph_config(thread_id: str) -> dict[str, dict[str, str]]:
    return {"configurable": {"thread_id": thread_id}}


def _interrupts(snapshot: Any) -> list[GraphInterruptInfo]:
    values: list[GraphInterruptInfo] = []
    for task in getattr(snapshot, "tasks", ()):
        for item in getattr(task, "interrupts", ()):
            values.append(
                GraphInterruptInfo(
                    value=getattr(item, "value", None),
                    interrupt_id=getattr(item, "id", None),
                )
            )
    return values


def _checkpoint_id(snapshot: Any) -> str | None:
    config_value = getattr(snapshot, "config", {})
    config = cast(dict[str, object], config_value) if isinstance(config_value, dict) else {}
    configurable_value = config.get("configurable", {})
    configurable = (
        cast(dict[str, object], configurable_value)
        if isinstance(configurable_value, dict)
        else {}
    )
    value = configurable.get("checkpoint_id")
    return str(value) if value else None


def _nonnegative_int(value: object) -> int:
    return value if isinstance(value, int) and value >= 0 else 0


def inspect_graph_state(graph: Any, thread_id: str, *, history_limit: int = 20) -> GraphStateView:
    config = graph_config(thread_id)
    snapshot = graph.get_state(config)
    values = cast(dict[str, object], dict(getattr(snapshot, "values", {})))
    if not values:
        raise ValueError(f"Graph thread 不存在：{thread_id}")
    canonical = json.dumps(
        values, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    history: list[CheckpointHistoryItem] = []
    for item in list(graph.get_state_history(config))[:history_limit]:
        item_values = cast(dict[str, object], dict(getattr(item, "values", {})))
        created_at = getattr(item, "created_at", None)
        history.append(
            CheckpointHistoryItem(
                checkpoint_id=_checkpoint_id(item),
                created_at=str(created_at) if created_at else None,
                next_nodes=list(getattr(item, "next", ())),
                status=str(item_values.get("status")) if item_values.get("status") else None,
                research_round=_nonnegative_int(item_values.get("research_round", 0)),
                revision_count=_nonnegative_int(item_values.get("revision_count", 0)),
            )
        )
    return GraphStateView(
        thread_id=thread_id,
        checkpoint_id=_checkpoint_id(snapshot),
        state_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        next_nodes=list(getattr(snapshot, "next", ())),
        interrupts=_interrupts(snapshot),
        status=str(values.get("status")) if values.get("status") else None,
        state=values,
        history=history,
    )
