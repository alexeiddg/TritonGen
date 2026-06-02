"""Seam test: Cluster2JsonlAppendLogger.append -> ``c2.*`` MLflow metrics.

Closes the Phase 5 gap of not exercising the real logger hook end-to-end:
builds a valid Cluster2EvalRow (reusing the logger test's ``_generated_row`` /
``_sidecar`` helpers) and drives the real logger inside an active run, asserting
``c2.*`` metrics are logged after the JSONL line is written. ``fsync=False``
avoids the directory fsync unavailable in some sandboxes; the tracking hook is
independent of fsync. A fake mlflow is injected.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import shared.tracking.client as client  # noqa: E402
from cluster2.results.logger import Cluster2JsonlAppendLogger  # noqa: E402
from cluster2.tests.test_results_logger import _generated_row, _sidecar  # noqa: E402
from shared import tracking  # noqa: E402
from shared.tests._fake_mlflow import FakeMlflow  # noqa: E402
from shared.tracking import config  # noqa: E402


@pytest.fixture
def fake_mlflow(monkeypatch: pytest.MonkeyPatch) -> FakeMlflow:
    fake = FakeMlflow()
    monkeypatch.setattr(client, "_mlflow", fake)
    return fake


def test_logger_hook_logs_c2_metrics_within_run(
    fake_mlflow: FakeMlflow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(config.ENABLE_ENV_VAR, "1")
    row = _generated_row(condition="C")
    out = tmp_path / "c2.jsonl"

    with tracking.run_context(backend="modal", cluster="cluster2"):
        with Cluster2JsonlAppendLogger(
            out,
            content_hash_sidecar=_sidecar([row]),
            mode="overwrite",
            fsync=False,
        ) as logger:
            assert logger.append(row) is True

    assert out.read_text("utf-8").strip(), "a JSONL line was written"
    assert len(fake_mlflow.metric_calls) == 1
    metrics = fake_mlflow.metric_calls[0][1]
    assert all(key.startswith("c2.") for key in metrics)
    assert "c2.compile_success" in metrics


def test_logger_hook_noop_when_disabled(
    fake_mlflow: FakeMlflow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv(config.ENABLE_ENV_VAR, raising=False)
    row = _generated_row(condition="C")
    out = tmp_path / "c2.jsonl"

    with Cluster2JsonlAppendLogger(
        out,
        content_hash_sidecar=_sidecar([row]),
        mode="overwrite",
        fsync=False,
    ) as logger:
        assert logger.append(row) is True

    assert out.read_text("utf-8").strip(), "JSONL still written when disabled"
    assert fake_mlflow.calls == []