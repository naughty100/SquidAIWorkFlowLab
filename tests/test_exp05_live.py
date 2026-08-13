import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pytest

from ai_workflow_lab.exp01.capability import freeze_native_method
from ai_workflow_lab.live_validation import (
    live_env_file_cli_args,
    load_live_validation_settings,
)

PROJECT_ROOT = Path(__file__).parents[1]
THREAD_PATTERN = re.compile(r"^thread_id:\s*([a-f0-9]+)\s*$", re.MULTILINE)


def _run_lab(args: list[str]) -> str:
    completed = subprocess.run(
        [sys.executable, "-m", "ai_workflow_lab.cli", *args],
        cwd=PROJECT_ROOT,
        env={**os.environ, "PYTHONUTF8": "1"},
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=900,
    )
    assert completed.returncode == 0, f"lab subprocess failed with exit {completed.returncode}"
    return completed.stdout


def _output_root() -> Path:
    settings = load_live_validation_settings()
    root = settings.lab_output_dir
    return root.resolve() if root.is_absolute() else (PROJECT_ROOT / root).resolve()


def _thread_summaries(thread_id: str) -> dict[str, dict[str, Any]]:
    summaries: dict[str, dict[str, Any]] = {}
    for path in (_output_root() / "commands").glob("*/summary.json"):
        try:
            payload_value: object = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload_value, dict):
            continue
        payload = cast(dict[str, Any], payload_value)
        if payload.get("thread_id") == thread_id and isinstance(payload.get("operation"), str):
            summaries[str(payload["operation"])] = payload
    return summaries


@pytest.mark.live
@pytest.mark.skipif(
    os.getenv("RUN_LIVE_TESTS") != "1",
    reason="set RUN_LIVE_TESTS=1 to run billable exp05 cross-process validation",
)
def test_live_graph_interrupt_resumes_in_a_new_process_and_saves_proposal() -> None:
    settings = load_live_validation_settings()
    settings.require_live_credentials()
    settings.require_tavily_credentials()
    freeze_native_method(settings, project_root=PROJECT_ROOT)
    env_args = live_env_file_cli_args()

    start_output = _run_lab(["run", "exp05", "--mode", "live", *env_args])
    match = THREAD_PATTERN.search(start_output)
    assert match is not None
    thread_id = match.group(1)

    _run_lab(
        [
            "graph",
            "resume",
            thread_id,
            "--topic-id",
            "topic-career-roadmap",
            "--mode",
            "live",
            *env_args,
        ]
    )
    _run_lab(["graph", "state", thread_id, *env_args])

    summaries = _thread_summaries(thread_id)
    assert {"start", "resume", "state"} <= summaries.keys()
    assert summaries["start"]["workflow_status"] == "awaiting_topic_selection"
    assert summaries["resume"]["workflow_status"] in {"succeeded", "needs_review"}
    assert summaries["state"]["read_only"] is True
    assert summaries["start"]["run_id"] != summaries["resume"]["run_id"]

    resume_dir = _output_root() / "commands" / str(summaries["resume"]["run_id"])
    assert (resume_dir / "proposal.json").is_file()
    assert (resume_dir / "proposal.md").is_file()
    persisted = json.loads(
        (resume_dir / "workflow-state.json").read_text(encoding="utf-8")
    )
    assert persisted["status"] in {"succeeded", "needs_review"}
