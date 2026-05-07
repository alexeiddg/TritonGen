"""Phase 5 Cluster 1 Modal experiment runner.

Mirrors the cell iteration semantics of ``cluster1.experiments.run_cluster1``
but routes generation and compile through the shared Modal harness adapters
in ``cluster1.generation.modal_generate`` and
``cluster1.validation.modal_compile_check``.

Cluster 1 boundary: this runner records compile errors as result fields,
never as control signals. No timing, profiling, regeneration, or
correctness logic appears here. Reserved factor cells (``C``, ``P``,
``G+C``, …) are rejected at request validation time by the shared schemas.

Local-import contract: heavy ML deps (``torch``, ``transformers``,
``xgrammar``, ``autoawq``) and ``cluster1.data.kernels`` (which top-level
imports ``torch``) are *all* deferred into function bodies so that
``import cluster1.experiments.run_cluster1_modal`` stays cheap on a developer
machine. The local-imports test in ``shared/tests`` enforces this.

CLI::

    modal run -m cluster1.experiments.run_cluster1_modal \\
      --condition baseline \\
      --kernel-class elementwise \\
      --n 1 \\
      --model-id Qwen/Qwen2.5-Coder-7B-Instruct-AWQ \\
      --output outputs/cluster1/modal_smoke_baseline.jsonl
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from shared.modal_harness.app import app

# Modal hydrates ``@app.cls`` / ``@app.function`` references at the moment
# ``app.run()`` enters. Anything registered later — e.g. via lazy imports
# inside ``main`` — comes back as ``ExecutionError: Function has not been
# hydrated``. Both adapters below are light wrappers (no torch / transformers
# / xgrammar / autoawq at module top), so eager-importing them here
# satisfies hydration without breaking the local-import contract; the
# ``test_run_cluster1_modal_does_not_load_heavy_deps`` probe locks that in.
from cluster1.generation.modal_generate import generate_source_modal  # noqa: E402
from cluster1.validation.modal_compile_check import check_compiles_modal  # noqa: E402

DEFAULT_MODEL_ID = "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"
DEFAULT_DATASET_ID = "ScalingIntelligence/KernelBench"
SUPPORTED_BACKENDS: frozenset[str] = frozenset({"modal"})
SUPPORTED_CONDITIONS: tuple[str, ...] = ("baseline", "G", "both")
SUPPORTED_KERNEL_CLASSES: tuple[str, ...] = (
    "elementwise",
    "reduction",
    "matmul",
    "all",
)
SUPPORTED_DTYPES: tuple[str, ...] = ("fp32", "fp16", "bf16")

# Stable namespace so a given (condition, kernel, dtype, seed) cell always
# produces the same run_id. Phase 6 will need this for resume behavior; for
# now it just makes smoke output reproducible.
RUN_ID_NAMESPACE = uuid.UUID("4f0a8a2a-4d4c-4f7d-b4a0-1c2c1c2c1c2c")

# Cluster 1 stores ``CompileErrorType = Literal["CompilationError",
# "RuntimeError", "SignatureError", None]``. The remote harness can also
# emit "TimeoutError" / "UnknownError"; collapse both into "RuntimeError"
# so existing analyzers keep working — the unmapped detail is preserved in
# ``compile_error_msg``.
_REMOTE_TO_LOCAL_ERROR: dict[str, str] = {
    "CompilationError": "CompilationError",
    "RuntimeError": "RuntimeError",
    "SignatureError": "SignatureError",
    "TimeoutError": "RuntimeError",
    "UnknownError": "RuntimeError",
}


# ---------------------------------------------------------------------------
# Pure helpers (importable from tests; do not touch Modal)
# ---------------------------------------------------------------------------


def _grammar_conditions(condition: str) -> list[tuple[str, bool]]:
    """Return ``[(factor_cell, grammar_active), ...]`` for one --condition."""
    if condition == "baseline":
        return [("none", False)]
    if condition == "G":
        return [("G", True)]
    if condition == "both":
        return [("none", False), ("G", True)]
    raise ValueError(
        f"unknown condition {condition!r}. Cluster 1 Modal runner accepts: "
        "baseline, G, both."
    )


def _validate_backends(*, compile_backend: str, generation_backend: str) -> None:
    if compile_backend not in SUPPORTED_BACKENDS:
        raise ValueError(
            f"--compile-backend={compile_backend!r} is not supported. "
            f"Phase 5 only ships the Modal backend; allowed: {sorted(SUPPORTED_BACKENDS)}."
        )
    if generation_backend not in SUPPORTED_BACKENDS:
        raise ValueError(
            f"--generation-backend={generation_backend!r} is not supported. "
            f"Phase 5 only ships the Modal backend; allowed: {sorted(SUPPORTED_BACKENDS)}."
        )


def _selected_kernel_classes(kernel_class: str) -> list[str]:
    if kernel_class == "all":
        from cluster1.data.kernels import KERNEL_SPECS

        return list(KERNEL_SPECS)
    return [kernel_class]


def _validate_dataset_id(kernel_classes: list[str], dataset_id: str) -> None:
    from cluster1.data.kernels import get_kernel_spec

    for kernel_class in kernel_classes:
        spec = get_kernel_spec(kernel_class)
        if spec.dataset_id != dataset_id:
            raise ValueError(
                f"{kernel_class} spec uses dataset_id={spec.dataset_id!r}, "
                f"but CLI requested {dataset_id!r}"
            )


def iter_experiment_cells(
    kernel_classes: list[str],
    condition: str,
    n: int,
    dtypes: tuple[str, ...] = SUPPORTED_DTYPES,
) -> Iterator[tuple[Any, str, bool, str, int]]:
    """Yield ``(spec, factor_cell, grammar_active, dtype, seed)`` cells.

    Iteration order matches the local runner: kernel → condition → dtype → seed.
    """
    from cluster1.data.kernels import KERNEL_SPECS, get_kernel_spec

    selected_classes = (
        list(KERNEL_SPECS) if kernel_classes == ["all"] else kernel_classes
    )
    factor_pairs = _grammar_conditions(condition)
    for kernel_class in selected_classes:
        spec = get_kernel_spec(kernel_class)
        for factor_cell, grammar_active in factor_pairs:
            for dtype in dtypes:
                for seed in range(n):
                    yield spec, factor_cell, grammar_active, dtype, seed


def _expected_row_count(
    kernel_classes: list[str],
    condition: str,
    n: int,
    dtypes: tuple[str, ...] = SUPPORTED_DTYPES,
) -> int:
    selected_classes = (
        list(_kernel_specs_by_class()) if kernel_classes == ["all"] else kernel_classes
    )
    return len(selected_classes) * len(_grammar_conditions(condition)) * len(dtypes) * n


def _kernel_specs_by_class() -> dict[str, Any]:
    from cluster1.data.kernels import KERNEL_SPECS

    return KERNEL_SPECS


def make_run_id(
    *,
    factor_cell: str,
    kernel_class: str,
    kernel_name: str,
    dtype: str,
    seed: int,
) -> str:
    """Deterministic run_id for a given experiment cell."""
    key = f"{factor_cell}/{kernel_class}/{kernel_name}/{dtype}/{seed}"
    return str(uuid.uuid5(RUN_ID_NAMESPACE, key))


def remote_results_to_generation_result(
    *,
    generation,
    compile_,
    spec,
    dtype: str,
    grammar_active: bool,
    seed: int,
    temperature: float,
    model_id: str,
    run_id: str,
):
    """Convert ``(RemoteGenerationResult, RemoteCompileResult)`` into a
    canonical ``GenerationResult`` row for one (kernel, dtype, seed) cell.
    """
    from cluster1.results.dataclass import (
        GenerationResult,
        compute_unique_solution_hash,
    )

    compile_results_by_dtype = dict(compile_.compile_results_by_dtype)
    dtype_success = bool(compile_results_by_dtype.get(dtype, False))
    # The remote returns one ``n_shapes_tested`` summed across dtypes, not a
    # per-dtype count. Approximate per-dtype: full count on success, 0 on
    # failure. Partial-dtype-failure granularity is lost but the magnitude
    # matches the local runner for green rows, and analyzers compare
    # ``compile_success`` not ``n_shapes_tested`` for pass@k.
    n_shapes_for_dtype = (
        len(spec.shapes_by_dtype.get(dtype, [])) if dtype_success else 0
    )

    raw_error = compile_.compile_error_type
    mapped_error = (
        _REMOTE_TO_LOCAL_ERROR.get(raw_error, "RuntimeError")
        if raw_error is not None
        else None
    )

    return GenerationResult(
        source=generation.source,
        model_id=model_id,
        grammar_active=grammar_active,
        kernel_class=spec.kernel_class,
        kernel_name=spec.name,
        dtype=dtype,
        compile_success=bool(compile_.compile_success),
        compile_results_by_dtype=compile_results_by_dtype,
        compile_error_type=mapped_error,
        compile_error_msg=(
            compile_.compile_error_msg[:500]
            if compile_.compile_error_msg is not None
            else None
        ),
        masked_token_rate=generation.masked_token_rate if grammar_active else None,
        unique_solution_hash=compute_unique_solution_hash(generation.source),
        n_shapes_tested=n_shapes_for_dtype,
        generation_seed=seed,
        temperature=temperature,
        run_id=run_id,
        timestamp_utc=datetime.now(UTC).isoformat(),
    )


def _build_progress_line(result, factor_cell: str) -> str:
    condition = "G" if factor_cell == "G" else "baseline"
    error = result.compile_error_type or "none"
    return (
        f"run_id={result.run_id} condition={condition} "
        f"kernel={result.kernel_class}/{result.kernel_name} "
        f"dtype={result.dtype} seed={result.generation_seed} "
        f"compile={'true' if result.compile_success else 'false'} "
        f"error={error}"
    )


def _build_failure_line(
    *,
    run_id: str,
    factor_cell: str,
    kernel_class: str,
    kernel_name: str,
    dtype: str,
    seed: int,
    exc: BaseException,
) -> str:
    condition = "G" if factor_cell == "G" else "baseline"
    return (
        f"run_id={run_id} condition={condition} "
        f"kernel={kernel_class}/{kernel_name} "
        f"dtype={dtype} seed={seed} "
        f"compile=false error={type(exc).__name__}: {exc}"
    )


# ---------------------------------------------------------------------------
# Per-cell remote roundtrip + main loop
# ---------------------------------------------------------------------------


def _run_one_cell(
    *,
    spec,
    factor_cell: str,
    grammar_active: bool,
    dtype: str,
    seed: int,
    model_id: str,
    temperature: float,
    max_new_tokens: int,
    run_id: str,
):
    from cluster1.data.prompts.prompt_contract import build_prompt

    prompt = build_prompt(spec, dtype)

    generation = generate_source_modal(
        prompt=prompt,
        model_id=model_id,
        kernel_class=spec.kernel_class,
        kernel_name=spec.name,
        dtype=dtype,
        grammar_active=grammar_active,
        generation_seed=seed,
        temperature=temperature,
        max_new_tokens=max_new_tokens,
        run_id=run_id,
    )
    compile_ = check_compiles_modal(
        source=generation.source,
        kernel_class=spec.kernel_class,
        kernel_name=spec.name,
        factor_cell=factor_cell,
        run_id=run_id,
    )
    return remote_results_to_generation_result(
        generation=generation,
        compile_=compile_,
        spec=spec,
        dtype=dtype,
        grammar_active=grammar_active,
        seed=seed,
        temperature=temperature,
        model_id=model_id,
        run_id=run_id,
    )


def _run(*, args) -> int:
    """Run all experiment cells described by ``args`` and return the row count.

    Imported by the Modal local entrypoint *and* by tests. Tests pass a
    ``SimpleNamespace`` so they don't need argparse or the Modal runtime.
    """
    from cluster1.results.dataclass import validate_result_invariants
    from cluster1.results.logger import append_result_jsonl

    _validate_backends(
        compile_backend=args.compile_backend,
        generation_backend=args.generation_backend,
    )
    if args.condition not in SUPPORTED_CONDITIONS:
        raise ValueError(
            f"--condition={args.condition!r} not in {list(SUPPORTED_CONDITIONS)}"
        )
    if args.kernel_class not in SUPPORTED_KERNEL_CLASSES:
        raise ValueError(
            f"--kernel-class={args.kernel_class!r} not in "
            f"{list(SUPPORTED_KERNEL_CLASSES)}"
        )

    kernel_classes = _selected_kernel_classes(args.kernel_class)
    _validate_dataset_id(kernel_classes, args.dataset_id)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    requested_rows = _expected_row_count(
        kernel_classes,
        args.condition,
        args.n,
    )
    written_rows = 0
    infrastructure_failures = 0
    for spec, factor_cell, grammar_active, dtype, seed in iter_experiment_cells(
        kernel_classes,
        args.condition,
        args.n,
    ):
        run_id = make_run_id(
            factor_cell=factor_cell,
            kernel_class=spec.kernel_class,
            kernel_name=spec.name,
            dtype=dtype,
            seed=seed,
        )
        try:
            result = _run_one_cell(
                spec=spec,
                factor_cell=factor_cell,
                grammar_active=grammar_active,
                dtype=dtype,
                seed=seed,
                model_id=args.model_id,
                temperature=args.temperature,
                max_new_tokens=args.max_new_tokens,
                run_id=run_id,
            )
            validate_result_invariants(result)
            append_result_jsonl(output, result)
            print(_build_progress_line(result, factor_cell), flush=True)
            written_rows += 1
        except Exception as exc:
            infrastructure_failures += 1
            print(
                _build_failure_line(
                    run_id=run_id,
                    factor_cell=factor_cell,
                    kernel_class=spec.kernel_class,
                    kernel_name=spec.name,
                    dtype=dtype,
                    seed=seed,
                    exc=exc,
                ),
                flush=True,
            )
            if args.fail_fast:
                raise

    if written_rows != requested_rows or infrastructure_failures > 0:
        print(
            "run incomplete "
            f"requested_rows={requested_rows} "
            f"written_rows={written_rows} "
            f"infrastructure_failures={infrastructure_failures}",
            flush=True,
        )
        raise SystemExit(1)
    return written_rows


# ---------------------------------------------------------------------------
# Modal local entrypoint
# ---------------------------------------------------------------------------


@app.local_entrypoint()
def main(
    condition: str,
    kernel_class: str,
    n: int,
    output: str,
    model_id: str = DEFAULT_MODEL_ID,
    dataset_id: str = DEFAULT_DATASET_ID,
    temperature: float = 0.2,
    max_new_tokens: int = 1024,
    compile_backend: str = "modal",
    generation_backend: str = "modal",
    fail_fast: bool = False,
) -> None:
    args = SimpleNamespace(
        condition=condition,
        kernel_class=kernel_class,
        n=n,
        output=output,
        model_id=model_id,
        dataset_id=dataset_id,
        temperature=temperature,
        max_new_tokens=max_new_tokens,
        compile_backend=compile_backend,
        generation_backend=generation_backend,
        fail_fast=fail_fast,
    )
    rows = _run(args=args)
    print(f"wrote {rows} rows to {output}", flush=True)
