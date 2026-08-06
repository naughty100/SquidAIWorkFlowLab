"""AI Workflow Lab 命令行入口。"""

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
) -> None:
    """检查本地实验环境和可选的 Provider 能力。"""
    settings = LabSettings()
    recorder = RunRecorder(settings, command="doctor --live" if live else "doctor")
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
