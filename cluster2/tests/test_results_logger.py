"""Phase 10 tests for Cluster 2 result rows, logger, and hash sidecars."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

import cluster2.results.logger as results_logger
from cluster1.results.dataclass import GenerationResult
from cluster1.results.logger import append_result_jsonl
from cluster2.feedback.trace import TraceSummary
from cluster2.results.dataclass import (
    CLUSTER2_GENERATION_METADATA_SCHEMA_VERSION,
    CLUSTER2_RESULTS_SCHEMA_VERSION,
    FORBIDDEN_CLUSTER2_RESULT_FIELDS,
    Cluster2ContentHashSidecar,
    Cluster2EvalRow,
    Cluster2GeneratedRowMetadata,
    Cluster2OptionalDiagnostics,
    Cluster2ReplayRowMetadata,
    generated_row,
    replay_control_row,
    validate_generated_paper_scale_metadata,
)
from cluster2.results.logger import (
    Cluster2JsonlAppendLogger,
    Cluster2ResultsLogger,
    build_content_hash_sidecar,
    default_content_hash_sidecar_path,
    load_cluster2_results_jsonl,
    load_content_hash_sidecar,
    validate_cluster2_results_jsonl,
    validate_content_hash_sidecar_for_rows,
    write_cluster2_results_jsonl,
)
from shared.generation_metadata import modal_image_provenance_digest


def test_cluster2_eval_row_serialization_is_deterministic() -> None:
    row = _generated_row(attempt_index=1, functional_success=False)

    first = row.to_json()
    second = Cluster2EvalRow.from_dict(json.loads(first)).to_json()

    assert first == second
    assert first == json.dumps(json.loads(first), sort_keys=True, separators=(",", ":"))


def test_trace_summary_must_match_row_eval_result() -> None:
    source_hash = _source_hash("import triton\n@triton.jit\ndef mismatch(): pass")

    with pytest.raises(ValueError, match="trace_summary functional_success"):
        generated_row(
            condition="C",
            attempt_index=0,
            kernel_class="elementwise",
            kernel_name="relu",
            dtype="fp32",
            base_seed=11,
            source_hash=source_hash,
            functional_success=True,
            repair_set_success=True,
            eval_set_success=True,
            failure_code=None,
            trace_summary=TraceSummary(
                attempt_index=0,
                failure_code="F2_NUMERIC_LARGE",
                public_failure_summary="Validation failed.",
                functional_success=False,
                repair_set_success=False,
                eval_set_success=False,
                source_hash=source_hash,
            ),
            c2_generation_hashes=_c2_hashes("C"),
            generation_seed=110,
        )


def test_kernel_name_must_match_locked_kernel_class() -> None:
    with pytest.raises(ValueError, match="requires kernel_name 'relu'"):
        _generated_row(kernel_class="elementwise", kernel_name="softmax")


def test_overwrite_writes_rows_and_hash_sidecar(tmp_path: Path) -> None:
    output = tmp_path / "results.jsonl"
    first = _replay_row(condition="none", source_text="first")
    second = _replay_row(condition="none", source_text="second")

    write_cluster2_results_jsonl(
        output,
        [first],
        content_hash_sidecar=_sidecar([first]),
        mode="overwrite",
    )
    write_cluster2_results_jsonl(
        output,
        [second],
        content_hash_sidecar=_sidecar([second]),
        mode="overwrite",
    )

    assert load_cluster2_results_jsonl(output) == (second,)
    sidecar = load_content_hash_sidecar(default_content_hash_sidecar_path(output))
    assert sidecar.replay_control_hashes == {"none": _frozen_hashes("none")}


def test_append_mode_is_rejected(tmp_path: Path) -> None:
    output = tmp_path / "results.jsonl"
    row = _replay_row()

    with pytest.raises(ValueError, match="append mode is not supported"):
        write_cluster2_results_jsonl(
            output,
            [row],
            content_hash_sidecar=_sidecar([row]),
            mode="append",
        )
    assert not hasattr(Cluster2ResultsLogger(output), "append")


def test_durable_append_logger_writes_one_valid_jsonl_row(tmp_path: Path) -> None:
    output = tmp_path / "results.jsonl"
    row = _generated_row(condition="C")

    with Cluster2JsonlAppendLogger(
        output,
        content_hash_sidecar=_sidecar([row]),
        mode="overwrite",
        fsync=False,
    ) as logger:
        assert logger.append(row) is True

    lines = output.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["condition"] == "C"
    assert payload["kernel_class"] == "elementwise"
    assert payload["dtype"] == "fp32"
    assert payload["base_seed"] == 11
    assert payload["generated_metadata"]["generation_seed"] == 110
    assert payload["failure_code"] is None


def test_durable_append_logger_persists_multiple_rows_incrementally(
    tmp_path: Path,
) -> None:
    output = tmp_path / "results.jsonl"
    first = _generated_row(condition="C", attempt_index=0)
    second = _generated_row(condition="C", attempt_index=1, source_text="second")

    with Cluster2JsonlAppendLogger(
        output,
        content_hash_sidecar=_sidecar([first, second]),
        mode="overwrite",
        fsync=False,
    ) as logger:
        logger.append(first)
        _assert_jsonl_rows(output, expected_count=1)
        logger.append(second)
        _assert_jsonl_rows(output, expected_count=2)

    text = output.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert "\n\n" not in text


def test_durable_append_logger_resume_does_not_duplicate_existing_rows(
    tmp_path: Path,
) -> None:
    output = tmp_path / "results.jsonl"
    first = _generated_row(condition="C", attempt_index=0)
    second = _generated_row(condition="C", attempt_index=1, source_text="second")
    sidecar = _sidecar([first, second])

    with Cluster2JsonlAppendLogger(
        output,
        content_hash_sidecar=sidecar,
        mode="overwrite",
        fsync=False,
    ) as logger:
        logger.append(first)

    with Cluster2JsonlAppendLogger(
        output,
        content_hash_sidecar=sidecar,
        mode="resume",
        fsync=False,
    ) as logger:
        assert logger.append(first) is False
        assert logger.append(second) is True

    assert load_cluster2_results_jsonl(output) == (first, second)


def test_durable_append_logger_resume_rejects_stale_extra_rows(
    tmp_path: Path,
) -> None:
    output = tmp_path / "results.jsonl"
    first = _generated_row(condition="C", attempt_index=0)
    second = _generated_row(condition="C", attempt_index=1, source_text="second")
    sidecar = _sidecar([first, second])

    write_cluster2_results_jsonl(
        output,
        [first, second],
        content_hash_sidecar=sidecar,
        mode="overwrite",
    )

    with pytest.raises(ValueError, match="more rows than completed resume"):
        with Cluster2JsonlAppendLogger(
            output,
            content_hash_sidecar=sidecar,
            mode="resume",
            fsync=False,
        ) as logger:
            assert logger.append(first) is False


def test_durable_append_logger_overwrite_truncates_target_at_start(
    tmp_path: Path,
) -> None:
    output = tmp_path / "results.jsonl"
    row = _generated_row(condition="C")
    output.write_text('{"old":true}\n', encoding="utf-8")

    with Cluster2JsonlAppendLogger(
        output,
        content_hash_sidecar=_sidecar([row]),
        mode="overwrite",
        fsync=False,
    ):
        assert output.read_text(encoding="utf-8") == ""


def test_strict_row_count_validation_rejects_partial_jsonl(tmp_path: Path) -> None:
    output = tmp_path / "results.jsonl"
    row = _generated_row(condition="C")
    write_cluster2_results_jsonl(
        output,
        [row],
        content_hash_sidecar=_sidecar([row]),
        mode="overwrite",
    )

    with pytest.raises(ValueError, match="expected 2 rows, found 1"):
        validate_cluster2_results_jsonl(output, expected_rows=2)
    assert validate_cluster2_results_jsonl(
        output,
        expected_rows=2,
        allow_partial=True,
    ) == (row,)


def test_durable_append_logger_fsyncs_once_per_appended_row(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "results.jsonl"
    first = _generated_row(condition="C", attempt_index=0)
    second = _generated_row(condition="C", attempt_index=1, source_text="second")
    fsync_calls: list[int] = []

    monkeypatch.setattr(results_logger.os, "fsync", lambda fd: fsync_calls.append(fd))
    with Cluster2JsonlAppendLogger(
        output,
        content_hash_sidecar=_sidecar([first, second]),
        mode="overwrite",
        fsync=True,
    ) as logger:
        fsync_calls.clear()
        logger.append(first)
        logger.append(second)

    assert len(fsync_calls) == 2


def test_resume_requires_matching_content_hash_sidecar(tmp_path: Path) -> None:
    output = tmp_path / "results.jsonl"
    row = _generated_row(condition="C")
    original_sidecar = _sidecar([row])
    mismatched_sidecar = _sidecar([row], eval_hashes={"shared/eval/pipeline.py": "f" * 64})

    write_cluster2_results_jsonl(
        output,
        [row],
        content_hash_sidecar=original_sidecar,
        mode="overwrite",
    )

    with pytest.raises(ValueError, match="content-hash sidecar mismatch"):
        write_cluster2_results_jsonl(
            output,
            [row],
            content_hash_sidecar=mismatched_sidecar,
            mode="resume",
        )


def test_resume_requires_existing_rows_to_match_deterministic_prefix(
    tmp_path: Path,
) -> None:
    output = tmp_path / "results.jsonl"
    first = _generated_row(condition="C", attempt_index=0)
    second = _generated_row(condition="C", attempt_index=1)
    sidecar = _sidecar([first, second])

    write_cluster2_results_jsonl(
        output,
        [first],
        content_hash_sidecar=sidecar,
        mode="overwrite",
    )
    write_cluster2_results_jsonl(
        output,
        [first, second],
        content_hash_sidecar=sidecar,
        mode="resume",
    )

    assert load_cluster2_results_jsonl(output) == (first, second)

    output.write_text(_replay_row().to_json() + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="deterministic resume prefix"):
        write_cluster2_results_jsonl(
            output,
            [first, second],
            content_hash_sidecar=sidecar,
            mode="resume",
        )


def test_replay_and_generated_rows_serialize_distinct_source_classes() -> None:
    replay = _replay_row(condition="G")
    generated = _generated_row(condition="G+C")

    replay_payload = json.loads(replay.to_json())
    generated_payload = json.loads(generated.to_json())

    assert replay_payload["source_class"] == "replay_control_row"
    assert replay_payload["generation_mode"] == "replay_control"
    assert replay_payload["replay_metadata"] is not None
    assert replay_payload["generated_metadata"] is None
    assert replay_payload["trace_summary"] is None

    assert generated_payload["source_class"] == "generated_row"
    assert generated_payload["generation_mode"] == "new_c2_generation_with_G_adapter"
    assert generated_payload["generated_metadata"] is not None
    assert (
        generated_payload["generated_metadata"]["grammar_variant"]
        == "task_agnostic"
    )
    assert (
        generated_payload["generated_metadata"]["grammar_path"]
        == "cluster1/grammar/triton_kernel_agnostic.gbnf"
    )
    assert "grammar_sha" in generated_payload["generated_metadata"]
    assert "grammar_valid" in generated_payload["generated_metadata"]
    assert "stop_reason" in generated_payload["generated_metadata"]
    assert "xgrammar_version" in generated_payload["generated_metadata"]
    assert generated_payload["replay_metadata"] is None
    assert generated_payload["trace_summary"] is not None


def test_generated_row_rejects_malformed_modal_image_sha() -> None:
    with pytest.raises(ValueError, match="modal_image_sha"):
        _generated_row(condition="C", modal_image_sha="not-a-sha")


@pytest.mark.parametrize(
    "field_name",
    (
        "grammar_sha",
        "gbnf_parse_valid",
        "semantic_valid",
        "grammar_valid",
    ),
)
def test_generated_current_schema_gc_requires_complete_grammar_metadata(
    field_name: str,
) -> None:
    overrides = {
        "generation_metadata_schema_version": (
            CLUSTER2_GENERATION_METADATA_SCHEMA_VERSION
        ),
        "grammar_sha": "a" * 64,
        "gbnf_parse_valid": True,
        "semantic_valid": True,
        "grammar_valid": True,
        "rejection_layer": None,
        "modal_image_sha": "sha256:" + "a" * 64,
    }
    overrides[field_name] = None

    with pytest.raises(ValueError, match=field_name):
        _generated_row(condition="G+C", **overrides)


def test_generated_current_schema_gc_requires_invalid_rejection_layer() -> None:
    with pytest.raises(ValueError, match="rejection_layer is required"):
        _generated_row(
            condition="G+C",
            generation_metadata_schema_version=(
                CLUSTER2_GENERATION_METADATA_SCHEMA_VERSION
            ),
            grammar_sha="a" * 64,
            gbnf_parse_valid=False,
            semantic_valid=True,
            grammar_valid=False,
            rejection_layer=None,
            modal_image_sha="sha256:" + "a" * 64,
        )


def test_generated_current_schema_unknown_modal_image_requires_fallback_components() -> None:
    with pytest.raises(ValueError, match="modal_image_provenance_components"):
        _generated_row(
            condition="C",
            generation_metadata_schema_version=(
                CLUSTER2_GENERATION_METADATA_SCHEMA_VERSION
            ),
            modal_image_sha="unknown",
            modal_image_provenance_sha256="b" * 64,
            modal_image_provenance_components=None,
        )


def test_generated_current_schema_rejects_modal_image_fallback_digest_mismatch() -> None:
    with pytest.raises(
        ValueError,
        match="modal_image_provenance_sha256 must equal",
    ):
        _generated_row(
            condition="C",
            generation_metadata_schema_version=(
                CLUSTER2_GENERATION_METADATA_SCHEMA_VERSION
            ),
            modal_image_sha="unknown",
            modal_image_provenance_sha256="b" * 64,
            modal_image_provenance_components=_fallback_modal_image_components(),
        )


def test_generated_current_schema_accepts_valid_modal_image_fallback() -> None:
    row = _generated_row(
        condition="C",
        generation_metadata_schema_version=(
            CLUSTER2_GENERATION_METADATA_SCHEMA_VERSION
        ),
        modal_image_sha="unknown",
        modal_image_provenance_sha256=_fallback_modal_image_sha256(),
        modal_image_provenance_components=_fallback_modal_image_components(),
    )

    assert row.generated_metadata is not None
    assert row.generated_metadata.modal_image_sha == "unknown"


def test_generated_paper_scale_metadata_accepts_stable_modal_image_sha() -> None:
    row = _generated_row(
        condition="C",
        stop_reason="eos_token",
        xgrammar_version="0.1.33",
        transformers_version="4.51.0",
        tokenizers_version="0.21.0",
        model_revision="a" * 40,
        tokenizer_revision="b" * 40,
        modal_image_sha="sha256:" + "a" * 64,
        generation_metadata_schema_version=1,
    )

    assert row.generated_metadata is not None
    validate_generated_paper_scale_metadata(row.generated_metadata)


def test_generated_paper_scale_metadata_rejects_floating_revision() -> None:
    row = _generated_row(
        condition="C",
        stop_reason="eos_token",
        xgrammar_version="0.1.33",
        transformers_version="4.51.0",
        tokenizers_version="0.21.0",
        model_revision="refs/heads/main",
        tokenizer_revision="b" * 40,
        modal_image_sha="sha256:" + "a" * 64,
        generation_metadata_schema_version=1,
    )

    assert row.generated_metadata is not None
    with pytest.raises(ValueError, match="model_revision_not_immutable"):
        validate_generated_paper_scale_metadata(row.generated_metadata)


def test_replay_rows_preserve_frozen_cluster1_hash_semantics() -> None:
    row = _replay_row(condition="none")
    sidecar = _sidecar([row])

    assert row.replay_metadata is not None
    assert row.replay_metadata.frozen_cluster1_source_hash == row.source_hash
    assert row.replay_metadata.frozen_cluster1_generation_hashes == _frozen_hashes("none")
    assert sidecar.replay_control_hashes == {"none": _frozen_hashes("none")}
    assert sidecar.generated_condition_hashes == {}


def test_replay_metadata_preserves_frozen_failure_diagnostics() -> None:
    source_text = "import triton\n@triton.jit\ndef replay_bad_signature(): pass"
    row = replay_control_row(
        condition="none",
        attempt_index=0,
        kernel_class="elementwise",
        kernel_name="relu",
        dtype="fp32",
        base_seed=11,
        source_hash=_source_hash(source_text),
        functional_success=False,
        repair_set_success=False,
        eval_set_success=False,
        failure_code="F0_BAD_SIGNATURE",
        frozen_cluster1_artifact_id="none_baseline_n20_l4",
        frozen_cluster1_generation_hashes=_frozen_hashes("none"),
        frozen_cluster1_row_hash="a" * 64,
        frozen_cluster1_failure_code="F0_BAD_SIGNATURE",
        legacy_compile_error_type="SignatureError",
    )

    rebuilt = Cluster2EvalRow.from_dict(json.loads(row.to_json()))

    assert rebuilt.replay_metadata is not None
    assert rebuilt.failure_code == "F0_BAD_SIGNATURE"
    assert rebuilt.replay_metadata.frozen_cluster1_failure_code == "F0_BAD_SIGNATURE"
    assert rebuilt.replay_metadata.legacy_compile_error_type == "SignatureError"


def test_generated_rows_preserve_c2_generation_hash_semantics() -> None:
    row = _generated_row(condition="C")
    sidecar = _sidecar([row])

    assert row.generated_metadata is not None
    assert row.generated_metadata.c2_generation_hashes == _c2_hashes("C")
    assert sidecar.generated_condition_hashes == {"C": _c2_hashes("C")}
    assert sidecar.replay_control_hashes == {}


def test_hash_sidecar_rejects_collapsed_hash_classes() -> None:
    row = _generated_row(condition="C")
    bad_sidecar = Cluster2ContentHashSidecar(
        schema_version=CLUSTER2_RESULTS_SCHEMA_VERSION,
        eval_pipeline_hashes=_eval_hashes(),
        generated_condition_hashes={"C": _frozen_hashes("none")},
        replay_control_hashes={},
        external_pins=_external_pins(),
    )

    with pytest.raises(ValueError, match="C2 generation class"):
        validate_content_hash_sidecar_for_rows([row], bad_sidecar)


def test_default_hash_sidecar_collects_authoritative_condition_hashes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row = _generated_row(condition="C")
    authoritative_hashes = {"cluster2/modal/generation.py": "9" * 64}
    monkeypatch.setattr(
        results_logger,
        "collect_c2_generation_hashes",
        lambda condition: authoritative_hashes,
    )

    sidecar = build_content_hash_sidecar(
        [row],
        eval_pipeline_hashes=_eval_hashes(),
        external_pins=_external_pins(),
    )

    assert sidecar.generated_condition_hashes == {"C": authoritative_hashes}
    assert sidecar.generated_condition_hashes != {"C": _c2_hashes("C")}
    with pytest.raises(ValueError, match="C2 generation class"):
        validate_content_hash_sidecar_for_rows([row], sidecar)


def test_writer_without_sidecar_rejects_non_authoritative_row_hashes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row = _generated_row(condition="C")
    monkeypatch.setattr(
        results_logger,
        "collect_c2_generation_hashes",
        lambda condition: {"cluster2/modal/generation.py": "9" * 64},
    )

    with pytest.raises(ValueError, match="C2 generation class"):
        write_cluster2_results_jsonl(
            tmp_path / "results.jsonl",
            [row],
            mode="overwrite",
        )


def test_forbidden_fields_are_absent_from_rows_sidecars_and_trace() -> None:
    row = _generated_row(condition="C")
    sidecar = _sidecar([row])

    dataclass_field_names = set()
    for cls in (
        Cluster2EvalRow,
        Cluster2ReplayRowMetadata,
        Cluster2GeneratedRowMetadata,
        Cluster2ContentHashSidecar,
        Cluster2OptionalDiagnostics,
    ):
        dataclass_field_names.update(field.name for field in fields(cls))
    assert FORBIDDEN_CLUSTER2_RESULT_FIELDS.isdisjoint(dataclass_field_names)

    rendered_payloads = [
        row.to_dict(),
        sidecar.to_dict(),
        row.trace_summary.to_dict() if row.trace_summary is not None else {},
    ]
    rendered_keys = set().union(*(_recursive_keys(payload) for payload in rendered_payloads))
    assert FORBIDDEN_CLUSTER2_RESULT_FIELDS.isdisjoint(rendered_keys)


def test_optional_diagnostics_are_not_required_runtime_paths(tmp_path: Path) -> None:
    row = _generated_row(condition="C")
    no_diagnostics = _sidecar([row])
    diagnostics = Cluster2OptionalDiagnostics(
        full_trace_sidecar_path=str(tmp_path / "missing-full-trace.jsonl"),
        private_eval_sidecar_path=str(tmp_path / "missing-private-eval.jsonl"),
    )
    with_diagnostics = build_content_hash_sidecar(
        [row],
        eval_pipeline_hashes=_eval_hashes(),
        generated_condition_hashes={"C": _c2_hashes("C")},
        replay_control_hashes={},
        external_pins=_external_pins(),
        optional_diagnostics=diagnostics,
    )

    assert no_diagnostics.optional_diagnostics is None
    assert with_diagnostics.optional_diagnostics == diagnostics
    assert Cluster2ContentHashSidecar.from_dict(with_diagnostics.to_dict()) == with_diagnostics


def test_cluster1_generation_result_schema_includes_generation_metadata() -> None:
    assert [field.name for field in fields(GenerationResult)] == [
        "source",
        "model_id",
        "grammar_active",
        "grammar_variant",
        "kernel_class",
        "kernel_name",
        "dtype",
        "compile_success",
        "compile_results_by_dtype",
        "compile_error_type",
        "compile_error_msg",
        "masked_token_rate",
        "unique_solution_hash",
        "n_shapes_tested",
        "generation_seed",
        "temperature",
        "run_id",
        "timestamp_utc",
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


def test_cluster1_jsonl_logger_compatibility_is_preserved(tmp_path: Path) -> None:
    output = tmp_path / "cluster1.jsonl"
    result = _cluster1_generation_result()

    append_result_jsonl(output, result)
    payload = json.loads(output.read_text(encoding="utf-8").strip())

    assert payload["grammar_active"] is True
    assert payload["grammar_variant"] == "template_upper_bound"
    assert set(payload["compile_results_by_dtype"]) == {"fp32", "fp16", "bf16"}


def _generated_row(
    *,
    condition: str = "C",
    attempt_index: int = 0,
    kernel_class: str = "elementwise",
    kernel_name: str = "relu",
    source_text: str = "import triton\n@triton.jit\ndef k(): pass",
    functional_success: bool = True,
    **metadata_overrides: Any,
) -> Cluster2EvalRow:
    source_hash = _source_hash(source_text)
    return generated_row(
        condition=condition,
        attempt_index=attempt_index,
        kernel_class=kernel_class,
        kernel_name=kernel_name,
        dtype="fp32",
        base_seed=11,
        source_hash=source_hash,
        functional_success=functional_success,
        repair_set_success=functional_success,
        eval_set_success=functional_success,
        failure_code=None if functional_success else "F2_NUMERIC_LARGE",
        trace_summary=TraceSummary(
            attempt_index=attempt_index,
            failure_code=None if functional_success else "F2_NUMERIC_LARGE",
            public_failure_summary=(
                "Candidate passed Level 2."
                if functional_success
                else "Validation failed."
            ),
            functional_success=functional_success,
            repair_set_success=functional_success,
            eval_set_success=functional_success,
            source_hash=source_hash,
        ),
        c2_generation_hashes=_c2_hashes(condition),
        generation_seed=110 + attempt_index,
        grammar_variant="task_agnostic" if condition == "G+C" else None,
        grammar_path=(
            "cluster1/grammar/triton_kernel_agnostic.gbnf"
            if condition == "G+C"
            else None
        ),
        grammar_claim_scope="primary" if condition == "G+C" else None,
        **metadata_overrides,
    )


def _replay_row(
    *,
    condition: str = "none",
    attempt_index: int = 0,
    source_text: str = "import triton\n@triton.jit\ndef replay(): pass",
) -> Cluster2EvalRow:
    return replay_control_row(
        condition=condition,
        attempt_index=attempt_index,
        kernel_class="elementwise",
        kernel_name="relu",
        dtype="fp32",
        base_seed=11,
        source_hash=_source_hash(source_text),
        functional_success=True,
        repair_set_success=True,
        eval_set_success=True,
        failure_code=None,
        frozen_cluster1_artifact_id=(
            "none_baseline_n20_l4"
            if condition == "none"
            else "g_template_upper_bound_n20_l4"
        ),
        frozen_cluster1_generation_hashes=_frozen_hashes(condition),
        frozen_cluster1_row_hash="a" * 64,
    )


def _sidecar(
    rows: list[Cluster2EvalRow],
    *,
    eval_hashes: dict[str, str] | None = None,
) -> Cluster2ContentHashSidecar:
    generated_hashes = {
        row.condition: row.generated_metadata.c2_generation_hashes
        for row in rows
        if row.generated_metadata is not None
    }
    replay_hashes = {
        row.condition: row.replay_metadata.frozen_cluster1_generation_hashes
        for row in rows
        if row.replay_metadata is not None
    }
    return build_content_hash_sidecar(
        rows,
        eval_pipeline_hashes=_eval_hashes() if eval_hashes is None else eval_hashes,
        generated_condition_hashes=generated_hashes,
        replay_control_hashes=replay_hashes,
        external_pins=_external_pins(),
    )


def _eval_hashes() -> dict[str, str]:
    return {"shared/eval/pipeline.py": "0" * 64}


def _c2_hashes(condition: str) -> dict[str, str]:
    prefix = "2" if condition == "C" else "3"
    return {"cluster2/modal/generation.py": prefix * 64}


def _frozen_hashes(condition: str) -> dict[str, str]:
    prefix = "4" if condition == "none" else "5"
    return {f"{condition}:frozen_cluster1_artifact": prefix * 64}


def _external_pins() -> dict[str, str]:
    return {"python_version": "3.11.test"}


def _source_hash(source_text: str) -> str:
    return hashlib.sha256(source_text.encode("utf-8")).hexdigest()


def _assert_jsonl_rows(path: Path, *, expected_count: int) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == expected_count
    for line in lines:
        assert line
        assert isinstance(json.loads(line), dict)


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


def _recursive_keys(payload: Any) -> set[str]:
    if isinstance(payload, dict):
        keys = set(payload)
        for value in payload.values():
            keys.update(_recursive_keys(value))
        return keys
    if isinstance(payload, list | tuple):
        keys: set[str] = set()
        for value in payload:
            keys.update(_recursive_keys(value))
        return keys
    return set()


def _cluster1_generation_result() -> GenerationResult:
    return GenerationResult(
        source="import triton\n@triton.jit\ndef k(): pass",
        model_id="Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        grammar_active=True,
        grammar_variant="template_upper_bound",
        kernel_class="elementwise",
        kernel_name="relu",
        dtype="fp32",
        compile_success=True,
        compile_results_by_dtype={"fp32": True, "fp16": True, "bf16": True},
        compile_error_type=None,
        compile_error_msg=None,
        masked_token_rate=0.25,
        unique_solution_hash="abc123",
        n_shapes_tested=5,
        generation_seed=0,
        temperature=0.2,
        run_id=str(uuid.uuid4()),
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
    )
