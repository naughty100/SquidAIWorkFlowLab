import json
from pathlib import Path

import pytest

from ai_workflow_lab.artifacts import (
    ArtifactError,
    ArtifactStore,
    externalize_large_text,
    reconstruct_externalized,
)
from ai_workflow_lab.security import JSONValue


def test_identical_normalized_text_reuses_artifact(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)

    first = store.put_text("第一行\r\n第二行")
    second = store.put_text("第一行\n第二行")

    assert first.artifact_ref == second.artifact_ref
    assert first.content_hash == second.content_hash
    assert len(list((tmp_path / "artifacts" / "trace").glob("*.json.gz"))) == 1
    assert store.read_text(first) == "第一行\n第二行"


def test_externalized_payload_can_be_reconstructed(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    payload: JSONValue = {"small": "ok", "large": "长文本" * 400}

    externalized = externalize_large_text(payload, store=store, threshold=10)
    reconstructed = reconstruct_externalized(externalized, store=store)

    assert reconstructed == payload
    encoded = json.dumps(externalized, ensure_ascii=False)
    assert "长文本" * 400 not in encoded


def test_artifact_reference_cannot_escape_run_dir(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)

    with pytest.raises(ArtifactError, match="超出"):
        store.read_text("../outside.json.gz")
