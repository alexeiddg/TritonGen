"""Phase 11 tests for frozen Cluster 1 replay-control mapping."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from cluster1.results.dataclass import (
    GenerationResult,
    generation_result_record_for_deserialization,
)
from cluster1.data.kernels import KERNEL_SPECS
from cluster1.data.prompts.prompt_contract import build_prompt
from cluster2.replay.cluster1_controls import (
    COVERAGE_FAILURE_MISSING_FROZEN_CONTROL,
    map_replay_candidates,
    replay_generation_hashes,
)
from shared.eval.adapter_cluster1 import eval_result_from_generation_result
from shared.eval.failure_taxonomy import classify_failure


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
    assert [candidate.base_seed for candidate in mapping.candidates] == [0, 1, 2]
    assert [candidate.attempt_index for candidate in mapping.candidates] == [0, 0, 0]
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
    assert first.replay_pair_id == "elementwise:fp32:0"
    assert first.max_new_tokens == 64
    assert first.failure_code is None
    assert first.legacy_compile_error_type is None


def test_replay_adapter_maps_task_agnostic_g_when_requested(tmp_path: Path) -> None:
    manifest = _write_replay_fixture(
        tmp_path,
        condition="G",
        row_count=3,
        grammar_variant="task_agnostic",
    )

    mapping = map_replay_candidates(
        condition="G",
        kernel_class="elementwise",
        dtype="fp32",
        candidate_count=2,
        manifest_path=manifest,
        grammar_variant="task_agnostic",
    )

    first = mapping.candidates[0]
    assert mapping.ok
    assert first.grammar_active is True
    assert first.grammar_variant == "task_agnostic"
    assert first.artifact_id == "g_task_agnostic_n5_l4_rerun"


def test_replay_adapter_canonicalizes_legacy_cluster1_failure_code(
    tmp_path: Path,
) -> None:
    manifest = _write_replay_fixture(
        tmp_path,
        condition="none",
        row_count=1,
        compile_success=False,
        compile_error_type="SignatureError",
        compile_error_msg="signature mismatch",
    )
    artifact_path = _manifest_artifact_path(manifest)
    manifest_before = manifest.read_bytes()
    artifact_before = artifact_path.read_bytes()

    mapping = map_replay_candidates(
        condition="none",
        kernel_class="elementwise",
        dtype="fp32",
        candidate_count=1,
        manifest_path=manifest,
    )

    assert mapping.ok
    candidate = mapping.candidates[0]
    assert candidate.failure_code == "F0_BAD_SIGNATURE"
    assert candidate.legacy_compile_error_type == "SignatureError"
    assert manifest.read_bytes() == manifest_before
    assert artifact_path.read_bytes() == artifact_before


def test_replay_adapter_canonicalizes_legacy_signature_syntax_as_parse(
    tmp_path: Path,
) -> None:
    manifest = _write_replay_fixture(
        tmp_path,
        condition="none",
        row_count=1,
        compile_success=False,
        compile_error_type="SignatureError",
        compile_error_msg=(
            "SignatureError: syntax error in generated source: "
            "invalid syntax (tmp.py, line 19)"
        ),
    )

    mapping = map_replay_candidates(
        condition="none",
        kernel_class="elementwise",
        dtype="fp32",
        candidate_count=1,
        manifest_path=manifest,
    )

    assert mapping.ok
    candidate = mapping.candidates[0]
    assert candidate.failure_code == "F0_PARSE"
    assert candidate.legacy_compile_error_type == "SignatureError"


def test_replay_adapter_honors_row_level_canonical_failure_code(
    tmp_path: Path,
) -> None:
    manifest = _write_replay_fixture(
        tmp_path,
        condition="none",
        row_count=1,
        compile_success=False,
        compile_error_type="RuntimeError",
        compile_error_msg="runtime launch failure",
        failure_code="F1_RUNTIME",
    )

    mapping = map_replay_candidates(
        condition="none",
        kernel_class="elementwise",
        dtype="fp32",
        candidate_count=1,
        manifest_path=manifest,
    )

    assert mapping.ok
    assert mapping.candidates[0].failure_code == "F1_RUNTIME"
    assert mapping.candidates[0].legacy_compile_error_type == "RuntimeError"


def test_replay_adapter_matches_shared_taxonomy_for_legacy_rows(
    tmp_path: Path,
) -> None:
    manifest = _write_replay_fixture(
        tmp_path,
        condition="none",
        row_count=2,
        compile_success=False,
        compile_error_type="SignatureError",
        compile_error_msg="signature mismatch",
    )

    mapping = map_replay_candidates(
        condition="none",
        kernel_class="elementwise",
        dtype="fp32",
        candidate_count=2,
        manifest_path=manifest,
    )

    raw_rows = _artifact_rows(manifest)
    expected = [
        classify_failure(
            eval_result_from_generation_result(
                GenerationResult(
                    **generation_result_record_for_deserialization(raw_row)
                )
            )
        )
        for raw_row in raw_rows
    ]
    assert [candidate.failure_code for candidate in mapping.candidates] == expected


def test_replay_adapter_marks_missing_rows_coverage_failure(tmp_path: Path) -> None:
    manifest = _write_replay_fixture(tmp_path, condition="none", row_count=3)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["artifacts"][0]["row_records"] = payload["artifacts"][0]["row_records"][:2]
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


def test_replay_adapter_rejects_missing_seed_schedule(tmp_path: Path) -> None:
    manifest = _write_replay_fixture(tmp_path, condition="none", row_count=1)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["artifacts"][0].pop("seed_schedule")
    manifest.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="seed_schedule"):
        map_replay_candidates(
            condition="none",
            kernel_class="elementwise",
            dtype="fp32",
            candidate_count=1,
            manifest_path=manifest,
        )


def test_replay_adapter_rejects_missing_seed_schedule_before_coverage_failure(
    tmp_path: Path,
) -> None:
    manifest = _write_replay_fixture(tmp_path, condition="none", row_count=2)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["artifacts"][0].pop("seed_schedule")
    payload["artifacts"][0]["row_records"] = payload["artifacts"][0]["row_records"][1:]
    manifest.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="seed_schedule"):
        map_replay_candidates(
            condition="none",
            kernel_class="elementwise",
            dtype="fp32",
            candidate_count=3,
            manifest_path=manifest,
        )


def test_replay_adapter_rejects_malformed_seed_schedule_before_coverage_failure(
    tmp_path: Path,
) -> None:
    manifest = _write_replay_fixture(tmp_path, condition="none", row_count=2)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    artifact = payload["artifacts"][0]
    artifact["seed_schedule"]["records"][0].pop("generation_seeds")
    artifact["row_records"] = artifact["row_records"][1:]
    manifest.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="generation_seeds"):
        map_replay_candidates(
            condition="none",
            kernel_class="elementwise",
            dtype="fp32",
            candidate_count=3,
            manifest_path=manifest,
        )


def test_replay_adapter_rejects_bad_prompt_hash_before_coverage_failure(
    tmp_path: Path,
) -> None:
    manifest = _write_replay_fixture(tmp_path, condition="none", row_count=2)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    artifact = payload["artifacts"][0]
    artifact["seed_schedule"]["records"][0]["prompt_sha256"] = "bad"
    artifact["row_records"] = artifact["row_records"][1:]
    manifest.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="prompt_sha256"):
        map_replay_candidates(
            condition="none",
            kernel_class="elementwise",
            dtype="fp32",
            candidate_count=3,
            manifest_path=manifest,
        )


def test_replay_adapter_rejects_schedule_row_drift_before_coverage_failure(
    tmp_path: Path,
) -> None:
    manifest = _write_replay_fixture(tmp_path, condition="none", row_count=2)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    artifact = payload["artifacts"][0]
    artifact["seed_schedule"]["records"][0]["max_new_tokens"] = 65
    artifact["row_records"] = artifact["row_records"][:1]
    manifest.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="max_new_tokens"):
        map_replay_candidates(
            condition="none",
            kernel_class="elementwise",
            dtype="fp32",
            candidate_count=2,
            manifest_path=manifest,
        )


def test_replay_adapter_rejects_selection_key_drift_before_coverage_failure(
    tmp_path: Path,
) -> None:
    manifest = _write_replay_fixture(tmp_path, condition="none", row_count=2)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["artifacts"][0]["row_records"][0]["attempt_index"] = 99
    manifest.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="attempt_index"):
        map_replay_candidates(
            condition="none",
            kernel_class="elementwise",
            dtype="fp32",
            candidate_count=2,
            manifest_path=manifest,
        )


def test_replay_adapter_rejects_incomplete_seed_schedule_before_coverage_failure(
    tmp_path: Path,
) -> None:
    manifest = _write_replay_fixture(tmp_path, condition="none", row_count=3)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    artifact = payload["artifacts"][0]
    schedule = artifact["seed_schedule"]["records"][0]
    for field_name in (
        "base_seeds",
        "generation_seeds",
        "attempt_indexes",
        "generation_indexes",
        "line_numbers",
        "replay_pair_ids",
    ):
        schedule[field_name] = schedule[field_name][:2]
    artifact["row_records"] = artifact["row_records"][:1]
    manifest.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="seed_schedule coverage failure"):
        map_replay_candidates(
            condition="none",
            kernel_class="elementwise",
            dtype="fp32",
            candidate_count=3,
            manifest_path=manifest,
        )


def test_replay_adapter_rejects_schedule_revision_drift(tmp_path: Path) -> None:
    manifest = _write_replay_fixture(tmp_path, condition="none", row_count=1)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["artifacts"][0]["seed_schedule"]["records"][0][
        "model_revision"
    ] = "frozen-model-rev"
    manifest.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="model_revision"):
        map_replay_candidates(
            condition="none",
            kernel_class="elementwise",
            dtype="fp32",
            candidate_count=1,
            manifest_path=manifest,
        )


def test_replay_adapter_selects_schedule_line_not_extra_attempt_record(
    tmp_path: Path,
) -> None:
    manifest = _write_replay_fixture(tmp_path, condition="none", row_count=2)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    artifact = payload["artifacts"][0]
    artifact_path = Path(artifact["path"])
    first_raw = json.loads(artifact_path.read_text(encoding="utf-8").splitlines()[0])
    extra_source = (
        "import torch\n"
        "import triton\n"
        "import triton.language as tl\n"
        "# extra replay source none 0\n"
    )
    first_raw["source"] = extra_source
    first_raw["run_id"] = "run-none-extra"
    first_raw["unique_solution_hash"] = hashlib.sha256(
        extra_source.encode("utf-8")
    ).hexdigest()
    extra_line = (
        json.dumps(first_raw, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    artifact_path.write_bytes(artifact_path.read_bytes() + extra_line)

    extra_record = dict(artifact["row_records"][0])
    extra_record.update(
        {
            "line_number": 3,
            "base_seed": 999,
            "generation_index": -1,
            "replay_pair_id": "elementwise:fp32:extra",
            "run_id": first_raw["run_id"],
            "source_sha256": hashlib.sha256(extra_source.encode("utf-8")).hexdigest(),
            "row_sha256": hashlib.sha256(extra_line).hexdigest(),
            "unique_solution_hash": first_raw["unique_solution_hash"],
        }
    )
    artifact["row_records"].append(extra_record)
    artifact["sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    manifest.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    mapping = map_replay_candidates(
        condition="none",
        kernel_class="elementwise",
        dtype="fp32",
        candidate_count=1,
        manifest_path=manifest,
    )

    assert "# replay source none 0" in mapping.candidates[0].source
    assert "# extra replay source" not in mapping.candidates[0].source
    assert mapping.candidates[0].row_sha256 == artifact["row_records"][0]["row_sha256"]


def _write_replay_fixture(
    tmp_path: Path,
    *,
    condition: str,
    row_count: int,
    grammar_variant: str = "template_upper_bound",
    max_new_tokens: int = 64,
    compile_success: bool = True,
    compile_error_type: str | None = None,
    compile_error_msg: str | None = None,
    failure_code: str | None = None,
) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    grammar_active = condition == "G"
    artifact_id = (
        (
            "g_task_agnostic_n5_l4_rerun"
            if grammar_variant == "task_agnostic"
            else "g_template_upper_bound_n20_l4"
        )
        if condition == "G"
        else "none_baseline_n20_l4"
    )
    artifact_path = tmp_path / f"{condition.lower()}_artifact.jsonl"
    prompt_sha256 = hashlib.sha256(
        build_prompt(KERNEL_SPECS["elementwise"], "fp32").encode("utf-8")
    ).hexdigest()
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
            "compile_success": compile_success,
            "compile_results_by_dtype": {
                "fp32": compile_success,
                "fp16": compile_success,
                "bf16": compile_success,
            },
            "compile_error_type": compile_error_type,
            "compile_error_msg": compile_error_msg,
            "masked_token_rate": 0.9 if grammar_active else None,
            "unique_solution_hash": hashlib.sha256(source.encode("utf-8")).hexdigest(),
            "n_shapes_tested": 5,
            "generation_seed": index,
            "temperature": 0.2,
            "run_id": f"run-{condition}-{index}",
            "timestamp_utc": "2026-05-12T00:00:00+00:00",
        }
        if failure_code is not None:
            raw_row["failure_code"] = failure_code
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
                "grammar_variant": grammar_variant if grammar_active else None,
                "generation_seed": index,
                "base_seed": index,
                "generation_index": index,
                "attempt_index": index,
                "prompt_sha256": prompt_sha256,
                "temperature": 0.2,
                "max_new_tokens": max_new_tokens,
                "replay_pair_id": f"elementwise:fp32:{index}",
                "pairing_metadata_complete": True,
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
                    "expected_grammar_variant": (
                        grammar_variant if grammar_active else None
                    ),
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
                "seed_schedule": {
                    "schedule_type": "paired_by_seed",
                    "canonical_order": ["kernel_class", "dtype", "base_seed"],
                    "pair_key_fields": ["kernel_class", "dtype", "base_seed"],
                    "fresh_generation_seed_rule": (
                        "attempt 0 consumes replay generation_seed; repair attempts "
                        "derive deterministically from the paired base_seed"
                    ),
                    "artifact_invariants": {
                        "base_seed_equals_generation_seed": True,
                        "attempt_index_equals_generation_index": True,
                        "dense_zero_based_per_kernel_dtype": True,
                        "prompt_model_temperature_token_budget_constant_per_kernel_dtype": True,
                    },
                    "records": [
                        {
                            "kernel_class": "elementwise",
                            "kernel_name": "relu",
                            "dtype": "fp32",
                            "prompt_sha256": prompt_sha256,
                            "model_id": "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
                            "model_revision": "unavailable_in_frozen_cluster1_artifact",
                            "tokenizer_revision": "unavailable_in_frozen_cluster1_artifact",
                            "temperature": 0.2,
                            "max_new_tokens": max_new_tokens,
                            "row_count": row_count,
                            "base_seeds": list(range(row_count)),
                            "generation_seeds": list(range(row_count)),
                            "attempt_indexes": list(range(row_count)),
                            "generation_indexes": list(range(row_count)),
                            "line_numbers": list(range(1, row_count + 1)),
                            "replay_pair_ids": [
                                f"elementwise:fp32:{index}" for index in range(row_count)
                            ],
                        }
                    ],
                },
            }
        ],
        "selected_controls": {
            "cluster2_v5_template_upper_bound_controls": {
                "artifact_ids": [artifact_id],
                "coverage_failures": [],
            }
        },
    }
    if condition == "G" and grammar_variant == "task_agnostic":
        manifest["selected_controls"]["task_agnostic_g_status"] = {
            "available_development_artifact_id": artifact_id,
            "development_rows_per_cell_sufficient": True,
            "paper_rows_per_cell_sufficient": False,
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


def _manifest_artifact_path(manifest: Path) -> Path:
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    return Path(payload["artifacts"][0]["path"])


def _artifact_rows(manifest: Path) -> list[dict[str, Any]]:
    artifact_path = _manifest_artifact_path(manifest)
    return [
        json.loads(line)
        for line in artifact_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
