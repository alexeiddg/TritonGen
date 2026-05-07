"""Phase 5 unit tests for ``cluster1.experiments.run_cluster1_modal``.

These cover only the pure helpers and the conversion function. The Modal
roundtrip itself is exercised by the smoke command, not unit tests.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from cluster1.data.kernels import get_kernel_spec
from cluster1.experiments import run_cluster1_modal as runner
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
    assert runner._grammar_conditions("baseline") == [("none", False)]


def test_g_maps_to_g_factor_cell_and_grammar_on() -> None:
    assert runner._grammar_conditions("G") == [("G", True)]


def test_both_expands_baseline_then_g() -> None:
    assert runner._grammar_conditions("both") == [
        ("none", False),
        ("G", True),
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
    grammar_flags = [grammar for *_, grammar, _, _ in cells]

    assert factor_cells == ["none", "none", "none", "G", "G", "G"]
    assert grammar_flags == [False, False, False, True, True, True]
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


# ---------------------------------------------------------------------------
# Remote → GenerationResult conversion
# ---------------------------------------------------------------------------


_FAKE_SOURCE = "import triton\n@triton.jit\ndef relu_kernel():\n    pass\n"


def _baseline_remote_pair() -> tuple[RemoteGenerationResult, RemoteCompileResult]:
    generation = RemoteGenerationResult(
        source=_FAKE_SOURCE,
        model_id="Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        grammar_active=False,
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
        temperature=0.2,
        max_new_tokens=64,
        compile_backend="modal",
        generation_backend="modal",
        fail_fast=False,
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
        assert row["masked_token_rate"] is None


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
    lines = Path(args.output).read_text().splitlines()
    assert len(lines) == 2


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
    lines = Path(args.output).read_text().splitlines()
    assert len(lines) == 2


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
