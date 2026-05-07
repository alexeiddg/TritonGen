"""Validate Cluster 1 compile-only GenerationResult JSONL files."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, fields
from itertools import product
from pathlib import Path

from cluster1.results.dataclass import GenerationResult, validate_result_invariants


CONDITIONS = ("baseline", "G")
KERNEL_CLASSES = ("elementwise", "reduction", "matmul")
DTYPES = ("fp32", "fp16", "bf16")
FULL_SAMPLE_SIZE = 20


@dataclass(frozen=True)
class CellIdentity:
    condition: str
    kernel_class: str
    dtype: str
    seed: int

    def label(self) -> str:
        return (
            f"condition={self.condition} "
            f"kernel_class={self.kernel_class} "
            f"dtype={self.dtype} seed={self.seed}"
        )


@dataclass(frozen=True)
class Cluster1ValidationReport:
    input_path: Path
    row_count: int
    expected_row_count: int
    expected_conditions: tuple[str, ...]
    observed_conditions: tuple[str, ...]
    expected_kernel_classes: tuple[str, ...]
    observed_kernel_classes: tuple[str, ...]
    expected_dtypes: tuple[str, ...]
    observed_dtypes: tuple[str, ...]
    file_failures: tuple[str, ...] = ()
    row_count_failures: tuple[str, ...] = ()
    deserialization_failures: tuple[str, ...] = ()
    invariant_failures: tuple[str, ...] = ()
    masked_token_rate_failures: tuple[str, ...] = ()
    compile_results_by_dtype_failures: tuple[str, ...] = ()
    missing_cells: tuple[str, ...] = ()
    unexpected_cells: tuple[str, ...] = ()
    duplicate_identities: tuple[str, ...] = ()
    seed_failures: tuple[str, ...] = ()
    sample_size_failures: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return not any(
            (
                self.file_failures,
                self.row_count_failures,
                self.deserialization_failures,
                self.invariant_failures,
                self.masked_token_rate_failures,
                self.compile_results_by_dtype_failures,
                self.missing_cells,
                self.unexpected_cells,
                self.duplicate_identities,
                self.seed_failures,
                self.sample_size_failures,
            )
        )

    def render(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        lines = [
            f"Cluster 1 result validation: {status}",
            f"input: {self.input_path}",
            f"row_count: {self.row_count} expected={self.expected_row_count}",
            (
                "condition_coverage: "
                f"expected={list(self.expected_conditions)} "
                f"observed={list(self.observed_conditions)}"
            ),
            (
                "kernel_coverage: "
                f"expected={list(self.expected_kernel_classes)} "
                f"observed={list(self.observed_kernel_classes)}"
            ),
            (
                "dtype_coverage: "
                f"expected={list(self.expected_dtypes)} "
                f"observed={list(self.observed_dtypes)}"
            ),
            self._section("file_failures", self.file_failures),
            self._section("row_count_failures", self.row_count_failures),
            self._section("deserialization_failures", self.deserialization_failures),
            self._section("invariant_failures", self.invariant_failures),
            self._section("masked_token_rate_failures", self.masked_token_rate_failures),
            self._section(
                "compile_results_by_dtype_failures",
                self.compile_results_by_dtype_failures,
            ),
            self._section("missing_cells", self.missing_cells),
            self._section("unexpected_cells", self.unexpected_cells),
            self._section("duplicate_identities", self.duplicate_identities),
            self._section("seed_failures", self.seed_failures),
            self._section("sample_size_failures", self.sample_size_failures),
        ]
        return "\n".join(lines)

    @staticmethod
    def _section(name: str, values: tuple[str, ...], limit: int = 5) -> str:
        if not values:
            return f"{name}: 0"
        shown = list(values[:limit])
        suffix = "" if len(values) <= limit else f" ... (+{len(values) - limit} more)"
        return f"{name}: {len(values)}; " + " | ".join(shown) + suffix


def validate_cluster1_results(
    input_path: Path,
    *,
    condition: str,
    kernel_class: str,
    n: int,
    require_full_n20: bool = False,
    allow_duplicate_identities: bool = False,
) -> Cluster1ValidationReport:
    expected_conditions = _expected_conditions(condition)
    expected_kernel_classes = _expected_kernel_classes(kernel_class)
    expected_dtypes = DTYPES
    expected_identities = _expected_identities(
        expected_conditions,
        expected_kernel_classes,
        expected_dtypes,
        n,
    )
    expected_row_count = len(expected_identities)

    file_failures: list[str] = []
    row_count_failures: list[str] = []
    deserialization_failures: list[str] = []
    invariant_failures: list[str] = []
    masked_token_rate_failures: list[str] = []
    compile_results_by_dtype_failures: list[str] = []
    unexpected_cells: list[str] = []
    duplicate_identities: list[str] = []
    seed_failures: list[str] = []
    sample_size_failures: list[str] = []

    rows: list[GenerationResult] = []
    if n <= 0:
        sample_size_failures.append(f"n must be positive; got {n}")
    if require_full_n20 and n != FULL_SAMPLE_SIZE:
        sample_size_failures.append(
            f"--require-full-n20 requires --n {FULL_SAMPLE_SIZE}; got {n}"
        )

    if not input_path.exists():
        file_failures.append(f"{input_path} does not exist")
    elif not input_path.is_file():
        file_failures.append(f"{input_path} is not a file")
    else:
        rows = _load_generation_results(
            input_path,
            deserialization_failures=deserialization_failures,
            invariant_failures=invariant_failures,
        )

    observed_conditions_set: set[str] = set()
    observed_kernel_classes_set: set[str] = set()
    observed_dtypes_set: set[str] = set()
    observed_expected_identities: set[CellIdentity] = set()
    seen_identities: set[CellIdentity] = set()

    for row_number, row in enumerate(rows, start=1):
        row_label = _row_label(row_number, row)
        condition_label = _condition_for_row(row)
        observed_conditions_set.add(condition_label)
        observed_kernel_classes_set.add(row.kernel_class)
        observed_dtypes_set.add(row.dtype)

        _check_masked_token_rate(
            row,
            row_label,
            masked_token_rate_failures,
        )
        _check_compile_results_by_dtype(
            row,
            row_label,
            compile_results_by_dtype_failures,
        )

        identity = _identity_for_row(
            row,
            condition_label,
            row_label,
            seed_failures,
        )
        if identity is None:
            continue

        if identity in seen_identities and not allow_duplicate_identities:
            duplicate_identities.append(identity.label())
        seen_identities.add(identity)

        if identity in expected_identities:
            observed_expected_identities.add(identity)
        else:
            unexpected_cells.append(identity.label())

    if len(rows) != expected_row_count:
        row_count_failures.append(
            f"expected {expected_row_count} rows; observed {len(rows)}"
        )

    missing_cells = tuple(
        identity.label()
        for identity in sorted(
            expected_identities - observed_expected_identities,
            key=_identity_sort_key,
        )
    )

    return Cluster1ValidationReport(
        input_path=input_path,
        row_count=len(rows),
        expected_row_count=expected_row_count,
        expected_conditions=expected_conditions,
        observed_conditions=tuple(sorted(observed_conditions_set)),
        expected_kernel_classes=expected_kernel_classes,
        observed_kernel_classes=tuple(sorted(observed_kernel_classes_set)),
        expected_dtypes=expected_dtypes,
        observed_dtypes=tuple(sorted(observed_dtypes_set)),
        file_failures=tuple(file_failures),
        row_count_failures=tuple(row_count_failures),
        deserialization_failures=tuple(deserialization_failures),
        invariant_failures=tuple(invariant_failures),
        masked_token_rate_failures=tuple(masked_token_rate_failures),
        compile_results_by_dtype_failures=tuple(compile_results_by_dtype_failures),
        missing_cells=missing_cells,
        unexpected_cells=tuple(unexpected_cells),
        duplicate_identities=tuple(duplicate_identities),
        seed_failures=tuple(seed_failures),
        sample_size_failures=tuple(sample_size_failures),
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate Cluster 1 compile-only GenerationResult JSONL before "
            "analysis. compile_success must be strict all-dtype acceptance; "
            "prompt_dtype_compile_success is derived from "
            "compile_results_by_dtype[row.dtype]."
        )
    )
    parser.add_argument("--input", type=Path, required=True, help="Path to result JSONL.")
    parser.add_argument("--condition", choices=("baseline", "G", "both"), required=True)
    parser.add_argument(
        "--kernel-class",
        choices=("elementwise", "reduction", "matmul", "all"),
        required=True,
    )
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument(
        "--require-full-n20",
        action="store_true",
        help="Require --n 20 for full Cluster 1 sample-size validation.",
    )
    parser.add_argument(
        "--allow-duplicate-identities",
        action="store_true",
        help="Allow duplicate condition/kernel/dtype/seed rows.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = validate_cluster1_results(
        args.input,
        condition=args.condition,
        kernel_class=args.kernel_class,
        n=args.n,
        require_full_n20=args.require_full_n20,
        allow_duplicate_identities=args.allow_duplicate_identities,
    )
    print(report.render())
    return 0 if report.passed else 1


def _load_generation_results(
    input_path: Path,
    *,
    deserialization_failures: list[str],
    invariant_failures: list[str],
) -> list[GenerationResult]:
    field_names = {field.name for field in fields(GenerationResult)}
    rows: list[GenerationResult] = []
    with input_path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                deserialization_failures.append(
                    f"{input_path}:{line_number} invalid JSON: {exc}"
                )
                continue
            if not isinstance(record, dict):
                deserialization_failures.append(
                    f"{input_path}:{line_number} expected JSON object"
                )
                continue

            keys = set(record)
            missing = sorted(field_names - keys)
            extra = sorted(keys - field_names)
            if missing:
                deserialization_failures.append(
                    f"{input_path}:{line_number} missing fields: {', '.join(missing)}"
                )
                continue
            if extra:
                deserialization_failures.append(
                    f"{input_path}:{line_number} unexpected fields: {', '.join(extra)}"
                )
                continue
            if not isinstance(record["compile_results_by_dtype"], dict):
                observed_type = type(record["compile_results_by_dtype"]).__name__
                deserialization_failures.append(
                    f"{input_path}:{line_number} compile_results_by_dtype "
                    f"must be an object; got {observed_type}"
                )
                continue

            try:
                row = GenerationResult(**record)
            except TypeError as exc:
                deserialization_failures.append(
                    f"{input_path}:{line_number} GenerationResult error: {exc}"
                )
                continue

            try:
                validate_result_invariants(row)
            except ValueError as exc:
                invariant_failures.append(f"{input_path}:{line_number} {exc}")
            rows.append(row)
    return rows


def _expected_conditions(condition: str) -> tuple[str, ...]:
    if condition == "baseline":
        return ("baseline",)
    if condition == "G":
        return ("G",)
    if condition == "both":
        return CONDITIONS
    raise ValueError(f"unknown condition: {condition!r}")


def _expected_kernel_classes(kernel_class: str) -> tuple[str, ...]:
    if kernel_class == "all":
        return KERNEL_CLASSES
    if kernel_class in KERNEL_CLASSES:
        return (kernel_class,)
    raise ValueError(f"unknown kernel_class: {kernel_class!r}")


def _expected_identities(
    expected_conditions: tuple[str, ...],
    expected_kernel_classes: tuple[str, ...],
    expected_dtypes: tuple[str, ...],
    n: int,
) -> set[CellIdentity]:
    if n <= 0:
        return set()
    return {
        CellIdentity(condition, kernel_class, dtype, seed)
        for condition, kernel_class, dtype, seed in product(
            expected_conditions,
            expected_kernel_classes,
            expected_dtypes,
            range(n),
        )
    }


def _condition_for_row(row: GenerationResult) -> str:
    return "G" if row.grammar_active else "baseline"


def _identity_for_row(
    row: GenerationResult,
    condition: str,
    row_label: str,
    seed_failures: list[str],
) -> CellIdentity | None:
    if not isinstance(row.generation_seed, int):
        seed_failures.append(
            f"{row_label} generation_seed must be an int; got {row.generation_seed!r}"
        )
        return None
    return CellIdentity(
        condition=condition,
        kernel_class=row.kernel_class,
        dtype=row.dtype,
        seed=row.generation_seed,
    )


def _check_masked_token_rate(
    row: GenerationResult,
    row_label: str,
    failures: list[str],
) -> None:
    if not row.grammar_active and row.masked_token_rate is not None:
        failures.append(f"{row_label} baseline/none row has masked_token_rate")
    if row.grammar_active and row.masked_token_rate is None:
        failures.append(f"{row_label} G row missing masked_token_rate")


def _check_compile_results_by_dtype(
    row: GenerationResult,
    row_label: str,
    failures: list[str],
) -> None:
    keys = set(row.compile_results_by_dtype)
    missing = sorted(set(DTYPES) - keys)
    extra = sorted(keys - set(DTYPES))
    if missing:
        failures.append(
            f"{row_label} missing compile_results_by_dtype keys: {', '.join(missing)}"
        )
    if extra:
        failures.append(
            f"{row_label} unexpected compile_results_by_dtype keys: {', '.join(extra)}"
        )
    if row.dtype not in keys:
        failures.append(
            f"{row_label} cannot derive prompt_dtype_compile_success for dtype={row.dtype}"
        )

    non_bool = sorted(
        dtype
        for dtype, success in row.compile_results_by_dtype.items()
        if not isinstance(success, bool)
    )
    if non_bool:
        failures.append(
            f"{row_label} compile_results_by_dtype values must be bool: "
            f"{', '.join(non_bool)}"
        )

    if not missing and not non_bool:
        strict_success = all(row.compile_results_by_dtype[dtype] for dtype in DTYPES)
        if row.compile_success is not strict_success:
            failures.append(
                f"{row_label} compile_success={row.compile_success} does not match "
                f"strict all-dtype acceptance={strict_success}"
            )


def _row_label(row_number: int, row: GenerationResult) -> str:
    return (
        f"row={row_number} run_id={row.run_id!r} "
        f"kernel_class={row.kernel_class} dtype={row.dtype}"
    )


def _identity_sort_key(identity: CellIdentity) -> tuple[str, str, str, int]:
    return (identity.condition, identity.kernel_class, identity.dtype, identity.seed)


if __name__ == "__main__":
    raise SystemExit(main())
