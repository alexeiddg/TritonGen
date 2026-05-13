"""Tests for Cluster 2 content-hash helpers."""

from __future__ import annotations

import hashlib

import pytest

from shared.eval.content_hashes import (
    collect_c2_generation_hashes,
    collect_c2_modal_hashes,
    collect_cluster1_frozen_generation_hashes,
    collect_eval_pipeline_hashes,
    collect_external_pins,
    collect_modal_source_manifest,
    file_sha256,
    function_source_sha256,
    module_content_sha256,
)


def _sample_function() -> str:
    return "sample"


def test_file_sha256_hashes_raw_bytes(tmp_path) -> None:
    path = tmp_path / "sample.txt"
    path.write_bytes(b"abc\n")

    assert file_sha256(path) == hashlib.sha256(b"abc\n").hexdigest()


def test_module_content_sha256_accepts_dotted_module_and_repo_path() -> None:
    dotted = module_content_sha256("shared.eval.constants")
    direct = module_content_sha256("shared/eval/constants.py")

    assert dotted == direct


def test_function_source_sha256_is_stable() -> None:
    assert function_source_sha256(_sample_function) == function_source_sha256(
        _sample_function
    )


def test_collect_eval_pipeline_hashes_includes_phase0_modules() -> None:
    hashes = collect_eval_pipeline_hashes()

    assert "shared/eval/run_config.py" in hashes
    assert "shared/eval/pipeline.py" in hashes
    assert "shared/eval/content_hashes.py" in hashes
    assert "shared/eval/correctness_shapes.py" in hashes
    assert "shared/eval/reference_runner.py" in hashes
    assert "shared/eval/schema.py" in hashes


def test_collect_c2_generation_hashes_rejects_replay_controls() -> None:
    with pytest.raises(ValueError, match="C and G\\+C"):
        collect_c2_generation_hashes("none")


def test_collect_c2_generation_hashes_include_isolated_modal_scaffold() -> None:
    hashes = collect_c2_generation_hashes("C")

    assert "cluster2/modal/schemas.py" in hashes
    assert "cluster2/modal/generation.py" in hashes


def test_collect_c2_modal_hashes_include_phase0_scaffolds() -> None:
    hashes = collect_c2_modal_hashes()

    assert set(hashes) == {
        "cluster2/modal/schemas.py",
        "cluster2/modal/generation.py",
        "cluster2/modal/correctness.py",
        "cluster2/modal/correctness_runner.py",
    }


def test_collect_cluster1_frozen_generation_hashes_for_template_controls() -> None:
    manifest = "cluster2/contracts/frozen_cluster1_artifacts_manifest.json"

    none_hashes = collect_cluster1_frozen_generation_hashes("none", manifest)
    g_hashes = collect_cluster1_frozen_generation_hashes("G", manifest)

    assert "none_baseline_n20_l4:artifact" in none_hashes
    assert "g_template_upper_bound_n20_l4:artifact" in g_hashes


def test_collect_modal_source_manifest_hashes_existing_paths_only() -> None:
    manifest = collect_modal_source_manifest(
        ["shared/modal_harness/generation.py", "missing.py"]
    )

    assert set(manifest) == {"shared/modal_harness/generation.py"}


def test_collect_external_pins_is_lightweight() -> None:
    pins = collect_external_pins()

    assert "python_version" in pins
    assert "package:modal" in pins
