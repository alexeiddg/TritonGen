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
    C_GENERATION_MODE,
    G_PLUS_C_GENERATION_MODE,
    GENERATED_SOURCE_CLASS,
    REPLAY_CONTROL_GENERATION_MODE,
    REPLAY_CONTROL_SOURCE_CLASS,
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
    Cluster2ContentHashSidecar,
    Cluster2EvalRow,
    Cluster2GeneratedRowMetadata,
    Cluster2ReplayRowMetadata,
)
from cluster2.tests.test_replay_controls import _write_replay_fixture
from shared.eval.pipeline import EvalPipelineSkeletonResult, PipelineStageStatus
from shared.eval.run_config import RunConfig


REPO_ROOT = Path(__file__).resolve().parents[2]
PHASE_MINUS1_MANIFEST = REPO_ROOT / "cluster2/contracts/phase_minus1_manifest.json"
FROZEN_CLUSTER1_MANIFEST = (
    REPO_ROOT / "cluster2/contracts/frozen_cluster1_artifacts_manifest.json"
)

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
    manifest = _load_json(PHASE_MINUS1_MANIFEST)
    record = manifest["cluster1_invariants"]["modal_generation"][
        "RemoteGenerator.generate_one"
    ]
    current_hash = _source_range_sha256(
        REPO_ROOT / record["path"],
        start_line=int(record["lines"]["start"]),
        end_line=int(record["lines"]["end"]),
    )

    assert current_hash == record["source_sha256"]


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
    phase_head = _load_json(PHASE_MINUS1_MANIFEST)["git"]["current_head"]

    assert _file_sha256(REPO_ROOT / rel_path) == _git_blob_sha256(phase_head, rel_path)


def test_frozen_cluster1_manifest_hash_matches_phase_minus1() -> None:
    manifest = _load_json(PHASE_MINUS1_MANIFEST)
    record = manifest["frozen_cluster1_artifacts_manifest"]

    assert record["path"] == "cluster2/contracts/frozen_cluster1_artifacts_manifest.json"
    assert _file_sha256(REPO_ROOT / record["path"]) == record["sha256"]


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

    assert observed_fields == expected["field_list"]
    assert _canonical_json_sha256(observed_fields) == expected["field_list_sha256"]


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
    generation_calls: list[dict[str, Any]] = []

    result = run_cluster2(
        _runner_config(tmp_path / f"out-{condition}", condition=condition),
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
            model_revision="model-rev",
            tokenizer_revision="tokenizer-rev",
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
        model_revision="model-rev",
        tokenizer_revision="tok-rev",
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
        return {
            "source": (
                "import torch\n"
                "import triton\n"
                "import triton.language as tl\n"
                f"# generated {identity.condition} {identity.attempt_index}\n"
            ),
            "generation_identity": {
                "grammar_active": identity.condition == "G+C",
                "grammar_variant": (
                    grammar_variant if identity.condition == "G+C" else None
                ),
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
        "model_revision": "model-rev",
        "tokenizer_revision": "tok-rev",
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
