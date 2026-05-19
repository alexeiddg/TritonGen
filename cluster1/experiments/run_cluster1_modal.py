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
from dataclasses import dataclass, fields
from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
from typing import Any

from shared.modal_harness.app import app

from cluster1.constants import DEFAULT_MAX_NEW_TOKENS

# Modal hydrates ``@app.cls`` / ``@app.function`` references at the moment
# ``app.run()`` enters. Anything registered later — e.g. via lazy imports
# inside ``main`` — comes back as ``ExecutionError: Function has not been
# hydrated``. Both adapters below are light wrappers (no torch / transformers
# / xgrammar / autoawq at module top), so eager-importing them here
# satisfies hydration without breaking the local-import contract; the
# ``test_run_cluster1_modal_does_not_load_heavy_deps`` probe locks that in.
from cluster1.generation.modal_generate import (  # noqa: E402
    DEFAULT_GRAMMAR_PATH,
    generate_source_modal,
)
from cluster1.generation.grammar_variants import grammar_path_for_cell  # noqa: E402
from cluster1.results.dataclass import (  # noqa: E402
    DEFAULT_GRAMMAR_VARIANT,
    GENERATION_METADATA_SCHEMA_VERSION,
    VALID_GRAMMAR_VARIANTS,
    generation_result_record_for_deserialization,
    grammar_variant_for_cell,
    validate_grammar_path_variant_invariants,
    validate_paper_scale_metadata,
)
from cluster1.validation.modal_compile_check import check_compiles_modal  # noqa: E402
from shared.eval.failure_taxonomy import (  # noqa: E402
    canonical_failure_code_from_compile_error,
)
from shared.modal_harness.generation import DEFAULT_GENERATION_GPU  # noqa: E402

DEFAULT_MODEL_ID = "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"
DEFAULT_MODEL_REVISION = "8e8ed243bbe6f9a5aff549a0924562fc719b2b8a"
DEFAULT_DATASET_ID = "ScalingIntelligence/KernelBench"
SUPPORTED_BACKENDS: frozenset[str] = frozenset({"modal"})
SUPPORTED_CONDITIONS: tuple[str, ...] = ("baseline", "G", "both")
SUPPORTED_GRAMMAR_VARIANTS: tuple[str, ...] = (*VALID_GRAMMAR_VARIANTS, "both")
SUPPORTED_KERNEL_CLASSES: tuple[str, ...] = (
    "elementwise",
    "reduction",
    "matmul",
    "all",
)
SUPPORTED_DTYPES: tuple[str, ...] = ("fp32", "fp16", "bf16")
SUPPORTED_SCALE_TIERS: tuple[str, ...] = ("smoke", "development", "paper")
RUNNING_STATUS = "running"
COMPLETED_STATUS = "completed"
FAILED_PARTIAL_STATUS = "failed_partial"

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


class OutputPreflightError(ValueError):
    """Raised before any remote call when output mode is unsafe."""


@dataclass(frozen=True)
class ResumeIdentity:
    run_id: str
    condition: str
    grammar_variant: str | None
    kernel_class: str
    kernel_name: str
    dtype: str
    generation_seed: int
    temperature: float
    model_id: str

    def label(self) -> str:
        return (
            f"run_id={self.run_id} condition={self.condition} "
            f"grammar_variant={self.grammar_variant} "
            f"kernel={self.kernel_class}/{self.kernel_name} "
            f"dtype={self.dtype} seed={self.generation_seed} "
            f"temperature={self.temperature} model_id={self.model_id}"
        )


# ---------------------------------------------------------------------------
# Pure helpers (importable from tests; do not touch Modal)
# ---------------------------------------------------------------------------


def _metadata_path(output: Path) -> Path:
    return Path(f"{output}.meta.json")


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _git_commit_or_none() -> str | None:
    repo_root = Path(__file__).resolve().parents[2]
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    commit = completed.stdout.strip()
    return commit or None


def _json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return str(value)


def _run_config_from_args(args) -> dict[str, Any]:
    return {
        key: _json_safe(value)
        for key, value in sorted(vars(args).items())
        if not key.startswith("_")
    }


def _normalize_revision_args(args) -> None:
    from cluster1.generation.provenance import (
        normalize_explicit_revision,
        resolve_tokenizer_revision,
        tokenizer_revision_policy,
    )

    requested_model_revision = getattr(args, "model_revision", None)
    if requested_model_revision is None and args.model_id == DEFAULT_MODEL_ID:
        requested_model_revision = DEFAULT_MODEL_REVISION

    model_revision = normalize_explicit_revision(
        requested_model_revision,
        field_name="model_revision",
    )
    tokenizer_revision = resolve_tokenizer_revision(
        model_id=args.model_id,
        model_revision=model_revision,
        tokenizer_revision=getattr(args, "tokenizer_revision", None),
    )
    policy = tokenizer_revision_policy(
        model_id=args.model_id,
        model_revision=model_revision,
        tokenizer_revision=getattr(args, "tokenizer_revision", None),
    )
    setattr(args, "model_revision", model_revision)
    setattr(args, "tokenizer_revision", tokenizer_revision)
    setattr(args, "tokenizer_revision_policy", policy)


def _build_initial_metadata(
    *,
    output: Path,
    args,
    expected_rows: int,
    started_at_utc: str,
) -> dict[str, Any]:
    resume = bool(getattr(args, "resume", False))
    metadata: dict[str, Any] = {
        "output_path": str(output),
        "condition": args.condition,
        "kernel_class": args.kernel_class,
        "grammar_variant": _metadata_grammar_variant(args),
        "n": args.n,
        "model_id": args.model_id,
        "model_revision": getattr(args, "model_revision", None),
        "tokenizer_revision": getattr(args, "tokenizer_revision", None),
        "tokenizer_revision_policy": getattr(
            args,
            "tokenizer_revision_policy",
            "best_effort_extraction",
        ),
        "scale_tier": getattr(args, "scale_tier", "smoke"),
        "expected_rows": expected_rows,
        "written_rows": 0,
        "infrastructure_failures": 0,
        "status": RUNNING_STATUS,
        "started_at_utc": started_at_utc,
        "finished_at_utc": None,
        "git_commit": _git_commit_or_none(),
        "run_config": _run_config_from_args(args),
        "generation_metadata_schema_version": GENERATION_METADATA_SCHEMA_VERSION,
    }
    if resume:
        metadata.update(
            {
                "resume": True,
                "existing_rows_loaded": 0,
                "skipped_rows": 0,
                "newly_written_rows": 0,
            }
        )
    return metadata


def _metadata_grammar_variant(args) -> str | None:
    if args.condition == "baseline":
        return None
    return getattr(args, "grammar_variant", None) or DEFAULT_GRAMMAR_VARIANT


def _write_run_metadata(path: Path, metadata: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.tmp")
    temp_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(path)


def _safe_write_run_metadata(path: Path, metadata: dict[str, Any]) -> None:
    try:
        _write_run_metadata(path, metadata)
    except Exception as exc:
        print(f"metadata update failed: {type(exc).__name__}: {exc}", flush=True)


def _update_run_metadata_counts(
    metadata: dict[str, Any],
    *,
    written_rows: int,
    infrastructure_failures: int,
    newly_written_rows: int | None = None,
) -> None:
    metadata["written_rows"] = written_rows
    metadata["infrastructure_failures"] = infrastructure_failures
    if newly_written_rows is not None:
        metadata["newly_written_rows"] = newly_written_rows


def _finish_run_metadata(
    metadata: dict[str, Any],
    *,
    status: str,
    written_rows: int,
    infrastructure_failures: int,
    newly_written_rows: int | None = None,
) -> None:
    _update_run_metadata_counts(
        metadata,
        written_rows=written_rows,
        infrastructure_failures=infrastructure_failures,
        newly_written_rows=newly_written_rows,
    )
    metadata["status"] = status
    metadata["finished_at_utc"] = _utc_now_iso()


def _validate_output_mode(*, overwrite: bool, append: bool, resume: bool) -> None:
    selected_modes = sum(1 for enabled in (overwrite, append, resume) if enabled)
    if selected_modes > 1:
        raise OutputPreflightError(
            "--overwrite, --append, and --resume are mutually exclusive."
        )


def _prepare_output_paths(
    *,
    output: Path,
    metadata_path: Path,
    overwrite: bool,
    append: bool,
    resume: bool,
) -> None:
    _validate_output_mode(overwrite=overwrite, append=append, resume=resume)
    if output.exists() and not output.is_file():
        raise OutputPreflightError(f"{output} exists but is not a file.")
    if metadata_path.exists() and not metadata_path.is_file():
        raise OutputPreflightError(f"{metadata_path} exists but is not a file.")

    if overwrite:
        return

    if append or resume:
        _validate_terminal_jsonl_newline(output)
        return

    if output.exists() and output.stat().st_size > 0:
        raise OutputPreflightError(
            "Output exists. Refusing to append without --append, --overwrite, "
            "or --resume."
        )


def _validate_terminal_jsonl_newline(output: Path) -> None:
    if not output.exists() or output.stat().st_size == 0:
        return
    with output.open("rb") as f:
        f.seek(-1, 2)
        if f.read(1) != b"\n":
            raise OutputPreflightError(
                f"Cannot append to {output}: non-empty JSONL output must end "
                "with a trailing newline."
            )


def _overwrite_output_paths(*, output: Path, metadata_path: Path) -> None:
    if output.exists():
        output.unlink()
    if metadata_path.exists():
        metadata_path.unlink()


def _load_resume_metadata(meta_path: Path) -> dict[str, Any]:
    try:
        record = json.loads(meta_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise OutputPreflightError(
            f"Cannot resume non-empty output without metadata sidecar: {meta_path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise OutputPreflightError(
            f"Cannot resume with corrupt metadata sidecar {meta_path}: {exc}"
        ) from exc
    if not isinstance(record, dict):
        raise OutputPreflightError(
            f"Cannot resume with corrupt metadata sidecar {meta_path}: "
            "expected JSON object."
        )
    return record


def _validate_resume_metadata(
    *,
    meta_path: Path,
    metadata: dict[str, Any],
    output: Path,
    args,
    expected_rows: int,
) -> None:
    missing = sorted(
        key
        for key in (
            "output_path",
            "condition",
            "kernel_class",
            "n",
            "model_id",
            "expected_rows",
            "status",
        )
        if key not in metadata
    )
    if missing:
        raise OutputPreflightError(
            f"Cannot resume with incomplete metadata sidecar {meta_path}: "
            f"missing {', '.join(missing)}."
        )

    status = metadata["status"]
    if status not in {RUNNING_STATUS, COMPLETED_STATUS, FAILED_PARTIAL_STATUS}:
        raise OutputPreflightError(
            f"Cannot resume with metadata status={status!r}; expected one of "
            f"{RUNNING_STATUS!r}, {COMPLETED_STATUS!r}, {FAILED_PARTIAL_STATUS!r}."
        )

    expected_values = {
        "output_path": str(output),
        "condition": args.condition,
        "kernel_class": args.kernel_class,
        "n": args.n,
        "model_id": args.model_id,
        "expected_rows": expected_rows,
    }
    if "grammar_variant" in metadata and args.condition != "baseline":
        expected_values["grammar_variant"] = _metadata_grammar_variant(args)
    mismatches = [
        f"{key}: metadata={metadata.get(key)!r} requested={expected!r}"
        for key, expected in expected_values.items()
        if metadata.get(key) != expected
    ]
    if mismatches:
        raise OutputPreflightError(
            f"Cannot resume because metadata sidecar {meta_path} does not match "
            "this run: "
            + " | ".join(mismatches)
        )

    run_config = metadata.get("run_config")
    if isinstance(run_config, dict):
        comparable_keys = [
            "dataset_id",
            "temperature",
            "max_new_tokens",
            "model_revision",
            "tokenizer_revision",
        ]
        if args.condition != "baseline":
            comparable_keys.append("grammar_variant")
        for key in comparable_keys:
            requested = getattr(args, key, None)
            if key in run_config and run_config[key] != requested:
                raise OutputPreflightError(
                    f"Cannot resume because metadata run_config {key}="
                    f"{run_config[key]!r} does not match requested "
                    f"{requested!r}."
                )


def _validate_resume_manifest_if_needed(
    *,
    output: Path,
    meta_path: Path,
    args,
    expected_rows: int,
) -> None:
    if not output.exists() or output.stat().st_size == 0:
        return
    metadata = _load_resume_metadata(meta_path)
    _validate_resume_metadata(
        meta_path=meta_path,
        metadata=metadata,
        output=output,
        args=args,
        expected_rows=expected_rows,
    )


def _grammar_conditions(
    condition: str,
    grammar_variant: str | None = None,
) -> list[tuple[str, bool, str | None]]:
    """Return ``[(factor_cell, grammar_active, grammar_variant), ...]``."""
    if condition == "baseline":
        return [("none", False, None)]
    if condition == "G":
        return [
            (
                "G",
                True,
                grammar_variant_for_cell(
                    factor_cell="G",
                    grammar_active=True,
                    grammar_variant=variant,
                ),
            )
            for variant in _active_grammar_variants(grammar_variant)
        ]
    if condition == "both":
        return _grammar_conditions("baseline") + _grammar_conditions(
            "G",
            grammar_variant=grammar_variant,
        )
    raise ValueError(
        f"unknown condition {condition!r}. Cluster 1 Modal runner accepts: "
        "baseline, G, both."
    )


def _active_grammar_variants(grammar_variant: str | None) -> tuple[str, ...]:
    if grammar_variant is None:
        return (DEFAULT_GRAMMAR_VARIANT,)
    if grammar_variant == "both":
        return VALID_GRAMMAR_VARIANTS
    if grammar_variant in VALID_GRAMMAR_VARIANTS:
        return (grammar_variant,)
    allowed = ", ".join(SUPPORTED_GRAMMAR_VARIANTS)
    raise ValueError(f"--grammar-variant={grammar_variant!r} not in [{allowed}]")


def _validation_grammar_variants(
    condition: str,
    grammar_variant: str | None,
) -> tuple[str, ...]:
    if condition == "baseline":
        return (DEFAULT_GRAMMAR_VARIANT,)
    return _active_grammar_variants(grammar_variant)


def _validate_grammar_variant_request(
    *,
    condition: str,
    grammar_variant: str | None,
) -> None:
    if condition == "baseline":
        return
    _active_grammar_variants(grammar_variant)


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
    grammar_variant: str | None = DEFAULT_GRAMMAR_VARIANT,
    dtypes: tuple[str, ...] = SUPPORTED_DTYPES,
) -> Iterator[tuple[Any, str, bool, str | None, str, int]]:
    """Yield ``(spec, factor_cell, grammar_active, variant, dtype, seed)`` cells.

    Iteration order matches the local runner: kernel → condition → dtype → seed.
    """
    from cluster1.data.kernels import KERNEL_SPECS, get_kernel_spec

    selected_classes = (
        list(KERNEL_SPECS) if kernel_classes == ["all"] else kernel_classes
    )
    factor_pairs = _grammar_conditions(condition, grammar_variant=grammar_variant)
    for kernel_class in selected_classes:
        spec = get_kernel_spec(kernel_class)
        for factor_cell, grammar_active, grammar_variant in factor_pairs:
            for dtype in dtypes:
                for seed in range(n):
                    yield spec, factor_cell, grammar_active, grammar_variant, dtype, seed


def _expected_row_count(
    kernel_classes: list[str],
    condition: str,
    n: int,
    grammar_variant: str | None = DEFAULT_GRAMMAR_VARIANT,
    dtypes: tuple[str, ...] = SUPPORTED_DTYPES,
) -> int:
    selected_classes = (
        list(_kernel_specs_by_class()) if kernel_classes == ["all"] else kernel_classes
    )
    return (
        len(selected_classes)
        * len(_grammar_conditions(condition, grammar_variant=grammar_variant))
        * len(dtypes)
        * n
    )


def _kernel_specs_by_class() -> dict[str, Any]:
    from cluster1.data.kernels import KERNEL_SPECS

    return KERNEL_SPECS


def make_run_id(
    *,
    factor_cell: str,
    grammar_variant: str | None = None,
    kernel_class: str,
    kernel_name: str,
    dtype: str,
    seed: int,
) -> str:
    """Deterministic run_id for a given experiment cell."""
    grammar_active = factor_cell == "G"
    resolved_variant = grammar_variant_for_cell(
        factor_cell=factor_cell,
        grammar_active=grammar_active,
        grammar_variant=grammar_variant,
    )
    variant_part = f"/{resolved_variant}" if resolved_variant is not None else ""
    key = f"{factor_cell}{variant_part}/{kernel_class}/{kernel_name}/{dtype}/{seed}"
    return str(uuid.uuid5(RUN_ID_NAMESPACE, key))


def _condition_label_for_factor_cell(factor_cell: str) -> str:
    return "G" if factor_cell == "G" else "baseline"


def _condition_label_for_result(result) -> str:
    return "G" if result.grammar_active else "baseline"


def _resume_identity_for_cell(
    *,
    spec,
    factor_cell: str,
    grammar_variant: str | None,
    dtype: str,
    seed: int,
    temperature: float,
    model_id: str,
    run_id: str,
) -> ResumeIdentity:
    return ResumeIdentity(
        run_id=run_id,
        condition=_condition_label_for_factor_cell(factor_cell),
        grammar_variant=grammar_variant,
        kernel_class=spec.kernel_class,
        kernel_name=spec.name,
        dtype=dtype,
        generation_seed=seed,
        temperature=float(temperature),
        model_id=model_id,
    )


def _resume_identity_for_result(result, *, row_label: str) -> ResumeIdentity:
    if not isinstance(result.generation_seed, int):
        raise ValueError(
            f"{row_label} generation_seed must be an int; "
            f"got {result.generation_seed!r}"
        )
    if not isinstance(result.temperature, (int, float)):
        raise ValueError(
            f"{row_label} temperature must be numeric; got {result.temperature!r}"
        )
    if not isinstance(result.model_id, str) or not result.model_id:
        raise ValueError(f"{row_label} model_id must be a nonempty string")
    if not isinstance(result.run_id, str) or not result.run_id:
        raise ValueError(f"{row_label} run_id must be a nonempty string")
    return ResumeIdentity(
        run_id=result.run_id,
        condition=_condition_label_for_result(result),
        grammar_variant=result.grammar_variant,
        kernel_class=result.kernel_class,
        kernel_name=result.kernel_name,
        dtype=result.dtype,
        generation_seed=result.generation_seed,
        temperature=float(result.temperature),
        model_id=result.model_id,
    )


def _validate_resume_result_contract(result, *, row_label: str) -> None:
    keys = set(result.compile_results_by_dtype)
    expected_dtypes = set(SUPPORTED_DTYPES)
    missing = sorted(expected_dtypes - keys)
    extra = sorted(keys - expected_dtypes)
    failures: list[str] = []
    if missing:
        failures.append(
            "missing compile_results_by_dtype keys: " + ", ".join(missing)
        )
    if extra:
        failures.append(
            "unexpected compile_results_by_dtype keys: " + ", ".join(extra)
        )

    non_bool = sorted(
        dtype
        for dtype, success in result.compile_results_by_dtype.items()
        if not isinstance(success, bool)
    )
    if non_bool:
        failures.append(
            "compile_results_by_dtype values must be bool: "
            + ", ".join(non_bool)
        )

    if not missing and not extra and not non_bool:
        strict_success = all(
            result.compile_results_by_dtype[dtype] for dtype in SUPPORTED_DTYPES
        )
        if result.compile_success is not strict_success:
            failures.append(
                f"compile_success={result.compile_success} does not match "
                f"strict all-dtype acceptance={strict_success}"
            )

    if failures:
        raise ValueError(
            f"{row_label} invalid compile result fields: "
            + " | ".join(failures)
        )


def _load_resume_identities(output: Path) -> dict[ResumeIdentity, Any]:
    from cluster1.results.dataclass import (
        GenerationResult,
        validate_result_invariants,
    )

    if not output.exists() or output.stat().st_size == 0:
        return {}

    field_names = {field.name for field in fields(GenerationResult)}
    identities: dict[ResumeIdentity, Any] = {}
    with output.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            row_label = f"{output}:{line_number}"
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{row_label} invalid JSON: {exc}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"{row_label} expected JSON object")
            record = generation_result_record_for_deserialization(record)
            keys = set(record)
            missing = sorted(field_names - keys)
            extra = sorted(keys - field_names)
            if missing:
                raise ValueError(
                    f"{row_label} missing fields: {', '.join(missing)}"
                )
            if extra:
                raise ValueError(
                    f"{row_label} unexpected fields: {', '.join(extra)}"
                )
            if not isinstance(record["compile_results_by_dtype"], dict):
                observed_type = type(record["compile_results_by_dtype"]).__name__
                raise ValueError(
                    f"{row_label} compile_results_by_dtype must be an object; "
                    f"got {observed_type}"
                )

            try:
                result = GenerationResult(**record)
                validate_result_invariants(result)
                _validate_resume_result_contract(result, row_label=row_label)
                identity = _resume_identity_for_result(result, row_label=row_label)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{row_label} corrupt existing row: {exc}") from exc

            if identity in identities:
                raise ValueError(
                    f"{row_label} duplicate existing row identity: "
                    f"{identity.label()}"
                )
            identities[identity] = result
    return identities


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

    _validate_remote_generation_metadata_against_local(generation, grammar_active)
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
    failure_code = (
        compile_.failure_code
        if compile_.failure_code is not None
        else canonical_failure_code_from_compile_error(
            mapped_error,
            compile_.compile_error_msg,
        )
    )

    return GenerationResult(
        source=generation.source,
        model_id=model_id,
        grammar_active=grammar_active,
        grammar_variant=generation.grammar_variant,
        generation_metadata_schema_version=generation.generation_metadata_schema_version,
        grammar_sha=generation.grammar_sha,
        grammar_path=generation.grammar_path,
        gbnf_parse_valid=generation.gbnf_parse_valid,
        semantic_valid=generation.semantic_valid,
        grammar_valid=generation.grammar_valid,
        rejection_layer=generation.rejection_layer,
        stop_reason=generation.stop_reason,
        xgrammar_version=generation.xgrammar_version,
        transformers_version=generation.transformers_version,
        tokenizers_version=generation.tokenizers_version,
        model_revision=generation.model_revision,
        tokenizer_revision=generation.tokenizer_revision,
        modal_image_sha=generation.modal_image_sha,
        modal_image_provenance_sha256=generation.modal_image_provenance_sha256,
        modal_image_provenance_components=(
            generation.modal_image_provenance_components
        ),
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
        failure_code=failure_code,
        masked_token_rate=generation.masked_token_rate if grammar_active else None,
        unique_solution_hash=compute_unique_solution_hash(generation.source),
        n_shapes_tested=n_shapes_for_dtype,
        generation_seed=seed,
        temperature=temperature,
        run_id=run_id,
        timestamp_utc=datetime.now(UTC).isoformat(),
    )


def _validate_remote_generation_metadata_against_local(
    generation,
    grammar_active: bool,
) -> None:
    """Audit Modal validation evidence against the local grammar when possible."""

    if not grammar_active:
        return
    if generation.generation_metadata_schema_version < GENERATION_METADATA_SCHEMA_VERSION:
        raise ValueError(
            "grammar-active Modal row is missing current generation metadata "
            f"schema: expected >= {GENERATION_METADATA_SCHEMA_VERSION}, "
            f"got {generation.generation_metadata_schema_version}"
        )
    if (
        generation.grammar_variant is None
        or generation.grammar_sha is None
        or generation.grammar_path is None
    ):
        raise ValueError("grammar-active Modal row is missing grammar provenance")
    validate_grammar_path_variant_invariants(
        grammar_path=generation.grammar_path,
        grammar_variant=generation.grammar_variant,
    )

    from cluster1.generation.grammar_variants import grammar_path_for_variant
    from cluster1.generation.provenance import sha256_file
    from cluster1.grammar.triton_kernel_validator import validate_source_layers

    local_grammar_path = Path(grammar_path_for_variant(generation.grammar_variant))
    local_sha = sha256_file(local_grammar_path)
    if local_sha != generation.grammar_sha:
        raise ValueError(
            "Modal grammar_sha does not match local canonical grammar: "
            f"variant={generation.grammar_variant!r} "
            f"modal={generation.grammar_sha} local={local_sha}"
        )
    local_validation = validate_source_layers(
        generation.source,
        grammar_path=local_grammar_path,
    )
    expected = local_validation.to_row_fields()
    observed = {
        "gbnf_parse_valid": generation.gbnf_parse_valid,
        "semantic_valid": generation.semantic_valid,
        "grammar_valid": generation.grammar_valid,
        "rejection_layer": generation.rejection_layer,
    }
    if observed != expected:
        raise ValueError(
            "Modal validation fields disagree with local revalidation after "
            f"grammar_sha match: observed={observed!r} expected={expected!r}"
        )


def _build_progress_line(result, factor_cell: str) -> str:
    condition = "G" if factor_cell == "G" else "baseline"
    error = result.compile_error_type or "none"
    return (
        f"run_id={result.run_id} condition={condition} "
        f"grammar_variant={result.grammar_variant} "
        f"kernel={result.kernel_class}/{result.kernel_name} "
        f"dtype={result.dtype} seed={result.generation_seed} "
        f"compile={'true' if result.compile_success else 'false'} "
        f"error={error}"
    )


def _build_failure_line(
    *,
    run_id: str,
    factor_cell: str,
    grammar_variant: str | None,
    kernel_class: str,
    kernel_name: str,
    dtype: str,
    seed: int,
    exc: BaseException,
) -> str:
    condition = "G" if factor_cell == "G" else "baseline"
    return (
        f"run_id={run_id} condition={condition} "
        f"grammar_variant={grammar_variant} "
        f"kernel={kernel_class}/{kernel_name} "
        f"dtype={dtype} seed={seed} "
        f"compile=false error={type(exc).__name__}: {exc}"
    )


def _validate_result_for_scale_tier(result, *, scale_tier: str) -> None:
    if scale_tier != "paper":
        return
    validate_paper_scale_metadata(result)


# ---------------------------------------------------------------------------
# Per-cell remote roundtrip + main loop
# ---------------------------------------------------------------------------


def _run_one_cell(
    *,
    spec,
    factor_cell: str,
    grammar_active: bool,
    grammar_variant: str | None,
    dtype: str,
    seed: int,
    model_id: str,
    model_revision: str | None,
    tokenizer_revision: str | None,
    temperature: float,
    max_new_tokens: int,
    run_id: str,
    grammar_path: str | None,
    modal_generation_gpu: str = DEFAULT_GENERATION_GPU,
):
    from cluster1.data.prompts.prompt_contract import build_prompt

    prompt = build_prompt(spec, dtype)

    generation = generate_source_modal(
        prompt=prompt,
        model_id=model_id,
        model_revision=model_revision,
        tokenizer_revision=tokenizer_revision,
        kernel_class=spec.kernel_class,
        kernel_name=spec.name,
        dtype=dtype,
        grammar_active=grammar_active,
        grammar_variant=grammar_variant,
        grammar_path=grammar_path,
        generation_seed=seed,
        temperature=temperature,
        max_new_tokens=max_new_tokens,
        run_id=run_id,
        modal_generation_gpu=modal_generation_gpu,
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

    output = Path(args.output)
    meta_path = _metadata_path(output)
    metadata: dict[str, Any] | None = None
    requested_rows = 0
    written_rows = 0
    newly_written_rows = 0
    infrastructure_failures = 0
    resume = bool(getattr(args, "resume", False))

    try:
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
        scale_tier = getattr(args, "scale_tier", "smoke")
        if scale_tier not in SUPPORTED_SCALE_TIERS:
            raise ValueError(
                f"--scale-tier={scale_tier!r} not in {list(SUPPORTED_SCALE_TIERS)}"
            )
        _normalize_revision_args(args)
        _validate_grammar_variant_request(
            condition=args.condition,
            grammar_variant=args.grammar_variant,
        )

        overwrite = bool(getattr(args, "overwrite", False))
        append = bool(getattr(args, "append", False))
        _prepare_output_paths(
            output=output,
            metadata_path=meta_path,
            overwrite=overwrite,
            append=append,
            resume=resume,
        )

        kernel_classes = _selected_kernel_classes(args.kernel_class)
        _validate_dataset_id(kernel_classes, args.dataset_id)

        output.parent.mkdir(parents=True, exist_ok=True)
        requested_rows = _expected_row_count(
            kernel_classes,
            args.condition,
            args.n,
            grammar_variant=args.grammar_variant,
        )
        cells = list(
            iter_experiment_cells(
                kernel_classes,
                args.condition,
                args.n,
                grammar_variant=args.grammar_variant,
            )
        )
        if overwrite:
            _overwrite_output_paths(output=output, metadata_path=meta_path)

        existing_identities: dict[ResumeIdentity, Any] = {}
        expected_identities: set[ResumeIdentity] = set()
        if resume:
            _validate_resume_manifest_if_needed(
                output=output,
                meta_path=meta_path,
                args=args,
                expected_rows=requested_rows,
            )
            for spec, factor_cell, _, grammar_variant, dtype, seed in cells:
                expected_run_id = make_run_id(
                    factor_cell=factor_cell,
                    grammar_variant=grammar_variant,
                    kernel_class=spec.kernel_class,
                    kernel_name=spec.name,
                    dtype=dtype,
                    seed=seed,
                )
                expected_identities.add(
                    _resume_identity_for_cell(
                        spec=spec,
                        factor_cell=factor_cell,
                        grammar_variant=grammar_variant,
                        dtype=dtype,
                        seed=seed,
                        temperature=args.temperature,
                        model_id=args.model_id,
                        run_id=expected_run_id,
                    )
                )
            existing_identities = _load_resume_identities(output)
            if scale_tier == "paper":
                for identity, result in existing_identities.items():
                    try:
                        validate_paper_scale_metadata(result)
                    except ValueError as exc:
                        raise ValueError(
                            "existing paper-scale resume row is missing "
                            f"generation metadata: {identity.label()}: {exc}"
                        ) from exc
            unexpected = sorted(
                set(existing_identities) - expected_identities,
                key=lambda identity: identity.label(),
            )
            if unexpected:
                raise ValueError(
                    "existing output contains rows outside this resume run: "
                    + " | ".join(identity.label() for identity in unexpected[:5])
                )
            written_rows = len(existing_identities)

        metadata = _build_initial_metadata(
            output=output,
            args=args,
            expected_rows=requested_rows,
            started_at_utc=_utc_now_iso(),
        )
        if resume:
            metadata["existing_rows_loaded"] = len(existing_identities)
            metadata["skipped_rows"] = len(existing_identities)
            metadata["written_rows"] = len(existing_identities)
        _write_run_metadata(meta_path, metadata)

        for spec, factor_cell, grammar_active, grammar_variant, dtype, seed in cells:
            run_id = make_run_id(
                factor_cell=factor_cell,
                grammar_variant=grammar_variant,
                kernel_class=spec.kernel_class,
                kernel_name=spec.name,
                dtype=dtype,
                seed=seed,
            )
            identity = _resume_identity_for_cell(
                spec=spec,
                factor_cell=factor_cell,
                grammar_variant=grammar_variant,
                dtype=dtype,
                seed=seed,
                temperature=args.temperature,
                model_id=args.model_id,
                run_id=run_id,
            )
            if resume and identity in existing_identities:
                continue
            try:
                result = _run_one_cell(
                    spec=spec,
                    factor_cell=factor_cell,
                    grammar_active=grammar_active,
                    grammar_variant=grammar_variant,
                    dtype=dtype,
                    seed=seed,
                    model_id=args.model_id,
                    model_revision=getattr(args, "model_revision", None),
                    tokenizer_revision=getattr(args, "tokenizer_revision", None),
                    temperature=args.temperature,
                    max_new_tokens=args.max_new_tokens,
                    run_id=run_id,
                    grammar_path=grammar_path_for_cell(
                        grammar_active=grammar_active,
                        grammar_variant=grammar_variant,
                    ),
                    modal_generation_gpu=getattr(
                        args,
                        "modal_generation_gpu",
                        DEFAULT_GENERATION_GPU,
                    ),
                )
                validate_result_invariants(result)
                _validate_result_for_scale_tier(result, scale_tier=scale_tier)
                append_result_jsonl(output, result)
                print(_build_progress_line(result, factor_cell), flush=True)
                newly_written_rows += 1
                written_rows += 1
                _update_run_metadata_counts(
                    metadata,
                    written_rows=written_rows,
                    infrastructure_failures=infrastructure_failures,
                    newly_written_rows=newly_written_rows if resume else None,
                )
                _write_run_metadata(meta_path, metadata)
            except Exception as exc:
                infrastructure_failures += 1
                _update_run_metadata_counts(
                    metadata,
                    written_rows=written_rows,
                    infrastructure_failures=infrastructure_failures,
                    newly_written_rows=newly_written_rows if resume else None,
                )
                _safe_write_run_metadata(meta_path, metadata)
                print(
                    _build_failure_line(
                        run_id=run_id,
                        factor_cell=factor_cell,
                        grammar_variant=grammar_variant,
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

        if resume and infrastructure_failures == 0:
            from cluster1.experiments.validate_cluster1_results import (
                validate_cluster1_results,
            )

            report = validate_cluster1_results(
                output,
                condition=args.condition,
                kernel_class=args.kernel_class,
                n=args.n,
                grammar_variants=_validation_grammar_variants(
                    args.condition,
                    args.grammar_variant,
                ),
                require_generation_metadata=scale_tier == "paper",
            )
            if not report.passed:
                print(report.render(), flush=True)
                raise SystemExit(1)

        if written_rows != requested_rows or infrastructure_failures > 0:
            print(
                "run incomplete "
                f"requested_rows={requested_rows} "
                f"written_rows={written_rows} "
                f"infrastructure_failures={infrastructure_failures}",
                flush=True,
            )
            raise SystemExit(1)

        _finish_run_metadata(
            metadata,
            status=COMPLETED_STATUS,
            written_rows=written_rows,
            infrastructure_failures=infrastructure_failures,
            newly_written_rows=newly_written_rows if resume else None,
        )
        _write_run_metadata(meta_path, metadata)
        return newly_written_rows if resume else written_rows
    except BaseException:
        if metadata is not None:
            _finish_run_metadata(
                metadata,
                status=FAILED_PARTIAL_STATUS,
                written_rows=written_rows,
                infrastructure_failures=infrastructure_failures,
                newly_written_rows=newly_written_rows if resume else None,
            )
            _safe_write_run_metadata(meta_path, metadata)
        raise


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
    model_revision: str | None = None,
    tokenizer_revision: str | None = None,
    dataset_id: str = DEFAULT_DATASET_ID,
    grammar_variant: str = DEFAULT_GRAMMAR_VARIANT,
    grammar_path: str | None = None,
    temperature: float = 0.2,
    max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS,
    modal_generation_gpu: str = DEFAULT_GENERATION_GPU,
    scale_tier: str = "smoke",
    compile_backend: str = "modal",
    generation_backend: str = "modal",
    fail_fast: bool = False,
    overwrite: bool = False,
    append: bool = False,
    resume: bool = False,
) -> None:
    args = SimpleNamespace(
        condition=condition,
        kernel_class=kernel_class,
        n=n,
        output=output,
        model_id=model_id,
        model_revision=model_revision,
        tokenizer_revision=tokenizer_revision,
        dataset_id=dataset_id,
        grammar_variant=grammar_variant,
        grammar_path=grammar_path,
        temperature=temperature,
        max_new_tokens=max_new_tokens,
        modal_generation_gpu=modal_generation_gpu,
        scale_tier=scale_tier,
        compile_backend=compile_backend,
        generation_backend=generation_backend,
        fail_fast=fail_fast,
        overwrite=overwrite,
        append=append,
        resume=resume,
    )
    rows = _run(args=args)
    print(f"wrote {rows} rows to {output}", flush=True)
