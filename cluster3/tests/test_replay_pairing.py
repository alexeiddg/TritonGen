from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any

import pytest

import cluster3.replay.build_no_p_pair_manifest as manifest_builder_module
from cluster3.replay.build_no_p_pair_manifest import (
    build_no_p_pair_manifest,
    main as build_manifest_main,
)
from cluster3.replay.no_p_pairs import (
    NO_P_PAIR_MANIFEST_SCHEMA_VERSION,
    NoPControlManifestEntry,
    NoPPairManifest,
    load_no_p_pair_manifest,
    pair_for_condition,
    resolve_no_p_control,
    validate_pair_identity,
)


REV_A = "a" * 40
REV_B = "b" * 40
SOURCE_HASH = "1" * 64
PROMPT_HASH = "2" * 64
CONTROL_SOURCE_HASH = "3" * 64


def test_pair_for_condition_full_table() -> None:
    assert pair_for_condition("P") == "none"
    assert pair_for_condition("G+P") == "G"
    assert pair_for_condition("C+P") == "C"
    assert pair_for_condition("G+C+P") == "G+C"


def test_validate_pair_identity_accepts_matching_rows() -> None:
    p_row, control_row = _pair_rows("P")
    validate_pair_identity(p_row, control_row)


def test_validate_pair_identity_rejects_diverging_seed() -> None:
    p_row, control_row = _pair_rows("P")
    control_row["base_seed"] = 99
    with pytest.raises(ValueError, match="base_seed"):
        validate_pair_identity(p_row, control_row)


def test_validate_pair_identity_rejects_diverging_kernel() -> None:
    p_row, control_row = _pair_rows("P")
    control_row["kernel_name"] = "softmax"
    with pytest.raises(ValueError, match="kernel_name"):
        validate_pair_identity(p_row, control_row)


def test_validate_pair_identity_rejects_diverging_dtype() -> None:
    p_row, control_row = _pair_rows("P")
    control_row["dtype"] = "fp16"
    with pytest.raises(ValueError, match="dtype"):
        validate_pair_identity(p_row, control_row)


def test_validate_pair_identity_rejects_diverging_prompt_sha() -> None:
    p_row, control_row = _pair_rows("P")
    control_row["prompt_sha256"] = "4" * 64
    with pytest.raises(ValueError, match="prompt hash"):
        validate_pair_identity(p_row, control_row)


def test_validate_pair_identity_rejects_diverging_model_revision() -> None:
    p_row, control_row = _pair_rows("P")
    control_row["model_revision"] = REV_B
    with pytest.raises(ValueError, match="model_revision"):
        validate_pair_identity(p_row, control_row)


def test_validate_pair_identity_rejects_diverging_tokenizer_revision() -> None:
    p_row, control_row = _pair_rows("P")
    control_row["tokenizer_revision"] = REV_A
    with pytest.raises(ValueError, match="tokenizer_revision"):
        validate_pair_identity(p_row, control_row)


def test_validate_pair_identity_rejects_temperature_mismatch() -> None:
    p_row, control_row = _pair_rows("P")
    control_row["temperature"] = 0.7
    with pytest.raises(ValueError, match="temperature"):
        validate_pair_identity(p_row, control_row)


def test_validate_pair_identity_rejects_scale_tier_conflict() -> None:
    p_row, control_row = _pair_rows("P")
    control_row["scale_tier"] = "development"
    with pytest.raises(ValueError, match="scale_tier"):
        validate_pair_identity(p_row, control_row)


def test_validate_pair_identity_rejects_source_hash_mismatch() -> None:
    p_row, control_row = _pair_rows("P")
    p_row["expected_control_source_hash"] = CONTROL_SOURCE_HASH
    control_row["source_sha256"] = SOURCE_HASH
    with pytest.raises(ValueError, match="control source hash"):
        validate_pair_identity(p_row, control_row)


def test_build_no_p_pair_manifest_from_fixtures(tmp_path: Path) -> None:
    cluster1_manifest, cluster2_output = _write_fixture_inputs(tmp_path)
    output = tmp_path / "no_p_pair_manifest.json"

    result = build_manifest_main(
        [
            "--cluster1-frozen-manifest",
            str(cluster1_manifest),
            "--cluster2-outputs",
            str(cluster2_output),
            "--output",
            str(output),
        ]
    )

    assert result == 0
    manifest = json.loads(output.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == NO_P_PAIR_MANIFEST_SCHEMA_VERSION
    assert [entry["condition"] for entry in manifest["entries"]] == [
        "none",
        "G",
        "C",
        "G+C",
    ]
    assert manifest["build_metadata"]["row_counts"]["accepted_entries"] == 4
    assert manifest["build_metadata"]["rejected_row_counts"]["total"] == 0


def test_manifest_builder_rejects_duplicate_pair_keys_before_write(
    tmp_path: Path,
) -> None:
    cluster1_manifest = _write_cluster1_manifest(tmp_path)
    cluster2_output = tmp_path / "cluster2.jsonl"
    duplicate = _control_row(
        "C",
        sample_index=None,
        base_seed_is_sample_identity=True,
    )
    _write_jsonl(cluster2_output, [duplicate, dict(duplicate)])
    output = tmp_path / "manifest.json"

    with pytest.raises(SystemExit):
        build_manifest_main(
            [
                "--cluster1-frozen-manifest",
                str(cluster1_manifest),
                "--cluster2-outputs",
                str(cluster2_output),
                "--output",
                str(output),
            ]
        )

    assert not output.exists()


def test_manifest_builder_rejects_invalid_condition_without_aborting(
    tmp_path: Path,
) -> None:
    cluster1_manifest = _write_cluster1_manifest(tmp_path)
    cluster2_output = tmp_path / "cluster2.jsonl"
    invalid = _control_row("C")
    invalid["condition"] = 123
    _write_jsonl(cluster2_output, [invalid])

    manifest = build_no_p_pair_manifest(
        cluster1_frozen_manifest=cluster1_manifest,
        cluster2_outputs=[cluster2_output],
        built_at_utc="2026-01-01T00:00:00+00:00",
    )

    assert [entry["condition"] for entry in manifest["entries"]] == ["none", "G"]
    rejection_reasons = manifest["build_metadata"]["rejection_reasons"]
    assert (
        sum(
            count
            for reason, count in rejection_reasons.items()
            if reason.startswith("invalid_condition:")
        )
        == 1
    )
    assert manifest["build_metadata"]["rejected_row_counts"]["total"] == 1


def test_manifest_builder_rejects_non_object_jsonl_row_without_aborting(
    tmp_path: Path,
) -> None:
    cluster1_manifest = _write_cluster1_manifest(tmp_path)
    cluster2_output = tmp_path / "cluster2.jsonl"
    valid = _control_row(
        "C",
        sample_index=None,
        base_seed_is_sample_identity=True,
    )
    cluster2_output.write_text(
        json.dumps(["not", "an", "object"]) + "\n" + json.dumps(valid) + "\n",
        encoding="utf-8",
    )

    manifest = build_no_p_pair_manifest(
        cluster1_frozen_manifest=cluster1_manifest,
        cluster2_outputs=[cluster2_output],
        built_at_utc="2026-01-01T00:00:00+00:00",
    )

    assert [entry["condition"] for entry in manifest["entries"]] == ["none", "G", "C"]
    assert manifest["build_metadata"]["rejection_reasons"]["row_not_object"] == 1
    assert manifest["build_metadata"]["rejected_row_counts"]["total"] == 1


def test_manifest_builder_rejects_outputs_path_from_subdirectory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(Path("cluster3"))

    with pytest.raises(ValueError, match="outputs"):
        manifest_builder_module._reject_output_path_under_outputs(
            Path("..") / "outputs" / "phase6_review_fix_manifest.json"
        )


def test_cluster3_manifest_fields_support_validate_pair_identity(tmp_path: Path) -> None:
    manifest = _build_fixture_manifest(tmp_path)

    for condition in ("P", "G+P", "C+P", "G+C+P"):
        control = resolve_no_p_control(manifest, _p_row_for_condition(condition))
        validate_pair_identity(_p_row_for_condition(condition), control)


def test_cluster3_manifest_entries_resolve_no_p_controls(tmp_path: Path) -> None:
    manifest = _build_fixture_manifest(tmp_path)

    assert resolve_no_p_control(manifest, _p_row_for_condition("P")).condition == "none"
    assert resolve_no_p_control(manifest, _p_row_for_condition("G+P")).condition == "G"
    assert resolve_no_p_control(manifest, _p_row_for_condition("C+P")).condition == "C"
    assert (
        resolve_no_p_control(manifest, _p_row_for_condition("G+C+P")).condition
        == "G+C"
    )


def test_cluster3_manifest_row_contains_pair_identity_fields(tmp_path: Path) -> None:
    manifest = _build_fixture_manifest(tmp_path)
    required = {
        "artifact_id",
        "artifact_path",
        "condition",
        "grammar_variant",
        "kernel_class",
        "kernel_name",
        "dtype",
        "base_seed",
        "generation_seed",
        "sample_index",
        "sample_index_source",
        "replay_pair_id",
        "source_sha256",
        "prompt_sha256",
        "model_id",
        "model_revision",
        "tokenizer_revision",
        "temperature",
        "max_new_tokens",
        "scale_tier",
        "compile_success",
        "functional_success",
        "failure_code",
        "row_index",
        "row_schema_version",
    }
    for entry in manifest.entries:
        assert required == set(entry.to_dict())


def test_manifest_derives_sample_index_from_base_seed_when_absent(tmp_path: Path) -> None:
    cluster1_manifest = _write_cluster1_manifest(tmp_path)
    cluster2_output = tmp_path / "cluster2.jsonl"
    _write_jsonl(
        cluster2_output,
        [_control_row("C", sample_index=None, base_seed_is_sample_identity=True)],
    )

    manifest = build_no_p_pair_manifest(
        cluster1_frozen_manifest=cluster1_manifest,
        cluster2_outputs=[cluster2_output],
        built_at_utc="2026-01-01T00:00:00+00:00",
    )

    c_entry = next(entry for entry in manifest["entries"] if entry["condition"] == "C")
    assert c_entry["sample_index"] == 0
    assert c_entry["sample_index_source"] == "base_seed_derived"


def test_manifest_rejects_missing_sample_index_when_not_derivable(tmp_path: Path) -> None:
    cluster1_manifest = _write_cluster1_manifest(tmp_path)
    cluster2_output = tmp_path / "cluster2.jsonl"
    _write_jsonl(cluster2_output, [_control_row("C", sample_index=None)])

    manifest = build_no_p_pair_manifest(
        cluster1_frozen_manifest=cluster1_manifest,
        cluster2_outputs=[cluster2_output],
        built_at_utc="2026-01-01T00:00:00+00:00",
    )

    assert [entry["condition"] for entry in manifest["entries"]] == ["none", "G"]
    assert (
        manifest["build_metadata"]["rejection_reasons"][
            "missing_sample_index_identity"
        ]
        == 1
    )


def test_validate_pair_identity_accepts_c2_generated_control_with_derived_sample_index(
    tmp_path: Path,
) -> None:
    manifest = _build_fixture_manifest(tmp_path)
    p_row = _p_row_for_condition("C+P")
    control = resolve_no_p_control(manifest, p_row)

    assert control.sample_index_source == "base_seed_derived"
    validate_pair_identity(p_row, control)


def test_load_no_p_pair_manifest_rejects_unknown_schema_version(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    _write_json(
        manifest_path,
        {
            "schema_version": "cluster3.no_p_pair_manifest.v0",
            "entries": [],
        },
    )

    with pytest.raises(ValueError, match="schema_version"):
        load_no_p_pair_manifest(manifest_path)


def test_load_no_p_pair_manifest_rejects_duplicate_pair_keys(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    entry = _manifest_entry("none")
    duplicate = {**entry, "artifact_id": "other"}
    _write_json(
        manifest_path,
        {
            "schema_version": NO_P_PAIR_MANIFEST_SCHEMA_VERSION,
            "entries": [entry, duplicate],
        },
    )

    with pytest.raises(ValueError, match="duplicate"):
        load_no_p_pair_manifest(manifest_path)


def test_resolve_no_p_control_returns_expected_none_for_p(tmp_path: Path) -> None:
    manifest = _build_fixture_manifest(tmp_path)
    assert resolve_no_p_control(manifest, _p_row_for_condition("P")).condition == "none"


def test_resolve_no_p_control_returns_expected_g_for_gp(tmp_path: Path) -> None:
    manifest = _build_fixture_manifest(tmp_path)
    assert resolve_no_p_control(manifest, _p_row_for_condition("G+P")).condition == "G"


def test_resolve_no_p_control_returns_expected_c_for_cp(tmp_path: Path) -> None:
    manifest = _build_fixture_manifest(tmp_path)
    assert resolve_no_p_control(manifest, _p_row_for_condition("C+P")).condition == "C"


def test_resolve_no_p_control_returns_expected_gc_for_gcp(tmp_path: Path) -> None:
    manifest = _build_fixture_manifest(tmp_path)
    assert (
        resolve_no_p_control(manifest, _p_row_for_condition("G+C+P")).condition
        == "G+C"
    )


def test_resolve_no_p_control_rejects_missing_control() -> None:
    manifest = NoPPairManifest(
        schema_version=NO_P_PAIR_MANIFEST_SCHEMA_VERSION,
        entries=(NoPControlManifestEntry.from_dict(_manifest_entry("G")),),
    )

    with pytest.raises(ValueError, match="no matching"):
        resolve_no_p_control(manifest, _p_row_for_condition("P"))


def test_resolve_no_p_control_rejects_multiple_controls() -> None:
    first = NoPControlManifestEntry.from_dict(_manifest_entry("none"))
    second = NoPControlManifestEntry.from_dict(
        _manifest_entry("none", sample_index=1, replay_pair_id="pair-1")
    )
    manifest = NoPPairManifest(
        schema_version=NO_P_PAIR_MANIFEST_SCHEMA_VERSION,
        entries=(first, second),
    )
    p_row = _p_row_for_condition("P")
    p_row.pop("sample_index")
    p_row.pop("replay_pair_id")

    with pytest.raises(ValueError, match="multiple"):
        resolve_no_p_control(manifest, p_row)


def test_gp_vs_g_rejects_mixed_grammar_variant() -> None:
    p_row, control_row = _pair_rows("G+P")
    control_row["grammar_variant"] = "template_upper_bound"
    with pytest.raises(ValueError, match="grammar_variant"):
        validate_pair_identity(p_row, control_row)


def test_gcp_vs_gc_rejects_mixed_grammar_variant() -> None:
    p_row, control_row = _pair_rows("G+C+P")
    control_row["grammar_variant"] = "template_upper_bound"
    with pytest.raises(ValueError, match="grammar_variant"):
        validate_pair_identity(p_row, control_row)


def test_cluster3_contracts_directory_exists() -> None:
    assert Path("cluster3/contracts").is_dir()
    assert Path("cluster3/contracts/no_p_pair_manifest.json").is_file()


def test_build_no_p_pair_manifest_module_importable() -> None:
    module = importlib.import_module("cluster3.replay.build_no_p_pair_manifest")
    assert hasattr(module, "build_no_p_pair_manifest")


def test_manifest_builder_does_not_modify_cluster2_frozen_manifest(tmp_path: Path) -> None:
    frozen_manifest = Path("cluster2/contracts/frozen_cluster1_artifacts_manifest.json")
    before = frozen_manifest.read_bytes()
    cluster1_manifest, cluster2_output = _write_fixture_inputs(tmp_path)

    build_manifest_main(
        [
            "--cluster1-frozen-manifest",
            str(cluster1_manifest),
            "--cluster2-outputs",
            str(cluster2_output),
            "--output",
            str(tmp_path / "manifest.json"),
        ]
    )

    assert frozen_manifest.read_bytes() == before


def _pair_rows(p_condition: str) -> tuple[dict[str, Any], dict[str, Any]]:
    control_condition = pair_for_condition(p_condition)
    common = _common_identity()
    p_row = {"condition": p_condition, **common}
    control_row = {"condition": control_condition, **common}
    if p_condition in {"G+P", "G+C+P"}:
        p_row["grammar_variant"] = "task_agnostic"
        control_row["grammar_variant"] = "task_agnostic"
    return p_row, control_row


def _p_row_for_condition(condition: str) -> dict[str, Any]:
    p_row, _control_row = _pair_rows(condition)
    return p_row


def _common_identity() -> dict[str, Any]:
    return {
        "kernel_class": "elementwise",
        "kernel_name": "relu",
        "dtype": "fp32",
        "base_seed": 0,
        "sample_index": 0,
        "replay_pair_id": "pair-0",
        "model_id": "model",
        "model_revision": REV_A,
        "tokenizer_revision": REV_B,
        "temperature": 0.2,
        "max_new_tokens": 1536,
        "scale_tier": "paper",
        "prompt_sha256": PROMPT_HASH,
    }


def _manifest_entry(condition: str, **overrides: Any) -> dict[str, Any]:
    grammar_variant = "task_agnostic" if condition in {"G", "G+C"} else None
    entry = {
        "artifact_id": f"{condition.replace('+', '_').lower()}_fixture",
        "artifact_path": f"/tmp/{condition.replace('+', '_').lower()}.jsonl",
        "condition": condition,
        "grammar_variant": grammar_variant,
        "kernel_class": "elementwise",
        "kernel_name": "relu",
        "dtype": "fp32",
        "base_seed": 0,
        "generation_seed": 0,
        "sample_index": 0,
        "sample_index_source": "row_sample_index",
        "replay_pair_id": "pair-0",
        "source_sha256": CONTROL_SOURCE_HASH,
        "prompt_sha256": PROMPT_HASH,
        "model_id": "model",
        "model_revision": REV_A,
        "tokenizer_revision": REV_B,
        "temperature": 0.2,
        "max_new_tokens": 1536,
        "scale_tier": "paper",
        "compile_success": True,
        "functional_success": True,
        "failure_code": None,
        "row_index": 0,
        "row_schema_version": 1,
    }
    entry.update(overrides)
    return entry


def _control_row(
    condition: str,
    *,
    sample_index: int | None = 0,
    base_seed_is_sample_identity: bool = False,
) -> dict[str, Any]:
    row = _manifest_entry(condition)
    row["source_sha256"] = SOURCE_HASH
    if sample_index is None:
        row.pop("sample_index")
        row.pop("sample_index_source")
    else:
        row["sample_index"] = sample_index
        row["sample_index_source"] = "row_sample_index"
    if base_seed_is_sample_identity:
        row["base_seed_is_sample_identity"] = True
    return row


def _write_fixture_inputs(tmp_path: Path) -> tuple[Path, Path]:
    cluster1_manifest = _write_cluster1_manifest(tmp_path)
    cluster2_output = tmp_path / "cluster2.jsonl"
    _write_jsonl(
        cluster2_output,
        [
            _control_row("C", sample_index=None, base_seed_is_sample_identity=True),
            _control_row("G+C", sample_index=None, base_seed_is_sample_identity=True),
        ],
    )
    return cluster1_manifest, cluster2_output


def _write_cluster1_manifest(tmp_path: Path) -> Path:
    manifest_path = tmp_path / "frozen_cluster1_manifest.json"
    _write_json(
        manifest_path,
        {
            "artifacts": [
                {
                    "artifact_id": "none_fixture",
                    "condition": "none",
                    "path": str(tmp_path / "none.jsonl"),
                    "condition_flag_check": {
                        "expected_grammar_variant": None,
                    },
                    "row_records": [_cluster1_row("none")],
                },
                {
                    "artifact_id": "g_task_agnostic_fixture",
                    "condition": "G",
                    "path": str(tmp_path / "g.jsonl"),
                    "condition_flag_check": {
                        "expected_grammar_variant": "task_agnostic",
                    },
                    "row_records": [_cluster1_row("G")],
                },
            ],
        },
    )
    return manifest_path


def _cluster1_row(condition: str) -> dict[str, Any]:
    row = _control_row(condition, sample_index=None)
    row["generation_index"] = 0
    row["attempt_index"] = 0
    row["line_number"] = 1
    row["condition"] = condition
    if condition == "G":
        row["grammar_variant"] = "task_agnostic"
    return row


def _build_fixture_manifest(tmp_path: Path) -> NoPPairManifest:
    cluster1_manifest, cluster2_output = _write_fixture_inputs(tmp_path)
    output = tmp_path / "manifest.json"
    manifest = build_no_p_pair_manifest(
        cluster1_frozen_manifest=cluster1_manifest,
        cluster2_outputs=[cluster2_output],
        built_at_utc="2026-01-01T00:00:00+00:00",
    )
    _write_json(output, manifest)
    return load_no_p_pair_manifest(output)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )
