"""Phase 5 unit tests for ``cluster1.experiments.run_cluster1_modal``.

These cover only the pure helpers and the conversion function. The Modal
roundtrip itself is exercised by the smoke command, not unit tests.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import pytest

from cluster1.data.kernels import get_kernel_spec
from cluster1.experiments import run_cluster1_modal as runner
from cluster1.experiments.validate_cluster1_results import validate_cluster1_results
from cluster1.results.dataclass import (
    GenerationResult,
    validate_result_invariants,
)
from shared.modal_harness.schemas import (
    RemoteCompileResult,
    RemoteGenerationResult,
)


# ---------------------------------------------------------------------------
# Condition → (factor_cell, grammar_active) mapping
# ---------------------------------------------------------------------------


def test_baseline_maps_to_none_factor_cell_and_grammar_off() -> None:
    assert runner._grammar_conditions("baseline") == [("none", False, None)]


def test_g_maps_to_g_factor_cell_and_grammar_on() -> None:
    assert runner._grammar_conditions("G") == [
        ("G", True, "template_upper_bound")
    ]


def test_both_expands_baseline_then_g() -> None:
    assert runner._grammar_conditions("both") == [
        ("none", False, None),
        ("G", True, "template_upper_bound"),
    ]


@pytest.mark.parametrize("condition", ["C", "P", "G+C", "G+P", "C+P", "G+C+P", ""])
def test_unknown_or_reserved_condition_rejected(condition: str) -> None:
    with pytest.raises(ValueError, match="unknown condition"):
        runner._grammar_conditions(condition)


def test_iter_experiment_cells_both_yields_baseline_then_g() -> None:
    """`condition='both'` yields all baseline cells before any G cells, per
    the kernel→condition→dtype→seed iteration order."""
    cells = list(runner.iter_experiment_cells(["elementwise"], "both", n=1))
    factor_cells = [factor for _, factor, *_ in cells]
    grammar_flags = [cell[2] for cell in cells]
    grammar_variants = [cell[3] for cell in cells]

    assert factor_cells == ["none", "none", "none", "G", "G", "G"]
    assert grammar_flags == [False, False, False, True, True, True]
    assert grammar_variants == [
        None,
        None,
        None,
        "template_upper_bound",
        "template_upper_bound",
        "template_upper_bound",
    ]
    # And one row per dtype per condition.
    dtypes = [dtype for *_, dtype, _ in cells]
    assert dtypes == ["fp32", "fp16", "bf16", "fp32", "fp16", "bf16"]


def test_iter_experiment_cells_baseline_elementwise_n1_yields_three_rows() -> None:
    """Mirrors the user's smoke expectation: 1 kernel × 1 condition × 3 dtypes × 1 seed = 3."""
    cells = list(
        runner.iter_experiment_cells(["elementwise"], "baseline", n=1)
    )
    assert len(cells) == 3
    seeds = {seed for *_, seed in cells}
    assert seeds == {0}


# ---------------------------------------------------------------------------
# Backend validation
# ---------------------------------------------------------------------------


def test_modal_backends_accepted() -> None:
    runner._validate_backends(compile_backend="modal", generation_backend="modal")


@pytest.mark.parametrize("bad", ["local", "cpu", "", "MODAL"])
def test_invalid_compile_backend_rejected(bad: str) -> None:
    with pytest.raises(ValueError, match="--compile-backend"):
        runner._validate_backends(compile_backend=bad, generation_backend="modal")


@pytest.mark.parametrize("bad", ["local", "cpu", "", "MODAL"])
def test_invalid_generation_backend_rejected(bad: str) -> None:
    with pytest.raises(ValueError, match="--generation-backend"):
        runner._validate_backends(compile_backend="modal", generation_backend=bad)


# ---------------------------------------------------------------------------
# Deterministic run_id
# ---------------------------------------------------------------------------


def test_make_run_id_is_deterministic() -> None:
    a = runner.make_run_id(
        factor_cell="none",
        kernel_class="elementwise",
        kernel_name="relu",
        dtype="fp32",
        seed=0,
    )
    b = runner.make_run_id(
        factor_cell="none",
        kernel_class="elementwise",
        kernel_name="relu",
        dtype="fp32",
        seed=0,
    )
    assert a == b


def test_make_run_id_distinguishes_factor_cell() -> None:
    none_id = runner.make_run_id(
        factor_cell="none",
        kernel_class="elementwise",
        kernel_name="relu",
        dtype="fp32",
        seed=0,
    )
    g_id = runner.make_run_id(
        factor_cell="G",
        kernel_class="elementwise",
        kernel_name="relu",
        dtype="fp32",
        seed=0,
    )
    assert none_id != g_id


def test_make_run_id_distinguishes_grammar_variant() -> None:
    template_id = runner.make_run_id(
        factor_cell="G",
        grammar_variant="template_upper_bound",
        kernel_class="elementwise",
        kernel_name="relu",
        dtype="fp32",
        seed=0,
    )
    task_agnostic_id = runner.make_run_id(
        factor_cell="G",
        grammar_variant="task_agnostic",
        kernel_class="elementwise",
        kernel_name="relu",
        dtype="fp32",
        seed=0,
    )
    assert template_id != task_agnostic_id


def test_resume_identity_distinguishes_grammar_variant() -> None:
    spec = get_kernel_spec("elementwise")
    run_id_template = runner.make_run_id(
        factor_cell="G",
        grammar_variant="template_upper_bound",
        kernel_class=spec.kernel_class,
        kernel_name=spec.name,
        dtype="fp32",
        seed=0,
    )
    run_id_task = runner.make_run_id(
        factor_cell="G",
        grammar_variant="task_agnostic",
        kernel_class=spec.kernel_class,
        kernel_name=spec.name,
        dtype="fp32",
        seed=0,
    )

    template_identity = runner._resume_identity_for_cell(
        spec=spec,
        factor_cell="G",
        grammar_variant="template_upper_bound",
        dtype="fp32",
        seed=0,
        temperature=0.2,
        model_id="model",
        run_id=run_id_template,
    )
    task_identity = runner._resume_identity_for_cell(
        spec=spec,
        factor_cell="G",
        grammar_variant="task_agnostic",
        dtype="fp32",
        seed=0,
        temperature=0.2,
        model_id="model",
        run_id=run_id_task,
    )

    assert template_identity != task_identity


# ---------------------------------------------------------------------------
# Remote → GenerationResult conversion
# ---------------------------------------------------------------------------


_FAKE_SOURCE = "import triton\n@triton.jit\ndef relu_kernel():\n    pass\n"


def _baseline_remote_pair() -> tuple[RemoteGenerationResult, RemoteCompileResult]:
    generation = RemoteGenerationResult(
        source=_FAKE_SOURCE,
        model_id="Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        grammar_active=False,
        grammar_variant=None,
        masked_token_rate=None,
        generation_seed=0,
        temperature=0.2,
        run_id="rid-baseline",
    )
    compile_ = RemoteCompileResult(
        compile_success=True,
        compile_results_by_dtype={"fp32": True, "fp16": True, "bf16": True},
        n_shapes_tested=9,
        run_id="rid-baseline",
        factor_cell="none",
    )
    return generation, compile_


def _g_remote_pair() -> tuple[RemoteGenerationResult, RemoteCompileResult]:
    generation = RemoteGenerationResult(
        source=_FAKE_SOURCE,
        model_id="Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        grammar_active=True,
        grammar_variant="template_upper_bound",
        masked_token_rate=0.42,
        generation_seed=0,
        temperature=0.2,
        run_id="rid-g",
    )
    compile_ = RemoteCompileResult(
        compile_success=False,
        compile_results_by_dtype={"fp32": False, "fp16": True, "bf16": True},
        compile_error_type="CompilationError",
        compile_error_msg="bad IR",
        n_shapes_tested=4,
        run_id="rid-g",
        factor_cell="G",
    )
    return generation, compile_


def _compile_failure_pair() -> tuple[RemoteGenerationResult, RemoteCompileResult]:
    generation = RemoteGenerationResult(
        source=_FAKE_SOURCE,
        model_id="Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        grammar_active=False,
        grammar_variant=None,
        masked_token_rate=None,
        generation_seed=0,
        temperature=0.2,
        run_id="rid-baseline",
    )
    compile_ = RemoteCompileResult(
        compile_success=False,
        compile_results_by_dtype={"fp32": False, "fp16": False, "bf16": False},
        compile_error_type="SignatureError",
        compile_error_msg="invalid generated launcher signature",
        n_shapes_tested=0,
        run_id="rid-baseline",
        factor_cell="none",
    )
    return generation, compile_


def test_conversion_baseline_produces_valid_generation_result() -> None:
    spec = get_kernel_spec("elementwise")
    generation, compile_ = _baseline_remote_pair()

    result = runner.remote_results_to_generation_result(
        generation=generation,
        compile_=compile_,
        spec=spec,
        dtype="fp32",
        grammar_active=False,
        seed=0,
        temperature=0.2,
        model_id="Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        run_id="rid-baseline",
    )

    assert isinstance(result, GenerationResult)
    validate_result_invariants(result)  # raises on invariant violation
    assert result.kernel_class == "elementwise"
    assert result.kernel_name == "relu"
    assert result.dtype == "fp32"
    assert result.grammar_active is False
    assert result.grammar_variant is None
    assert result.masked_token_rate is None
    assert result.compile_success is True
    assert result.compile_results_by_dtype == {
        "fp32": True,
        "fp16": True,
        "bf16": True,
    }
    assert result.compile_error_type is None
    assert result.compile_error_msg is None
    assert result.n_shapes_tested == len(spec.shapes_by_dtype["fp32"])
    assert result.unique_solution_hash  # nonempty
    assert result.run_id == "rid-baseline"
    assert result.timestamp_utc.endswith("+00:00")


def test_conversion_g_failure_produces_valid_failed_row() -> None:
    spec = get_kernel_spec("elementwise")
    generation, compile_ = _g_remote_pair()

    result = runner.remote_results_to_generation_result(
        generation=generation,
        compile_=compile_,
        spec=spec,
        dtype="fp32",
        grammar_active=True,
        seed=0,
        temperature=0.2,
        model_id="Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        run_id="rid-g",
    )

    validate_result_invariants(result)
    assert result.grammar_active is True
    assert result.grammar_variant == "template_upper_bound"
    assert result.masked_token_rate == 0.42
    assert result.compile_success is False
    assert result.compile_error_type == "CompilationError"
    assert result.compile_error_msg == "bad IR"
    # fp32 is the row's dtype and it failed → 0 shapes credited.
    assert result.n_shapes_tested == 0


def test_conversion_maps_unknown_error_to_runtime_error() -> None:
    spec = get_kernel_spec("elementwise")
    generation, _ = _baseline_remote_pair()
    compile_ = RemoteCompileResult(
        compile_success=False,
        compile_results_by_dtype={"fp32": False, "fp16": False, "bf16": False},
        compile_error_type="UnknownError",
        compile_error_msg="harness-side oops",
        n_shapes_tested=0,
        run_id="rid-baseline",
        factor_cell="none",
    )

    result = runner.remote_results_to_generation_result(
        generation=generation,
        compile_=compile_,
        spec=spec,
        dtype="fp32",
        grammar_active=False,
        seed=0,
        temperature=0.2,
        model_id="Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        run_id="rid-baseline",
    )

    # Cluster 1 taxonomy doesn't include UnknownError; the runner collapses
    # it into RuntimeError so existing analyzers keep working.
    assert result.compile_error_type == "RuntimeError"
    assert result.compile_error_msg == "harness-side oops"


def test_conversion_truncates_long_compile_error_msg() -> None:
    spec = get_kernel_spec("elementwise")
    generation, _ = _baseline_remote_pair()
    compile_ = RemoteCompileResult(
        compile_success=False,
        compile_results_by_dtype={"fp32": False, "fp16": True, "bf16": True},
        compile_error_type="CompilationError",
        compile_error_msg="x" * 600,
        n_shapes_tested=0,
        run_id="rid-baseline",
        factor_cell="none",
    )

    result = runner.remote_results_to_generation_result(
        generation=generation,
        compile_=compile_,
        spec=spec,
        dtype="fp32",
        grammar_active=False,
        seed=0,
        temperature=0.2,
        model_id="Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        run_id="rid-baseline",
    )

    assert result.compile_error_msg is not None
    assert len(result.compile_error_msg) == 500


# ---------------------------------------------------------------------------
# Full _run loop with monkeypatched adapters
# ---------------------------------------------------------------------------


def _make_args(tmp_path: Path, **overrides) -> SimpleNamespace:
    base = dict(
        condition="baseline",
        kernel_class="elementwise",
        n=1,
        output=str(tmp_path / "out.jsonl"),
        model_id="Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        dataset_id="ScalingIntelligence/KernelBench",
        grammar_variant="template_upper_bound",
        grammar_path=runner.DEFAULT_GRAMMAR_PATH,
        temperature=0.2,
        max_new_tokens=64,
        modal_generation_gpu=runner.DEFAULT_GENERATION_GPU,
        compile_backend="modal",
        generation_backend="modal",
        fail_fast=False,
        overwrite=False,
        append=False,
        resume=False,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _patch_adapters(monkeypatch, *, generation, compile_) -> dict:
    """Replace the eagerly-imported adapter symbols on the runner module.

    The runner imports ``generate_source_modal`` / ``check_compiles_modal``
    at module top so Modal hydrates the underlying ``@app.cls`` /
    ``@app.function`` decorators before ``app.run()`` enters. That means
    the runner holds its own references to these callables, so we patch
    on ``runner`` itself rather than on the adapter modules.
    """
    calls: dict = {"generate": [], "compile": []}

    def fake_generate(**kwargs):
        calls["generate"].append(kwargs)
        return generation

    def fake_compile(**kwargs):
        calls["compile"].append(kwargs)
        return compile_

    monkeypatch.setattr(runner, "generate_source_modal", fake_generate)
    monkeypatch.setattr(runner, "check_compiles_modal", fake_compile)
    return calls


def _read_metadata(output: Path) -> dict:
    return json.loads(runner._metadata_path(output).read_text(encoding="utf-8"))


def _existing_result(
    *,
    factor_cell: str = "none",
    dtype: str = "fp32",
    seed: int = 0,
    model_id: str = "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
    temperature: float = 0.2,
    grammar_variant: str | None = None,
) -> GenerationResult:
    spec = get_kernel_spec("elementwise")
    grammar_active = factor_cell == "G"
    if grammar_active and grammar_variant is None:
        grammar_variant = "template_upper_bound"
    return GenerationResult(
        source=_FAKE_SOURCE,
        model_id=model_id,
        grammar_active=grammar_active,
        grammar_variant=grammar_variant if grammar_active else None,
        kernel_class=spec.kernel_class,
        kernel_name=spec.name,
        dtype=dtype,
        compile_success=True,
        compile_results_by_dtype={"fp32": True, "fp16": True, "bf16": True},
        compile_error_type=None,
        compile_error_msg=None,
        masked_token_rate=0.42 if grammar_active else None,
        unique_solution_hash="hash",
        n_shapes_tested=len(spec.shapes_by_dtype[dtype]),
        generation_seed=seed,
        temperature=temperature,
        run_id=runner.make_run_id(
            factor_cell=factor_cell,
            grammar_variant=grammar_variant if grammar_active else None,
            kernel_class=spec.kernel_class,
            kernel_name=spec.name,
            dtype=dtype,
            seed=seed,
        ),
        timestamp_utc="2026-05-08T00:00:00+00:00",
    )


def _write_existing_results(path: Path, rows: list[GenerationResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(asdict(row)) + "\n" for row in rows),
        encoding="utf-8",
    )


def _write_resume_metadata(
    output: Path,
    *,
    condition: str = "baseline",
    kernel_class: str = "elementwise",
    n: int = 1,
    model_id: str = "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
    grammar_variant: str = "template_upper_bound",
    grammar_path: str = runner.DEFAULT_GRAMMAR_PATH,
    expected_rows: int = 3,
    status: str = "failed_partial",
    dataset_id: str = "ScalingIntelligence/KernelBench",
    temperature: float = 0.2,
    max_new_tokens: int = 64,
) -> None:
    runner._metadata_path(output).write_text(
        json.dumps(
            {
                "output_path": str(output),
                "condition": condition,
                "kernel_class": kernel_class,
                "n": n,
                "model_id": model_id,
                "grammar_variant": grammar_variant,
                "expected_rows": expected_rows,
                "written_rows": 2,
                "infrastructure_failures": 1,
                "status": status,
                "started_at_utc": "2026-05-08T00:00:00+00:00",
                "finished_at_utc": "2026-05-08T00:01:00+00:00",
                "git_commit": "test",
                "run_config": {
                    "condition": condition,
                    "kernel_class": kernel_class,
                    "n": n,
                    "output": str(output),
                    "model_id": model_id,
                    "dataset_id": dataset_id,
                    "grammar_variant": grammar_variant,
                    "grammar_path": grammar_path,
                    "temperature": temperature,
                    "max_new_tokens": max_new_tokens,
                    "modal_generation_gpu": runner.DEFAULT_GENERATION_GPU,
                    "compile_backend": "modal",
                    "generation_backend": "modal",
                    "fail_fast": False,
                    "overwrite": False,
                    "append": False,
                    "resume": False,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )


def test_run_writes_three_rows_for_elementwise_baseline_n1(
    monkeypatch, tmp_path
) -> None:
    generation, compile_ = _baseline_remote_pair()
    calls = _patch_adapters(monkeypatch, generation=generation, compile_=compile_)
    args = _make_args(tmp_path)

    rows = runner._run(args=args)

    assert rows == 3
    assert len(calls["generate"]) == 3
    assert len(calls["compile"]) == 3

    out = Path(args.output)
    assert out.exists()
    lines = [json.loads(line) for line in out.read_text().splitlines()]
    assert len(lines) == 3
    assert {row["dtype"] for row in lines} == {"fp32", "fp16", "bf16"}
    for row in lines:
        assert row["compile_success"] is True
        assert row["grammar_active"] is False
        assert row["grammar_variant"] is None
        assert row["masked_token_rate"] is None


def test_run_writes_template_upper_bound_for_g_by_default(
    monkeypatch, tmp_path
) -> None:
    generation, compile_ = _g_remote_pair()
    calls = _patch_adapters(monkeypatch, generation=generation, compile_=compile_)
    args = _make_args(tmp_path, condition="G")

    rows = runner._run(args=args)

    assert rows == 3
    assert {call["grammar_variant"] for call in calls["generate"]} == {
        "template_upper_bound"
    }
    lines = [json.loads(line) for line in Path(args.output).read_text().splitlines()]
    assert {row["grammar_variant"] for row in lines} == {"template_upper_bound"}


def test_task_agnostic_schema_path_requires_explicit_grammar_path(
    monkeypatch, tmp_path
) -> None:
    generation, compile_ = _g_remote_pair()
    calls = _patch_adapters(monkeypatch, generation=generation, compile_=compile_)
    args = _make_args(tmp_path, condition="G", grammar_variant="task_agnostic")

    with pytest.raises(ValueError, match="task-agnostic grammar_path"):
        runner._run(args=args)

    assert calls["generate"] == []
    assert calls["compile"] == []


def test_run_passes_modal_generation_gpu_to_generation_adapter(
    monkeypatch, tmp_path
) -> None:
    generation, compile_ = _baseline_remote_pair()
    calls = _patch_adapters(monkeypatch, generation=generation, compile_=compile_)
    args = _make_args(tmp_path, modal_generation_gpu="L4")

    runner._run(args=args)

    assert len(calls["generate"]) == 3
    assert {call["modal_generation_gpu"] for call in calls["generate"]} == {"L4"}
    metadata = _read_metadata(Path(args.output))
    assert metadata["grammar_variant"] == "template_upper_bound"
    assert metadata["run_config"]["grammar_variant"] == "template_upper_bound"
    assert metadata["run_config"]["modal_generation_gpu"] == "L4"


def test_existing_output_without_mode_fails_before_remote_adapters(
    monkeypatch, tmp_path
) -> None:
    generation, compile_ = _baseline_remote_pair()
    calls = _patch_adapters(monkeypatch, generation=generation, compile_=compile_)
    output = tmp_path / "out.jsonl"
    output.write_text("stale row\n", encoding="utf-8")

    args = _make_args(tmp_path, output=str(output))
    with pytest.raises(runner.OutputPreflightError, match="Output exists"):
        runner._run(args=args)

    assert calls["generate"] == []
    assert calls["compile"] == []
    assert output.read_text(encoding="utf-8") == "stale row\n"


def test_overwrite_removes_existing_output_and_sidecar(monkeypatch, tmp_path) -> None:
    generation, compile_ = _baseline_remote_pair()
    _patch_adapters(monkeypatch, generation=generation, compile_=compile_)
    output = tmp_path / "out.jsonl"
    output.write_text("stale row\n", encoding="utf-8")
    runner._metadata_path(output).write_text(
        json.dumps({"status": "stale"}) + "\n",
        encoding="utf-8",
    )

    args = _make_args(tmp_path, output=str(output), overwrite=True)
    rows = runner._run(args=args)

    assert rows == 3
    lines = output.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    assert "stale row" not in output.read_text(encoding="utf-8")
    metadata = _read_metadata(output)
    assert metadata["status"] == "completed"
    assert metadata["written_rows"] == 3


def test_overwrite_does_not_delete_existing_files_before_dataset_validation(
    monkeypatch, tmp_path
) -> None:
    generation, compile_ = _baseline_remote_pair()
    calls = _patch_adapters(monkeypatch, generation=generation, compile_=compile_)
    output = tmp_path / "out.jsonl"
    meta_path = runner._metadata_path(output)
    output.write_text("existing results\n", encoding="utf-8")
    meta_path.write_text(json.dumps({"status": "completed"}) + "\n", encoding="utf-8")

    args = _make_args(
        tmp_path,
        output=str(output),
        overwrite=True,
        dataset_id="typo-dataset",
    )
    with pytest.raises(ValueError, match="dataset_id"):
        runner._run(args=args)

    assert calls["generate"] == []
    assert calls["compile"] == []
    assert output.read_text(encoding="utf-8") == "existing results\n"
    assert meta_path.read_text(encoding="utf-8") == '{"status": "completed"}\n'


def test_append_allows_existing_output(monkeypatch, tmp_path) -> None:
    generation, compile_ = _baseline_remote_pair()
    calls = _patch_adapters(monkeypatch, generation=generation, compile_=compile_)
    output = tmp_path / "out.jsonl"
    output.write_text("stale row\n", encoding="utf-8")

    args = _make_args(tmp_path, output=str(output), append=True)
    rows = runner._run(args=args)

    assert rows == 3
    assert len(calls["generate"]) == 3
    lines = output.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "stale row"
    assert len(lines) == 4
    metadata = _read_metadata(output)
    assert metadata["run_config"]["append"] is True
    assert metadata["status"] == "completed"


def test_append_requires_existing_output_trailing_newline(
    monkeypatch, tmp_path
) -> None:
    generation, compile_ = _baseline_remote_pair()
    calls = _patch_adapters(monkeypatch, generation=generation, compile_=compile_)
    output = tmp_path / "out.jsonl"
    output.write_text("stale row without newline", encoding="utf-8")

    args = _make_args(tmp_path, output=str(output), append=True)
    with pytest.raises(runner.OutputPreflightError, match="trailing newline"):
        runner._run(args=args)

    assert calls["generate"] == []
    assert calls["compile"] == []
    assert output.read_text(encoding="utf-8") == "stale row without newline"


def test_overwrite_and_append_together_fail_before_remote_adapters(
    monkeypatch, tmp_path
) -> None:
    generation, compile_ = _baseline_remote_pair()
    calls = _patch_adapters(monkeypatch, generation=generation, compile_=compile_)
    args = _make_args(tmp_path, overwrite=True, append=True)

    with pytest.raises(runner.OutputPreflightError, match="mutually exclusive"):
        runner._run(args=args)

    assert calls["generate"] == []
    assert calls["compile"] == []


@pytest.mark.parametrize("mode", ["overwrite", "append"])
def test_resume_is_mutually_exclusive_with_write_modes(
    monkeypatch, tmp_path, mode: str
) -> None:
    generation, compile_ = _baseline_remote_pair()
    calls = _patch_adapters(monkeypatch, generation=generation, compile_=compile_)
    args = _make_args(tmp_path, resume=True, **{mode: True})

    with pytest.raises(runner.OutputPreflightError, match="mutually exclusive"):
        runner._run(args=args)

    assert calls["generate"] == []
    assert calls["compile"] == []


def test_metadata_records_running_then_completed(monkeypatch, tmp_path) -> None:
    generation, compile_ = _baseline_remote_pair()
    _patch_adapters(monkeypatch, generation=generation, compile_=compile_)
    observed_statuses: list[str] = []
    original_write = runner._write_run_metadata

    def spy_write(path, metadata):
        observed_statuses.append(metadata["status"])
        original_write(path, metadata)

    monkeypatch.setattr(runner, "_write_run_metadata", spy_write)
    args = _make_args(tmp_path)

    runner._run(args=args)

    assert observed_statuses[0] == "running"
    assert observed_statuses[-1] == "completed"
    metadata = _read_metadata(Path(args.output))
    assert metadata["status"] == "completed"
    assert metadata["expected_rows"] == 3
    assert metadata["written_rows"] == 3
    assert metadata["infrastructure_failures"] == 0
    assert metadata["finished_at_utc"] is not None


def test_run_invalid_backend_rejected(monkeypatch, tmp_path) -> None:
    args = _make_args(tmp_path, compile_backend="local")
    with pytest.raises(ValueError, match="--compile-backend"):
        runner._run(args=args)


def test_run_generation_adapter_failure_exits_nonzero_after_continuing(
    monkeypatch, tmp_path
) -> None:
    """Generation infrastructure failures may continue but cannot exit cleanly."""
    generation, compile_ = _baseline_remote_pair()
    n_calls = {"value": 0}

    def fake_generate(**kwargs):
        n_calls["value"] += 1
        if n_calls["value"] == 2:  # fail the second cell (fp16)
            raise RuntimeError("boom on fp16")
        return generation

    monkeypatch.setattr(runner, "generate_source_modal", fake_generate)
    monkeypatch.setattr(runner, "check_compiles_modal", lambda **kw: compile_)

    args = _make_args(tmp_path)
    with pytest.raises(SystemExit) as excinfo:
        runner._run(args=args)

    assert excinfo.value.code == 1
    # 3 cells attempted, 1 failed, 2 valid rows written.
    assert n_calls["value"] == 3
    output = Path(args.output)
    lines = output.read_text().splitlines()
    assert len(lines) == 2
    metadata = _read_metadata(output)
    assert metadata["status"] == "failed_partial"
    assert metadata["expected_rows"] == 3
    assert metadata["written_rows"] == 2
    assert metadata["infrastructure_failures"] == 1


def test_run_compile_adapter_failure_exits_nonzero_after_continuing(
    monkeypatch, tmp_path
) -> None:
    """Compile adapter exceptions are infrastructure failures, not compile rows."""
    generation, compile_ = _baseline_remote_pair()
    n_calls = {"value": 0}

    def fake_compile(**kwargs):
        n_calls["value"] += 1
        if n_calls["value"] == 2:
            raise RuntimeError("compile RPC failed")
        return compile_

    monkeypatch.setattr(runner, "generate_source_modal", lambda **kw: generation)
    monkeypatch.setattr(runner, "check_compiles_modal", fake_compile)

    args = _make_args(tmp_path)
    with pytest.raises(SystemExit) as excinfo:
        runner._run(args=args)

    assert excinfo.value.code == 1
    assert n_calls["value"] == 3
    output = Path(args.output)
    lines = output.read_text().splitlines()
    assert len(lines) == 2
    metadata = _read_metadata(output)
    assert metadata["status"] == "failed_partial"
    assert metadata["written_rows"] == 2
    assert metadata["infrastructure_failures"] == 1


def test_run_compile_recursion_error_is_infrastructure_failure(
    monkeypatch, tmp_path
) -> None:
    """A RecursionError from the adapter is not a structured compile row."""
    generation, compile_ = _baseline_remote_pair()
    n_calls = {"value": 0}

    def fake_compile(**kwargs):
        n_calls["value"] += 1
        if n_calls["value"] == 2:
            raise RecursionError("modal adapter recursion")
        return compile_

    monkeypatch.setattr(runner, "generate_source_modal", lambda **kw: generation)
    monkeypatch.setattr(runner, "check_compiles_modal", fake_compile)

    args = _make_args(tmp_path)
    with pytest.raises(SystemExit) as excinfo:
        runner._run(args=args)

    assert excinfo.value.code == 1
    assert n_calls["value"] == 3
    output = Path(args.output)
    lines = [json.loads(line) for line in output.read_text().splitlines()]
    assert len(lines) == 2
    assert {row["compile_error_type"] for row in lines} == {None}
    metadata = _read_metadata(output)
    assert metadata["status"] == "failed_partial"
    assert metadata["written_rows"] == 2
    assert metadata["infrastructure_failures"] == 1


def test_run_remote_compile_failure_row_exits_zero(monkeypatch, tmp_path) -> None:
    """A structured compile failure is a valid result row, not infra failure."""
    generation, compile_ = _compile_failure_pair()
    _patch_adapters(monkeypatch, generation=generation, compile_=compile_)

    args = _make_args(tmp_path)
    rows = runner._run(args=args)

    assert rows == 3
    lines = [json.loads(line) for line in Path(args.output).read_text().splitlines()]
    assert len(lines) == 3
    assert {row["compile_success"] for row in lines} == {False}
    assert {row["compile_error_type"] for row in lines} == {"SignatureError"}


def test_resume_requires_metadata_sidecar_for_non_empty_output(
    monkeypatch, tmp_path
) -> None:
    generation, compile_ = _baseline_remote_pair()
    calls = _patch_adapters(monkeypatch, generation=generation, compile_=compile_)
    output = tmp_path / "out.jsonl"
    _write_existing_results(output, [_existing_result(dtype="fp32")])

    args = _make_args(tmp_path, output=str(output), resume=True)
    with pytest.raises(runner.OutputPreflightError, match="metadata sidecar"):
        runner._run(args=args)

    assert calls["generate"] == []
    assert calls["compile"] == []


def test_resume_requires_existing_output_trailing_newline(
    monkeypatch, tmp_path
) -> None:
    generation, compile_ = _baseline_remote_pair()
    calls = _patch_adapters(monkeypatch, generation=generation, compile_=compile_)
    output = tmp_path / "out.jsonl"
    row_text = json.dumps(asdict(_existing_result(dtype="fp32")))
    output.write_text(row_text, encoding="utf-8")
    _write_resume_metadata(output)

    args = _make_args(tmp_path, output=str(output), resume=True)
    with pytest.raises(runner.OutputPreflightError, match="trailing newline"):
        runner._run(args=args)

    assert calls["generate"] == []
    assert calls["compile"] == []
    assert output.read_text(encoding="utf-8") == row_text


def test_resume_fails_when_existing_run_id_does_not_match_cell(
    monkeypatch, tmp_path
) -> None:
    generation, compile_ = _baseline_remote_pair()
    calls = _patch_adapters(monkeypatch, generation=generation, compile_=compile_)
    output = tmp_path / "out.jsonl"
    row = _existing_result(dtype="fp32")
    wrong_run_id_row = GenerationResult(
        **dict(asdict(row), run_id="stale-or-hand-copied-run-id")
    )
    _write_existing_results(output, [wrong_run_id_row])
    _write_resume_metadata(output)

    args = _make_args(tmp_path, output=str(output), resume=True)
    with pytest.raises(ValueError, match="outside this resume run"):
        runner._run(args=args)

    assert calls["generate"] == []
    assert calls["compile"] == []


@pytest.mark.parametrize(
    "bad_fields, match",
    [
        (
            {"compile_results_by_dtype": {"fp32": True, "fp16": True}},
            "missing compile_results_by_dtype keys",
        ),
        (
            {
                "compile_success": True,
                "compile_results_by_dtype": {
                    "fp32": True,
                    "fp16": False,
                    "bf16": True,
                },
            },
            "strict all-dtype acceptance=False",
        ),
    ],
)
def test_resume_fails_on_invalid_existing_compile_fields_before_remote_calls(
    monkeypatch, tmp_path, bad_fields: dict, match: str
) -> None:
    generation, compile_ = _baseline_remote_pair()
    calls = _patch_adapters(monkeypatch, generation=generation, compile_=compile_)
    output = tmp_path / "out.jsonl"
    bad_row = GenerationResult(
        **dict(asdict(_existing_result(dtype="fp32")), **bad_fields)
    )
    _write_existing_results(
        output,
        [
            bad_row,
            _existing_result(dtype="fp16"),
        ],
    )
    original_contents = output.read_text(encoding="utf-8")
    _write_resume_metadata(output)

    args = _make_args(tmp_path, output=str(output), resume=True)
    with pytest.raises(ValueError, match=match):
        runner._run(args=args)

    assert calls["generate"] == []
    assert calls["compile"] == []
    assert output.read_text(encoding="utf-8") == original_contents


def test_resume_skips_existing_rows_and_writes_only_missing(
    monkeypatch, tmp_path
) -> None:
    generation, compile_ = _baseline_remote_pair()
    calls = _patch_adapters(monkeypatch, generation=generation, compile_=compile_)
    output = tmp_path / "out.jsonl"
    _write_existing_results(
        output,
        [
            _existing_result(dtype="fp32"),
            _existing_result(dtype="fp16"),
        ],
    )
    _write_resume_metadata(output)

    args = _make_args(tmp_path, output=str(output), resume=True)
    rows = runner._run(args=args)

    assert rows == 1
    assert [call["dtype"] for call in calls["generate"]] == ["bf16"]
    assert len(calls["compile"]) == 1
    assert len(output.read_text(encoding="utf-8").splitlines()) == 3


def test_resume_metadata_records_skipped_and_newly_written(
    monkeypatch, tmp_path
) -> None:
    generation, compile_ = _baseline_remote_pair()
    _patch_adapters(monkeypatch, generation=generation, compile_=compile_)
    output = tmp_path / "out.jsonl"
    _write_existing_results(
        output,
        [
            _existing_result(dtype="fp32"),
            _existing_result(dtype="fp16"),
        ],
    )
    _write_resume_metadata(output)

    args = _make_args(tmp_path, output=str(output), resume=True)
    runner._run(args=args)

    metadata = _read_metadata(output)
    assert metadata["status"] == "completed"
    assert metadata["resume"] is True
    assert metadata["existing_rows_loaded"] == 2
    assert metadata["skipped_rows"] == 2
    assert metadata["newly_written_rows"] == 1
    assert metadata["written_rows"] == 3


def test_resume_final_output_validates_to_expected_count(
    monkeypatch, tmp_path
) -> None:
    generation, compile_ = _baseline_remote_pair()
    _patch_adapters(monkeypatch, generation=generation, compile_=compile_)
    output = tmp_path / "out.jsonl"
    _write_existing_results(
        output,
        [
            _existing_result(dtype="fp32"),
            _existing_result(dtype="fp16"),
        ],
    )
    _write_resume_metadata(output)

    args = _make_args(tmp_path, output=str(output), resume=True)
    runner._run(args=args)

    report = validate_cluster1_results(
        output,
        condition="baseline",
        kernel_class="elementwise",
        n=1,
    )
    assert report.passed
    assert report.row_count == 3


def test_resume_fails_on_duplicate_existing_row_identities(
    monkeypatch, tmp_path
) -> None:
    generation, compile_ = _baseline_remote_pair()
    calls = _patch_adapters(monkeypatch, generation=generation, compile_=compile_)
    output = tmp_path / "out.jsonl"
    row = _existing_result(dtype="fp32")
    duplicate = GenerationResult(**dict(asdict(row)))
    _write_existing_results(output, [row, duplicate])
    _write_resume_metadata(output)

    args = _make_args(tmp_path, output=str(output), resume=True)
    with pytest.raises(ValueError, match="duplicate existing row identity"):
        runner._run(args=args)

    assert calls["generate"] == []
    assert calls["compile"] == []


def test_resume_fails_on_corrupt_existing_row(monkeypatch, tmp_path) -> None:
    generation, compile_ = _baseline_remote_pair()
    calls = _patch_adapters(monkeypatch, generation=generation, compile_=compile_)
    output = tmp_path / "out.jsonl"
    output.write_text("{not json\n", encoding="utf-8")
    _write_resume_metadata(output)

    args = _make_args(tmp_path, output=str(output), resume=True)
    with pytest.raises(ValueError, match="invalid JSON"):
        runner._run(args=args)

    assert calls["generate"] == []
    assert calls["compile"] == []


def test_run_expected_row_count_mismatch_exits_nonzero(
    monkeypatch, tmp_path
) -> None:
    """A runner accounting bug cannot silently produce fewer rows than requested."""
    generation, compile_ = _baseline_remote_pair()
    _patch_adapters(monkeypatch, generation=generation, compile_=compile_)

    original_iter = runner.iter_experiment_cells
    truncated_cells = list(original_iter(["elementwise"], "baseline", n=1))[:2]

    def fake_iter_experiment_cells(*args, **kwargs):
        yield from truncated_cells

    monkeypatch.setattr(runner, "iter_experiment_cells", fake_iter_experiment_cells)

    args = _make_args(tmp_path)
    with pytest.raises(SystemExit) as excinfo:
        runner._run(args=args)

    assert excinfo.value.code == 1
    lines = Path(args.output).read_text().splitlines()
    assert len(lines) == 2


def test_run_fail_fast_raises_on_first_failure(monkeypatch, tmp_path) -> None:
    def fake_generate(**kwargs):
        raise RuntimeError("first-cell boom")

    monkeypatch.setattr(runner, "generate_source_modal", fake_generate)
    monkeypatch.setattr(runner, "check_compiles_modal", lambda **kw: None)

    args = _make_args(tmp_path, fail_fast=True)
    with pytest.raises(RuntimeError, match="first-cell boom"):
        runner._run(args=args)
