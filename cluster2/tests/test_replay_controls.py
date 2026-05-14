"""Phase 11 tests for frozen Cluster 1 replay-control mapping."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from cluster2.replay.cluster1_controls import (
    COVERAGE_FAILURE_MISSING_FROZEN_CONTROL,
    map_replay_candidates,
    replay_generation_hashes,
)


def test_replay_adapter_maps_exactly_n_candidates(tmp_path: Path) -> None:
    manifest = _write_replay_fixture(tmp_path, condition="none", row_count=4)

    mapping = map_replay_candidates(
        condition="none",
        kernel_class="elementwise",
        dtype="fp32",
        candidate_count=3,
        manifest_path=manifest,
    )

    assert mapping.ok
    assert mapping.status == "ok"
    assert len(mapping.candidates) == 3
    assert [candidate.attempt_index for candidate in mapping.candidates] == [0, 1, 2]
    assert [candidate.frozen_attempt_index for candidate in mapping.candidates] == [
        0,
        1,
        2,
    ]


def test_replay_adapter_preserves_hashes_and_attempt_indexes(tmp_path: Path) -> None:
    manifest = _write_replay_fixture(tmp_path, condition="G", row_count=3)

    mapping = map_replay_candidates(
        condition="G",
        kernel_class="elementwise",
        dtype="fp32",
        candidate_count=2,
        manifest_path=manifest,
    )

    first = mapping.candidates[0]
    assert first.grammar_active is True
    assert first.grammar_variant == "template_upper_bound"
    assert first.source_sha256 == hashlib.sha256(
        first.source.encode("utf-8")
    ).hexdigest()
    assert first.row_sha256 == _manifest_row_records(manifest)[0]["row_sha256"]
    assert first.generation_seed == 0
    assert first.generation_index == 0
    assert first.attempt_index == 0
    assert first.frozen_attempt_index == 0


def test_replay_adapter_marks_missing_rows_coverage_failure(tmp_path: Path) -> None:
    manifest = _write_replay_fixture(tmp_path, condition="none", row_count=2)

    mapping = map_replay_candidates(
        condition="none",
        kernel_class="elementwise",
        dtype="fp32",
        candidate_count=3,
        manifest_path=manifest,
    )

    assert mapping.status == COVERAGE_FAILURE_MISSING_FROZEN_CONTROL
    assert mapping.candidates == ()
    assert mapping.coverage_failure is not None
    assert mapping.coverage_failure.required_rows == 3
    assert mapping.coverage_failure.observed_rows == 2
    assert mapping.coverage_failure.missing_rows == 1


def test_replay_adapter_marks_sparse_attempt_indexes_coverage_failure(
    tmp_path: Path,
) -> None:
    manifest = _write_replay_fixture(tmp_path, condition="none", row_count=3)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["artifacts"][0]["row_records"] = payload["artifacts"][0]["row_records"][1:]
    manifest.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    mapping = map_replay_candidates(
        condition="none",
        kernel_class="elementwise",
        dtype="fp32",
        candidate_count=3,
        manifest_path=manifest,
    )

    assert mapping.status == COVERAGE_FAILURE_MISSING_FROZEN_CONTROL
    assert mapping.candidates == ()
    assert mapping.coverage_failure is not None
    assert mapping.coverage_failure.observed_rows == 2
    assert mapping.coverage_failure.missing_rows == 1


def test_replay_generation_hashes_use_frozen_artifact_manifest(
    tmp_path: Path,
) -> None:
    manifest = _write_replay_fixture(tmp_path, condition="none", row_count=1)
    artifact = json.loads(manifest.read_text(encoding="utf-8"))["artifacts"][0]

    hashes = replay_generation_hashes("none", manifest)

    assert hashes == {f"{artifact['artifact_id']}:artifact": artifact["sha256"]}


def test_replay_adapter_rejects_artifact_hash_drift(tmp_path: Path) -> None:
    manifest = _write_replay_fixture(tmp_path, condition="none", row_count=1)
    artifact_path = Path(
        json.loads(manifest.read_text(encoding="utf-8"))["artifacts"][0]["path"]
    )
    artifact_path.write_bytes(artifact_path.read_bytes() + b"\n")

    with pytest.raises(ValueError, match="artifact hash mismatch"):
        map_replay_candidates(
            condition="none",
            kernel_class="elementwise",
            dtype="fp32",
            candidate_count=1,
            manifest_path=manifest,
        )


def _write_replay_fixture(
    tmp_path: Path,
    *,
    condition: str,
    row_count: int,
) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    grammar_active = condition == "G"
    artifact_id = (
        "g_template_upper_bound_n20_l4"
        if condition == "G"
        else "none_baseline_n20_l4"
    )
    artifact_path = tmp_path / f"{condition.lower()}_artifact.jsonl"
    records: list[dict[str, Any]] = []
    raw_lines: list[bytes] = []
    for index in range(row_count):
        source = (
            "import torch\n"
            "import triton\n"
            "import triton.language as tl\n"
            f"# replay source {condition} {index}\n"
        )
        raw_row = {
            "source": source,
            "model_id": "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
            "grammar_active": grammar_active,
            "kernel_class": "elementwise",
            "kernel_name": "relu",
            "dtype": "fp32",
            "compile_success": True,
            "compile_results_by_dtype": {
                "fp32": True,
                "fp16": True,
                "bf16": True,
            },
            "compile_error_type": None,
            "compile_error_msg": None,
            "masked_token_rate": 0.9 if grammar_active else None,
            "unique_solution_hash": hashlib.sha256(source.encode("utf-8")).hexdigest(),
            "n_shapes_tested": 5,
            "generation_seed": index,
            "temperature": 0.2,
            "run_id": f"run-{condition}-{index}",
            "timestamp_utc": "2026-05-12T00:00:00+00:00",
        }
        raw_line = (
            json.dumps(raw_row, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8")
        raw_lines.append(raw_line)
        records.append(
            {
                "line_number": index + 1,
                "condition": condition,
                "kernel_class": "elementwise",
                "kernel_name": "relu",
                "dtype": "fp32",
                "grammar_active": grammar_active,
                "grammar_variant": (
                    "template_upper_bound" if grammar_active else None
                ),
                "generation_seed": index,
                "generation_index": index,
                "attempt_index": index,
                "run_id": raw_row["run_id"],
                "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
                "row_sha256": hashlib.sha256(raw_line).hexdigest(),
                "unique_solution_hash": raw_row["unique_solution_hash"],
                "model_id": raw_row["model_id"],
                "model_revision": "unavailable_in_frozen_cluster1_artifact",
                "tokenizer_revision": "unavailable_in_frozen_cluster1_artifact",
            }
        )
    artifact_path.write_bytes(b"".join(raw_lines))
    manifest = {
        "schema_version": 1,
        "artifacts": [
            {
                "artifact_id": artifact_id,
                "condition": condition,
                "path": str(artifact_path),
                "sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
                "row_count": row_count,
                "condition_flag_check": {
                    "expected_grammar_active": grammar_active,
                },
                "rows_per_kernel_dtype_grammar_active": [
                    {
                        "kernel_class": "elementwise",
                        "dtype": "fp32",
                        "grammar_active": grammar_active,
                        "row_count": row_count,
                    }
                ],
                "row_records": records,
            }
        ],
        "selected_controls": {
            "cluster2_v5_template_upper_bound_controls": {
                "artifact_ids": [artifact_id],
                "coverage_failures": [],
            }
        },
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def _manifest_row_records(manifest: Path) -> list[dict[str, Any]]:
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    return payload["artifacts"][0]["row_records"]
