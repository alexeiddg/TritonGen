"""Seam C integration tests: Cluster 1 ``append_result_jsonl`` -> ``gen.*`` metrics.

Mirrors the Seam B tests for the *other* write seam (the distinct
``GenerationResult`` record type), and adds an end-to-end test proving the seam
fires inside a real ``run_cluster1.main()`` run together with Seam A's run
boundary/tags. A fake mlflow is injected since mlflow is not installed here.
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
from cluster1.results.dataclass import GenerationResult  # noqa: E402
from cluster1.results.logger import append_result_jsonl  # noqa: E402
from shared import tracking  # noqa: E402
from shared.tests._fake_mlflow import FakeMlflow  # noqa: E402
from shared.tracking import config  # noqa: E402


@pytest.fixture
def fake_mlflow(monkeypatch: pytest.MonkeyPatch) -> FakeMlflow:
    fake = FakeMlflow()
    monkeypatch.setattr(client, "_mlflow", fake)
    return fake


def make_generation_result(**overrides: object) -> GenerationResult:
    base: dict[str, object] = dict(
        source="def relu(x):\n    return x\n",
        model_id="m",
        grammar_active=False,
        grammar_variant=None,
        kernel_class="elementwise",
        kernel_name="relu",
        dtype="fp32",
        compile_success=True,
        compile_results_by_dtype={"fp32": True},
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
    base.update(overrides)
    return GenerationResult(**base)  # type: ignore[arg-type]


def test_active_run_logs_gen_metrics(
    fake_mlflow: FakeMlflow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(config.ENABLE_ENV_VAR, "1")
    out = tmp_path / "gen.jsonl"

    with tracking.run_context(
        run_config={"condition": "baseline", "scale_tier": "smoke"},
        backend="local",
        cluster="cluster1",
    ):
        append_result_jsonl(out, make_generation_result(compile_success=True))
        append_result_jsonl(out, make_generation_result(compile_success=False))

    assert len(out.read_text(encoding="utf-8").splitlines()) == 2

    metric_calls = fake_mlflow.metric_calls
    assert len(metric_calls) == 2
    metrics0, step0 = metric_calls[0][1], metric_calls[0][2]
    assert metrics0["gen.compile_success"] == 1.0
    assert all(key.startswith("gen.") for key in metrics0)
    assert step0 is None  # GenerationResult has no per-sample step
    assert metric_calls[1][1]["gen.compile_success"] == 0.0


def test_disabled_flag_logs_nothing(
    fake_mlflow: FakeMlflow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(config.ENABLE_ENV_VAR, "0")
    out = tmp_path / "gen.jsonl"

    append_result_jsonl(out, make_generation_result())

    assert len(out.read_text(encoding="utf-8").splitlines()) == 1
    assert fake_mlflow.calls == []


def test_enabled_without_active_run_creates_no_metrics(
    fake_mlflow: FakeMlflow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(config.ENABLE_ENV_VAR, "1")
    out = tmp_path / "gen.jsonl"

    append_result_jsonl(out, make_generation_result())  # no run_context

    assert len(out.read_text(encoding="utf-8").splitlines()) == 1
    assert fake_mlflow.metric_calls == []
    assert not any(call[0] == "start_run" for call in fake_mlflow.calls)


def test_tracking_exception_never_escapes_logger(
    fake_mlflow: FakeMlflow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(config.ENABLE_ENV_VAR, "1")

    def boom(metrics, step=None):
        raise RuntimeError("mlflow exploded")

    fake_mlflow.log_metrics = boom  # type: ignore[method-assign]
    out = tmp_path / "gen.jsonl"

    with tracking.run_context(run_config={"condition": "baseline", "scale_tier": "smoke"}):
        append_result_jsonl(out, make_generation_result())  # must not raise

    assert len(out.read_text(encoding="utf-8").splitlines()) == 1


def test_runner_main_logs_gen_metrics_end_to_end(
    fake_mlflow: FakeMlflow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import cluster1.experiments.run_cluster1 as runner
    from cluster1.validation.compile_check import CompileResult

    monkeypatch.setattr(runner, "load_model_and_tokenizer", lambda model_id: ("model", "tok"))
    monkeypatch.setattr(runner, "load_compiled_grammar", lambda gp, mid: "compiled")
    monkeypatch.setattr(
        runner,
        "generate_source",
        lambda **kw: SimpleNamespace(
            source="def relu(x):\n    return x\n",
            masked_token_rate=0.5 if kw["grammar_active"] else None,
            generation_seed=kw["seed"],
            temperature=kw["temperature"],
        ),
    )
    monkeypatch.setattr(
        runner,
        "check_compiles_all_dtypes",
        lambda source, cs, sh: [
            CompileResult(True, None, None, "fp32", 5),
            CompileResult(True, None, None, "fp16", 5),
            CompileResult(True, None, None, "bf16", 5),
        ],
    )
    monkeypatch.setenv(config.ENABLE_ENV_VAR, "1")
    out = tmp_path / "baseline.jsonl"

    exit_code = runner.main(
        ["--condition", "baseline", "--kernel-class", "elementwise",
         "--n", "2", "--output", str(out)]
    )

    assert exit_code == 0
    # baseline x elementwise x n=2 over 3 dtypes = 6 generated rows.
    assert len(out.read_text(encoding="utf-8").splitlines()) == 6

    kinds = [call[0] for call in fake_mlflow.calls]
    assert kinds.count("start_run") == 1
    assert kinds.count("end_run") == 1
    assert len(fake_mlflow.metric_calls) == 6
    for _, metrics, step in fake_mlflow.metric_calls:
        assert all(key.startswith("gen.") for key in metrics)
        assert step is None

    # Seam A's run-level tags are present on the same run.
    tags = next(call[1] for call in fake_mlflow.calls if call[0] == "set_tags")
    assert tags["cluster"] == "cluster1"
    assert tags["source_class"] == "generated_row"
    assert tags["condition"] == "baseline"
