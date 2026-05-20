"""Phase 11 tests for the main Cluster 2 runner."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

import cluster2.experiments.run_cluster2_modal as runner_mod
from cluster2.constants import DEFAULT_FROZEN_CLUSTER1_MANIFEST, DEFAULT_MAX_NEW_TOKENS
from cluster2.experiments.run_f2_repair_smoke import _corrected_source, run_f2_repair_smoke
from cluster2.experiments.run_cluster2_modal import (
    Cluster2RunnerConfig,
    RunnerDependencies,
    parse_args,
    run_cluster2,
)
from cluster2.modal.correctness_runner import build_success_payload
from cluster2.modal.schemas import (
    EvalIdentity,
    RemoteCorrectnessRequest,
    RemoteCorrectnessResult,
)
from cluster2.results.dataclass import CLUSTER2_GENERATION_METADATA_SCHEMA_VERSION
from cluster2.results.logger import (
    default_content_hash_sidecar_path,
    load_cluster2_results_jsonl,
)
from cluster2.tests.test_replay_controls import (
    _drop_seed_schedule_entry,
    _write_replay_fixture,
)
from shared.eval.content_hashes import collect_c2_generation_hashes
from shared.generation_metadata import modal_image_provenance_digest


REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_MODEL_REVISION = "a" * 40
TEST_TOKENIZER_REVISION = "b" * 40


def _fallback_modal_image_components() -> dict[str, object]:
    return {
        "schema": "modal_image_fallback_provenance.v1",
        "image_source": {
            "path": "shared/modal_harness/images.py",
            "sha256": "a" * 64,
            "generation_package_pins": ["torch==2.8.0"],
        },
        "runtime_versions": {
            "xgrammar_version": "0.1.33",
            "transformers_version": "4.47.1",
            "tokenizers_version": "0.21.4",
        },
        "extra": {"modal_generation_gpu": "L4"},
    }


def _fallback_modal_image_sha256() -> str:
    return modal_image_provenance_digest(_fallback_modal_image_components())


def test_runner_routes_none_to_replay_adapter(tmp_path: Path) -> None:
    manifest = _write_replay_fixture(tmp_path, condition="none", row_count=2)
    generation_calls: list[dict[str, Any]] = []
    correctness_calls: list[Any] = []

    result = run_cluster2(
        _config(tmp_path, condition="none", manifest=manifest, n=2),
        dependencies=RunnerDependencies(
            generation=_forbidden_generation(generation_calls),
            correctness=_success_correctness(correctness_calls),
        ),
    )

    assert generation_calls == []
    assert len(correctness_calls) == 2
    assert len(result.rows) == 2
    assert result.route_audit[0].route == "replay_adapter"
    assert result.route_audit[0].generation_calls == 0
    assert {row.generation_mode for row in result.rows} == {"replay_control"}
    assert all(row.replay_metadata is not None for row in result.rows)
    assert all(row.generated_metadata is None for row in result.rows)


def test_runner_preserves_canonical_frozen_replay_failure_metadata(
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

    def bad_signature_correctness(request: Any) -> dict[str, Any]:
        return {
            "correctness_result": {
                "identity": request.identity.model_dump(),
                "functional_success": False,
                "repair_set_success": False,
                "eval_set_success": False,
                "failure_code": "F0_BAD_SIGNATURE",
                "correctness_error": "signature mismatch",
            }
        }

    result = run_cluster2(
        _config(tmp_path, condition="none", manifest=manifest, n=1),
        dependencies=RunnerDependencies(
            generation=_forbidden_generation([]),
            correctness=bad_signature_correctness,
        ),
    )

    row = result.rows[0]
    assert row.failure_code == "F0_BAD_SIGNATURE"
    assert row.replay_metadata is not None
    assert row.replay_metadata.frozen_cluster1_failure_code == "F0_BAD_SIGNATURE"
    assert row.replay_metadata.frozen_cluster1_compile_success is False
    assert row.replay_metadata.legacy_compile_error_type == "SignatureError"


def test_runner_routes_g_to_replay_adapter(tmp_path: Path) -> None:
    manifest = _write_replay_fixture(
        tmp_path,
        condition="G",
        row_count=2,
        grammar_variant="task_agnostic",
    )
    generation_calls: list[dict[str, Any]] = []

    result = run_cluster2(
        _config(tmp_path, condition="G", manifest=manifest, n=2),
        dependencies=RunnerDependencies(
            generation=_forbidden_generation(generation_calls),
            correctness=_success_correctness([]),
        ),
    )

    assert generation_calls == []
    assert len(result.rows) == 2
    assert {row.condition for row in result.rows} == {"G"}
    assert {row.source_class for row in result.rows} == {"replay_control_row"}
    assert {
        row.replay_metadata.frozen_cluster1_artifact_id
        for row in result.rows
        if row.replay_metadata is not None
    } == {"g_task_agnostic_aligned_pipeline_n20_l4"}
    assert {
        row.replay_metadata.grammar_variant
        for row in result.rows
        if row.replay_metadata is not None
    } == {"task_agnostic"}
    assert {row.grammar_active for row in result.rows} == {True}
    assert {row.compile_success for row in result.rows} == {True}
    assert result.route_audit[0].generation_allowed is False


def test_runner_never_calls_generation_for_replay_controls(tmp_path: Path) -> None:
    for condition in ("none", "G"):
        manifest = _write_replay_fixture(
            tmp_path / condition,
            condition=condition,
            row_count=1,
            grammar_variant=(
                "task_agnostic" if condition == "G" else "template_upper_bound"
            ),
        )
        generation_calls: list[dict[str, Any]] = []

        result = run_cluster2(
            _config(tmp_path / f"out-{condition}", condition=condition, manifest=manifest, n=1),
            dependencies=RunnerDependencies(
                generation=_forbidden_generation(generation_calls),
                correctness=_success_correctness([]),
            ),
        )

        assert generation_calls == []
        assert result.route_audit[0].generation_calls == 0


def test_runner_routes_c_to_c2_generation(tmp_path: Path) -> None:
    generation_calls: list[dict[str, Any]] = []
    correctness_calls: list[Any] = []

    result = run_cluster2(
        _config(tmp_path, condition="C", repair_budget=0, n=1),
        dependencies=RunnerDependencies(
            generation=_fake_generation(generation_calls),
            correctness=_success_correctness(correctness_calls),
        ),
    )

    assert len(generation_calls) == 1
    assert generation_calls[0]["identity"].condition == "C"
    assert generation_calls[0]["identity"].generation_mode == "new_c2_generation"
    assert generation_calls[0]["generation_seed"] == 0
    assert generation_calls[0]["modal_generation_gpu"] == "L4"
    assert len(correctness_calls) == 1
    assert len(result.rows) == 1
    assert result.rows[0].source_class == "generated_row"
    assert result.rows[0].grammar_active is False
    assert result.rows[0].compile_success is True
    assert result.rows[0].generated_metadata is not None
    assert result.rows[0].generated_metadata.replay_control_condition == "none"
    assert result.rows[0].generated_metadata.replay_generation_seed == 0
    assert result.rows[0].generated_metadata.model_revision == TEST_MODEL_REVISION
    assert (
        result.rows[0].generated_metadata.tokenizer_revision
        == TEST_TOKENIZER_REVISION
    )
    assert result.rows[0].replay_metadata is None
    assert result.route_audit[0].route == "c2_repair_loop"


def test_generation_metadata_from_payload_uses_modal_observed_revisions() -> None:
    metadata = runner_mod._generation_grammar_metadata_from_payload(
        {
            "generation_identity": {
                "grammar_active": False,
                "grammar_variant": None,
                "grammar_path": None,
                "grammar_sha": None,
                "grammar_claim_scope": None,
            },
            "model_identity": {
                "model_revision": "requested-model",
                "tokenizer_revision": "requested-tokenizer",
                "observed_model_revision": "observed-model",
                "observed_tokenizer_revision": "observed-tokenizer",
            },
            "runtime_identity": {
                "xgrammar_version": "0.1.33",
                "transformers_version": "4.47.1",
                "tokenizers_version": "0.21.4",
                "modal_image_sha": "unknown",
                "modal_image_provenance_sha256": _fallback_modal_image_sha256(),
                "modal_image_provenance_components": (
                    _fallback_modal_image_components()
                ),
            },
            "generation_result": {
                "model_revision": "result-model",
                "tokenizer_revision": "result-tokenizer",
                "stop_reason": "eos_token",
                "generation_metadata_schema_version": (
                    CLUSTER2_GENERATION_METADATA_SCHEMA_VERSION
                ),
            },
        },
        condition="C",
    )

    assert metadata["model_revision"] == "result-model"
    assert metadata["tokenizer_revision"] == "result-tokenizer"


def test_c_generation_metadata_from_payload_rejects_validation_evidence() -> None:
    payload = {
        "generation_identity": {
            "grammar_active": False,
            "grammar_variant": None,
            "grammar_path": None,
            "grammar_sha": None,
            "grammar_claim_scope": None,
            "gbnf_parse_valid": True,
            "semantic_valid": True,
            "grammar_valid": True,
            "rejection_layer": None,
        },
    }

    with pytest.raises(ValueError, match="must not record grammar validation"):
        runner_mod._generation_grammar_metadata_from_payload(
            payload,
            condition="C",
        )


def test_task_agnostic_gc_generation_uses_canonical_token_budget(
    tmp_path: Path,
) -> None:
    manifest = _write_replay_fixture(
        tmp_path,
        condition="G",
        row_count=1,
        grammar_variant="task_agnostic",
        max_new_tokens=DEFAULT_MAX_NEW_TOKENS,
    )
    generation_calls: list[dict[str, Any]] = []

    run_cluster2(
        _config(
            tmp_path,
            condition="G+C",
            manifest=manifest,
            repair_budget=0,
            n=1,
            grammar_variant="task_agnostic",
            max_new_tokens=DEFAULT_MAX_NEW_TOKENS,
        ),
        dependencies=RunnerDependencies(
            generation=_fake_generation(generation_calls),
            correctness=_success_correctness([]),
        ),
    )

    assert DEFAULT_MAX_NEW_TOKENS >= 1024
    assert generation_calls[0]["grammar_variant"] == "task_agnostic"
    assert generation_calls[0]["max_new_tokens"] == DEFAULT_MAX_NEW_TOKENS


def test_default_frozen_manifest_allows_fresh_generation_budget_migration(
    tmp_path: Path,
) -> None:
    generation_calls: list[dict[str, Any]] = []

    result = run_cluster2(
        _config(
            tmp_path,
            condition="C",
            manifest=Path(DEFAULT_FROZEN_CLUSTER1_MANIFEST),
            repair_budget=0,
            n=1,
            max_new_tokens=DEFAULT_MAX_NEW_TOKENS,
        ),
        dependencies=RunnerDependencies(
            generation=_fake_generation(generation_calls),
            correctness=_success_correctness([]),
        ),
    )

    assert len(generation_calls) == 1
    assert generation_calls[0]["max_new_tokens"] == DEFAULT_MAX_NEW_TOKENS
    assert result.rows[0].generated_metadata is not None
    assert result.rows[0].generated_metadata.max_new_tokens == DEFAULT_MAX_NEW_TOKENS


def test_runner_c_non_f2_failure_does_not_request_repair_generation(
    tmp_path: Path,
) -> None:
    generation_calls: list[dict[str, Any]] = []
    correctness_calls: list[Any] = []

    def compile_failure_correctness(request: Any) -> dict[str, Any]:
        correctness_calls.append(request)
        return {
            "correctness_result": {
                "identity": request.identity.model_dump(),
                "functional_success": False,
                "repair_set_success": False,
                "eval_set_success": False,
                "level_reached": 1,
                "failure_code": "F1_COMPILE",
                "correctness_error": "compile failed before Level 2",
            }
        }

    result = run_cluster2(
        _config(tmp_path, condition="C", repair_budget=3, n=1),
        dependencies=RunnerDependencies(
            generation=_fake_generation(generation_calls),
            correctness=compile_failure_correctness,
        ),
    )

    assert len(generation_calls) == 1
    assert len(correctness_calls) == 1
    assert len(result.rows) == 1
    assert result.rows[0].attempt_index == 0
    assert result.rows[0].failure_code == "F1_COMPILE"
    assert result.rows[0].compile_success is False
    assert result.rows[0].trace_summary is not None
    assert result.rows[0].trace_summary.attempt_index == 0
    assert result.route_audit[0].generation_calls == 1


def test_runner_repair_attempts_preserve_repair_loop_seed_schedule(
    tmp_path: Path,
) -> None:
    generation_calls: list[dict[str, Any]] = []

    def first_attempt_fails_then_succeeds(request: Any) -> dict[str, Any]:
        success = request.identity.attempt_index == 1
        return {
            "correctness_result": {
                "identity": request.identity.model_dump(),
                "functional_success": success,
                "repair_set_success": success,
                "eval_set_success": success,
                "level_reached": 2,
                "failure_code": None if success else "F2_NUMERIC_LARGE",
                "correctness_error": None if success else "numeric mismatch",
            }
        }

    result = run_cluster2(
        _config(tmp_path, condition="C", repair_budget=1, n=1),
        dependencies=RunnerDependencies(
            generation=_fake_generation(generation_calls),
            correctness=first_attempt_fails_then_succeeds,
        ),
    )

    assert [call["generation_seed"] for call in generation_calls] == [0, 1]
    assert len(result.rows) == 1
    assert result.rows[0].attempt_index == 1
    assert result.rows[0].repair_trace is not None
    assert [trace.attempt_index for trace in result.rows[0].repair_trace] == [0, 1]
    assert [
        row.generated_metadata.generation_seed
        for row in result.rows
        if row.generated_metadata is not None
    ] == [1]


def test_runner_routes_gc_to_c2_generation_with_g_adapter(tmp_path: Path) -> None:
    generation_calls: list[dict[str, Any]] = []

    result = run_cluster2(
        _config(tmp_path, condition="G+C", repair_budget=0, n=1),
        dependencies=RunnerDependencies(
            generation=_fake_generation(generation_calls),
            correctness=_success_correctness([]),
        ),
    )

    assert generation_calls[0]["identity"].condition == "G+C"
    assert generation_calls[0]["grammar_variant"] == "task_agnostic"
    assert (
        generation_calls[0]["identity"].generation_mode
        == "new_c2_generation_with_G_adapter"
    )
    assert result.rows[0].generation_mode == "new_c2_generation_with_G_adapter"
    assert result.rows[0].grammar_active is True
    assert result.rows[0].compile_success is True
    assert result.rows[0].generated_metadata is not None
    assert result.rows[0].generated_metadata.grammar_variant == "task_agnostic"
    assert result.rows[0].generated_metadata.replay_control_condition == "G"
    assert (
        result.rows[0].generated_metadata.grammar_path
        == "cluster1/grammar/triton_kernel_agnostic.gbnf"
    )
    assert len(result.rows[0].generated_metadata.grammar_sha) == 64
    assert result.rows[0].generated_metadata.gbnf_parse_valid is False
    assert result.rows[0].generated_metadata.semantic_valid is False
    assert result.rows[0].generated_metadata.grammar_valid is False
    assert result.rows[0].generated_metadata.rejection_layer == "gbnf_parse"
    assert result.rows[0].generated_metadata.stop_reason == "eos_token"
    assert result.rows[0].generated_metadata.xgrammar_version == "0.1.33"
    assert result.rows[0].generated_metadata.grammar_claim_scope == "primary"
    assert result.route_audit[0].route == "c2_repair_loop_with_g_adapter"


def test_gc_conversion_rejects_modal_grammar_sha_mismatch() -> None:
    payload = _gc_fake_payload()
    payload["generation_identity"]["grammar_sha"] = "0" * 64

    with pytest.raises(ValueError, match="grammar_sha does not match"):
        runner_mod._generation_grammar_metadata_from_payload(
            payload,
            condition="G+C",
        )


def test_gc_conversion_rejects_modal_local_validation_mismatch() -> None:
    payload = _gc_fake_payload()
    payload["generation_identity"].update(
        {
            "gbnf_parse_valid": True,
            "semantic_valid": True,
            "grammar_valid": True,
            "rejection_layer": None,
        }
    )

    with pytest.raises(ValueError, match="validation fields disagree"):
        runner_mod._generation_grammar_metadata_from_payload(
            payload,
            condition="G+C",
        )


def test_runner_generated_conditions_consume_replay_seed_schedule(
    tmp_path: Path,
) -> None:
    manifest = _write_replay_fixture(tmp_path, condition="none", row_count=3)
    generation_calls: list[dict[str, Any]] = []

    result = run_cluster2(
        _config(tmp_path, condition="C", manifest=manifest, repair_budget=0, n=3),
        dependencies=RunnerDependencies(
            generation=_fake_generation(generation_calls),
            correctness=_success_correctness([]),
        ),
    )

    assert [call["identity"].base_seed for call in generation_calls] == [0, 1, 2]
    assert [call["generation_seed"] for call in generation_calls] == [0, 1, 2]
    assert [
        row.generated_metadata.replay_generation_seed
        for row in result.rows
        if row.generated_metadata is not None
    ] == [0, 1, 2]


def test_gc_preflight_uses_matched_rows_under_task_agnostic_skip_policy(
    tmp_path: Path,
) -> None:
    coverage_warnings: list[Any] = []
    actual_revision = "8e8ed243bbe6f9a5aff549a0924562fc719b2b8a"
    config = Cluster2RunnerConfig(
        condition="G+C",
        kernel_class="all",
        scale_tier="smoke",
        n=20,
        frozen_cluster1_manifest=DEFAULT_FROZEN_CLUSTER1_MANIFEST,
        model_id="Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        model_revision=actual_revision,
        tokenizer_revision=actual_revision,
        grammar_variant="task_agnostic",
        dtypes=("fp32", "fp16", "bf16"),
        temperature=0.2,
        max_new_tokens=DEFAULT_MAX_NEW_TOKENS,
        repair_budget=0,
        modal_generation_gpu="L4",
        modal_eval_gpu="L4",
        output=str(tmp_path / "cluster2.jsonl"),
        write_mode="overwrite",
    )

    replay_condition, schedules = runner_mod._preflight_paired_generation_schedules(
        condition="G+C",
        config=config,
        coverage_warnings=coverage_warnings,
    )

    assert replay_condition == "G"
    assert sum(len(entries) for entries in schedules.values()) == 177
    assert [entry.base_seed for entry in schedules[("matmul", "fp32")]].count(5) == 0
    assert [entry.base_seed for entry in schedules[("matmul", "bf16")]].count(0) == 0
    assert [entry.base_seed for entry in schedules[("matmul", "bf16")]].count(18) == 0
    assert len(coverage_warnings) == 1
    assert coverage_warnings[0].replay_expected_rows == 180
    assert coverage_warnings[0].replay_observed_rows == 177
    assert len(coverage_warnings[0].replay_missing_rows) == 3


@pytest.mark.parametrize(
    ("coverage_mutation", "expected_message"),
    [
        ("duplicate", "duplicate_rows"),
        ("unexpected", "unexpected_rows"),
        ("invalid", "invalid_rows"),
    ],
)
def test_gc_preflight_rejects_malformed_task_agnostic_skip_policy_coverage(
    tmp_path: Path,
    coverage_mutation: str,
    expected_message: str,
) -> None:
    manifest = json.loads(
        Path(DEFAULT_FROZEN_CLUSTER1_MANIFEST).read_text(encoding="utf-8")
    )
    artifact = next(
        artifact
        for artifact in manifest["artifacts"]
        if artifact["artifact_id"] == "g_task_agnostic_aligned_pipeline_n20_l4"
    )
    if coverage_mutation == "duplicate":
        artifact["row_records"][1]["generation_seed"] = artifact["row_records"][0][
            "generation_seed"
        ]
    elif coverage_mutation == "unexpected":
        artifact["row_records"][0]["generation_seed"] = 20
    elif coverage_mutation == "invalid":
        artifact["row_records"][0]["kernel_class"] = "not-a-kernel"
    else:  # pragma: no cover - parametrization guard
        raise AssertionError(f"unexpected coverage mutation {coverage_mutation!r}")

    manifest_path = tmp_path / f"{coverage_mutation}_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    config = Cluster2RunnerConfig(
        condition="G+C",
        kernel_class="all",
        scale_tier="smoke",
        n=20,
        frozen_cluster1_manifest=str(manifest_path),
        model_id="Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        model_revision="8e8ed243bbe6f9a5aff549a0924562fc719b2b8a",
        tokenizer_revision="8e8ed243bbe6f9a5aff549a0924562fc719b2b8a",
        grammar_variant="task_agnostic",
        dtypes=("fp32", "fp16", "bf16"),
        temperature=0.2,
        max_new_tokens=DEFAULT_MAX_NEW_TOKENS,
        repair_budget=0,
        modal_generation_gpu="L4",
        modal_eval_gpu="L4",
        output=str(tmp_path / "cluster2.jsonl"),
        write_mode="overwrite",
    )

    with pytest.raises(ValueError, match=expected_message):
        runner_mod._preflight_paired_generation_schedules(
            condition="G+C",
            config=config,
            coverage_warnings=[],
        )


def test_gc_preflight_rejects_schedule_holes_not_reported_missing(
    tmp_path: Path,
) -> None:
    manifest = json.loads(
        Path(DEFAULT_FROZEN_CLUSTER1_MANIFEST).read_text(encoding="utf-8")
    )
    artifact = next(
        artifact
        for artifact in manifest["artifacts"]
        if artifact["artifact_id"] == "g_task_agnostic_aligned_pipeline_n20_l4"
    )
    _drop_seed_schedule_entry(
        artifact,
        kernel_class="elementwise",
        dtype="fp32",
        base_seed=2,
    )
    manifest_path = tmp_path / "schedule_hole_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    actual_revision = "8e8ed243bbe6f9a5aff549a0924562fc719b2b8a"
    config = Cluster2RunnerConfig(
        condition="G+C",
        kernel_class="all",
        scale_tier="smoke",
        n=20,
        frozen_cluster1_manifest=str(manifest_path),
        model_id="Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        model_revision=actual_revision,
        tokenizer_revision=actual_revision,
        grammar_variant="task_agnostic",
        dtypes=("fp32", "fp16", "bf16"),
        temperature=0.2,
        max_new_tokens=DEFAULT_MAX_NEW_TOKENS,
        repair_budget=0,
        modal_generation_gpu="L4",
        modal_eval_gpu="L4",
        output=str(tmp_path / "cluster2.jsonl"),
        write_mode="overwrite",
    )

    with pytest.raises(ValueError, match="missing_from_schedule"):
        runner_mod._preflight_paired_generation_schedules(
            condition="G+C",
            config=config,
            coverage_warnings=[],
        )


def test_runner_durable_rows_survive_mid_run_exception(tmp_path: Path) -> None:
    generation_calls: list[dict[str, Any]] = []
    correctness_calls: list[Any] = []
    config = _config(tmp_path, condition="C", repair_budget=0, n=3)

    def crash_after_two_completed_rows(request: Any) -> dict[str, Any]:
        correctness_calls.append(request)
        if len(correctness_calls) > 2:
            raise RuntimeError("simulated modal interruption")
        return {
            "correctness_result": {
                "identity": request.identity.model_dump(),
                "functional_success": True,
                "repair_set_success": True,
                "eval_set_success": True,
                "compile_success": True,
                "failure_code": None,
                "correctness_error": None,
            }
        }

    with pytest.raises(RuntimeError, match="simulated modal interruption"):
        run_cluster2(
            config,
            dependencies=RunnerDependencies(
                generation=_fake_generation(generation_calls),
                correctness=crash_after_two_completed_rows,
            ),
        )

    persisted_rows = load_cluster2_results_jsonl(config.output)
    assert len(persisted_rows) == 2
    assert [row.base_seed for row in persisted_rows] == [0, 1]
    assert [row.condition for row in persisted_rows] == ["C", "C"]
    assert all(row.functional_success for row in persisted_rows)
    assert len(generation_calls) == 3


def test_runner_preflights_all_requested_cells_before_generation(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "bad_pairing_manifest.json"
    payload = json.loads(Path(DEFAULT_FROZEN_CLUSTER1_MANIFEST).read_text(encoding="utf-8"))
    artifact = payload["artifacts"][0]
    for schedule in artifact["seed_schedule"]["records"]:
        if schedule["kernel_class"] == "elementwise" and schedule["dtype"] == "fp16":
            schedule["temperature"] = 0.9
            for line_number in schedule["line_numbers"]:
                for record in artifact["row_records"]:
                    if record["line_number"] == line_number:
                        record["temperature"] = 0.9
            break
    manifest.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    generation_calls: list[dict[str, Any]] = []

    with pytest.raises(ValueError, match="temperature"):
        run_cluster2(
            _config(
                tmp_path,
                condition="C",
                manifest=manifest,
                repair_budget=0,
                n=1,
                dtypes=("fp32", "fp16"),
                max_new_tokens=512,
            ),
            dependencies=RunnerDependencies(
                generation=_fake_generation(generation_calls),
                correctness=_success_correctness([]),
            ),
        )

    assert generation_calls == []


def test_runner_preflights_all_generated_conditions_before_generation(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "bad_gc_pairing_manifest.json"
    payload = json.loads(Path(DEFAULT_FROZEN_CLUSTER1_MANIFEST).read_text(encoding="utf-8"))
    task_agnostic_g_id = payload["selected_controls"]["task_agnostic_g_status"][
        "available_development_artifact_id"
    ]
    artifact = next(
        item
        for item in payload["artifacts"]
        if item["artifact_id"] == task_agnostic_g_id
    )
    for schedule in artifact["seed_schedule"]["records"]:
        if schedule["kernel_class"] == "elementwise" and schedule["dtype"] == "fp32":
            schedule["temperature"] = 0.9
            for line_number in schedule["line_numbers"]:
                for record in artifact["row_records"]:
                    if record["line_number"] == line_number:
                        record["temperature"] = 0.9
            break
    manifest.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    generation_calls: list[dict[str, Any]] = []

    with pytest.raises(ValueError, match="temperature"):
        run_cluster2(
            _config(
                tmp_path,
                condition="both",
                manifest=manifest,
                repair_budget=0,
                n=1,
                max_new_tokens=512,
            ),
            dependencies=RunnerDependencies(
                generation=_fake_generation(generation_calls),
                correctness=_success_correctness([]),
            ),
        )

    assert generation_calls == []


def test_runner_rejects_known_frozen_revision_mismatch(tmp_path: Path) -> None:
    manifest = _write_replay_fixture(tmp_path, condition="none", row_count=1)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    artifact = payload["artifacts"][0]
    artifact["seed_schedule"]["records"][0]["model_revision"] = "frozen-model-rev"
    artifact["row_records"][0]["model_revision"] = "frozen-model-rev"
    manifest.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    generation_calls: list[dict[str, Any]] = []

    with pytest.raises(ValueError, match="model_revision"):
        run_cluster2(
            _config(tmp_path, condition="C", manifest=manifest, repair_budget=0, n=1),
            dependencies=RunnerDependencies(
                generation=_fake_generation(generation_calls),
                correctness=_success_correctness([]),
            ),
        )

    assert generation_calls == []


def test_runner_template_upper_bound_requires_explicit_diagnostic_flag(
    tmp_path: Path,
) -> None:
    generation_calls: list[dict[str, Any]] = []

    result = run_cluster2(
        _config(
            tmp_path,
            condition="G+C",
            repair_budget=0,
            n=1,
            grammar_variant="template_upper_bound",
        ),
        dependencies=RunnerDependencies(
            generation=_fake_generation(generation_calls),
            correctness=_success_correctness([]),
        ),
    )

    assert generation_calls[0]["grammar_variant"] == "template_upper_bound"
    assert result.rows[0].generated_metadata is not None
    assert result.rows[0].generated_metadata.grammar_variant == "template_upper_bound"
    assert (
        result.rows[0].generated_metadata.grammar_path
        == "cluster1/grammar/triton_kernel.gbnf"
    )
    assert (
        result.rows[0].generated_metadata.grammar_claim_scope
        == "diagnostic_non_primary"
    )


def test_runner_blocks_paper_primary_gc_until_task_agnostic_g_n20_exists(
    tmp_path: Path,
) -> None:
    manifest = _write_replay_fixture(
        tmp_path / "manifest",
        condition="G",
        row_count=5,
        grammar_variant="task_agnostic",
    )
    generation_calls: list[dict[str, Any]] = []

    with pytest.raises(ValueError, match="paper-scale primary G\\+C requires"):
        run_cluster2(
            _config(
                tmp_path,
                condition="G+C",
                manifest=manifest,
                scale_tier="paper",
                n=20,
            ),
            dependencies=RunnerDependencies(
                generation=_forbidden_generation(generation_calls),
                correctness=_success_correctness([]),
            ),
        )

    assert generation_calls == []


def test_runner_blocks_paper_generated_run_without_f2_smoke_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generation_calls: list[dict[str, Any]] = []
    monkeypatch.setattr(runner_mod, "REPO_ROOT", tmp_path / "repo_without_smoke")

    with pytest.raises(FileNotFoundError, match="missing F2 smoke trace artifact"):
        run_cluster2(
            _config(
                tmp_path,
                condition="C",
                scale_tier="paper",
                repair_budget=0,
                n=1,
            ),
            dependencies=RunnerDependencies(
                generation=_forbidden_generation(generation_calls),
                correctness=_success_correctness([]),
            ),
        )

    assert generation_calls == []


def test_runner_allows_paper_generated_run_with_valid_f2_smoke_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generation_calls: list[dict[str, Any]] = []
    _copy_f2_smoke_artifacts(tmp_path / "repo_with_smoke")
    monkeypatch.setattr(runner_mod, "REPO_ROOT", tmp_path / "repo_with_smoke")

    result = run_cluster2(
        _config(
            tmp_path,
            condition="C",
            scale_tier="paper",
            repair_budget=0,
            n=1,
        ),
        dependencies=RunnerDependencies(
            generation=_fake_generation(generation_calls),
            correctness=_success_correctness([]),
        ),
    )

    assert len(generation_calls) == 1
    assert len(result.rows) == 1


def test_runner_paper_gate_rejects_missing_generation_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_f2_smoke_artifacts(tmp_path / "repo_with_smoke")
    monkeypatch.setattr(runner_mod, "REPO_ROOT", tmp_path / "repo_with_smoke")

    def incomplete_generation(**kwargs: Any) -> dict[str, Any]:
        payload = _fake_generation([])(**kwargs)
        payload.pop("runtime_identity", None)
        payload.pop("generation_result", None)
        return payload

    with pytest.raises(ValueError, match="paper-scale Cluster 2"):
        run_cluster2(
            _config(
                tmp_path,
                condition="C",
                scale_tier="paper",
                repair_budget=0,
                n=1,
            ),
            dependencies=RunnerDependencies(
                generation=incomplete_generation,
                correctness=_success_correctness([]),
            ),
        )


def test_runner_blocks_paper_generated_run_with_mock_f2_smoke_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generation_calls: list[dict[str, Any]] = []
    _copy_f2_smoke_artifacts(tmp_path / "repo_with_mock_smoke", modalized=False)
    monkeypatch.setattr(runner_mod, "REPO_ROOT", tmp_path / "repo_with_mock_smoke")

    with pytest.raises(ValueError, match="expected evaluation_mode"):
        run_cluster2(
            _config(
                tmp_path,
                condition="C",
                scale_tier="paper",
                repair_budget=0,
                n=1,
            ),
            dependencies=RunnerDependencies(
                generation=_forbidden_generation(generation_calls),
                correctness=_success_correctness([]),
            ),
        )

    assert generation_calls == []


def test_runner_blocks_paper_generated_run_with_mismatched_f2_smoke_revision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generation_calls: list[dict[str, Any]] = []
    repo_root = tmp_path / "repo_with_mismatched_smoke_revision"
    _copy_f2_smoke_artifacts(repo_root)
    trace_path = repo_root / "outputs" / "cluster2" / "smoke_f2_repair_relu.jsonl"
    rows = [
        json.loads(line)
        for line in trace_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rows[0]["model_revision"] = "c" * 40
    trace_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows)
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(runner_mod, "REPO_ROOT", repo_root)

    with pytest.raises(ValueError, match="model_revision"):
        run_cluster2(
            _config(
                tmp_path,
                condition="C",
                scale_tier="paper",
                repair_budget=0,
                n=1,
            ),
            dependencies=RunnerDependencies(
                generation=_forbidden_generation(generation_calls),
                correctness=_success_correctness([]),
            ),
        )

    assert generation_calls == []


def test_runner_blocks_paper_generated_run_with_old_f2_smoke_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generation_calls: list[dict[str, Any]] = []
    repo_root = tmp_path / "repo_with_old_smoke"
    _copy_f2_smoke_artifacts(repo_root)
    trace_path = repo_root / "outputs" / "cluster2" / "smoke_f2_repair_relu.jsonl"
    old_mtime = time.time() - runner_mod.F2_SMOKE_MAX_AGE_SECONDS - 10
    os.utime(trace_path, (old_mtime, old_mtime))
    monkeypatch.setattr(runner_mod, "REPO_ROOT", repo_root)

    with pytest.raises(ValueError, match="dated within the last 30 days"):
        run_cluster2(
            _config(
                tmp_path,
                condition="C",
                scale_tier="paper",
                repair_budget=0,
                n=1,
            ),
            dependencies=RunnerDependencies(
                generation=_forbidden_generation(generation_calls),
                correctness=_success_correctness([]),
            ),
        )

    assert generation_calls == []


def test_runner_blocks_paper_generated_run_with_fixture_newer_than_f2_smoke(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generation_calls: list[dict[str, Any]] = []
    repo_root = tmp_path / "repo_with_fixture_newer_than_smoke"
    _copy_f2_smoke_artifacts(repo_root)
    fixture_path = repo_root / "cluster2" / "tests" / "fixtures" / "f2_corrupted_relu.py"
    trace_path = repo_root / "outputs" / "cluster2" / "smoke_f2_repair_relu.jsonl"
    fixture_mtime = time.time()
    os.utime(fixture_path, (fixture_mtime, fixture_mtime))
    os.utime(trace_path, (fixture_mtime - 10, fixture_mtime - 10))
    monkeypatch.setattr(runner_mod, "REPO_ROOT", repo_root)

    with pytest.raises(ValueError, match="newer than their fixtures"):
        run_cluster2(
            _config(
                tmp_path,
                condition="C",
                scale_tier="paper",
                repair_budget=0,
                n=1,
            ),
            dependencies=RunnerDependencies(
                generation=_forbidden_generation(generation_calls),
                correctness=_success_correctness([]),
            ),
        )

    assert generation_calls == []


def test_runner_records_generation_mode_sidecar(tmp_path: Path) -> None:
    manifest = _write_replay_fixture(tmp_path, condition="none", row_count=1)

    replay = run_cluster2(
        _config(tmp_path / "replay", condition="none", manifest=manifest, n=1),
        dependencies=RunnerDependencies(
            generation=_forbidden_generation([]),
            correctness=_success_correctness([]),
        ),
    )
    generated = run_cluster2(
        _config(tmp_path / "generated", condition="G+C", repair_budget=0, n=1),
        dependencies=RunnerDependencies(
            generation=_fake_generation([]),
            correctness=_success_correctness([]),
        ),
    )

    assert replay.rows[0].generation_mode == "replay_control"
    assert generated.rows[0].generation_mode == "new_c2_generation_with_G_adapter"


def test_runner_resume_rejects_hash_mismatch(tmp_path: Path) -> None:
    config = _config(tmp_path, condition="C", repair_budget=0, n=1)
    deps = RunnerDependencies(
        generation=_fake_generation([]),
        correctness=_success_correctness([]),
    )
    run_cluster2(config, dependencies=deps)
    sidecar_path = default_content_hash_sidecar_path(config.output)
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    sidecar["eval_pipeline_hashes"]["shared/eval/pipeline.py"] = "f" * 64
    sidecar_path.write_text(json.dumps(sidecar, sort_keys=True) + "\n", encoding="utf-8")
    resume_generation_calls: list[dict[str, Any]] = []
    resume_correctness_calls: list[Any] = []

    resume_config = _config(
        tmp_path,
        condition="C",
        repair_budget=0,
        n=1,
        write_mode="resume",
    )
    with pytest.raises(ValueError, match="content-hash sidecar mismatch"):
        run_cluster2(
            resume_config,
            dependencies=RunnerDependencies(
                generation=_forbidden_generation(resume_generation_calls),
                correctness=_success_correctness(resume_correctness_calls),
            ),
        )
    assert resume_generation_calls == []
    assert resume_correctness_calls == []


def test_append_flag_is_rejected_by_cli(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        parse_args(
            [
                "--condition",
                "C",
                "--kernel-class",
                "elementwise",
                "--scale-tier",
                "smoke",
                "--n",
                "1",
                "--model-revision",
                TEST_MODEL_REVISION,
                "--tokenizer-revision",
                TEST_TOKENIZER_REVISION,
                "--output",
                str(tmp_path / "out.jsonl"),
                "--append",
            ]
        )


def test_replay_cli_allows_omitted_revision_flags(tmp_path: Path) -> None:
    config = parse_args(
        [
            "--condition",
            "none",
            "--kernel-class",
            "elementwise",
            "--scale-tier",
            "smoke",
            "--n",
            "1",
            "--output",
            str(tmp_path / "out.jsonl"),
            "--overwrite",
        ]
    )

    assert config.condition == "none"
    assert config.model_revision is None
    assert config.tokenizer_revision is None


def test_cli_defaults_gc_grammar_variant_to_task_agnostic(tmp_path: Path) -> None:
    config = parse_args(
        [
            "--condition",
            "G+C",
            "--kernel-class",
            "elementwise",
            "--scale-tier",
            "smoke",
            "--n",
            "1",
            "--model-revision",
            TEST_MODEL_REVISION,
            "--tokenizer-revision",
            TEST_TOKENIZER_REVISION,
            "--output",
            str(tmp_path / "out.jsonl"),
            "--overwrite",
        ]
    )

    assert config.grammar_variant == "task_agnostic"
    assert config.max_new_tokens == DEFAULT_MAX_NEW_TOKENS
    assert config.max_new_tokens >= 1024


def test_cli_accepts_explicit_template_upper_bound_diagnostic(
    tmp_path: Path,
) -> None:
    config = parse_args(
        [
            "--condition",
            "G+C",
            "--kernel-class",
            "elementwise",
            "--scale-tier",
            "smoke",
            "--n",
            "1",
            "--model-revision",
            TEST_MODEL_REVISION,
            "--tokenizer-revision",
            TEST_TOKENIZER_REVISION,
            "--grammar-variant",
            "template_upper_bound",
            "--output",
            str(tmp_path / "out.jsonl"),
            "--overwrite",
        ]
    )

    assert config.grammar_variant == "template_upper_bound"


def test_generated_cli_requires_revision_flags(tmp_path: Path) -> None:
    with pytest.raises((TypeError, ValueError), match="model_revision"):
        parse_args(
            [
                "--condition",
                "C",
                "--kernel-class",
                "elementwise",
                "--scale-tier",
                "smoke",
                "--n",
                "1",
                "--output",
                str(tmp_path / "out.jsonl"),
                "--overwrite",
            ]
        )


def test_generated_cli_rejects_floating_revisions(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="40-character Hub commit SHA"):
        parse_args(
            [
                "--condition",
                "C",
                "--kernel-class",
                "elementwise",
                "--scale-tier",
                "smoke",
                "--n",
                "1",
                "--model-revision",
                "refs/heads/main",
                "--tokenizer-revision",
                TEST_TOKENIZER_REVISION,
                "--output",
                str(tmp_path / "out.jsonl"),
                "--overwrite",
            ]
        )


def test_runner_imports_cheaply() -> None:
    code = "\n".join(
        [
            "import sys",
            "import cluster2.experiments.run_cluster2_modal",
            "for name in (",
            "    'modal',",
            "    'torch',",
            "    'triton',",
            "    'transformers',",
            "    'xgrammar',",
            "    'cluster2.generation.modal_generate_c2',",
            "    'cluster2.modal.generation',",
            "):",
            "    if name in sys.modules:",
            "        print(name)",
        ]
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
    )

    assert proc.stdout.strip() == ""


def test_runner_preserves_l4_explicit_gpu_routing(tmp_path: Path) -> None:
    generation_calls: list[dict[str, Any]] = []

    run_cluster2(
        _config(tmp_path, condition="C", repair_budget=0, n=1),
        dependencies=RunnerDependencies(
            generation=_fake_generation(generation_calls),
            correctness=_success_correctness([]),
        ),
    )

    assert generation_calls[0]["modal_generation_gpu"] == "L4"
    with pytest.raises(ValueError, match="modal_generation_gpu must be L4"):
        _config(
            tmp_path / "bad",
            condition="C",
            repair_budget=0,
            n=1,
            modal_generation_gpu="L40S",
        )


def _config(
    tmp_path: Path,
    *,
    condition: str,
    manifest: Path | None = None,
    scale_tier: str = "smoke",
    n: int = 1,
    repair_budget: int = 0,
    write_mode: str = "overwrite",
    modal_generation_gpu: str = "L4",
    grammar_variant: str = "task_agnostic",
    dtypes: tuple[str, ...] = ("fp32",),
    max_new_tokens: int = 64,
) -> Cluster2RunnerConfig:
    tmp_path.mkdir(parents=True, exist_ok=True)
    if manifest is None and condition in {"C", "G+C"}:
        replay_condition = "none" if condition == "C" else "G"
        manifest = _write_replay_fixture(
            tmp_path / f"{condition}-paired-manifest",
            condition=replay_condition,
            row_count=n,
            grammar_variant=grammar_variant,
        )
    return Cluster2RunnerConfig(
        condition=condition,
        kernel_class="elementwise",
        scale_tier=scale_tier,
        n=n,
        frozen_cluster1_manifest=str(
            manifest if manifest is not None else tmp_path / "unused_manifest.json"
        ),
        model_id="Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        model_revision=TEST_MODEL_REVISION,
        tokenizer_revision=TEST_TOKENIZER_REVISION,
        grammar_variant=grammar_variant,
        dtypes=dtypes,
        temperature=0.2,
        max_new_tokens=max_new_tokens,
        repair_budget=repair_budget,
        modal_generation_gpu=modal_generation_gpu,
        modal_eval_gpu="L4",
        output=str(tmp_path / "cluster2.jsonl"),
        write_mode=write_mode,
    )


def _forbidden_generation(calls: list[dict[str, Any]]):
    def generation(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        raise AssertionError("replay controls must not call generation")

    return generation


def _fake_generation(calls: list[dict[str, Any]]):
    def generation(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        identity = kwargs["identity"]
        grammar_variant = kwargs.get("grammar_variant")
        grammar_path = None
        grammar_claim_scope = None
        if identity.condition == "G+C":
            grammar_variant = grammar_variant or "task_agnostic"
            grammar_path = (
                "cluster1/grammar/triton_kernel.gbnf"
                if grammar_variant == "template_upper_bound"
                else "cluster1/grammar/triton_kernel_agnostic.gbnf"
            )
            grammar_claim_scope = (
                "diagnostic_non_primary"
                if grammar_variant == "template_upper_bound"
                else "primary"
            )
        source = (
            "import torch\n"
            "import triton\n"
            "import triton.language as tl\n"
            f"# generated {identity.condition} {identity.attempt_index}\n"
        )
        grammar_sha = None
        validation_fields = {
            "gbnf_parse_valid": None,
            "semantic_valid": None,
            "grammar_valid": None,
            "rejection_layer": None,
        }
        if identity.condition == "G+C":
            from cluster1.generation.provenance import sha256_file
            from cluster1.grammar.triton_kernel_validator import validate_source_layers

            assert grammar_path is not None
            local_grammar_path = REPO_ROOT / grammar_path
            grammar_sha = sha256_file(local_grammar_path)
            validation_fields = validate_source_layers(
                source,
                grammar_path=local_grammar_path,
            ).to_row_fields()
        model_revision = kwargs.get("model_revision", TEST_MODEL_REVISION)
        tokenizer_revision = kwargs.get("tokenizer_revision", TEST_TOKENIZER_REVISION)
        image_components = _fallback_modal_image_components()
        image_sha = modal_image_provenance_digest(image_components)
        return {
            "source": source,
            "generation_hashes": collect_c2_generation_hashes(identity.condition),
            "generation_identity": {
                "grammar_active": identity.condition == "G+C",
                "grammar_variant": (
                    grammar_variant if identity.condition == "G+C" else None
                ),
                "grammar_path": grammar_path,
                "grammar_sha": grammar_sha,
                "grammar_claim_scope": grammar_claim_scope,
                **validation_fields,
                "stop_reason": "eos_token",
                "generation_metadata_schema_version": (
                    CLUSTER2_GENERATION_METADATA_SCHEMA_VERSION
                ),
            },
            "runtime_identity": {
                "xgrammar_version": "0.1.33",
                "transformers_version": "4.47.1",
                "tokenizers_version": "0.21.4",
                "modal_image_sha": "unknown",
                "modal_image_provenance_sha256": image_sha,
                "modal_image_provenance_components": image_components,
            },
            "model_identity": {
                "model_revision": model_revision,
                "tokenizer_revision": tokenizer_revision,
                "observed_model_revision": model_revision,
                "observed_tokenizer_revision": tokenizer_revision,
            },
            "generation_result": {
                "model_revision": model_revision,
                "tokenizer_revision": tokenizer_revision,
                "stop_reason": "eos_token",
                "xgrammar_version": "0.1.33",
                "transformers_version": "4.47.1",
                "tokenizers_version": "0.21.4",
                "modal_image_sha": "unknown",
                "modal_image_provenance_sha256": image_sha,
                "modal_image_provenance_components": image_components,
                "generation_metadata_schema_version": (
                    CLUSTER2_GENERATION_METADATA_SCHEMA_VERSION
                ),
            },
        }

    return generation


def _gc_fake_payload() -> dict[str, Any]:
    identity = EvalIdentity(
        run_id="test-run",
        condition="G+C",
        source_class="generated_row",
        generation_mode="new_c2_generation_with_G_adapter",
        kernel_class="elementwise",
        kernel_name="relu",
        dtype="fp32",
        sample_index=0,
        base_seed=0,
        attempt_index=0,
    )
    return _fake_generation([])(
        identity=identity,
        grammar_variant="task_agnostic",
    )


def _copy_f2_smoke_artifacts(repo_root: Path, *, modalized: bool = True) -> None:
    fixture_source_dir = REPO_ROOT / "cluster2" / "tests" / "fixtures"
    fixture_target_dir = repo_root / "cluster2" / "tests" / "fixtures"
    trace_target_dir = repo_root / "outputs" / "cluster2"
    fixture_target_dir.mkdir(parents=True, exist_ok=True)
    trace_target_dir.mkdir(parents=True, exist_ok=True)
    for name in (
        "f2_corrupted_relu.py",
        "f2_corrupted_softmax.py",
        "f2_corrupted_matmul.py",
    ):
        (fixture_target_dir / name).write_text(
            (fixture_source_dir / name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    for archetype in ("relu", "softmax", "matmul"):
        if modalized:
            fixture_path = fixture_target_dir / f"f2_corrupted_{archetype}.py"
            corrected_source = _corrected_source(
                fixture_path.read_text(encoding="utf-8"),
                archetype,
            )

            def generation_adapter(**kwargs: Any) -> dict[str, Any]:
                identity = kwargs["identity"]
                return {
                    "source": corrected_source,
                    "modal_context": _generation_modal_context(identity.attempt_index),
                }

            def correctness_adapter(request: RemoteCorrectnessRequest) -> dict[str, Any]:
                return _remote_smoke_correctness_payload(
                    request,
                    functional_success=request.identity.attempt_index > 0,
                )

            run_f2_repair_smoke(
                fixture_path=fixture_path,
                archetype=archetype,
                output_path=trace_target_dir / f"smoke_f2_repair_{archetype}.jsonl",
                repair_budget=1,
                mock_repair=False,
                model_revision=TEST_MODEL_REVISION,
                tokenizer_revision=TEST_TOKENIZER_REVISION,
                generation_adapter=generation_adapter,
                correctness_adapter=correctness_adapter,
            )
        else:
            rows = [
                json.loads(line)
                for line in (
                    fixture_source_dir
                    / "expected_smoke_traces"
                    / f"{archetype}.jsonl"
                ).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            (trace_target_dir / f"smoke_f2_repair_{archetype}.jsonl").write_text(
                "\n".join(
                    json.dumps(row, sort_keys=True, separators=(",", ":"))
                    for row in rows
                )
                + "\n",
                encoding="utf-8",
            )


def _remote_smoke_correctness_payload(
    request: RemoteCorrectnessRequest,
    *,
    functional_success: bool,
) -> dict[str, Any]:
    result = RemoteCorrectnessResult(
        identity=request.identity,
        functional_success=functional_success,
        repair_set_success=functional_success,
        eval_set_success=functional_success,
        failure_code=None if functional_success else "F2_NUMERIC_LARGE",
        correctness_error=(
            None
            if functional_success
            else "F2_NUMERIC_LARGE max_abs_diff=1.0 max_rel_diff=1.0"
        ),
        feedback=None if functional_success else "max_abs_diff=1.0 max_rel_diff=1.0",
        num_repair_shapes=1,
        num_eval_shapes=1,
        num_test_shapes=2,
        shapes_passed=2 if functional_success else 0,
        repair_shapes_passed=1 if functional_success else 0,
        eval_shapes_passed=1 if functional_success else 0,
        max_abs_diff=0.0 if functional_success else 1.0,
        max_rel_diff=0.0 if functional_success else 1.0,
    )
    payload = build_success_payload(request, result)
    payload["modal_context"] = _correctness_modal_context(
        request.identity.attempt_index
    )
    return payload


def _generation_modal_context(attempt_index: int) -> dict[str, str]:
    return {
        "function_call_id": f"generation-call-{attempt_index}",
        "input_id": f"generation-input-{attempt_index}",
        "modal_generation_gpu": "L4",
    }


def _correctness_modal_context(attempt_index: int) -> dict[str, str]:
    return {
        "function_call_id": f"correctness-call-{attempt_index}",
        "input_id": f"correctness-input-{attempt_index}",
        "modal_eval_gpu": "L4",
    }


def _success_correctness(calls: list[Any]):
    def correctness(request: Any) -> dict[str, Any]:
        calls.append(request)
        return {
            "correctness_result": {
                "identity": request.identity.model_dump(),
                "functional_success": True,
                "repair_set_success": True,
                "eval_set_success": True,
                "failure_code": None,
                "correctness_error": None,
            }
        }

    return correctness
