"""Seam B integration tests: `append_result` -> MLflow `eval.*` metrics.

`mlflow` is not installed in this environment, so a fake mlflow client is
injected into `shared.tracking.client._mlflow` and records calls. These tests
lock the Phase 2 contract:

* an active run logs `eval.*` metrics stepped by `sample_index`;
* the disabled flag logs nothing (JSONL still written);
* the flag on but no active run creates no metrics and no implicit run;
* a tracking exception never escapes `append_result` (JSONL still written).
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import shared.tracking.client as client  # noqa: E402
from shared import tracking  # noqa: E402
from shared.eval.schema import EvalResult, append_result  # noqa: E402
from shared.tracking import config  # noqa: E402


class FakeMlflow:
    """Records calls and tracks active-run state, like a tiny mlflow stub."""

    def __init__(self) -> None:
        self.calls: list = []
        self._active = False

    def set_tracking_uri(self, uri) -> None:
        self.calls.append(("set_tracking_uri", uri))

    def set_experiment(self, name) -> None:
        self.calls.append(("set_experiment", name))

    def start_run(self):
        self._active = True
        self.calls.append(("start_run",))
        return SimpleNamespace(info=SimpleNamespace(run_id="fake"))

    def active_run(self):
        return SimpleNamespace() if self._active else None

    def log_params(self, params) -> None:
        self.calls.append(("log_params", dict(params)))

    def set_tags(self, tags) -> None:
        self.calls.append(("set_tags", dict(tags)))

    def set_tag(self, key, value) -> None:
        self.calls.append(("set_tag", key, value))

    def log_metrics(self, metrics, step=None) -> None:
        self.calls.append(("log_metrics", dict(metrics), step))

    def end_run(self) -> None:
        self._active = False
        self.calls.append(("end_run",))

    @property
    def metric_calls(self) -> list:
        return [call for call in self.calls if call[0] == "log_metrics"]


@pytest.fixture
def fake_mlflow(monkeypatch: pytest.MonkeyPatch) -> FakeMlflow:
    fake = FakeMlflow()
    monkeypatch.setattr(client, "_mlflow", fake)
    return fake


def make_eval_result(**overrides: object) -> EvalResult:
    base: dict[str, object] = dict(
        kernel_id=1,
        kernel_name="relu",
        kernel_class="elementwise",
        kernelbench_level=1,
        condition="C",
        sample_index=2,
        model_id="m",
        run_id="r",
        timestamp="t",
        dtype_tested="fp32",
        source="x",
        source_hash="h",
        ast_hash=None,
        level_reached=1,
        parse_success=True,
        parse_error=None,
        has_triton_decorator=True,
        signature_valid=True,
        compile_success=True,
        compile_error=None,
        failure_code=None,
    )
    base.update(overrides)
    return EvalResult(**base)  # type: ignore[arg-type]


def test_active_run_logs_eval_metrics_stepped(
    fake_mlflow: FakeMlflow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(config.ENABLE_ENV_VAR, "1")
    out = tmp_path / "eval.jsonl"

    with tracking.run_context(
        run_config={"condition": "C", "scale_tier": "smoke"},
        backend="local",
        cluster="cluster2",
    ):
        append_result(out, make_eval_result(sample_index=2, compile_success=True))
        append_result(out, make_eval_result(sample_index=3, compile_success=False))

    assert len(out.read_text(encoding="utf-8").splitlines()) == 2

    metric_calls = fake_mlflow.metric_calls
    assert len(metric_calls) == 2
    metrics0, step0 = metric_calls[0][1], metric_calls[0][2]
    assert metrics0["eval.compile_success"] == 1.0
    assert metrics0["eval.level_reached"] == 1.0
    assert step0 == 2
    assert all(key.startswith("eval.") for key in metrics0)
    metrics1, step1 = metric_calls[1][1], metric_calls[1][2]
    assert metrics1["eval.compile_success"] == 0.0
    assert step1 == 3


def test_disabled_flag_logs_nothing(
    fake_mlflow: FakeMlflow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(config.ENABLE_ENV_VAR, "0")
    out = tmp_path / "eval.jsonl"

    append_result(out, make_eval_result())

    assert len(out.read_text(encoding="utf-8").splitlines()) == 1
    assert fake_mlflow.calls == []


def test_enabled_without_active_run_creates_no_metrics(
    fake_mlflow: FakeMlflow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(config.ENABLE_ENV_VAR, "1")
    out = tmp_path / "eval.jsonl"

    # No run_context: append_result must not open a run or log metrics.
    append_result(out, make_eval_result())

    assert len(out.read_text(encoding="utf-8").splitlines()) == 1
    assert fake_mlflow.metric_calls == []
    assert not any(call[0] == "start_run" for call in fake_mlflow.calls)


def test_tracking_exception_never_escapes_append_result(
    fake_mlflow: FakeMlflow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(config.ENABLE_ENV_VAR, "1")

    def boom(metrics, step=None):
        raise RuntimeError("mlflow exploded")

    fake_mlflow.log_metrics = boom  # type: ignore[method-assign]
    out = tmp_path / "eval.jsonl"

    with tracking.run_context(run_config={"condition": "C", "scale_tier": "smoke"}):
        append_result(out, make_eval_result())  # must not raise

    assert len(out.read_text(encoding="utf-8").splitlines()) == 1
