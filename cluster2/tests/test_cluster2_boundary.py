"""Phase 14 boundary and preservation tests for Cluster 2."""

from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
from dataclasses import fields
from pathlib import Path
from typing import Any

import pytest

from cluster2.constants import (
    AGENTIC_TRANSCRIPT_MAX_PROMPT_CHARS_V1,
    AGENTIC_TRANSCRIPT_REPAIR_HISTORY_POLICY_V1,
    C_GENERATION_MODE,
    DEFAULT_REPAIR_HISTORY_POLICY_V1,
    G_PLUS_C_GENERATION_MODE,
    GENERATED_SOURCE_CLASS,
    LAST_ATTEMPT_ONLY_REPAIR_HISTORY_POLICY_V1,
    REPLAY_CONTROL_GENERATION_MODE,
    REPLAY_CONTROL_SOURCE_CLASS,
    REPAIR_HISTORY_POLICIES_V1,
    generation_allowed_for_condition,
)
from cluster2.experiments.run_cluster2_modal import (
    Cluster2RunnerConfig,
    RunnerDependencies,
    run_cluster2,
)
from cluster2.feedback.trace import TraceSummary
from cluster2.modal.schemas import (
    EvalIdentity,
    RemoteC2GenerationRequest,
    RemoteC2GenerationResult,
    RemoteCorrectnessRequest,
    RemoteCorrectnessResult,
)
from cluster2.results.dataclass import (
    CLUSTER2_GENERATION_METADATA_SCHEMA_VERSION,
    Cluster2ContentHashSidecar,
    Cluster2EvalRow,
    Cluster2GeneratedRowMetadata,
    Cluster2ReplayRowMetadata,
)
from cluster2.tests.test_replay_controls import _write_replay_fixture
from shared.eval.pipeline import EvalPipelineSkeletonResult, PipelineStageStatus
from shared.eval.run_config import RunConfig
from shared.generation_metadata import modal_image_provenance_digest


REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_MODEL_REVISION = "a" * 40
TEST_TOKENIZER_REVISION = "b" * 40
PHASE_MINUS1_MANIFEST = REPO_ROOT / "cluster2/contracts/phase_minus1_manifest.json"
FROZEN_CLUSTER1_MANIFEST = (
    REPO_ROOT / "cluster2/contracts/frozen_cluster1_artifacts_manifest.json"
)


def test_repair_history_policy_constants_are_legacy_default_opt_in_v1() -> None:
    assert LAST_ATTEMPT_ONLY_REPAIR_HISTORY_POLICY_V1 == "last_attempt_only_v1"
    assert AGENTIC_TRANSCRIPT_REPAIR_HISTORY_POLICY_V1 == "agentic_transcript_v1"
    assert REPAIR_HISTORY_POLICIES_V1 == frozenset(
        {
            LAST_ATTEMPT_ONLY_REPAIR_HISTORY_POLICY_V1,
            AGENTIC_TRANSCRIPT_REPAIR_HISTORY_POLICY_V1,
        }
    )
    assert DEFAULT_REPAIR_HISTORY_POLICY_V1 == LAST_ATTEMPT_ONLY_REPAIR_HISTORY_POLICY_V1
    assert DEFAULT_REPAIR_HISTORY_POLICY_V1 != AGENTIC_TRANSCRIPT_REPAIR_HISTORY_POLICY_V1
    assert AGENTIC_TRANSCRIPT_MAX_PROMPT_CHARS_V1 == 24000


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

FORBIDDEN_SCHEMA_FIELD_NAMES = frozenset(
    {
        "timing",
        "profiling",
        "profile",
        "profiler",
        "profiler_output",
        "speedup",
        "speedup_vs_compile",
        "speedup_vs_eager",
        "fast@",
        "nsight",
        "ncu",
        "nvml",
        "throughput",
        "latency",
        "latency_ms",
        "token_count",
        "token_counts",
        "tokens",
        "tokens_input",
        "tokens_output",
        "tokens_generated",
        "input_token_count",
        "output_token_count",
        "benchmark_score",
    }
)

FORBIDDEN_SOURCE_TERMS = (
    "timing",
    "profiling",
    "profiler",
    "speedup",
    "fast@",
    "nsight",
    "ncu",
    "nvml",
    "throughput",
    "latency",
    "token_count",
    "tokens",
    "benchmark_score",
)

FORBIDDEN_TERM_ALLOWLIST_PATHS = frozenset(
    {
        "cluster2/feedback/prompts.py",
        "cluster2/results/dataclass.py",
        "cluster2/modal/schemas.py",
        "shared/eval/constants.py",
        "shared/eval/schema.py",
        "shared/eval/levels/level0_ast_sanitizer.py",
    }
)


def test_remote_generator_generate_one_hash_matches_phase_minus1() -> None:
    from cluster2.modal.generation import (
        current_remote_generator_generate_one_hash,
        verify_phase_minus1_remote_generator_hash,
    )

    manifest = _load_json(PHASE_MINUS1_MANIFEST)
    record = manifest["cluster1_invariants"]["modal_generation"][
        "RemoteGenerator.generate_one"
    ]
    phase_minus1_range_hash = _source_range_sha256(
        REPO_ROOT / record["path"],
        start_line=int(record["lines"]["start"]),
        end_line=int(record["lines"]["end"]),
    )
    current_hash = current_remote_generator_generate_one_hash()

    observed = verify_phase_minus1_remote_generator_hash()
    assert observed["RemoteGenerator.generate_one"] == record["source_sha256"]
    assert (
        observed.get("RemoteGenerator.generate_one:current_instrumented")
        == current_hash
    )
    assert current_hash != phase_minus1_range_hash


def test_cluster1_model_loading_hash_matches_phase_minus1_if_recorded() -> None:
    manifest = _load_json(PHASE_MINUS1_MANIFEST)
    modal_generation = manifest["cluster1_invariants"]["modal_generation"]
    record = (
        modal_generation.get("RemoteGenerator.load_model")
        or modal_generation.get("RemoteGenerator.model_loading")
    )
    if record is None:
        pytest.skip("Phase -1 manifest does not record a Cluster 1 model-loading hash")

    if "lines" in record:
        current_hash = _source_range_sha256(
            REPO_ROOT / record["path"],
            start_line=int(record["lines"]["start"]),
            end_line=int(record["lines"]["end"]),
        )
    else:
        current_hash = _file_sha256(REPO_ROOT / record["path"])

    assert current_hash == record["source_sha256"]


@pytest.mark.parametrize(
    "rel_path",
    [
        "shared/modal_harness/generation.py",
        "shared/modal_harness/schemas.py",
        "shared/modal_harness/smoke.py",
    ],
)
def test_shared_modal_files_match_phase_minus1_git_head(rel_path: str) -> None:
    manifest = _load_json(PHASE_MINUS1_MANIFEST)
    phase_head = manifest["git"]["current_head"]
    current_hash = _file_sha256(REPO_ROOT / rel_path)
    phase_hash = _git_blob_sha256(phase_head, rel_path)
    instrumented_modal_files = {
        "shared/modal_harness/generation.py",
        "shared/modal_harness/schemas.py",
    }
    if rel_path in instrumented_modal_files:
        assert current_hash != phase_hash
        assert current_hash
        return

    accepted_hash_record = (
        manifest.get("accepted_boundary_hash_overrides", {})
        .get("shared_modal_files", {})
        .get(rel_path)
    )
    if accepted_hash_record is not None:
        assert accepted_hash_record["previous_phase_minus1_sha256"] == phase_hash
        assert current_hash == accepted_hash_record["expected_sha256"]
        return

    assert current_hash == phase_hash


def test_frozen_cluster1_manifest_hash_matches_phase_minus1() -> None:
    manifest = _load_json(PHASE_MINUS1_MANIFEST)
    record = manifest["frozen_cluster1_artifacts_manifest"]
    current_manifest_path = REPO_ROOT / record["path"]
    current_sha256 = _file_sha256(current_manifest_path)

    assert record["path"] == "cluster2/contracts/frozen_cluster1_artifacts_manifest.json"
    if current_sha256 == record["sha256"]:
        return

    current_manifest = _load_json(current_manifest_path)
    artifacts = {
        artifact["artifact_id"]: artifact
        for artifact in current_manifest["artifacts"]
    }
    assert current_manifest["schema_version"] == record["schema_version"]
    assert [artifact["artifact_id"] for artifact in current_manifest["artifacts"]] == [
        "none_baseline_n20_l4",
        "g_template_upper_bound_n20_l4",
        "g_task_agnostic_n5_l4_rerun",
        "g_task_agnostic_aligned_pipeline_n20_l4",
    ]
    assert {
        artifact_id: _frozen_cluster1_artifact_boundary(artifacts[artifact_id])
        for artifact_id in (
            "none_baseline_n20_l4",
            "g_template_upper_bound_n20_l4",
            "g_task_agnostic_n5_l4_rerun",
        )
    } == {
        "none_baseline_n20_l4": {
            "condition": "none",
            "path": "outputs/cluster1/baseline_repaired_l4_n20.jsonl",
            "sha256": (
                "1f3e004b25564f347b2fb293216d2a9589ac7aaa60728cabd1d20e40af4f4cc3"
            ),
            "row_count": 180,
            "role": "frozen_none_replay_control",
            "metadata_sidecar_path": (
                "outputs/cluster1/baseline_repaired_l4_n20.jsonl.meta.json"
            ),
            "metadata_sidecar_sha256": (
                "ce14490c915515305c7a9e9c310f8e79c3c5f192eea55a9f6a77f5623759d551"
            ),
        },
        "g_template_upper_bound_n20_l4": {
            "condition": "G",
            "path": "outputs/cluster1/final_g_l4_n20.jsonl",
            "sha256": (
                "51af551433ae5180eac85cf877409a8d73b0e53fba07b40699d42024757a3d18"
            ),
            "row_count": 180,
            "role": "frozen_g_template_upper_bound_replay_control",
            "metadata_sidecar_path": "outputs/cluster1/final_g_l4_n20.jsonl.meta.json",
            "metadata_sidecar_sha256": (
                "9248134ebd45f3e6ba614a8897ce4e7431f5ce3b00e1b0829cb668a00b8ce83b"
            ),
        },
        "g_task_agnostic_n5_l4_rerun": {
            "condition": "G",
            "path": "outputs/cluster1/task_agnostic_g_all_n5_l4_rerun.jsonl",
            "sha256": (
                "0efb88886ec0abca432835e66309e232155bce55f562de385d13d8f506e55d56"
            ),
            "row_count": 45,
            "role": "frozen_g_task_agnostic_development_control",
            "metadata_sidecar_path": (
                "outputs/cluster1/task_agnostic_g_all_n5_l4_rerun.jsonl.meta.json"
            ),
            "metadata_sidecar_sha256": (
                "7094670cfe51d22dcd64a9ce34738143678eebd0acd4d8a2ed459c743f8b9937"
            ),
        },
    }
    assert _frozen_cluster1_artifact_boundary(
        artifacts["g_task_agnostic_aligned_pipeline_n20_l4"]
    ) == {
        "condition": "G",
        "path": "outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl",
        "sha256": (
            "59e6026d18db58fae0472591f3b924f83c837e99b0a543b131efe94a9e37751a"
        ),
        "row_count": 177,
        "role": "frozen_g_task_agnostic_n20_replay_control",
        "metadata_sidecar_path": (
            "outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl.meta.json"
        ),
        "metadata_sidecar_sha256": (
            "a8af73753916f2c5cff2dd35942762890bfc9f8d7d6ab8ec8517c89e18e000b0"
        ),
        "coverage_policy": "COVERAGE_WARNING_SKIP_MISSING",
        "expected_n": 20,
        "intended_rows": 180,
        "observed_rows": 177,
    }
    assert current_manifest["selected_controls"] == {
        "cluster2_v5_template_upper_bound_controls": {
            "artifact_ids": [
                "none_baseline_n20_l4",
                "g_template_upper_bound_n20_l4",
            ],
            "coverage_failures": [],
            "paper_rows_per_cell_sufficient": True,
        },
        "task_agnostic_g_status": {
            "artifact_path": (
                "outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl"
            ),
            "available_development_artifact_id": (
                "g_task_agnostic_aligned_pipeline_n20_l4"
            ),
            "available_task_agnostic_g_n20_replay_artifact_id": (
                "g_task_agnostic_aligned_pipeline_n20_l4"
            ),
            "coverage_complete": False,
            "coverage_policy": "COVERAGE_WARNING_SKIP_MISSING",
            "development_rows_per_cell_sufficient": False,
            "expected_n": 20,
            "intended_rows": 180,
            "missing_rows": [
                {"dtype": "fp32", "kernel_class": "matmul", "sample_index": 5},
                {"dtype": "bf16", "kernel_class": "matmul", "sample_index": 0},
                {"dtype": "bf16", "kernel_class": "matmul", "sample_index": 18},
            ],
            "note": (
                "Task-agnostic G n=20 is registered for G+C replay with explicit "
                "177/180 coverage warning and matched-row skip policy; missing "
                "rows are not imputed."
            ),
            "observed_rows": 177,
            "paper_coverage_failures": [
                {
                    "artifact_id": "g_task_agnostic_aligned_pipeline_n20_l4",
                    "condition": "G",
                    "dtype": "fp32",
                    "grammar_active": True,
                    "kernel_class": "matmul",
                    "missing_rows": 1,
                    "observed_rows": 19,
                    "required_rows": 20,
                    "status": "coverage_warning_skip_missing",
                },
                {
                    "artifact_id": "g_task_agnostic_aligned_pipeline_n20_l4",
                    "condition": "G",
                    "dtype": "bf16",
                    "grammar_active": True,
                    "kernel_class": "matmul",
                    "missing_rows": 2,
                    "observed_rows": 18,
                    "required_rows": 20,
                    "status": "coverage_warning_skip_missing",
                },
            ],
            "paper_rows_available_with_skip_policy": True,
            "paper_rows_per_cell_sufficient": False,
        },
    }
    coverage_assessment = current_manifest["coverage_assessment"]
    assert "g_task_agnostic_n5_l4_rerun" not in json.dumps(
        coverage_assessment,
        sort_keys=True,
    )
    assert coverage_assessment["paper"] == {
        "coverage_failure_missing_frozen_control_count": 0,
        "coverage_failures": [],
        "coverage_warning_skip_missing_count": 2,
        "coverage_warnings": [
            {
                "artifact_id": "g_task_agnostic_aligned_pipeline_n20_l4",
                "condition": "G",
                "coverage_policy": "COVERAGE_WARNING_SKIP_MISSING",
                "dtype": "fp32",
                "grammar_active": True,
                "kernel_class": "matmul",
                "missing_rows": 1,
                "missing_samples": [5],
                "observed_rows": 19,
                "required_rows": 20,
                "status": "coverage_warning_skip_missing",
            },
            {
                "artifact_id": "g_task_agnostic_aligned_pipeline_n20_l4",
                "condition": "G",
                "coverage_policy": "COVERAGE_WARNING_SKIP_MISSING",
                "dtype": "bf16",
                "grammar_active": True,
                "kernel_class": "matmul",
                "missing_rows": 2,
                "missing_samples": [0, 18],
                "observed_rows": 18,
                "required_rows": 20,
                "status": "coverage_warning_skip_missing",
            },
        ],
        "passed": False,
        "passed_with_skip_policy": True,
        "required_rows_per_kernel_dtype_condition": 20,
    }


def test_default_generation_gpu_remains_l40s() -> None:
    manifest = _load_json(PHASE_MINUS1_MANIFEST)
    expected_gpu = manifest["cluster1_invariants"]["modal_generation"][
        "DEFAULT_GENERATION_GPU"
    ]

    assert expected_gpu == "L40S"
    assert (
        _literal_assignment(
            REPO_ROOT / "shared/modal_harness/generation.py",
            "DEFAULT_GENERATION_GPU",
        )
        == expected_gpu
    )


def test_cluster1_kernel_specs_keys_and_order_match_phase_minus1() -> None:
    from cluster1.data.kernels import KERNEL_SPECS

    manifest = _load_json(PHASE_MINUS1_MANIFEST)
    expected = manifest["cluster1_invariants"]["kernel_specs"]
    observed_keys = list(KERNEL_SPECS)

    assert observed_keys == expected["keys_order"]
    assert observed_keys == expected["expected_keys_order"]
    assert _canonical_json_sha256(observed_keys) == expected["keys_order_hash"]


def test_cluster1_generation_result_fields_match_phase_minus1() -> None:
    from cluster1.results.dataclass import GenerationResult

    manifest = _load_json(PHASE_MINUS1_MANIFEST)
    expected = manifest["cluster1_invariants"]["GenerationResult"]
    observed_fields = [field.name for field in fields(GenerationResult)]
    expected_fields = expected["field_list"]
    post_phase_minus1_fields = [
        "failure_code",
        "generation_metadata_schema_version",
        "grammar_sha",
        "grammar_path",
        "gbnf_parse_valid",
        "semantic_valid",
        "grammar_valid",
        "rejection_layer",
        "stop_reason",
        "xgrammar_version",
        "transformers_version",
        "tokenizers_version",
        "model_revision",
        "tokenizer_revision",
        "modal_image_sha",
        "modal_image_provenance_sha256",
        "modal_image_provenance_components",
    ]

    assert observed_fields[: len(expected_fields)] == expected_fields
    assert _canonical_json_sha256(expected_fields) == expected["field_list_sha256"]
    assert observed_fields[len(expected_fields) :] == post_phase_minus1_fields


def test_cluster1_prompt_hashes_match_phase_minus1_if_recorded() -> None:
    from cluster1.data.kernels import KERNEL_SPECS
    from cluster1.data.prompts.prompt_contract import build_prompt

    manifest = _load_json(PHASE_MINUS1_MANIFEST)
    records = manifest["cluster1_invariants"].get("prompt_hashes", {}).get(
        "records",
        [],
    )
    if not records:
        pytest.skip("Phase -1 manifest does not record prompt hashes")

    for record in records:
        prompt = build_prompt(KERNEL_SPECS[record["kernel_class"]], record["dtype"])
        assert hashlib.sha256(prompt.encode("utf-8")).hexdigest() == record[
            "prompt_sha256"
        ]


@pytest.mark.parametrize("factor_cell", ["C", "G+C", "P"])
def test_cluster1_request_schema_rejects_non_cluster1_modes(factor_cell: str) -> None:
    from shared.modal_harness.schemas import RemoteGenerationRequest

    with pytest.raises(ValueError, match="only 'none' and 'G'"):
        RemoteGenerationRequest(
            factor_cell=factor_cell,
            kernel_class="elementwise",
            kernel_name="relu",
            dtype="fp32",
            prompt="write relu",
            model_id="model",
            grammar_active=False,
            run_id="phase14-boundary",
        )


@pytest.mark.parametrize("condition", ["none", "G"])
def test_replay_conditions_never_call_c2_generation(
    tmp_path: Path,
    condition: str,
) -> None:
    manifest = _write_replay_fixture(
        tmp_path / f"replay-{condition}",
        condition=condition,
        row_count=1,
        grammar_variant=(
            "task_agnostic" if condition == "G" else "template_upper_bound"
        ),
    )
    generation_calls: list[dict[str, Any]] = []
    correctness_calls: list[Any] = []

    result = run_cluster2(
        _runner_config(tmp_path / f"out-{condition}", condition=condition, manifest=manifest),
        dependencies=RunnerDependencies(
            generation=_forbidden_generation(generation_calls),
            correctness=_success_correctness(correctness_calls),
        ),
    )

    assert generation_allowed_for_condition(condition) is False
    assert generation_calls == []
    assert len(correctness_calls) == 1
    assert result.route_audit[0].route == "replay_adapter"
    assert result.route_audit[0].generation_calls == 0
    assert {row.source_class for row in result.rows} == {REPLAY_CONTROL_SOURCE_CLASS}
    assert {row.generation_mode for row in result.rows} == {
        REPLAY_CONTROL_GENERATION_MODE
    }


@pytest.mark.parametrize(
    ("condition", "expected_generation_mode", "expected_route"),
    [
        ("C", C_GENERATION_MODE, "c2_repair_loop"),
        ("G+C", G_PLUS_C_GENERATION_MODE, "c2_repair_loop_with_g_adapter"),
    ],
)
def test_generated_conditions_route_to_generated_path(
    tmp_path: Path,
    condition: str,
    expected_generation_mode: str,
    expected_route: str,
) -> None:
    replay_manifest = _write_replay_fixture(
        tmp_path / f"replay-{condition}",
        condition="G" if condition == "G+C" else "none",
        row_count=1,
        grammar_variant=(
            "task_agnostic" if condition == "G+C" else "template_upper_bound"
        ),
    )
    generation_calls: list[dict[str, Any]] = []

    result = run_cluster2(
        _runner_config(
            tmp_path / f"out-{condition}",
            condition=condition,
            manifest=replay_manifest,
        ),
        dependencies=RunnerDependencies(
            generation=_fake_generation(generation_calls),
            correctness=_success_correctness([]),
        ),
    )

    assert generation_allowed_for_condition(condition) is True
    assert len(generation_calls) == 1
    assert generation_calls[0]["modal_generation_gpu"] == "L4"
    assert result.route_audit[0].route == expected_route
    assert result.rows[0].source_class == GENERATED_SOURCE_CLASS
    assert result.rows[0].generation_mode == expected_generation_mode
    assert result.rows[0].generated_metadata is not None
    assert result.rows[0].replay_metadata is None


def test_g_plus_c_default_grammar_routing_stays_task_agnostic() -> None:
    from cluster2.modal.generation import generation_routing_for_condition

    primary = generation_routing_for_condition("G+C")
    diagnostic = generation_routing_for_condition(
        "G+C",
        grammar_variant="template_upper_bound",
    )

    assert primary.grammar_variant == "task_agnostic"
    assert primary.grammar_path == "cluster1/grammar/triton_kernel_agnostic.gbnf"
    assert primary.grammar_claim_scope == "primary"
    assert diagnostic.grammar_variant == "template_upper_bound"
    assert diagnostic.grammar_path == "cluster1/grammar/triton_kernel.gbnf"
    assert diagnostic.grammar_claim_scope == "diagnostic_non_primary"


@pytest.mark.parametrize("condition", ["none", "G"])
def test_replay_controls_require_replay_generation_mode(condition: str) -> None:
    payload = _run_config_payload(condition)
    payload["generation_mode"] = C_GENERATION_MODE

    with pytest.raises(ValueError, match="requires generation_mode"):
        RunConfig.from_dict(payload)


@pytest.mark.parametrize("condition", ["C", "G+C"])
def test_generated_rows_require_generated_source_class(condition: str) -> None:
    payload = _identity_payload(condition)
    payload["source_class"] = REPLAY_CONTROL_SOURCE_CLASS

    with pytest.raises(ValueError, match="requires source_class"):
        EvalIdentity(**payload)


@pytest.mark.parametrize("condition", ["none", "G"])
def test_c2_generation_request_rejects_replay_controls(condition: str) -> None:
    with pytest.raises(ValueError, match="must not invoke C2 generation"):
        RemoteC2GenerationRequest(
            identity=EvalIdentity(**_identity_payload(condition)),
            prompt="write relu",
            model_id="model",
            model_revision=TEST_MODEL_REVISION,
            tokenizer_revision=TEST_TOKENIZER_REVISION,
        )


def test_cluster2_output_schemas_do_not_expose_forbidden_fields() -> None:
    dataclass_schema_types = (
        TraceSummary,
        Cluster2ReplayRowMetadata,
        Cluster2GeneratedRowMetadata,
        Cluster2EvalRow,
        Cluster2ContentHashSidecar,
        PipelineStageStatus,
        EvalPipelineSkeletonResult,
    )
    pydantic_schema_types = (
        EvalIdentity,
        RemoteC2GenerationRequest,
        RemoteC2GenerationResult,
        RemoteCorrectnessRequest,
        RemoteCorrectnessResult,
    )

    for schema_type in dataclass_schema_types:
        assert FORBIDDEN_SCHEMA_FIELD_NAMES.isdisjoint(
            field.name for field in fields(schema_type)
        )
    for schema_type in pydantic_schema_types:
        assert FORBIDDEN_SCHEMA_FIELD_NAMES.isdisjoint(schema_type.model_fields)


def test_forbidden_terms_are_confined_to_explicit_guardrail_files() -> None:
    violations: list[str] = []
    for path in _boundary_scanned_source_paths():
        rel_path = path.relative_to(REPO_ROOT).as_posix()
        if rel_path in FORBIDDEN_TERM_ALLOWLIST_PATHS:
            continue
        source = path.read_text(encoding="utf-8")
        for term in FORBIDDEN_SOURCE_TERMS:
            pattern = re.compile(
                rf"(?<![A-Za-z0-9_]){re.escape(term)}(?![A-Za-z0-9_])",
                re.IGNORECASE,
            )
            for match in pattern.finditer(source):
                line_number = source.count("\n", 0, match.start()) + 1
                line = source.splitlines()[line_number - 1]
                if _allowed_forbidden_term_occurrence(term, line):
                    continue
                violations.append(f"{rel_path}:{line_number}:{term}")

    assert violations == []


def _runner_config(
    tmp_path: Path,
    *,
    condition: str,
    manifest: Path | None = None,
) -> Cluster2RunnerConfig:
    tmp_path.mkdir(parents=True, exist_ok=True)
    return Cluster2RunnerConfig(
        condition=condition,
        kernel_class="elementwise",
        scale_tier="smoke",
        n=1,
        frozen_cluster1_manifest=str(
            manifest if manifest is not None else FROZEN_CLUSTER1_MANIFEST
        ),
        model_id="Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        model_revision=TEST_MODEL_REVISION,
        tokenizer_revision=TEST_TOKENIZER_REVISION,
        grammar_variant="task_agnostic",
        dtypes=("fp32",),
        temperature=0.2,
        max_new_tokens=512,
        repair_budget=0,
        modal_generation_gpu="L4",
        modal_eval_gpu="L4",
        output=str(tmp_path / "cluster2.jsonl"),
        write_mode="overwrite",
    )


def _forbidden_generation(calls: list[dict[str, Any]]):
    def generation(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        raise AssertionError("replay controls must not call C2 generation")

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


def _run_config_payload(condition: str) -> dict[str, Any]:
    source_class = (
        REPLAY_CONTROL_SOURCE_CLASS if condition in {"none", "G"} else GENERATED_SOURCE_CLASS
    )
    generation_mode = {
        "none": REPLAY_CONTROL_GENERATION_MODE,
        "G": REPLAY_CONTROL_GENERATION_MODE,
        "C": C_GENERATION_MODE,
        "G+C": G_PLUS_C_GENERATION_MODE,
    }[condition]
    return {
        "condition": condition,
        "source_class": source_class,
        "generation_mode": generation_mode,
        "scale_tier": "smoke",
        "repair_budget": 5,
        "equal_attempts_n": 6,
        "enable_ast_sanitizer": False,
        "dtypes": ("fp32",),
        "model_id": "model",
        "model_revision": TEST_MODEL_REVISION,
        "tokenizer_revision": TEST_TOKENIZER_REVISION,
        "modal_generation_gpu": None if condition in {"none", "G"} else "L4",
        "modal_eval_gpu": "L4",
    }


def _identity_payload(condition: str) -> dict[str, Any]:
    source_class = (
        REPLAY_CONTROL_SOURCE_CLASS if condition in {"none", "G"} else GENERATED_SOURCE_CLASS
    )
    generation_mode = {
        "none": REPLAY_CONTROL_GENERATION_MODE,
        "G": REPLAY_CONTROL_GENERATION_MODE,
        "C": C_GENERATION_MODE,
        "G+C": G_PLUS_C_GENERATION_MODE,
    }[condition]
    return {
        "run_id": "phase14-boundary",
        "condition": condition,
        "source_class": source_class,
        "generation_mode": generation_mode,
        "kernel_class": "elementwise",
        "kernel_name": "relu",
        "dtype": "fp32",
        "sample_index": 0,
        "base_seed": 0,
        "attempt_index": 0,
    }


def _boundary_scanned_source_paths() -> tuple[Path, ...]:
    roots = (REPO_ROOT / "cluster2", REPO_ROOT / "shared/eval")
    paths: list[Path] = []
    for root in roots:
        for path in root.rglob("*.py"):
            rel_parts = path.relative_to(REPO_ROOT).parts
            if "tests" in rel_parts or "__pycache__" in rel_parts:
                continue
            paths.append(path)
    return tuple(sorted(paths))


def _allowed_forbidden_term_occurrence(term: str, line: str) -> bool:
    if term != "tokens":
        return False
    return any(
        allowed in line
        for allowed in (
            "max_new_tokens",
            "max-new-tokens",
            "new_tokens",
            "added_tokens",
            "special_tokens",
        )
    )


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_range_sha256(path: Path, *, start_line: int, end_line: int) -> str:
    source = "".join(
        path.read_text(encoding="utf-8").splitlines(keepends=True)[
            start_line - 1 : end_line
        ]
    ).strip()
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _git_blob_sha256(revision: str, rel_path: str) -> str:
    proc = subprocess.run(
        ["git", "show", f"{revision}:{rel_path}"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=True,
    )
    return hashlib.sha256(proc.stdout).hexdigest()


def _canonical_json_sha256(value: Any) -> str:
    rendered = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _frozen_cluster1_artifact_boundary(artifact: dict[str, Any]) -> dict[str, Any]:
    metadata_sidecar = artifact.get("metadata_sidecar", {})
    boundary = {
        "condition": artifact.get("condition"),
        "path": artifact.get("path"),
        "sha256": artifact.get("sha256"),
        "row_count": artifact.get("row_count"),
        "role": artifact.get("role"),
        "metadata_sidecar_path": metadata_sidecar.get("path"),
        "metadata_sidecar_sha256": metadata_sidecar.get("sha256"),
    }
    for field_name in (
        "coverage_policy",
        "expected_n",
        "intended_rows",
        "observed_rows",
    ):
        if field_name in artifact:
            boundary[field_name] = artifact[field_name]
    return boundary


def _literal_assignment(path: Path, name: str) -> Any:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                return ast.literal_eval(node.value)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == name and node.value is not None:
                return ast.literal_eval(node.value)
    raise AssertionError(f"{name} assignment not found in {path}")
