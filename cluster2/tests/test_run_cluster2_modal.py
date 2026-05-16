"""Phase 11 tests for the main Cluster 2 runner."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

import cluster2.experiments.run_cluster2_modal as runner_mod
from cluster2.constants import DEFAULT_FROZEN_CLUSTER1_MANIFEST
from cluster2.experiments.run_f2_repair_smoke import _corrected_source, run_f2_repair_smoke
from cluster2.experiments.run_cluster2_modal import (
    Cluster2RunnerConfig,
    RunnerDependencies,
    parse_args,
    run_cluster2,
)
from cluster2.modal.correctness_runner import build_success_payload
from cluster2.modal.schemas import RemoteCorrectnessRequest, RemoteCorrectnessResult
from cluster2.results.logger import default_content_hash_sidecar_path
from cluster2.tests.test_replay_controls import _write_replay_fixture
from shared.eval.content_hashes import collect_c2_generation_hashes


REPO_ROOT = Path(__file__).resolve().parents[2]


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
    assert generation_calls[0]["generation_seed"] == 0
    assert generation_calls[0]["modal_generation_gpu"] == "L4"
    assert len(correctness_calls) == 1
    assert len(result.rows) == 1
    assert result.rows[0].source_class == "generated_row"
    assert result.rows[0].generated_metadata is not None
    assert result.rows[0].generated_metadata.replay_control_condition == "none"
    assert result.rows[0].generated_metadata.replay_generation_seed == 0
    assert result.rows[0].replay_metadata is None
    assert result.route_audit[0].route == "c2_repair_loop"


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
    assert [
        row.generated_metadata.generation_seed
        for row in result.rows
        if row.generated_metadata is not None
    ] == [0, 1]


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
    assert result.rows[0].generated_metadata.replay_control_condition == "G"
    assert (
        result.rows[0].generated_metadata.grammar_path
        == "cluster1/grammar/triton_kernel_agnostic.gbnf"
    )
    assert result.rows[0].generated_metadata.grammar_claim_scope == "primary"
    assert result.route_audit[0].route == "c2_repair_loop_with_g_adapter"


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


def test_runner_preflights_all_requested_cells_before_generation(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "bad_pairing_manifest.json"
    payload = json.loads(Path(DEFAULT_FROZEN_CLUSTER1_MANIFEST).read_text(encoding="utf-8"))
    artifact = payload["artifacts"][0]
    for schedule in artifact["seed_schedule"]["records"]:
        if schedule["kernel_class"] == "elementwise" and schedule["dtype"] == "fp16":
            schedule["max_new_tokens"] = 999
            for line_number in schedule["line_numbers"]:
                for record in artifact["row_records"]:
                    if record["line_number"] == line_number:
                        record["max_new_tokens"] = 999
            break
    manifest.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    generation_calls: list[dict[str, Any]] = []

    with pytest.raises(ValueError, match="max_new_tokens"):
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
            schedule["max_new_tokens"] = 999
            for line_number in schedule["line_numbers"]:
                for record in artifact["row_records"]:
                    if record["line_number"] == line_number:
                        record["max_new_tokens"] = 999
            break
    manifest.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    generation_calls: list[dict[str, Any]] = []

    with pytest.raises(ValueError, match="max_new_tokens"):
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
        model_revision="model-rev",
        tokenizer_revision="tok-rev",
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
                del kwargs
                return {"source": corrected_source}

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
                model_revision="test-model-revision",
                tokenizer_revision="test-tokenizer-revision",
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
    return build_success_payload(request, result)


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
