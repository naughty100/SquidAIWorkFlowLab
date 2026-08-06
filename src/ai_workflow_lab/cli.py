"""AI Workflow Lab 命令行入口。"""

from pathlib import Path
from typing import Annotated

import typer

from ai_workflow_lab.config import LabSettings
from ai_workflow_lab.doctor import run_doctor
from ai_workflow_lab.exp01.execution import ExperimentMode, ExperimentVariant
from ai_workflow_lab.exp01.service import run_exp01
from ai_workflow_lab.run_recording import RunRecorder

app = typer.Typer(
    name="lab",
    help="AI Workflow Lab 本地实验命令行。",
    no_args_is_help=True,
)
run_app = typer.Typer(help="运行实验。", no_args_is_help=True)
runs_app = typer.Typer(help="查看本地运行记录。", no_args_is_help=True)
app.add_typer(run_app, name="run")
app.add_typer(runs_app, name="runs")


@app.callback()
def main() -> None:
    """AI Workflow Lab 命令组。"""


@app.command()
def doctor(
    live: bool = typer.Option(False, "--live", help="显式执行外部模型能力探测。"),
    env_file: Annotated[
        Path | None,
        typer.Option(
            "--env-file",
            "-e",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
            help="指定 dotenv 配置档案，例如 .env.deepseek；未指定时读取 .env。",
        ),
    ] = None,
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


@run_app.command("exp01")
def run_structured_output_experiment(
    case_id: Annotated[
        str, typer.Option("--case", help="版本化案例 ID。")
    ] = "career-transition-v1",
    mode: Annotated[
        ExperimentMode, typer.Option("--mode", help="mock 或 live。")
    ] = ExperimentMode.MOCK,
    variant: Annotated[
        ExperimentVariant,
        typer.Option("--variant", help="结构化输出 variant。"),
    ] = ExperimentVariant.PROMPT_PARSE,
    env_file: Annotated[
        Path | None,
        typer.Option(
            "--env-file",
            "-e",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
            help="指定 dotenv 配置档案；未指定时读取 .env。",
        ),
    ] = None,
) -> None:
    """运行实验一的单个结构化输出 variant。"""
    settings = LabSettings.from_env_file(env_file)
    command = f"run exp01 --case {case_id} --mode {mode.value} --variant {variant.value}"
    if env_file is not None:
        command += f" --env-file {env_file}"
    recorder = RunRecorder(settings, command=command)
    try:
        outcome = run_exp01(
            settings,
            recorder,
            case_id=case_id,
            mode=mode,
            variant=variant,
        )
        recorder.finish("succeeded" if outcome.status != "failed" else "failed")
        typer.echo(outcome.model_dump_json(indent=2))
        typer.echo(f"run_id: {recorder.run_id}")
        if outcome.status == "failed":
            raise typer.Exit(code=1)
    except typer.Exit:
        raise
    except Exception as exc:
        recorder.record_event("exp01.error", exc)
        recorder.finish("failed", details=exc)
        raise


@runs_app.command("show")
def show_run(
    run_id: str,
    env_file: Annotated[
        Path | None,
        typer.Option(
            "--env-file",
            "-e",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
            help="指定 dotenv 配置档案；未指定时读取 .env。",
        ),
    ] = None,
) -> None:
    """显示一次运行的脱敏摘要。"""
    settings = LabSettings.from_env_file(env_file)
    root = settings.lab_output_dir
    if not root.is_absolute():
        root = Path.cwd() / root
    summary_path = (root / "commands" / run_id / "summary.json").resolve()
    commands_root = (root / "commands").resolve()
    if not summary_path.is_relative_to(commands_root) or not summary_path.is_file():
        raise typer.BadParameter(f"运行记录不存在：{run_id}", param_hint="RUN_ID")
    typer.echo(summary_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    app()
