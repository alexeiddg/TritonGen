"""Phase 11 tests for the main Cluster 2 runner."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from cluster2.experiments.run_cluster2_modal import (
    Cluster2RunnerConfig,
    RunnerDependencies,
    parse_args,
    run_cluster2,
)
from cluster2.results.logger import default_content_hash_sidecar_path
from cluster2.tests.test_replay_controls import _write_replay_fixture
from shared.eval.content_hashes import collect_c2_generation_hashes


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
    } == {"g_task_agnostic_n5_l4_rerun"}
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
    assert generation_calls[0]["modal_generation_gpu"] == "L4"
    assert len(correctness_calls) == 1
    assert len(result.rows) == 1
    assert result.rows[0].source_class == "generated_row"
    assert result.rows[0].generated_metadata is not None
    assert result.rows[0].replay_metadata is None
    assert result.route_audit[0].route == "c2_repair_loop"


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
    assert result.rows[0].generated_metadata is not None
    assert result.rows[0].generated_metadata.grammar_variant == "task_agnostic"
    assert (
        result.rows[0].generated_metadata.grammar_path
        == "cluster1/grammar/triton_kernel_agnostic.gbnf"
    )
    assert result.rows[0].generated_metadata.grammar_claim_scope == "primary"
    assert result.route_audit[0].route == "c2_repair_loop_with_g_adapter"


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
                "model-rev",
                "--tokenizer-revision",
                "tok-rev",
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
            "model-rev",
            "--tokenizer-revision",
            "tok-rev",
            "--output",
            str(tmp_path / "out.jsonl"),
            "--overwrite",
        ]
    )

    assert config.grammar_variant == "task_agnostic"


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
            "model-rev",
            "--tokenizer-revision",
            "tok-rev",
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
) -> Cluster2RunnerConfig:
    tmp_path.mkdir(parents=True, exist_ok=True)
    return Cluster2RunnerConfig(
        condition=condition,
        kernel_class="elementwise",
        scale_tier=scale_tier,
        n=n,
        frozen_cluster1_manifest=str(
            manifest if manifest is not None else tmp_path / "unused_manifest.json"
        ),
        model_id="Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        model_revision="model-rev",
        tokenizer_revision="tok-rev",
        grammar_variant=grammar_variant,
        dtypes=("fp32",),
        temperature=0.2,
        max_new_tokens=64,
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
        return {
            "source": source,
            "generation_hashes": collect_c2_generation_hashes(identity.condition),
            "generation_identity": {
                "grammar_active": identity.condition == "G+C",
                "grammar_variant": grammar_variant if identity.condition == "G+C" else None,
                "grammar_path": grammar_path,
                "grammar_claim_scope": grammar_claim_scope,
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
