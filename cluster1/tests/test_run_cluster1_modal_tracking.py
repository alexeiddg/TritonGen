"""Phase 5 tests: MLflow run boundary around the Cluster 1 Modal runner.

The Modal path logs from the LOCAL orchestrator: ``main()`` calls
``_run_with_tracking``, which opens a ``backend="modal"`` MLflow run and then
runs ``_run`` (which writes JSONL and, via the shared writer's Seam C, logs
``gen.*`` metrics). No MLflow runs inside the Modal container.

These tests stub ``_run`` so they exercise only the new wrapper (the inner
remote roundtrip is covered by the smoke command, and Seam C itself by
``test_tracking_seam_c.py``). A fake mlflow is injected since mlflow is not
installed here.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

pytest.importorskip("modal")  # the Modal runner imports the shared Modal app

import shared.tracking.client as client  # noqa: E402
from cluster1.experiments import run_cluster1_modal as runner  # noqa: E402
from cluster1.results.dataclass import GenerationResult  # noqa: E402
from cluster1.results.logger import append_result_jsonl  # noqa: E402
from shared.tests._fake_mlflow import FakeMlflow  # noqa: E402
from shared.tracking import config  # noqa: E402


@pytest.fixture
def fake_mlflow(monkeypatch: pytest.MonkeyPatch) -> FakeMlflow:
    fake = FakeMlflow()
    monkeypatch.setattr(client, "_mlflow", fake)
    return fake


def make_gen_result(compile_success: bool = True) -> GenerationResult:
    return GenerationResult(
        source="def relu(x):\n    return x\n",
        model_id="m",
        grammar_active=False,
        grammar_variant=None,
        kernel_class="elementwise",
        kernel_name="relu",
        dtype="fp32",
        compile_success=compile_success,
        compile_results_by_dtype={"fp32": compile_success},
        compile_error_type=None,
        compile_error_msg=None,
        masked_token_rate=None,
        unique_solution_hash="h",
        n_shapes_tested=5,
        generation_seed=0,
        temperature=0.2,
        run_id="r",
        timestamp_utc="t",
    )


def _args(out: Path) -> SimpleNamespace:
    return SimpleNamespace(
        condition="baseline",
        scale_tier="smoke",
        model_id="m",
        output=str(out),
    )


def test_run_with_tracking_opens_modal_run_and_logs(
    fake_mlflow: FakeMlflow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(config.ENABLE_ENV_VAR, "1")
    out = tmp_path / "modal.jsonl"

    def fake_run(*, args: SimpleNamespace) -> int:
        # Stand in for the remote roundtrip: write two records via the real
        # local writer so Seam C fires inside the active run.
        append_result_jsonl(Path(args.output), make_gen_result(compile_success=True))
        append_result_jsonl(Path(args.output), make_gen_result(compile_success=False))
        return 2

    monkeypatch.setattr(runner, "_run", fake_run)

    assert runner._run_with_tracking(args=_args(out)) == 2
    assert len(out.read_text("utf-8").splitlines()) == 2

    kinds = [call[0] for call in fake_mlflow.calls]
    assert kinds.count("start_run") == 1
    assert kinds.count("end_run") == 1

    assert len(fake_mlflow.metric_calls) == 2
    for _, metrics, _step in fake_mlflow.metric_calls:
        assert all(key.startswith("gen.") for key in metrics)

    tags = next(call[1] for call in fake_mlflow.calls if call[0] == "set_tags")
    assert tags["backend"] == "modal"
    assert tags["cluster"] == "cluster1"
    assert tags["condition"] == "baseline"
    assert tags["source_class"] == "generated_row"
    assert tags["reportable"] == "false"  # smoke is never paper evidence


def test_run_with_tracking_disabled_still_runs_and_logs_nothing(
    fake_mlflow: FakeMlflow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv(config.ENABLE_ENV_VAR, raising=False)
    out = tmp_path / "modal.jsonl"
    called: dict[str, bool] = {}

    def fake_run(*, args: SimpleNamespace) -> int:
        called["ran"] = True
        append_result_jsonl(Path(args.output), make_gen_result(compile_success=True))
        return 1

    monkeypatch.setattr(runner, "_run", fake_run)

    assert runner._run_with_tracking(args=_args(out)) == 1
    assert called.get("ran") is True
    assert len(out.read_text("utf-8").splitlines()) == 1
    assert fake_mlflow.calls == []