"""Validate L2b full-coverage result and observability artifacts.

This module is intentionally read-only. It reconciles result JSONL files,
content-hash sidecars, and observability sidecars against the existing Cluster 3
L2b planning matrix.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cluster3.planning.grammar_mode_matrix import (
    L2B_SELECTOR_PROFILE_IDS,
    build_l2b_full_coverage_shard_plan,
    l2b_full_coverage_stage_spec,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class ValidationResult:
    stage: str
    wave_id: str | None
    expected_rows: int
    actual_rows: int
    expected_shards: int | None
    complete_shards: int
    duplicate_logical_keys: int
    missing_logical_keys: int
    missing_result_files: tuple[str, ...]
    missing_content_hash_sidecars: tuple[str, ...]
    missing_observability_sidecars: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return (
            self.actual_rows == self.expected_rows
            and self.duplicate_logical_keys == 0
            and self.missing_logical_keys == 0
            and not self.missing_result_files
            and not self.missing_content_hash_sidecars
            and not self.missing_observability_sidecars
            and (
                self.expected_shards is None
                or self.complete_shards == self.expected_shards
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "wave_id": self.wave_id,
            "expected_rows": self.expected_rows,
            "actual_rows": self.actual_rows,
            "expected_shards": self.expected_shards,
            "complete_shards": self.complete_shards,
            "duplicate_logical_keys": self.duplicate_logical_keys,
            "missing_logical_keys": self.missing_logical_keys,
            "missing_result_files": list(self.missing_result_files),
            "missing_content_hash_sidecars": list(self.missing_content_hash_sidecars),
            "missing_observability_sidecars": list(self.missing_observability_sidecars),
            "classification": (
                "L2B_FULL_COVERAGE_VALIDATION_PASS"
                if self.ok
                else "L2B_FULL_COVERAGE_VALIDATION_FAIL"
            ),
        }


def _wave_selectors(wave_id: str | None) -> tuple[str, ...]:
    if wave_id is None:
        return ("all",)
    selectors = {
        "wave_1": ("wave:0:3",),
        "wave_2": ("wave:3:3",),
        "wave_3": ("matmul__fp16", "matmul__bf16"),
        "wave_4": ("matmul__fp32",),
    }
    try:
        return selectors[wave_id]
    except KeyError as exc:
        raise ValueError(f"unknown L2b wave id: {wave_id}") from exc


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSONL row") from exc
            if not isinstance(payload, dict):
                raise ValueError(f"{path}:{line_number}: row must be an object")
            rows.append(payload)
    return rows


def _normalize_cell_selector(value: str | tuple[str, ...]) -> str | tuple[str, ...]:
    if value == "all":
        return "all"
    if isinstance(value, str):
        selectors = tuple(part.strip() for part in value.split(",") if part.strip())
        if not selectors:
            raise ValueError("l2b_recovery_cells must not be empty")
        return selectors
    return value


def validate_l2b_full_coverage(
    *,
    stage: str,
    wave_id: str | None = None,
    l2b_recovery_cells: str | tuple[str, ...] = "all",
    expected_rows: int,
    expected_shards: int | None = None,
    require_content_hash_sidecars: bool = False,
    require_observability_sidecars: bool = False,
    repo_root: Path = REPO_ROOT,
) -> ValidationResult:
    if stage not in L2B_SELECTOR_PROFILE_IDS:
        raise ValueError(f"unsupported L2b stage: {stage}")

    stage_spec = l2b_full_coverage_stage_spec(stage)
    normalized_cell_selector = _normalize_cell_selector(l2b_recovery_cells)
    stage_n = stage_spec.n
    plans = tuple(
        shard
        for selector in _wave_selectors(wave_id)
        for shard in build_l2b_full_coverage_shard_plan(
            stage_id=stage,
            shard_selector=selector,
            cell_selector=normalized_cell_selector,
            repair_history_policy="agentic_transcript_v1",
            repo_root=repo_root,
        )
    )

    actual_rows = 0
    complete_shards = 0
    logical_keys: set[tuple[str, str, int]] = set()
    duplicate_logical_keys = 0
    missing_logical_keys = 0
    missing_result_files: list[str] = []
    missing_content_hash_sidecars: list[str] = []
    missing_observability_sidecars: list[str] = []

    for shard in plans:
        shard_rows = 0
        for result_file in shard.output_paths["result_files"]:
            result_path = repo_root / result_file
            if not result_path.exists():
                missing_result_files.append(result_file)
                missing_logical_keys += stage_n
                continue

            rows = _read_jsonl(result_path)
            shard_rows += len(rows)
            actual_rows += len(rows)
            cell_id = result_path.stem
            for row in rows:
                base_seed = row.get("base_seed")
                if not isinstance(base_seed, int):
                    raise ValueError(f"{result_file}: row missing integer base_seed")
                key = (shard.shard_id, cell_id, base_seed)
                if key in logical_keys:
                    duplicate_logical_keys += 1
                logical_keys.add(key)

            expected_seeds = set(range(stage_n))
            observed_seeds = {
                row["base_seed"]
                for row in rows
                if isinstance(row.get("base_seed"), int)
            }
            missing_logical_keys += len(expected_seeds - observed_seeds)

        if shard_rows == shard.planned_rows:
            complete_shards += 1

        if require_content_hash_sidecars:
            for sidecar in shard.output_paths["content_hash_sidecars"]:
                if not (repo_root / sidecar).exists():
                    missing_content_hash_sidecars.append(sidecar)

        if require_observability_sidecars:
            for sidecar in (
                *shard.artifact_paths["observability_event_files"],
                *shard.artifact_paths["observability_hash_sidecars"],
                *shard.artifact_paths["observability_summary_files"],
            ):
                if not (repo_root / sidecar).exists():
                    missing_observability_sidecars.append(sidecar)

    return ValidationResult(
        stage=stage,
        wave_id=wave_id,
        expected_rows=expected_rows,
        actual_rows=actual_rows,
        expected_shards=expected_shards,
        complete_shards=complete_shards,
        duplicate_logical_keys=duplicate_logical_keys,
        missing_logical_keys=missing_logical_keys,
        missing_result_files=tuple(missing_result_files),
        missing_content_hash_sidecars=tuple(missing_content_hash_sidecars),
        missing_observability_sidecars=tuple(missing_observability_sidecars),
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage",
        required=True,
        choices=tuple(sorted(L2B_SELECTOR_PROFILE_IDS)),
    )
    parser.add_argument("--wave-id")
    parser.add_argument("--l2b-recovery-cells", default="all")
    parser.add_argument("--expected-rows", type=int, required=True)
    parser.add_argument("--expected-shards", type=int)
    parser.add_argument("--require-content-hash-sidecars", action="store_true")
    parser.add_argument("--require-observability-sidecars", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = validate_l2b_full_coverage(
        stage=args.stage,
        wave_id=args.wave_id,
        l2b_recovery_cells=args.l2b_recovery_cells,
        expected_rows=args.expected_rows,
        expected_shards=args.expected_shards,
        require_content_hash_sidecars=args.require_content_hash_sidecars,
        require_observability_sidecars=args.require_observability_sidecars,
    )
    print(json.dumps(result.to_dict(), sort_keys=True))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
