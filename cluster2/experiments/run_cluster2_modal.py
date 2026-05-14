"""Main Cluster 2 runner CLI.

The runner owns condition routing for Phase 11. Replay controls (``none`` and
``G``) are loaded from frozen Cluster 1 artifacts and sent only to correctness
evaluation. Generated conditions (``C`` and ``G+C``) are the only conditions
allowed to call the C2 generation adapter.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from cluster2.constants import (
    CLUSTER2_CONDITIONS,
    DEFAULT_C2_MODAL_EVAL_GPU,
    DEFAULT_C2_MODAL_GENERATION_GPU,
    DEFAULT_FROZEN_CLUSTER1_MANIFEST,
    DEFAULT_REPAIR_BUDGET,
    DTYPE_NAMES,
    NEW_GENERATION_CONDITIONS,
    REPLAY_CONTROL_CONDITIONS,
    generation_mode_for_condition,
    normalize_cluster2_condition,
    source_class_for_condition,
)
from cluster2.feedback.repair_loop import (
    RepairEvaluationInput,
    RepairGenerationInput,
    run_repair_loop,
    seed_for_attempt,
)
from cluster2.modal.schemas import EvalIdentity, RemoteCorrectnessRequest
from cluster2.replay.cluster1_controls import (
    ReplayCandidateMapping,
    ReplayCoverageFailure,
    map_replay_candidates,
    replay_generation_hashes,
)
from cluster2.results.dataclass import (
    Cluster2ContentHashSidecar,
    Cluster2EvalRow,
    generated_row,
    replay_control_row,
)
from cluster2.results.logger import (
    collect_content_hash_sidecar_for_conditions,
    default_content_hash_sidecar_path,
    load_content_hash_sidecar,
    write_cluster2_results_jsonl,
)
from shared.eval.content_hashes import collect_c2_generation_hashes
from shared.eval.correctness_shapes import LOCKED_KERNEL_CLASSES, get_shape_metadata


MODEL_ID_DEFAULT = "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"
GRAMMAR_VARIANT_TEMPLATE_UPPER_BOUND = "template_upper_bound"
CONDITION_SELECTOR_CHOICES: tuple[str, ...] = (*CLUSTER2_CONDITIONS, "both", "all")
KERNEL_CLASS_SELECTOR_CHOICES: tuple[str, ...] = (*LOCKED_KERNEL_CLASSES, "all")
SCALE_TIER_CHOICES: tuple[str, ...] = ("smoke", "development", "paper")
MAX_CLI_N = 20

GenerationAdapter = Callable[..., dict[str, Any]]
CorrectnessAdapter = Callable[[RemoteCorrectnessRequest], dict[str, Any]]


@dataclass(frozen=True)
class Cluster2RunnerConfig:
    """Validated inputs for one Phase 11 runner invocation."""

    condition: str
    kernel_class: str
    scale_tier: str
    n: int
    frozen_cluster1_manifest: str
    model_id: str
    model_revision: str | None
    tokenizer_revision: str | None
    grammar_variant: str
    dtypes: tuple[str, ...]
    temperature: float
    max_new_tokens: int
    repair_budget: int
    modal_generation_gpu: str
    modal_eval_gpu: str
    output: str
    write_mode: str

    def __post_init__(self) -> None:
        _require_member(self.condition, CONDITION_SELECTOR_CHOICES, "condition")
        _require_member(self.kernel_class, KERNEL_CLASS_SELECTOR_CHOICES, "kernel_class")
        _require_member(self.scale_tier, SCALE_TIER_CHOICES, "scale_tier")
        _require_bounded_n(self.n)
        _require_non_empty_str(self.frozen_cluster1_manifest, "frozen_cluster1_manifest")
        _require_non_empty_str(self.model_id, "model_id")
        if any(condition in NEW_GENERATION_CONDITIONS for condition in self.conditions):
            _require_non_empty_str(self.model_revision, "model_revision")
            _require_non_empty_str(self.tokenizer_revision, "tokenizer_revision")
        if self.grammar_variant != GRAMMAR_VARIANT_TEMPLATE_UPPER_BOUND:
            raise ValueError("grammar_variant must be template_upper_bound")
        _require_dtypes(self.dtypes)
        _require_non_negative_float(self.temperature, "temperature")
        _require_positive_int(self.max_new_tokens, "max_new_tokens")
        _require_non_negative_int(self.repair_budget, "repair_budget")
        if self.repair_budget > DEFAULT_REPAIR_BUDGET:
            raise ValueError(f"repair_budget must be <= {DEFAULT_REPAIR_BUDGET}")
        if (
            any(condition in NEW_GENERATION_CONDITIONS for condition in self.conditions)
            and self.modal_generation_gpu != DEFAULT_C2_MODAL_GENERATION_GPU
        ):
            raise ValueError("modal_generation_gpu must be L4 for Cluster 2 generation")
        if self.modal_eval_gpu != DEFAULT_C2_MODAL_EVAL_GPU:
            raise ValueError("modal_eval_gpu must be L4 for Cluster 2")
        _require_non_empty_str(self.output, "output")
        _require_member(self.write_mode, ("overwrite", "resume"), "write_mode")

    @property
    def conditions(self) -> tuple[str, ...]:
        return expand_condition_selector(self.condition)

    @property
    def kernel_classes(self) -> tuple[str, ...]:
        return expand_kernel_class_selector(self.kernel_class)

    @classmethod
    def from_namespace(cls, namespace: argparse.Namespace) -> "Cluster2RunnerConfig":
        write_mode = "resume" if namespace.resume else "overwrite"
        return cls(
            condition=namespace.condition,
            kernel_class=namespace.kernel_class,
            scale_tier=namespace.scale_tier,
            n=namespace.n,
            frozen_cluster1_manifest=namespace.frozen_cluster1_manifest,
            model_id=namespace.model_id,
            model_revision=namespace.model_revision,
            tokenizer_revision=namespace.tokenizer_revision,
            grammar_variant=namespace.grammar_variant,
            dtypes=parse_dtypes(namespace.dtypes),
            temperature=namespace.temperature,
            max_new_tokens=namespace.max_new_tokens,
            repair_budget=namespace.repair_budget,
            modal_generation_gpu=namespace.modal_generation_gpu,
            modal_eval_gpu=namespace.modal_eval_gpu,
            output=namespace.output,
            write_mode=write_mode,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RunnerDependencies:
    """Injectable runtime adapters used by tests and the CLI."""

    generation: GenerationAdapter | None = None
    correctness: CorrectnessAdapter | None = None


@dataclass(frozen=True)
class ConditionRouteAudit:
    condition: str
    route: str
    generation_allowed: bool
    generation_calls: int
    correctness_calls: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Cluster2RunResult:
    rows: tuple[Cluster2EvalRow, ...]
    coverage_failures: tuple[ReplayCoverageFailure, ...]
    route_audit: tuple[ConditionRouteAudit, ...]
    output: str
    write_mode: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "rows": [row.to_dict() for row in self.rows],
            "coverage_failures": [
                failure.to_dict() for failure in self.coverage_failures
            ],
            "route_audit": [route.to_dict() for route in self.route_audit],
            "output": self.output,
            "write_mode": self.write_mode,
        }


@dataclass
class _ConditionRunStats:
    generation_calls: int = 0
    correctness_calls: int = 0


@dataclass
class _GeneratedAttemptRecord:
    attempt_index: int
    generation_seed: int
    source: str
    generation_payload: dict[str, Any]
    correctness_payload: dict[str, Any] | None = None
    correctness_result: dict[str, Any] | None = None


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_cluster2_modal",
        description="Run Phase 11 Cluster 2 condition routing.",
    )
    parser.add_argument("--condition", required=True, choices=CONDITION_SELECTOR_CHOICES)
    parser.add_argument("--kernel-class", required=True, choices=KERNEL_CLASS_SELECTOR_CHOICES)
    parser.add_argument("--scale-tier", required=True, choices=SCALE_TIER_CHOICES)
    parser.add_argument("--n", required=True, type=int)
    parser.add_argument(
        "--frozen-cluster1-manifest",
        default=DEFAULT_FROZEN_CLUSTER1_MANIFEST,
    )
    parser.add_argument("--model-id", default=MODEL_ID_DEFAULT)
    parser.add_argument("--model-revision")
    parser.add_argument("--tokenizer-revision")
    parser.add_argument(
        "--grammar-variant",
        default=GRAMMAR_VARIANT_TEMPLATE_UPPER_BOUND,
    )
    parser.add_argument("--dtypes", default=",".join(DTYPE_NAMES))
    parser.add_argument("--temperature", default=0.2, type=float)
    parser.add_argument("--max-new-tokens", default=1024, type=int)
    parser.add_argument("--repair-budget", default=DEFAULT_REPAIR_BUDGET, type=int)
    parser.add_argument("--modal-generation-gpu", default=DEFAULT_C2_MODAL_GENERATION_GPU)
    parser.add_argument("--modal-eval-gpu", default=DEFAULT_C2_MODAL_EVAL_GPU)
    parser.add_argument("--output", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--overwrite", action="store_true")
    mode.add_argument("--resume", action="store_true")
    return parser


def parse_args(argv: Sequence[str] | None = None) -> Cluster2RunnerConfig:
    namespace = build_arg_parser().parse_args(argv)
    return Cluster2RunnerConfig.from_namespace(namespace)


def main(argv: Sequence[str] | None = None) -> Cluster2RunResult:
    config = parse_args(argv)
    result = run_cluster2(config)
    print(
        json.dumps(
            {
                "rows": len(result.rows),
                "coverage_failures": [
                    failure.to_dict() for failure in result.coverage_failures
                ],
                "route_audit": [route.to_dict() for route in result.route_audit],
                "output": result.output,
                "write_mode": result.write_mode,
            },
            sort_keys=True,
        )
    )
    return result


def run_cluster2(
    config: Cluster2RunnerConfig,
    *,
    dependencies: RunnerDependencies | None = None,
) -> Cluster2RunResult:
    """Run the requested C2 routes and write deterministic JSONL results."""

    deps = dependencies or RunnerDependencies()
    rows: list[Cluster2EvalRow] = []
    coverage_failures: list[ReplayCoverageFailure] = []
    audits: list[ConditionRouteAudit] = []
    run_id = _stable_run_id(config)
    content_hash_sidecar = _build_runner_content_hash_sidecar(config)
    _preflight_resume_hashes(config, content_hash_sidecar)

    for condition in config.conditions:
        stats = _ConditionRunStats()
        before_rows = len(rows)
        before_failures = len(coverage_failures)
        if condition in REPLAY_CONTROL_CONDITIONS:
            _run_replay_condition(
                condition=condition,
                config=config,
                run_id=run_id,
                correctness=deps.correctness or _default_correctness_call,
                rows=rows,
                coverage_failures=coverage_failures,
                stats=stats,
            )
            route = "replay_adapter"
        else:
            _run_generated_condition(
                condition=condition,
                config=config,
                run_id=run_id,
                generation=deps.generation or _default_generation_call,
                correctness=deps.correctness or _default_correctness_call,
                rows=rows,
                stats=stats,
            )
            route = (
                "c2_repair_loop_with_g_adapter"
                if condition == "G+C"
                else "c2_repair_loop"
            )
        audits.append(
            ConditionRouteAudit(
                condition=condition,
                route=route,
                generation_allowed=condition in NEW_GENERATION_CONDITIONS,
                generation_calls=stats.generation_calls,
                correctness_calls=stats.correctness_calls,
            )
        )
        _assert_replay_route_did_not_generate(condition, stats)
        _assert_route_made_progress(
            condition=condition,
            before_rows=before_rows,
            after_rows=len(rows),
            before_failures=before_failures,
            after_failures=len(coverage_failures),
        )

    _write_rows(config, rows, content_hash_sidecar)
    return Cluster2RunResult(
        rows=tuple(rows),
        coverage_failures=tuple(coverage_failures),
        route_audit=tuple(audits),
        output=config.output,
        write_mode=config.write_mode,
    )


def expand_condition_selector(selector: str) -> tuple[str, ...]:
    if selector == "all":
        return CLUSTER2_CONDITIONS
    if selector == "both":
        return NEW_GENERATION_CONDITIONS
    return (normalize_cluster2_condition(selector),)


def expand_kernel_class_selector(selector: str) -> tuple[str, ...]:
    if selector == "all":
        return LOCKED_KERNEL_CLASSES
    _require_member(selector, LOCKED_KERNEL_CLASSES, "kernel_class")
    return (selector,)


def parse_dtypes(value: str) -> tuple[str, ...]:
    if not isinstance(value, str):
        raise TypeError("dtypes must be a string")
    dtypes = tuple(item.strip() for item in value.split(",") if item.strip())
    _require_dtypes(dtypes)
    return dtypes


def _run_replay_condition(
    *,
    condition: str,
    config: Cluster2RunnerConfig,
    run_id: str,
    correctness: CorrectnessAdapter,
    rows: list[Cluster2EvalRow],
    coverage_failures: list[ReplayCoverageFailure],
    stats: _ConditionRunStats,
) -> None:
    hashes = replay_generation_hashes(condition, config.frozen_cluster1_manifest)
    for kernel_class in config.kernel_classes:
        for dtype in config.dtypes:
            mapping = map_replay_candidates(
                condition=condition,
                kernel_class=kernel_class,
                dtype=dtype,
                candidate_count=config.n,
                manifest_path=config.frozen_cluster1_manifest,
                base_seed=0,
            )
            if not mapping.ok:
                assert mapping.coverage_failure is not None
                coverage_failures.append(mapping.coverage_failure)
                continue
            rows.extend(
                _evaluate_replay_mapping(
                    mapping,
                    run_id=run_id,
                    hashes=hashes,
                    correctness=correctness,
                    stats=stats,
                )
            )


def _evaluate_replay_mapping(
    mapping: ReplayCandidateMapping,
    *,
    run_id: str,
    hashes: dict[str, str],
    correctness: CorrectnessAdapter,
    stats: _ConditionRunStats,
) -> tuple[Cluster2EvalRow, ...]:
    rows: list[Cluster2EvalRow] = []
    for candidate in mapping.candidates:
        identity = _eval_identity(
            run_id=run_id,
            condition=candidate.condition,
            kernel_class=candidate.kernel_class,
            kernel_name=candidate.kernel_name,
            dtype=candidate.dtype,
            base_seed=candidate.base_seed,
            attempt_index=candidate.attempt_index,
        )
        request = RemoteCorrectnessRequest(identity=identity, source=candidate.source)
        payload = correctness(request)
        stats.correctness_calls += 1
        correctness_result = _extract_correctness_result_dict(payload)
        _validate_correctness_identity(correctness_result, identity)
        rows.append(
            replay_control_row(
                condition=candidate.condition,
                attempt_index=candidate.attempt_index,
                kernel_class=candidate.kernel_class,
                kernel_name=candidate.kernel_name,
                dtype=candidate.dtype,
                base_seed=candidate.base_seed,
                source_hash=candidate.source_sha256,
                functional_success=bool(correctness_result["functional_success"]),
                repair_set_success=bool(correctness_result["repair_set_success"]),
                eval_set_success=bool(correctness_result["eval_set_success"]),
                failure_code=correctness_result.get("failure_code"),
                frozen_cluster1_artifact_id=candidate.artifact_id,
                frozen_cluster1_generation_hashes=hashes,
                frozen_cluster1_row_hash=candidate.row_sha256,
            )
        )
    return tuple(rows)


def _run_generated_condition(
    *,
    condition: str,
    config: Cluster2RunnerConfig,
    run_id: str,
    generation: GenerationAdapter,
    correctness: CorrectnessAdapter,
    rows: list[Cluster2EvalRow],
    stats: _ConditionRunStats,
) -> None:
    c2_hashes = collect_c2_generation_hashes(condition)
    for kernel_class in config.kernel_classes:
        kernel_name = get_shape_metadata(kernel_class).kernel_name
        for dtype in config.dtypes:
            for base_seed in range(config.n):
                rows.extend(
                    _run_generated_cell(
                        condition=condition,
                        kernel_class=kernel_class,
                        kernel_name=kernel_name,
                        dtype=dtype,
                        base_seed=base_seed,
                        config=config,
                        run_id=run_id,
                        generation=generation,
                        correctness=correctness,
                        c2_hashes=c2_hashes,
                        stats=stats,
                    )
                )


def _run_generated_cell(
    *,
    condition: str,
    kernel_class: str,
    kernel_name: str,
    dtype: str,
    base_seed: int,
    config: Cluster2RunnerConfig,
    run_id: str,
    generation: GenerationAdapter,
    correctness: CorrectnessAdapter,
    c2_hashes: dict[str, str],
    stats: _ConditionRunStats,
) -> tuple[Cluster2EvalRow, ...]:
    attempt_records: dict[int, _GeneratedAttemptRecord] = {}
    base_prompt = _build_base_prompt(kernel_class, dtype)

    def generation_call(inputs: RepairGenerationInput) -> str:
        identity = _eval_identity(
            run_id=run_id,
            condition=condition,
            kernel_class=kernel_class,
            kernel_name=kernel_name,
            dtype=dtype,
            base_seed=base_seed,
            attempt_index=inputs.attempt_index,
        )
        payload = generation(
            identity=identity,
            prompt=inputs.prompt,
            model_id=config.model_id,
            model_revision=config.model_revision,
            tokenizer_revision=config.tokenizer_revision,
            generation_seed=inputs.generation_seed,
            temperature=config.temperature,
            max_new_tokens=config.max_new_tokens,
            modal_generation_gpu=config.modal_generation_gpu,
        )
        stats.generation_calls += 1
        source = _extract_generated_source(payload)
        attempt_records[inputs.attempt_index] = _GeneratedAttemptRecord(
            attempt_index=inputs.attempt_index,
            generation_seed=inputs.generation_seed,
            source=source,
            generation_payload=payload,
        )
        return source

    def evaluation_call(inputs: RepairEvaluationInput) -> object:
        identity = _eval_identity(
            run_id=run_id,
            condition=condition,
            kernel_class=kernel_class,
            kernel_name=kernel_name,
            dtype=dtype,
            base_seed=base_seed,
            attempt_index=inputs.attempt_index,
        )
        request = RemoteCorrectnessRequest(identity=identity, source=inputs.source)
        payload = correctness(request)
        stats.correctness_calls += 1
        result = _extract_correctness_result_dict(payload)
        _validate_correctness_identity(result, identity)
        attempt_records[inputs.attempt_index].correctness_payload = payload
        attempt_records[inputs.attempt_index].correctness_result = result
        return result

    repair_result = run_repair_loop(
        condition=condition,
        base_prompt=base_prompt,
        base_seed=base_seed,
        generation=generation_call,
        evaluation=evaluation_call,
        repair_budget=config.repair_budget,
    )
    trace_by_attempt = {
        trace.attempt_index: trace for trace in repair_result.trace_summaries
    }
    rows: list[Cluster2EvalRow] = []
    for attempt_index in sorted(attempt_records):
        record = attempt_records[attempt_index]
        if record.correctness_result is None:
            raise RuntimeError("generated attempt missing correctness result")
        generation_hashes = _generation_hashes_from_payload(
            record.generation_payload,
            fallback=c2_hashes,
        )
        source_hash = _source_sha256(record.source)
        rows.append(
            generated_row(
                condition=condition,
                attempt_index=record.attempt_index,
                kernel_class=kernel_class,
                kernel_name=kernel_name,
                dtype=dtype,
                base_seed=base_seed,
                source_hash=source_hash,
                functional_success=bool(
                    record.correctness_result["functional_success"]
                ),
                repair_set_success=bool(
                    record.correctness_result["repair_set_success"]
                ),
                eval_set_success=bool(record.correctness_result["eval_set_success"]),
                failure_code=record.correctness_result.get("failure_code"),
                trace_summary=trace_by_attempt[attempt_index],
                c2_generation_hashes=generation_hashes,
                generation_seed=record.generation_seed,
            )
        )
    return tuple(rows)


def _build_runner_content_hash_sidecar(
    config: Cluster2RunnerConfig,
) -> Cluster2ContentHashSidecar:
    return collect_content_hash_sidecar_for_conditions(
        config.conditions,
        frozen_cluster1_manifest_path=config.frozen_cluster1_manifest,
    )


def _preflight_resume_hashes(
    config: Cluster2RunnerConfig,
    content_hash_sidecar: Cluster2ContentHashSidecar,
) -> None:
    if config.write_mode != "resume":
        return

    output_path = Path(config.output)
    sidecar_path = default_content_hash_sidecar_path(output_path)
    if not output_path.exists():
        raise FileNotFoundError("resume requires an existing JSONL output")
    if not sidecar_path.exists():
        raise FileNotFoundError("resume requires an existing content-hash sidecar")

    existing_sidecar = load_content_hash_sidecar(sidecar_path)
    existing_sidecar.require_hash_compatible(content_hash_sidecar)


def _write_rows(
    config: Cluster2RunnerConfig,
    rows: Sequence[Cluster2EvalRow],
    content_hash_sidecar: Cluster2ContentHashSidecar,
) -> None:
    write_cluster2_results_jsonl(
        config.output,
        rows,
        content_hash_sidecar=content_hash_sidecar,
        mode=config.write_mode,
    )


def _default_generation_call(**kwargs: Any) -> dict[str, Any]:
    from cluster2.generation.modal_generate_c2 import generate_source_c2_modal

    return generate_source_c2_modal(**kwargs)


def _default_correctness_call(request: RemoteCorrectnessRequest) -> dict[str, Any]:
    from cluster2.validation.modal_correctness_check import check_remote_correctness

    return check_remote_correctness(request)


def _eval_identity(
    *,
    run_id: str,
    condition: str,
    kernel_class: str,
    kernel_name: str,
    dtype: str,
    base_seed: int,
    attempt_index: int,
) -> EvalIdentity:
    return EvalIdentity(
        run_id=run_id,
        condition=condition,
        source_class=source_class_for_condition(condition),
        generation_mode=generation_mode_for_condition(condition),
        kernel_class=kernel_class,
        kernel_name=kernel_name,
        dtype=dtype,
        sample_index=base_seed,
        base_seed=base_seed,
        attempt_index=attempt_index,
    )


def _build_base_prompt(kernel_class: str, dtype: str) -> str:
    from cluster1.data.kernels import KERNEL_SPECS
    from cluster1.data.prompts.prompt_contract import build_prompt

    return build_prompt(KERNEL_SPECS[kernel_class], dtype)


def _extract_generated_source(payload: dict[str, Any]) -> str:
    source = payload.get("source")
    if not isinstance(source, str) or not source:
        raise ValueError("generation payload must contain non-empty source")
    return source


def _extract_correctness_result_dict(payload: dict[str, Any]) -> dict[str, Any]:
    result = payload.get("correctness_result")
    if not isinstance(result, dict):
        raise RuntimeError("correctness payload did not contain correctness_result")
    return result


def _validate_correctness_identity(
    result: dict[str, Any],
    identity: EvalIdentity,
) -> None:
    result_identity = result.get("identity")
    if not isinstance(result_identity, dict):
        raise ValueError("correctness_result missing identity")
    if EvalIdentity(**result_identity) != identity:
        raise ValueError("correctness_result identity does not match request")


def _generation_hashes_from_payload(
    payload: dict[str, Any],
    *,
    fallback: dict[str, str],
) -> dict[str, str]:
    hashes = payload.get("generation_hashes")
    if hashes is None:
        return dict(fallback)
    if not isinstance(hashes, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in hashes.items()
    ):
        raise ValueError("generation_hashes must be a string mapping")
    return dict(hashes)


def _stable_run_id(config: Cluster2RunnerConfig) -> str:
    payload_dict = config.to_dict()
    payload_dict.pop("write_mode", None)
    payload_dict.pop("output", None)
    payload = json.dumps(payload_dict, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"cluster2-phase11-{digest}"


def _source_sha256(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _assert_replay_route_did_not_generate(
    condition: str,
    stats: _ConditionRunStats,
) -> None:
    if condition in REPLAY_CONTROL_CONDITIONS and stats.generation_calls != 0:
        raise RuntimeError(f"replay condition {condition!r} invoked generation")


def _assert_route_made_progress(
    *,
    condition: str,
    before_rows: int,
    after_rows: int,
    before_failures: int,
    after_failures: int,
) -> None:
    if after_rows > before_rows or after_failures > before_failures:
        return
    raise RuntimeError(f"condition {condition!r} produced no rows or coverage status")


def _require_member(value: str, allowed: Iterable[str], field_name: str) -> None:
    allowed_tuple = tuple(allowed)
    if value not in allowed_tuple:
        raise ValueError(
            f"unsupported {field_name} {value!r}; expected one of: "
            f"{', '.join(allowed_tuple)}"
        )


def _require_dtypes(values: tuple[str, ...]) -> None:
    if not isinstance(values, tuple) or not values:
        raise ValueError("dtypes must not be empty")
    for dtype in values:
        _require_member(dtype, DTYPE_NAMES, "dtype")


def _require_bounded_n(value: int) -> None:
    _require_positive_int(value, "n")
    if value > MAX_CLI_N:
        raise ValueError(f"n must be <= {MAX_CLI_N}")


def _require_positive_int(value: object, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field_name} must be an int")
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")


def _require_non_negative_int(value: object, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field_name} must be an int")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")


def _require_non_negative_float(value: object, field_name: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError(f"{field_name} must be numeric")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")


def _require_non_empty_str(value: object, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value:
        raise ValueError(f"{field_name} must not be empty")


if __name__ == "__main__":
    main()
