"""Phase 13 aggregation, coverage, convergence, and reporting tests."""

from __future__ import annotations

import hashlib
import json
from dataclasses import fields
from pathlib import Path
from typing import Any

import pytest

from cluster2.feedback.trace import TraceSummary
from cluster2.results.dataclass import (
    CLUSTER2_RESULTS_SCHEMA_VERSION,
    FORBIDDEN_CLUSTER2_RESULT_FIELDS,
    Cluster2ContentHashSidecar,
    Cluster2EvalRow,
    generated_row,
    replay_control_row,
)
from shared.eval.aggregation import (
    AggregationDataset,
    assert_no_forbidden_metric_fields,
    validate_hash_classes,
)
from shared.eval.metrics.coverage import compute_coverage
from shared.eval.metrics.equal_attempts import (
    compute_lift_with_bootstrap_ci,
    compute_pass_rate_within_n,
)
from shared.eval.metrics.repair import (
    RateResult,
    compute_convergence_rate,
    compute_pass_at_1_initial,
)
from shared.eval.reporting.coverage_table import build_coverage_table
from shared.eval.reporting.tables import (
    PRIMARY_COMPARISON_LABEL,
    SECONDARY_COMPARISON_LABEL,
    build_convergence_table,
    build_lift_table,
)


def test_generated_convergence_rate_is_per_cell() -> None:
    rows = [
        _generated_row(condition="C", base_seed=0, attempt_index=0, success=False),
        _generated_row(condition="C", base_seed=0, attempt_index=1, success=True),
        _generated_row(condition="C", base_seed=1, attempt_index=0, success=False),
        _generated_row(condition="C", base_seed=1, attempt_index=1, success=False),
    ]

    result = compute_convergence_rate(rows, max_attempts=6)

    assert result.metric == "convergence_rate"
    assert result.condition == "C"
    assert result.successes == 1
    assert result.total_cells == 2
    assert result.rate == 0.5


def test_replay_pass_within_n_is_per_cell() -> None:
    within_one_rows = [
        _replay_row(condition="none", base_seed=0, attempt_index=0, success=False),
        _replay_row(condition="none", base_seed=1, attempt_index=0, success=False),
    ]
    within_two_rows = [
        _replay_row(condition="none", base_seed=0, attempt_index=0, success=False),
        _replay_row(condition="none", base_seed=0, attempt_index=1, success=True),
        _replay_row(condition="none", base_seed=1, attempt_index=0, success=False),
        _replay_row(condition="none", base_seed=1, attempt_index=1, success=True),
    ]

    within_one = compute_pass_rate_within_n(within_one_rows, n=1)
    within_two = compute_pass_rate_within_n(within_two_rows, n=2)

    assert within_one.successes == 0
    assert within_one.rate == 0.0
    assert within_two.successes == 2
    assert within_two.rate == 1.0


def test_pass_at_1_initial_uses_only_attempt_zero() -> None:
    rows = [
        _generated_row(condition="C", base_seed=0, attempt_index=0, success=False),
        _generated_row(condition="C", base_seed=0, attempt_index=1, success=True),
        _generated_row(condition="C", base_seed=1, attempt_index=0, success=True),
    ]

    result = compute_pass_at_1_initial(rows)

    assert result.metric == "pass_at_1_initial"
    assert result.successes == 1
    assert result.total_cells == 2
    assert result.rate == 0.5


def test_lift_computation_uses_matched_cells() -> None:
    treatment = [
        _generated_row(condition="C", base_seed=0, attempt_index=0, success=True),
        _generated_row(condition="C", base_seed=1, attempt_index=0, success=False),
    ]
    control = [
        _replay_row(condition="none", base_seed=0, attempt_index=0, success=False),
        _replay_row(condition="none", base_seed=1, attempt_index=0, success=False),
    ]

    lift = compute_lift_with_bootstrap_ci(
        treatment,
        control,
        n=1,
        bootstrap_resamples=200,
        bootstrap_seed=17,
    )

    assert lift.treatment_rate == 0.5
    assert lift.control_rate == 0.0
    assert lift.lift == 0.5
    assert lift.total_cells == 2
    assert lift.ci_lower <= lift.lift <= lift.ci_upper


def test_bootstrap_ci_is_deterministic() -> None:
    treatment = [
        _generated_row(condition="C", base_seed=0, attempt_index=0, success=True),
        _generated_row(condition="C", base_seed=1, attempt_index=0, success=False),
        _generated_row(condition="C", base_seed=2, attempt_index=0, success=True),
    ]
    control = [
        _replay_row(condition="none", base_seed=0, attempt_index=0, success=False),
        _replay_row(condition="none", base_seed=1, attempt_index=0, success=False),
        _replay_row(condition="none", base_seed=2, attempt_index=0, success=True),
    ]

    first = compute_lift_with_bootstrap_ci(
        treatment,
        control,
        n=1,
        bootstrap_resamples=250,
        bootstrap_seed=91,
    )
    second = compute_lift_with_bootstrap_ci(
        treatment,
        control,
        n=1,
        bootstrap_resamples=250,
        bootstrap_seed=91,
    )

    assert first.to_dict() == second.to_dict()


def test_bootstrap_and_lift_are_over_cells_not_rows() -> None:
    treatment = [
        _generated_row(condition="C", base_seed=0, attempt_index=0, success=False),
        _generated_row(condition="C", base_seed=0, attempt_index=1, success=True),
        _generated_row(condition="C", base_seed=1, attempt_index=0, success=False),
        _generated_row(condition="C", base_seed=1, attempt_index=1, success=False),
        _generated_row(condition="C", base_seed=1, attempt_index=2, success=False),
    ]
    control = [
        _replay_row(condition="none", base_seed=0, attempt_index=0, success=False),
        _replay_row(condition="none", base_seed=0, attempt_index=1, success=False),
        _replay_row(condition="none", base_seed=1, attempt_index=0, success=False),
        _replay_row(condition="none", base_seed=1, attempt_index=1, success=False),
    ]

    lift = compute_lift_with_bootstrap_ci(
        treatment,
        control,
        n=2,
        bootstrap_resamples=100,
        bootstrap_seed=5,
    )

    assert lift.total_cells == 2
    assert lift.treatment_rate == 0.5
    assert lift.lift == 0.5


def test_eval_hash_mismatch_is_rejected() -> None:
    row = _generated_row(condition="C")
    first = AggregationDataset(
        rows=(row,),
        content_hash_sidecar=_sidecar(
            generated_condition_hashes={"C": _c2_hashes("C")},
            eval_hashes={"shared/eval/pipeline.py": "0" * 64},
        ),
        label="first",
    )
    second = AggregationDataset(
        rows=(row,),
        content_hash_sidecar=_sidecar(
            generated_condition_hashes={"C": _c2_hashes("C")},
            eval_hashes={"shared/eval/pipeline.py": "1" * 64},
        ),
        label="second",
    )

    with pytest.raises(ValueError, match="eval pipeline hash mismatch"):
        validate_hash_classes([first, second])


def test_generated_hash_mismatch_across_datasets_is_rejected() -> None:
    first_hashes = _c2_hashes("C")
    second_hashes = {"cluster2/modal/generation.py": "9" * 64}
    first = AggregationDataset(
        rows=(
            _generated_row(
                condition="C",
                base_seed=0,
                c2_generation_hashes=first_hashes,
            ),
        ),
        content_hash_sidecar=_sidecar(
            generated_condition_hashes={"C": first_hashes},
        ),
        label="first",
    )
    second = AggregationDataset(
        rows=(
            _generated_row(
                condition="C",
                base_seed=1,
                c2_generation_hashes=second_hashes,
            ),
        ),
        content_hash_sidecar=_sidecar(
            generated_condition_hashes={"C": second_hashes},
        ),
        label="second",
    )

    with pytest.raises(ValueError, match="generated hash mismatch across datasets"):
        validate_hash_classes([first, second])


def test_replay_vs_generated_generation_hash_mismatch_is_allowed(
    tmp_path: Path,
) -> None:
    manifest = _write_frozen_manifest(
        tmp_path,
        condition="none",
        artifact_hash="4" * 64,
    )
    generated = _generated_row(condition="C")
    replay = _replay_row(
        condition="none",
        frozen_hashes={"none_fixture:artifact": "4" * 64},
    )
    datasets = [
        AggregationDataset(
            rows=(generated,),
            content_hash_sidecar=_sidecar(
                generated_condition_hashes={"C": _c2_hashes("C")},
            ),
            label="generated",
        ),
        AggregationDataset(
            rows=(replay,),
            content_hash_sidecar=_sidecar(
                replay_control_hashes={"none": {"none_fixture:artifact": "4" * 64}},
            ),
            label="replay",
        ),
    ]

    validate_hash_classes(datasets, frozen_cluster1_manifest_path=manifest)


def test_replay_source_hash_missing_from_manifest_is_rejected(
    tmp_path: Path,
) -> None:
    manifest = _write_frozen_manifest(
        tmp_path,
        condition="none",
        artifact_hash="4" * 64,
        source_hash="9" * 64,
    )
    replay = _replay_row(
        condition="none",
        frozen_hashes={"none_fixture:artifact": "4" * 64},
    )
    dataset = AggregationDataset(
        rows=(replay,),
        content_hash_sidecar=_sidecar(
            replay_control_hashes={"none": {"none_fixture:artifact": "4" * 64}},
        ),
    )

    with pytest.raises(ValueError, match="source/row hash missing"):
        validate_hash_classes([dataset], frozen_cluster1_manifest_path=manifest)


def test_replay_row_hash_mismatch_is_rejected(tmp_path: Path) -> None:
    manifest = _write_frozen_manifest(
        tmp_path,
        condition="none",
        artifact_hash="4" * 64,
        row_hash="b" * 64,
    )
    replay = _replay_row(
        condition="none",
        frozen_hashes={"none_fixture:artifact": "4" * 64},
    )
    dataset = AggregationDataset(
        rows=(replay,),
        content_hash_sidecar=_sidecar(
            replay_control_hashes={"none": {"none_fixture:artifact": "4" * 64}},
        ),
    )

    with pytest.raises(ValueError, match="source/row hash missing"):
        validate_hash_classes([dataset], frozen_cluster1_manifest_path=manifest)


def test_frozen_replay_hash_mismatch_is_rejected(tmp_path: Path) -> None:
    manifest = _write_frozen_manifest(
        tmp_path,
        condition="none",
        artifact_hash="4" * 64,
    )
    replay = _replay_row(
        condition="none",
        frozen_hashes={"none_fixture:artifact": "5" * 64},
    )
    dataset = AggregationDataset(
        rows=(replay,),
        content_hash_sidecar=_sidecar(
            replay_control_hashes={"none": {"none_fixture:artifact": "5" * 64}},
        ),
    )

    with pytest.raises(ValueError, match="frozen replay hash mismatch"):
        validate_hash_classes([dataset], frozen_cluster1_manifest_path=manifest)


def test_nonselected_replay_artifact_is_rejected(tmp_path: Path) -> None:
    manifest = _write_frozen_manifest(
        tmp_path,
        condition="G",
        artifact_hash="5" * 64,
        selected_artifact_id="g_selected_template_fixture",
    )
    replay = _replay_row(
        condition="G",
        frozen_hashes={"g_fixture:artifact": "5" * 64},
    )
    dataset = AggregationDataset(
        rows=(replay,),
        content_hash_sidecar=_sidecar(
            replay_control_hashes={"G": {"g_fixture:artifact": "5" * 64}},
        ),
    )

    with pytest.raises(ValueError, match="not a selected Phase -1 control"):
        validate_hash_classes([dataset], frozen_cluster1_manifest_path=manifest)


def test_task_agnostic_g_replay_artifact_is_accepted_when_status_selects_it(
    tmp_path: Path,
) -> None:
    manifest = _write_frozen_manifest(
        tmp_path,
        condition="G",
        artifact_hash="5" * 64,
        selected_artifact_id="g_template_fixture",
        task_agnostic_artifact_id="g_fixture",
    )
    replay = _replay_row(
        condition="G",
        frozen_hashes={"g_fixture:artifact": "5" * 64},
    )
    dataset = AggregationDataset(
        rows=(replay,),
        content_hash_sidecar=_sidecar(
            replay_control_hashes={"G": {"g_fixture:artifact": "5" * 64}},
        ),
    )

    validate_hash_classes([dataset], frozen_cluster1_manifest_path=manifest)


def test_primary_task_agnostic_gc_rejects_template_g_replay_artifact(
    tmp_path: Path,
) -> None:
    manifest = _write_frozen_manifest(
        tmp_path,
        condition="G",
        artifact_hash="5" * 64,
        task_agnostic_artifact_id="g_task_agnostic_fixture",
    )
    generated = _generated_row(condition="G+C")
    replay = _replay_row(
        condition="G",
        frozen_hashes={"g_fixture:artifact": "5" * 64},
    )
    datasets = (
        AggregationDataset(
            rows=(generated,),
            content_hash_sidecar=_sidecar(
                generated_condition_hashes={"G+C": _c2_hashes("G+C")},
            ),
        ),
        AggregationDataset(
            rows=(replay,),
            content_hash_sidecar=_sidecar(
                replay_control_hashes={"G": {"g_fixture:artifact": "5" * 64}},
            ),
        ),
    )

    with pytest.raises(ValueError, match="requires task-agnostic G replay artifact"):
        validate_hash_classes(datasets, frozen_cluster1_manifest_path=manifest)


def test_primary_task_agnostic_gc_accepts_task_agnostic_g_replay_artifact(
    tmp_path: Path,
) -> None:
    manifest = _write_frozen_manifest(
        tmp_path,
        condition="G",
        artifact_hash="5" * 64,
        selected_artifact_id="g_template_fixture",
        task_agnostic_artifact_id="g_fixture",
    )
    generated = _generated_row(condition="G+C")
    replay = _replay_row(
        condition="G",
        frozen_hashes={"g_fixture:artifact": "5" * 64},
    )
    datasets = (
        AggregationDataset(
            rows=(generated,),
            content_hash_sidecar=_sidecar(
                generated_condition_hashes={"G+C": _c2_hashes("G+C")},
            ),
        ),
        AggregationDataset(
            rows=(replay,),
            content_hash_sidecar=_sidecar(
                replay_control_hashes={"G": {"g_fixture:artifact": "5" * 64}},
            ),
        ),
    )

    validate_hash_classes(datasets, frozen_cluster1_manifest_path=manifest)


def test_generated_duplicate_attempt_indexes_are_rejected() -> None:
    rows = [
        _generated_row(condition="C", base_seed=0, attempt_index=0, success=False),
        _generated_row(condition="C", base_seed=0, attempt_index=0, success=True),
    ]

    with pytest.raises(ValueError, match="duplicate attempt_index"):
        compute_convergence_rate(rows)


def test_replay_duplicate_attempt_indexes_are_rejected() -> None:
    rows = [
        _replay_row(condition="none", base_seed=0, attempt_index=0, success=False),
        _replay_row(condition="none", base_seed=0, attempt_index=0, success=True),
    ]

    with pytest.raises(ValueError, match="duplicate attempt_index"):
        compute_pass_rate_within_n(rows)


def test_replay_incomplete_attempt_window_is_rejected() -> None:
    rows = [
        _replay_row(condition="none", base_seed=0, attempt_index=0, success=False),
    ]

    with pytest.raises(ValueError, match="coverage_failure_missing_frozen_control"):
        compute_pass_rate_within_n(rows, n=2)


def test_replay_extra_attempt_window_is_rejected() -> None:
    rows = [
        _replay_row(condition="none", base_seed=0, attempt_index=0, success=False),
        _replay_row(condition="none", base_seed=0, attempt_index=1, success=False),
        _replay_row(condition="none", base_seed=0, attempt_index=2, success=True),
    ]

    with pytest.raises(ValueError, match="extra=2"):
        compute_pass_rate_within_n(rows, n=2)


def test_coverage_computation() -> None:
    summary = compute_coverage(
        [
            {"status": "ok"},
            {"status": "ok"},
            {"status": "coverage_failure_missing_frozen_control"},
        ]
    )

    assert summary.total_records == 3
    assert summary.covered_records == 2
    assert summary.coverage_failures == 1
    assert summary.candidate_failures == 0
    assert summary.coverage_rate == pytest.approx(2 / 3)
    assert not summary.passed


def test_coverage_failure_and_candidate_failure_are_distinct() -> None:
    candidate_failure = _generated_row(
        condition="C",
        base_seed=0,
        attempt_index=0,
        success=False,
    )

    summary = compute_coverage(
        [
            candidate_failure,
            {"status": "candidate_failure"},
            {"status": "coverage_failure_missing_frozen_control"},
        ]
    )

    assert summary.coverage_failures == 1
    assert summary.candidate_failures == 2
    assert summary.covered_records == 2
    assert summary.failure_reasons["coverage_failure_missing_frozen_control"] == 1


def test_primary_and_secondary_comparison_labels() -> None:
    primary = compute_lift_with_bootstrap_ci(
        [_generated_row(condition="C", base_seed=0, success=True)],
        [_replay_row(condition="none", base_seed=0, success=False)],
        n=1,
        bootstrap_resamples=50,
    )
    secondary = compute_lift_with_bootstrap_ci(
        [_generated_row(condition="G+C", base_seed=0, success=True)],
        [_replay_row(condition="G", base_seed=0, success=False)],
        n=1,
        bootstrap_resamples=50,
    )

    rows = build_lift_table([secondary, primary])

    assert rows[0]["comparison"] == PRIMARY_COMPARISON_LABEL
    assert rows[1]["comparison"] == SECONDARY_COMPARISON_LABEL


def test_forbidden_fields_are_absent_from_phase13_outputs() -> None:
    convergence = compute_convergence_rate(
        [_generated_row(condition="C", base_seed=0, success=True)]
    )
    replay = compute_pass_rate_within_n(
        [_replay_row(condition="none", base_seed=0, success=False)],
        n=1,
    )
    lift = compute_lift_with_bootstrap_ci(
        [_generated_row(condition="C", base_seed=0, success=True)],
        [_replay_row(condition="none", base_seed=0, success=False)],
        n=1,
        bootstrap_resamples=50,
    )
    coverage = compute_coverage([{"status": "ok"}])

    payloads: list[dict[str, Any]] = [
        convergence.to_dict(),
        replay.to_dict(),
        lift.to_dict(),
        *build_lift_table(lift),
        *build_convergence_table([convergence, replay]),
        *build_coverage_table(coverage),
    ]

    for payload in payloads:
        assert FORBIDDEN_CLUSTER2_RESULT_FIELDS.isdisjoint(_recursive_keys(payload))
        assert_no_forbidden_metric_fields(payload)

    assert "functional_success" in {field.name for field in fields(Cluster2EvalRow)}


def _generated_row(
    *,
    condition: str = "C",
    kernel_class: str = "elementwise",
    kernel_name: str = "relu",
    dtype: str = "fp32",
    base_seed: int = 0,
    attempt_index: int = 0,
    success: bool = True,
    c2_generation_hashes: dict[str, str] | None = None,
) -> Cluster2EvalRow:
    source_text = f"import triton\n# {condition} {base_seed} {attempt_index}\n"
    source_hash = _source_hash(source_text)
    failure_code = None if success else "F2_NUMERIC_LARGE"
    return generated_row(
        condition=condition,
        attempt_index=attempt_index,
        kernel_class=kernel_class,
        kernel_name=kernel_name,
        dtype=dtype,
        base_seed=base_seed,
        source_hash=source_hash,
        functional_success=success,
        repair_set_success=success,
        eval_set_success=success,
        failure_code=failure_code,
        trace_summary=TraceSummary(
            attempt_index=attempt_index,
            failure_code=failure_code,
            public_failure_summary=(
                "Candidate passed Level 2." if success else "Validation failed."
            ),
            functional_success=success,
            repair_set_success=success,
            eval_set_success=success,
            source_hash=source_hash,
        ),
        c2_generation_hashes=(
            _c2_hashes(condition)
            if c2_generation_hashes is None
            else c2_generation_hashes
        ),
        generation_seed=base_seed * 100 + attempt_index,
        grammar_variant="task_agnostic" if condition == "G+C" else None,
        grammar_path=(
            "cluster1/grammar/triton_kernel_agnostic.gbnf"
            if condition == "G+C"
            else None
        ),
        grammar_claim_scope="primary" if condition == "G+C" else None,
    )


def _replay_row(
    *,
    condition: str = "none",
    kernel_class: str = "elementwise",
    kernel_name: str = "relu",
    dtype: str = "fp32",
    base_seed: int = 0,
    attempt_index: int = 0,
    success: bool = True,
    frozen_hashes: dict[str, str] | None = None,
) -> Cluster2EvalRow:
    source_text = f"import triton\n# replay {condition} {base_seed} {attempt_index}\n"
    return replay_control_row(
        condition=condition,
        attempt_index=attempt_index,
        kernel_class=kernel_class,
        kernel_name=kernel_name,
        dtype=dtype,
        base_seed=base_seed,
        source_hash=_source_hash(source_text),
        functional_success=success,
        repair_set_success=success,
        eval_set_success=success,
        failure_code=None if success else "F2_NUMERIC_LARGE",
        frozen_cluster1_artifact_id=(
            "none_fixture" if condition == "none" else "g_fixture"
        ),
        frozen_cluster1_generation_hashes=(
            _frozen_hashes(condition) if frozen_hashes is None else frozen_hashes
        ),
        frozen_cluster1_row_hash="a" * 64,
    )


def _sidecar(
    *,
    eval_hashes: dict[str, str] | None = None,
    generated_condition_hashes: dict[str, dict[str, str]] | None = None,
    replay_control_hashes: dict[str, dict[str, str]] | None = None,
) -> Cluster2ContentHashSidecar:
    return Cluster2ContentHashSidecar(
        schema_version=CLUSTER2_RESULTS_SCHEMA_VERSION,
        eval_pipeline_hashes=(
            {"shared/eval/pipeline.py": "0" * 64}
            if eval_hashes is None
            else eval_hashes
        ),
        generated_condition_hashes=(
            {} if generated_condition_hashes is None else generated_condition_hashes
        ),
        replay_control_hashes=(
            {} if replay_control_hashes is None else replay_control_hashes
        ),
        external_pins={"python_version": "3.11.test"},
    )


def _write_frozen_manifest(
    tmp_path: Path,
    *,
    condition: str,
    artifact_hash: str,
    source_hash: str | None = None,
    row_hash: str = "a" * 64,
    selected_artifact_id: str | None = None,
    task_agnostic_artifact_id: str | None = None,
) -> Path:
    artifact_id = "none_fixture" if condition == "none" else "g_fixture"
    kernel_name = "relu"
    frozen_source_hash = (
        _source_hash(f"import triton\n# replay {condition} 0 0\n")
        if source_hash is None
        else source_hash
    )
    manifest = {
        "schema_version": 1,
        "artifacts": [
            {
                "artifact_id": artifact_id,
                "condition": condition,
                "path": f"{artifact_id}.jsonl",
                "sha256": artifact_hash,
                "row_records": [
                    {
                        "line_number": 1,
                        "condition": condition,
                        "kernel_class": "elementwise",
                        "kernel_name": kernel_name,
                        "dtype": "fp32",
                        "attempt_index": 0,
                        "generation_index": 0,
                        "generation_seed": 0,
                        "source_sha256": frozen_source_hash,
                        "row_sha256": row_hash,
                    }
                ],
            }
        ],
        "selected_controls": {
            "cluster2_v5_template_upper_bound_controls": {
                "artifact_ids": [
                    artifact_id
                    if selected_artifact_id is None
                    else selected_artifact_id
                ],
                "coverage_failures": [],
            }
        },
    }
    if task_agnostic_artifact_id is not None:
        manifest["selected_controls"]["task_agnostic_g_status"] = {
            "available_development_artifact_id": task_agnostic_artifact_id,
            "development_rows_per_cell_sufficient": True,
            "paper_rows_per_cell_sufficient": False,
        }
    path = tmp_path / "frozen_manifest.json"
    path.write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def _source_hash(source_text: str) -> str:
    return hashlib.sha256(source_text.encode("utf-8")).hexdigest()


def _c2_hashes(condition: str) -> dict[str, str]:
    prefix = "2" if condition == "C" else "3"
    return {"cluster2/modal/generation.py": prefix * 64}


def _frozen_hashes(condition: str) -> dict[str, str]:
    artifact_id = "none_fixture" if condition == "none" else "g_fixture"
    prefix = "4" if condition == "none" else "5"
    return {f"{artifact_id}:artifact": prefix * 64}


def _recursive_keys(payload: Any) -> set[str]:
    if isinstance(payload, dict):
        keys = set(payload)
        for value in payload.values():
            keys.update(_recursive_keys(value))
        return keys
    if isinstance(payload, list):
        keys: set[str] = set()
        for value in payload:
            keys.update(_recursive_keys(value))
        return keys
    return set()
