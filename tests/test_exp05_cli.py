from typer.testing import CliRunner

from ai_workflow_lab.cli import app


def test_graph_cli_exposes_resume_and_state_but_not_retry() -> None:
    result = CliRunner().invoke(app, ["graph", "--help"])

    assert result.exit_code == 0
    assert "resume" in result.stdout
    assert "state" in result.stdout
    assert "retry" not in result.stdout

