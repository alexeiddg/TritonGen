"""Validate the L2b n20 attempt2 two-lane rescue union.

This module is read-only. It checks the existing attempt2 Wave 1 and partial
Wave 2 artifacts plus the two fresh rescue namespaces.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from cluster3.analysis.validate_l2b_full_coverage import (
    REPO_ROOT,
    validate_l2b_full_coverage,
)
from cluster3.planning.grammar_mode_matrix import build_l2b_full_coverage_shard_plan

ATTEMPT2_STAGE = "l2b_n20_attempt2_full_coverage"
LANE_A_STAGE = "l2b_n20_attempt2_wave2_missing360_recovery_full_coverage"
LANE_B_STAGE = "l2b_n20_attempt2_wave3_parallel_full_coverage"

WAVE2_COMPLETED_CELLS = (
    "grammar_off__c_off__p_off",
    "grammar_off__c_on__p_off",
    "grammar_off__c_off__p_on",
    "grammar_off__c_on__p_on",
    "template_upper_bound__c_off__p_off",
    "template_upper_bound__c_on__p_off",
)
WAVE2_MISSING_CELLS = (
    "template_upper_bound__c_off__p_on",
    "template_upper_bound__c_on__p_on",
    "task_agnostic__c_off__p_off",
    "task_agnostic__c_on__p_off",
    "task_agnostic__c_off__p_on",
    "task_agnostic__c_on__p_on",
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def _logical_keys_for_scope(
    *,
    stage: str,
    shard_selector: str,
    cell_selector: str | tuple[str, ...],
    repo_root: Path,
) -> tuple[set[tuple[str, str, int]], int]:
    keys: set[tuple[str, str, int]] = set()
    duplicate_count = 0
    plans = build_l2b_full_coverage_shard_plan(
        stage_id=stage,
        shard_selector=shard_selector,
        cell_selector=cell_selector,
        repair_history_policy="agentic_transcript_v1",
        repo_root=repo_root,
    )
    for shard in plans:
        for result_file in shard.output_paths["result_files"]:
            result_path = repo_root / result_file
            rows = _read_jsonl(result_path)
            cell_id = result_path.stem
            for row in rows:
                base_seed = row.get("base_seed")
                if not isinstance(base_seed, int):
                    raise ValueError(f"{result_file}: row missing integer base_seed")
                key = (shard.shard_id, cell_id, base_seed)
                if key in keys:
                    duplicate_count += 1
                keys.add(key)
    return keys, duplicate_count


def validate_union(
    *,
    mode: str = "full",
    expected_total_rows: int = 1920,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    if mode not in {"lane-a", "full"}:
        raise ValueError("mode must be lane-a or full")
    validations = [
        validate_l2b_full_coverage(
            stage=ATTEMPT2_STAGE,
            wave_id="wave_1",
            expected_rows=720,
            require_content_hash_sidecars=True,
            require_observability_sidecars=True,
            repo_root=repo_root,
        ),
        validate_l2b_full_coverage(
            stage=ATTEMPT2_STAGE,
            wave_id="wave_2",
            l2b_recovery_cells=WAVE2_COMPLETED_CELLS,
            expected_rows=360,
            require_content_hash_sidecars=True,
            require_observability_sidecars=True,
            repo_root=repo_root,
        ),
        validate_l2b_full_coverage(
            stage=LANE_A_STAGE,
            wave_id="wave_2",
            l2b_recovery_cells=WAVE2_MISSING_CELLS,
            expected_rows=360,
            require_content_hash_sidecars=True,
            require_observability_sidecars=True,
            repo_root=repo_root,
        ),
    ]
    if mode == "full":
        validations.append(
            validate_l2b_full_coverage(
                stage=LANE_B_STAGE,
                wave_id="wave_3",
                expected_rows=480,
                require_content_hash_sidecars=True,
                require_observability_sidecars=True,
                repo_root=repo_root,
            )
        )

    key_scopes = [
        _logical_keys_for_scope(
            stage=ATTEMPT2_STAGE,
            shard_selector="wave:0:3",
            cell_selector="all",
            repo_root=repo_root,
        ),
        _logical_keys_for_scope(
            stage=ATTEMPT2_STAGE,
            shard_selector="wave:3:3",
            cell_selector=WAVE2_COMPLETED_CELLS,
            repo_root=repo_root,
        ),
        _logical_keys_for_scope(
            stage=LANE_A_STAGE,
            shard_selector="wave:3:3",
            cell_selector=WAVE2_MISSING_CELLS,
            repo_root=repo_root,
        ),
    ]
    if mode == "full":
        key_scopes.append(
            _logical_keys_for_scope(
                stage=LANE_B_STAGE,
                shard_selector="wave:7:2",
                cell_selector="all",
                repo_root=repo_root,
            )
        )

    union_keys: set[tuple[str, str, int]] = set()
    cross_scope_duplicates = 0
    duplicate_logical_keys = 0
    for keys, duplicates in key_scopes:
        duplicate_logical_keys += duplicates
        cross_scope_duplicates += len(union_keys.intersection(keys))
        union_keys.update(keys)

    actual_total_rows = sum(validation.actual_rows for validation in validations)
    ok = (
        all(validation.ok for validation in validations)
        and actual_total_rows == expected_total_rows
        and len(union_keys) == expected_total_rows
        and duplicate_logical_keys == 0
        and cross_scope_duplicates == 0
    )
    return {
        "classification": (
            "L2B_N20_ATTEMPT2_TWO_LANE_RESCUE_UNION_VALIDATION_PASS"
            if ok
            else "L2B_N20_ATTEMPT2_TWO_LANE_RESCUE_UNION_VALIDATION_FAIL"
        ),
        "mode": mode,
        "expected_total_rows": expected_total_rows,
        "actual_total_rows": actual_total_rows,
        "union_logical_keys": len(union_keys),
        "duplicate_logical_keys": duplicate_logical_keys,
        "cross_scope_duplicate_logical_keys": cross_scope_duplicates,
        "wave_4_authorized": False,
        "wave_4_expected_missing_rows": 240,
        "segments": [validation.to_dict() for validation in validations],
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("lane-a", "full"), default="full")
    parser.add_argument("--expected-total-rows", type=int, default=1920)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = validate_union(mode=args.mode, expected_total_rows=args.expected_total_rows)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["classification"].endswith("_PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
