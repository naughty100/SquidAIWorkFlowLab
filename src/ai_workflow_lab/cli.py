"""AI Workflow Lab 命令行入口。"""

from pathlib import Path
from typing import Annotated

import typer

from ai_workflow_lab.config import LabSettings
from ai_workflow_lab.doctor import run_doctor
from ai_workflow_lab.exp01.execution import ExperimentMode, ExperimentVariant
from ai_workflow_lab.exp01.service import run_exp01
from ai_workflow_lab.exp02.execution import Experiment02Mode, Experiment02Variant
from ai_workflow_lab.exp02.service import run_exp02
from ai_workflow_lab.exp03.comparison import run_comparison
from ai_workflow_lab.exp03.domain import Experiment03Variant
from ai_workflow_lab.exp03.service import run_exp03
from ai_workflow_lab.exp04.domain import RagVariant, RetrievalProfile
from ai_workflow_lab.exp04.service import run_exp04, run_rag_evaluation
from ai_workflow_lab.exp05.service import (
    get_workflow_state,
    resume_workflow,
    start_workflow,
)
from ai_workflow_lab.run_recording import RunRecorder

app = typer.Typer(
    name="lab",
    help="AI Workflow Lab 本地实验命令行。",
    no_args_is_help=True,
)
run_app = typer.Typer(help="运行实验。", no_args_is_help=True)
runs_app = typer.Typer(help="查看本地运行记录。", no_args_is_help=True)
compare_app = typer.Typer(help="执行配对实验比较。", no_args_is_help=True)
rag_app = typer.Typer(help="执行 RAG 检索评估。", no_args_is_help=True)
graph_app = typer.Typer(help="恢复或只读检查 Graph thread。", no_args_is_help=True)
app.add_typer(run_app, name="run")
app.add_typer(runs_app, name="runs")
app.add_typer(compare_app, name="compare")
app.add_typer(rag_app, name="rag")
app.add_typer(graph_app, name="graph")


def console_safe_text(text: str) -> str:
    """Return text that every Windows console encoding can print.

    Run artifacts keep their original UTF-8 content. CLI JSON is escaped only
    at the output boundary so an inherited GBK console cannot turn a completed
    run into a command failure.
    """
    return text.encode("ascii", errors="backslashreplace").decode("ascii")


def _echo_json(text: str) -> None:
    typer.echo(console_safe_text(text))


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
        _echo_json(report.model_dump_json(indent=2))
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
    # 命令文本写进 summary 以便复盘时定位配置档案
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
        _echo_json(outcome.model_dump_json(indent=2))
        typer.echo(f"run_id: {recorder.run_id}")
        if outcome.status == "failed":
            raise typer.Exit(code=1)
    except typer.Exit:
        raise
    except Exception as exc:
        recorder.record_event("exp01.error", exc)
        recorder.finish("failed", details=exc)
        raise


@run_app.command("exp02")
def run_controlled_tool_experiment(
    case_id: Annotated[str, typer.Option("--case", help="版本化研究案例 ID。")] = "career-ai-v1",
    mode: Annotated[
        Experiment02Mode, typer.Option("--mode", help="fixture 或 live。")
    ] = Experiment02Mode.FIXTURE,
    variant: Annotated[
        Experiment02Variant,
        typer.Option("--variant", help="fixed 或 tool-call。"),
    ] = Experiment02Variant.FIXED,
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
    """运行实验二的固定研究或受控 Tool Calling variant。"""
    settings = LabSettings.from_env_file(env_file)
    command = f"run exp02 --case {case_id} --mode {mode.value} --variant {variant.value}"
    if env_file is not None:
        command += f" --env-file {env_file}"
    recorder = RunRecorder(settings, command=command)
    try:
        outcome = run_exp02(
            settings,
            recorder,
            case_id=case_id,
            mode=mode,
            variant=variant,
        )
        recorder.finish("succeeded")
        _echo_json(outcome.model_dump_json(indent=2))
        typer.echo(f"run_id: {recorder.run_id}")
    except Exception as exc:
        recorder.record_event("exp02.error", exc)
        recorder.finish("failed", details=exc)
        raise


@run_app.command("exp03")
def run_agent_comparison_variant(
    case_id: Annotated[str, typer.Option("--case", help="版本化研究案例 ID。")] = "career-ai-v1",
    mode: Annotated[
        Experiment02Mode, typer.Option("--mode", help="fixture 或 live。")
    ] = Experiment02Mode.FIXTURE,
    variant: Annotated[
        Experiment03Variant, typer.Option("--variant", help="fixed 或 agent。")
    ] = Experiment03Variant.FIXED,
    env_file: Annotated[
        Path | None,
        typer.Option(
            "--env-file", "-e", exists=True, file_okay=True, dir_okay=False, readable=True
        ),
    ] = None,
) -> None:
    """运行实验三的单个公平对照 variant。"""
    settings = LabSettings.from_env_file(env_file)
    command = f"run exp03 --case {case_id} --mode {mode.value} --variant {variant.value}"
    recorder = RunRecorder(settings, command=command)
    try:
        outcome = run_exp03(
            settings,
            recorder,
            case_id=case_id,
            mode=mode,
            variant=variant,
        )
        recorder.finish("succeeded" if outcome.status == "succeeded" else "failed")
        _echo_json(outcome.model_dump_json(indent=2))
        typer.echo(f"run_id: {recorder.run_id}")
    except Exception as exc:
        recorder.record_event("exp03.error", exc)
        recorder.finish("failed", details=exc)
        raise


@compare_app.command("exp03")
def compare_agent_experiment(
    case_id: Annotated[str, typer.Option("--case", help="版本化研究案例 ID。")] = "career-ai-v1",
    runs: Annotated[int, typer.Option("--runs", min=1, help="每个 variant 的配对运行数。")] = 3,
    mode: Annotated[
        Experiment02Mode, typer.Option("--mode", help="fixture 或 live。")
    ] = Experiment02Mode.FIXTURE,
    env_file: Annotated[
        Path | None,
        typer.Option(
            "--env-file", "-e", exists=True, file_okay=True, dir_okay=False, readable=True
        ),
    ] = None,
) -> None:
    """配对运行 fixed/agent；达到差异门禁时要求至少十次。"""
    settings = LabSettings.from_env_file(env_file)
    recorder = RunRecorder(
        settings,
        command=f"compare exp03 --case {case_id} --runs {runs} --mode {mode.value}",
    )
    try:
        report = run_comparison(
            settings, recorder, case_id=case_id, mode=mode, runs=runs
        )
        recorder.finish("succeeded")
        _echo_json(report.model_dump_json(indent=2))
        typer.echo(f"run_id: {recorder.run_id}")
    except Exception as exc:
        recorder.record_event("exp03.compare.error", exc)
        recorder.finish("failed", details=exc)
        raise


@run_app.command("exp04")
def run_rag_variant(
    variant: Annotated[
        RagVariant, typer.Option("--variant", help="no-rag、full-context 或 vector。")
    ] = RagVariant.VECTOR,
    embedding_profile: Annotated[
        str, typer.Option("--embedding-profile", help="已版本化 embedding profile ID。")
    ] = "minilm-multilingual-v1",
    chunk_size: Annotated[int, typer.Option("--chunk-size", min=100, max=4000)] = 800,
    overlap: Annotated[int, typer.Option("--overlap", min=0)] = 120,
    top_k: Annotated[int, typer.Option("--top-k", min=1, max=32)] = 4,
    local_embeddings: Annotated[
        bool,
        typer.Option(
            "--local-embeddings/--fixed-embeddings",
            help="加载 pinned 本地模型；默认使用确定性离线 embedding。",
        ),
    ] = False,
    env_file: Annotated[
        Path | None,
        typer.Option(
            "--env-file", "-e", exists=True, file_okay=True, dir_okay=False, readable=True
        ),
    ] = None,
) -> None:
    """运行实验四的单个上下文策略。"""
    settings = LabSettings.from_env_file(env_file)
    retrieval = RetrievalProfile(
        profile_id=f"cli-{chunk_size}-{overlap}-k{top_k}",
        chunk_size=chunk_size,
        overlap=overlap,
        top_k=top_k,
        profile_version="1",
    )
    recorder = RunRecorder(
        settings,
        command=f"run exp04 --variant {variant.value} --embedding-profile {embedding_profile}",
    )
    try:
        outcome = run_exp04(
            settings,
            recorder,
            variant=variant,
            embedding_profile_id=embedding_profile,
            retrieval_profile=retrieval,
            local_embeddings=local_embeddings,
        )
        recorder.finish("succeeded")
        _echo_json(outcome.model_dump_json(indent=2))
        typer.echo(f"run_id: {recorder.run_id}")
    except Exception as exc:
        recorder.record_event("exp04.error", exc)
        recorder.finish("failed", details=exc)
        raise


@rag_app.command("evaluate")
def evaluate_rag(
    embedding_profile: Annotated[
        str,
        typer.Option(
            "--embedding-profile", help="auto、minilm-multilingual-v1 或 bge-small-zh-v1。"
        ),
    ] = "auto",
    local_embeddings: Annotated[
        bool,
        typer.Option("--local-embeddings/--fixed-embeddings"),
    ] = False,
    env_file: Annotated[
        Path | None,
        typer.Option(
            "--env-file", "-e", exists=True, file_okay=True, dir_okay=False, readable=True
        ),
    ] = None,
) -> None:
    """执行 Profile 门禁、逐查询排名和完整 retrieval matrix。"""
    settings = LabSettings.from_env_file(env_file)
    recorder = RunRecorder(
        settings,
        command=f"rag evaluate --embedding-profile {embedding_profile}",
    )
    try:
        report = run_rag_evaluation(
            settings,
            recorder,
            embedding_profile_id=embedding_profile,
            local_embeddings=local_embeddings,
        )
        recorder.finish("succeeded")
        _echo_json(report.model_dump_json(indent=2))
        typer.echo(f"run_id: {recorder.run_id}")
    except Exception as exc:
        recorder.record_event("exp04.evaluate.error", exc)
        recorder.finish("failed", details=exc)
        raise


@run_app.command("exp05")
def run_graph_workflow(
    case_id: Annotated[str, typer.Option("--case")] = "career-ai-v1",
    mode: Annotated[
        Experiment02Mode, typer.Option("--mode", help="fixture 或 live。")
    ] = Experiment02Mode.FIXTURE,
    env_file: Annotated[
        Path | None,
        typer.Option(
            "--env-file", "-e", exists=True, file_okay=True, dir_okay=False, readable=True
        ),
    ] = None,
) -> None:
    """创建独立 run/thread，并在选题 interrupt 处暂停。"""
    settings = LabSettings.from_env_file(env_file)
    recorder = RunRecorder(settings, command=f"run exp05 --case {case_id} --mode {mode.value}")
    try:
        outcome = start_workflow(
            settings, recorder, case_id=case_id, mode=mode
        )
        recorder.finish("succeeded")
        _echo_json(outcome.model_dump_json(indent=2))
        typer.echo(f"run_id: {recorder.run_id}")
        typer.echo(f"thread_id: {outcome.thread_id}")
    except Exception as exc:
        recorder.record_event("exp05.error", exc)
        recorder.finish("failed", details=exc)
        raise


@graph_app.command("resume")
def resume_graph_workflow(
    thread_id: str,
    topic_id: Annotated[str, typer.Option("--topic-id")],
    mode: Annotated[
        Experiment02Mode, typer.Option("--mode", help="fixture 或 live。")
    ] = Experiment02Mode.FIXTURE,
    env_file: Annotated[
        Path | None,
        typer.Option(
            "--env-file", "-e", exists=True, file_okay=True, dir_okay=False, readable=True
        ),
    ] = None,
) -> None:
    """新建 run 并用原 thread ID 恢复选题。"""
    settings = LabSettings.from_env_file(env_file)
    recorder = RunRecorder(
        settings, command=f"graph resume {thread_id} --topic-id {topic_id} --mode {mode.value}"
    )
    try:
        outcome = resume_workflow(
            settings,
            recorder,
            thread_id=thread_id,
            topic_id=topic_id,
            mode=mode,
        )
        recorder.finish(
            "succeeded" if outcome.status in {"succeeded", "needs_review"} else "failed"
        )
        _echo_json(outcome.model_dump_json(indent=2))
        typer.echo(f"run_id: {recorder.run_id}")
    except Exception as exc:
        recorder.record_event("exp05.resume.error", exc)
        recorder.finish("failed", details=exc)
        raise


@graph_app.command("state")
def show_graph_state(
    thread_id: str,
    env_file: Annotated[
        Path | None,
        typer.Option(
            "--env-file", "-e", exists=True, file_okay=True, dir_okay=False, readable=True
        ),
    ] = None,
) -> None:
    """只读显示最新 checkpoint、下一节点、interrupt 和历史摘要。"""
    settings = LabSettings.from_env_file(env_file)
    recorder = RunRecorder(settings, command=f"graph state {thread_id}")
    try:
        view = get_workflow_state(
            settings, recorder, thread_id=thread_id
        )
        recorder.finish("succeeded")
        _echo_json(view.model_dump_json(indent=2))
        typer.echo(f"run_id: {recorder.run_id}")
    except Exception as exc:
        recorder.record_event("exp05.state.error", exc)
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
        # 防止 RUN_ID 被构造成目录穿越路径 并避免读取非实验文件
        raise typer.BadParameter(f"运行记录不存在：{run_id}", param_hint="RUN_ID")
    typer.echo(console_safe_text(summary_path.read_text(encoding="utf-8")))


@runs_app.command("events")
def show_run_events(
    run_id: str,
    event_type: Annotated[
        str | None,
        typer.Option("--type", help="按事件类型或类型前缀过滤。"),
    ] = None,
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
    """显示一次运行的脱敏事件，可用于查看 Tool 轨迹。"""
    import json

    settings = LabSettings.from_env_file(env_file)
    root = settings.lab_output_dir
    if not root.is_absolute():
        root = Path.cwd() / root
    events_path = (root / "commands" / run_id / "events.jsonl").resolve()
    commands_root = (root / "commands").resolve()
    if not events_path.is_relative_to(commands_root) or not events_path.is_file():
        raise typer.BadParameter(f"运行记录不存在：{run_id}", param_hint="RUN_ID")
    for line in events_path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        current_type = str(event.get("type", ""))
        if event_type is None or current_type.startswith(event_type):
            typer.echo(json.dumps(event, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    app()
