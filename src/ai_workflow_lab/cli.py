"""AI Workflow Lab 命令行入口。"""

from pathlib import Path
from typing import Annotated

import typer

from ai_workflow_lab.config import LabSettings
from ai_workflow_lab.doctor import run_doctor
from ai_workflow_lab.run_recording import RunRecorder

app = typer.Typer(
    name="lab",
    help="AI Workflow Lab 本地实验命令行。",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """AI Workflow Lab 命令组。"""


@app.command()
def doctor(
    live: bool = typer.Option(False, "--live", help="显式执行外部模型能力探测。"),
    env_file: Annotated[Path | None, typer.Option(
        "--env-file",
        "-e",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="指定 dotenv 配置档案，例如 .env.deepseek；未指定时读取 .env。",
    )] = None,
) -> None:
    """检查本地实验环境和可选的 Provider 能力。"""
    settings = LabSettings.from_env_file(env_file)
    command_parts = ["doctor"]
    if live:
        command_parts.append("--live")
    if env_file is not None:
        command_parts.extend(["--env-file", str(env_file)])
    recorder = RunRecorder(settings, command=" ".join(command_parts))
    try:
        report = run_doctor(settings, live=live)
        report.run_id = recorder.run_id
        recorder.record_event("doctor.report", report)
        recorder.write_json("capabilities.json", report.capabilities)
        recorder.finish("succeeded" if report.ok else "failed", details={"ok": report.ok})
        typer.echo(report.model_dump_json(indent=2))
        if not report.ok:
            raise typer.Exit(code=1)
    except typer.Exit:
        raise
    except Exception as exc:
        recorder.record_event("doctor.error", exc)
        recorder.finish("failed", details=exc)
        raise


if __name__ == "__main__":
    app()
