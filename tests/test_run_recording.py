import gzip
import json
from pathlib import Path

from pydantic import SecretStr

from ai_workflow_lab.artifacts import reconstruct_externalized
from ai_workflow_lab.config import LabSettings
from ai_workflow_lab.run_recording import RunRecorder
from ai_workflow_lab.security import REDACTED, JSONValue


def test_run_recorder_redacts_and_externalizes_before_persisting(tmp_path: Path) -> None:
    secret = "sk-sensitive-value"
    (tmp_path / "uv.lock").write_text("version = 1", encoding="utf-8")
    settings = LabSettings(
        ai_base_url="https://example.com/v1",
        ai_api_key=SecretStr(secret),
        ai_model="model",
        lab_output_dir=tmp_path / "outputs",
        lab_artifact_inline_threshold=256,
    )
    recorder = RunRecorder(settings, command="test", project_root=tmp_path, run_id="run-1")
    original = {"authorization": secret, "body": (secret + "-正文") * 40}

    event = recorder.record_event("test.payload", original)
    recorder.finish("succeeded")

    persisted = recorder.events_path.read_text(encoding="utf-8")
    assert secret not in persisted
    for artifact in (recorder.run_dir / "artifacts").rglob("*.json.gz"):
        assert secret.encode() not in gzip.decompress(artifact.read_bytes())

    payload = event["payload"]
    assert isinstance(payload, dict)
    reconstructed: JSONValue = reconstruct_externalized(payload, store=recorder.artifacts)
    assert isinstance(reconstructed, dict)
    assert reconstructed["authorization"] == REDACTED
    assert reconstructed["body"] == (REDACTED + "-正文") * 40

    summary = json.loads(recorder.summary_path.read_text(encoding="utf-8"))
    assert summary["run_id"] == "run-1"
    assert summary["status"] == "succeeded"
    assert summary["dependency_lock_hash"]
