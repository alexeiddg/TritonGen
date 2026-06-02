"""Seam test: Cluster3JsonlAppendLogger.append -> ``c3.*`` MLflow metrics.

Closes the Phase 5 gap of not exercising the real logger hook end-to-end:
constructs a valid Cluster3EvalRow (reusing the schema test's ``_row`` builder)
and drives the real logger inside an active run, asserting ``c3.*`` metrics are
logged after the JSONL line is written. ``fsync=False`` avoids the directory
fsync that is unavailable in some sandboxes; the tracking hook is independent of
fsync. A fake mlflow is injected.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import shared.tracking.client as client  # noqa: E402
from cluster3.results.dataclass import (  # noqa: E402
    CLUSTER3_RESULTS_SCHEMA_VERSION,
    Cluster3ContentHashSidecar,
)
from cluster3.results.logger import Cluster3JsonlAppendLogger  # noqa: E402
from cluster3.tests.test_cluster3_schema import HASH_A, _row  # noqa: E402
from shared import tracking  # noqa: E402
from shared.tests._fake_mlflow import FakeMlflow  # noqa: E402
from shared.tracking import config  # noqa: E402


def _sidecar(rows: tuple) -> Cluster3ContentHashSidecar:
    generated_hashes: dict[str, dict[str, str]] = {}
    for row in rows:
        assert row.generated_metadata is not None
        generated_hashes[row.condition] = row.generated_metadata.c3_generation_hashes
    return Cluster3ContentHashSidecar(
        schema_version=CLUSTER3_RESULTS_SCHEMA_VERSION,
        eval_pipeline_hashes={"shared/eval/pipeline.py": HASH_A},
        generated_condition_hashes=generated_hashes,
        replay_control_hashes={},
        external_pins={"python": "3.14.2"},
    )


@pytest.fixture
def fake_mlflow(monkeypatch: pytest.MonkeyPatch) -> FakeMlflow:
    fake = FakeMlflow()
    monkeypatch.setattr(client, "_mlflow", fake)
    return fake


def test_logger_hook_logs_c3_metrics_within_run(
    fake_mlflow: FakeMlflow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(config.ENABLE_ENV_VAR, "1")
    row = _row()
    out = tmp_path / "c3.jsonl"

    with tracking.run_context(backend="modal", cluster="cluster3"):
        with Cluster3JsonlAppendLogger(
            out,
            content_hash_sidecar=_sidecar((row,)),
            mode="overwrite",
            fsync=False,
        ) as logger:
            assert logger.append(row) is True

    assert out.read_text("utf-8").strip(), "a JSONL line was written"
    assert len(fake_mlflow.metric_calls) == 1
    metrics = fake_mlflow.metric_calls[0][1]
    assert all(key.startswith("c3.") for key in metrics)
    assert "c3.compile_success" in metrics


def test_logger_hook_noop_when_disabled(
    fake_mlflow: FakeMlflow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv(config.ENABLE_ENV_VAR, raising=False)
    row = _row()
    out = tmp_path / "c3.jsonl"

    with Cluster3JsonlAppendLogger(
        out,
        content_hash_sidecar=_sidecar((row,)),
        mode="overwrite",
        fsync=False,
    ) as logger:
        assert logger.append(row) is True

    assert out.read_text("utf-8").strip(), "JSONL still written when disabled"
    assert fake_mlflow.calls == []