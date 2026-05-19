"""Final read-only cross-cluster evaluation alignment audit."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

import cluster1.constants as cluster1_constants
import cluster2.constants as cluster2_constants
from cluster1.data.kernels import KERNEL_SPECS
from cluster1.results.dataclass import (
    GenerationResult,
    compute_unique_solution_hash,
    generation_result_record_for_deserialization,
)
from cluster2.constants import DTYPE_NAMES, FROZEN_NONE_REPLAY_ARTIFACT
from cluster2.replay.cluster1_controls import canonical_failure_code_for_replay_row
from shared.eval.adapter_cluster1 import eval_result_from_generation_result
from shared.eval.correctness_shapes import (
    LOCKED_KERNEL_CLASSES,
    get_compile_shapes,
    validate_shape_for_kernel,
)
from shared.eval.failure_taxonomy import FAILURE_CODES, classify_failure
from shared.modal_harness.schemas import (
    RemoteCompileResult,
    remote_compile_result_to_cluster1_fields,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
PHASE4_DIAGNOSTIC_PATH = REPO_ROOT / (
    "outputs/cluster1/diagnostics/"
    "baseline_revalidation_aligned_pipeline_parse_reclassification.jsonl"
)
TASK_AGNOSTIC_GRAMMAR_PATH = REPO_ROOT / "cluster1/grammar/triton_kernel_agnostic.gbnf"


def test_cluster1_specs_still_derive_compile_shapes_from_shared_helpers() -> None:
    for kernel_class in LOCKED_KERNEL_CLASSES:
        spec = KERNEL_SPECS[kernel_class]
        assert spec.kernel_class == kernel_class
        for dtype in DTYPE_NAMES:
            compile_shapes = get_compile_shapes(kernel_class, dtype)
            assert spec.shapes_by_dtype[dtype] == list(compile_shapes)
            assert all(
                validate_shape_for_kernel(kernel_class, shape) == shape
                for shape in compile_shapes
            )


@pytest.mark.parametrize(
    ("compile_error_type", "compile_error_msg", "expected_failure_code"),
    [
        ("SignatureError", "signature mismatch for 'relu'", "F0_BAD_SIGNATURE"),
        (
            "SignatureError",
            "SignatureError: syntax error in generated source: invalid syntax",
            "F0_PARSE",
        ),
        ("CompilationError", "triton compiler rejected source", "F1_COMPILE"),
        ("RuntimeError", "runtime launch failure", "F1_RUNTIME"),
    ],
)
def test_analyzer_and_cluster2_replay_share_canonical_taxonomy_for_legacy_rows(
    compile_error_type: str,
    compile_error_msg: str,
    expected_failure_code: str,
) -> None:
    raw_row = _legacy_row(
        compile_error_type=compile_error_type,
        compile_error_msg=compile_error_msg,
    )
    generation_result = GenerationResult(
        **generation_result_record_for_deserialization(raw_row)
    )
    analyzer_code = classify_failure(
        eval_result_from_generation_result(generation_result)
    )
    replay_code = canonical_failure_code_for_replay_row(raw_row)

    assert expected_failure_code in FAILURE_CODES
    assert generation_result.failure_code == expected_failure_code
    assert analyzer_code == expected_failure_code
    assert replay_code == expected_failure_code


def test_modal_compile_schema_and_local_adapter_canonicalize_the_same_failure() -> None:
    remote_compile = RemoteCompileResult(
        compile_success=False,
        compile_results_by_dtype={"fp32": False, "fp16": False, "bf16": False},
        compile_error_type="SignatureError",
        compile_error_msg=(
            "SignatureError: syntax error in generated source: invalid syntax"
        ),
        failure_code=None,
        n_shapes_tested=0,
        run_id="phase5-modal-local-equivalence",
        factor_cell="none",
    )

    cluster1_fields = remote_compile_result_to_cluster1_fields(remote_compile)
    raw_row = _legacy_row(**cluster1_fields)
    generation_result = GenerationResult(
        **generation_result_record_for_deserialization(raw_row)
    )

    assert cluster1_fields["failure_code"] == "F0_PARSE"
    assert classify_failure(eval_result_from_generation_result(generation_result)) == (
        "F0_PARSE"
    )
    assert canonical_failure_code_for_replay_row(raw_row) == "F0_PARSE"


def test_phase4_modal_diagnostic_evidence_is_clean_and_nonlocal() -> None:
    rows = _read_jsonl(PHASE4_DIAGNOSTIC_PATH)

    assert len(rows) == 180
    assert {row["diagnostic_only"] for row in rows} == {True}
    assert {row["diagnostic_name"] for row in rows} == {
        "baseline_revalidation_aligned_pipeline"
    }
    assert {row["original_compile_success"] for row in rows} == {False}
    assert {row["new_compile_success"] for row in rows} == {False}
    assert {row["agreement"] for row in rows} == {True}
    assert {row["compile_success_drift"] for row in rows} == {False}
    assert {row["entrypoint_agreement"] for row in rows} == {True}
    assert {tuple(row["entrypoint_mismatch_fields"]) for row in rows} == {()}
    assert {row["cross_category_label_drift"] for row in rows} == {False}
    assert {row["original_canonical_failure_code"] for row in rows} == {"F0_PARSE"}
    assert {row["new_canonical_failure_code"] for row in rows} == {"F0_PARSE"}
    assert {row["drift_reason"] for row in rows} == {
        "expected_legacy_to_canonical_mapping"
    }
    assert all(
        "syntax" in row["original_compile_error_msg"].lower()
        for row in rows
    )
    assert all(
        _has_modal_l4_context(row["c1_entrypoint_modal_context"])
        and _has_modal_l4_context(row["c2_entrypoint_modal_context"])
        for row in rows
    )


def test_grammar_hash_gate_passes_after_phase4_interlock() -> None:
    from cluster2.modal.generation import (
        PHASE_MINUS1_G_GENERATION_SOURCE_HASHES,
        verify_phase_minus1_g_generation_hashes,
    )

    current_task_agnostic_hash = hashlib.sha256(
        TASK_AGNOSTIC_GRAMMAR_PATH.read_bytes()
    ).hexdigest()
    observed_hashes = verify_phase_minus1_g_generation_hashes()

    assert current_task_agnostic_hash == PHASE_MINUS1_G_GENERATION_SOURCE_HASHES[
        "cluster1/grammar/triton_kernel_agnostic.gbnf"
    ]
    assert observed_hashes[
        "frozen_g_asset:cluster1/grammar/triton_kernel_agnostic.gbnf"
    ] == current_task_agnostic_hash


def test_generation_token_defaults_document_current_cluster_policies() -> None:
    assert cluster1_constants.DEFAULT_MAX_NEW_TOKENS == 2048
    assert cluster2_constants.DEFAULT_MAX_NEW_TOKENS == 1536


def test_frozen_none_baseline_path_is_the_phase4_input_artifact() -> None:
    baseline_path = REPO_ROOT / FROZEN_NONE_REPLAY_ARTIFACT

    assert baseline_path.exists()
    assert baseline_path != PHASE4_DIAGNOSTIC_PATH
    baseline_rows = [
        line
        for line in baseline_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    assert len(baseline_rows) == 180


def _legacy_row(**overrides: Any) -> dict[str, Any]:
    source = str(overrides.pop("source", "import triton\n# phase5 audit row\n"))
    compile_error_type = overrides.pop("compile_error_type", "SignatureError")
    compile_error_msg = overrides.pop("compile_error_msg", "signature mismatch")
    row: dict[str, Any] = {
        "source": source,
        "model_id": "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        "grammar_active": False,
        "grammar_variant": None,
        "kernel_class": "elementwise",
        "kernel_name": "relu",
        "dtype": "fp32",
        "compile_success": False,
        "compile_results_by_dtype": {
            "fp32": False,
            "fp16": False,
            "bf16": False,
        },
        "compile_error_type": compile_error_type,
        "compile_error_msg": compile_error_msg,
        "masked_token_rate": None,
        "unique_solution_hash": compute_unique_solution_hash(source),
        "n_shapes_tested": 0,
        "generation_seed": 0,
        "temperature": 0.2,
        "run_id": "phase5-audit",
        "timestamp_utc": "2026-05-18T00:00:00Z",
    }
    row.update(overrides)
    return row


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _has_modal_l4_context(context: dict[str, Any] | None) -> bool:
    if not isinstance(context, dict):
        return False
    has_image_identity = bool(context.get("modal_image_sha")) or bool(
        context.get("modal_image_provenance_sha256")
    )
    return (
        context.get("modal_app_name") == "tritongen-gpu-harness"
        and context.get("modal_eval_gpu") == "L4"
        and bool(context.get("function_call_id"))
        and bool(context.get("input_id"))
        and has_image_identity
    )
