"""Local Cluster 3 runner orchestration CLI.

This file is an ordinary argparse runner. It relies on dependency-injected
generation/correctness surfaces in tests and does not define a Cluster 3 Modal
app, image, queue, endpoint, or asynchronous job wrapper.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from cluster2.constants import (
    AGENTIC_TRANSCRIPT_MAX_PROMPT_CHARS_V1,
    DEFAULT_C2_MODAL_EVAL_GPU,
    DEFAULT_C2_MODAL_GENERATION_GPU,
    DEFAULT_MAX_NEW_TOKENS,
    DEFAULT_REPAIR_BUDGET,
    DTYPE_NAMES,
    REPAIR_HISTORY_POLICIES_V1,
    generation_mode_for_condition,
    source_class_for_condition,
)
from cluster2.modal.schemas import EvalIdentity
from cluster3.constants import (
    CLUSTER3_CONDITIONS,
    DEFAULT_P_REPAIR_BUDGET,
    P_FEEDBACK_FORMAT_V1,
    P_HISTORY_POLICY_V1,
    generation_mode_for_cluster3_condition,
    normalize_cluster3_condition,
    source_class_for_cluster3_condition,
)
from cluster3.feedback.c_loop_adapter import (
    Cluster3CLoopResult,
    generated_c_repair_traces,
    run_cluster3_c_loop_from_f2,
)
from cluster3.feedback.compile_error_repair import (
    PRepairEvaluationInput,
    PRepairGenerationInput,
    PRepairLoopResult,
    PSeedAttempt,
    p_compile_repair_succeeded_from_result,
    run_p_repair_loop,
)
from cluster3.feedback.condition_adapters import (
    cluster3_to_cluster2_generation_condition,
)
from cluster3.feedback.dispatcher import dispatch
from cluster3.feedback.trace import build_cluster3_trace_summary
from cluster3.modal.correctness_runner import Cluster3CorrectnessRequest
from cluster3.modal.result_extraction import (
    extract_or_synthesize_cluster3_correctness_result_dict,
)
from cluster3.replay.no_p_pairs import pair_for_condition
from cluster3.results.dataclass import (
    CLUSTER3_RESULTS_SCHEMA_VERSION,
    Cluster3ContentHashSidecar,
    Cluster3EvalRow,
    generated_row,
)
from cluster3.results.logger import Cluster3JsonlAppendLogger
from shared.eval.correctness_shapes import LOCKED_KERNEL_CLASSES, get_shape_metadata
from shared.generation_metadata import (
    GRAMMAR_CLAIM_SCOPE_BY_VARIANT,
    GRAMMAR_PATHS_BY_VARIANT,
    UNKNOWN,
    normalize_immutable_hub_revision,
)
from shared.repair_history.policies import RepairHistoryConfig


MODEL_ID_DEFAULT = "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"
MODEL_REVISION_DEFAULT = "8e8ed243bbe6f9a5aff549a0924562fc719b2b8a"
TOKENIZER_REVISION_DEFAULT = MODEL_REVISION_DEFAULT
GRAMMAR_VARIANT_TASK_AGNOSTIC = "task_agnostic"
CONDITION_SELECTOR_CHOICES: tuple[str, ...] = (*CLUSTER3_CONDITIONS, "all")
KERNEL_CLASS_SELECTOR_CHOICES: tuple[str, ...] = (*LOCKED_KERNEL_CLASSES, "all")
SCALE_TIER_CHOICES: tuple[str, ...] = ("smoke", "development", "paper")
REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTIC_F1_SEED_CONDITIONS: tuple[str, ...] = ("P", "G+P")
DIAGNOSTIC_F2_SEED_CONDITIONS: tuple[str, ...] = ("C+P", "G+C+P")
DIAGNOSTIC_EXPECTED_INITIAL_FAILURES: tuple[str, ...] = (
    "F1_COMPILE",
    "F2_NUMERIC_LARGE",
)

GenerationAdapter = Callable[..., Any]
CorrectnessAdapter = Callable[[Cluster3CorrectnessRequest], Any]
DispatcherAdapter = Callable[..., Any]
PairIdentityValidator = Callable[[Any, Any], None]
ControlResolver = Callable[..., Any]
PRepairLoopCallable = Callable[..., PRepairLoopResult]
CLoopRunnerCallable = Callable[..., Cluster3CLoopResult]


@dataclass(frozen=True)
class Cluster3RunnerConfig:
    """Validated inputs for one local Cluster 3 runner invocation."""

    condition: str
    p_repair_budget: int = DEFAULT_P_REPAIR_BUDGET
    c_repair_budget: int = DEFAULT_REPAIR_BUDGET
    repair_history_policy: str = P_HISTORY_POLICY_V1
    repair_max_prompt_chars: int = AGENTIC_TRANSCRIPT_MAX_PROMPT_CHARS_V1
    repair_include_latest_source: bool = False
    modal_generation_gpu: str = DEFAULT_C2_MODAL_GENERATION_GPU
    modal_eval_gpu: str = DEFAULT_C2_MODAL_EVAL_GPU
    model_id: str = MODEL_ID_DEFAULT
    model_revision: str = MODEL_REVISION_DEFAULT
    tokenizer_revision: str = TOKENIZER_REVISION_DEFAULT
    max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS
    temperature: float = 0.2
    output: str = "outputs/cluster3/cluster3_phase5_runner.jsonl"
    scale_tier: str = "smoke"
    kernel_class: str = "elementwise"
    n: int = 1
    dtypes: tuple[str, ...] = ("fp32",)
    grammar_variant: str = GRAMMAR_VARIANT_TASK_AGNOSTIC
    write_mode: str = "overwrite"
    diagnostic_seed_source: str | None = None
    diagnostic_expected_initial_failure: str | None = None

    def __post_init__(self) -> None:
        _require_member(self.condition, CONDITION_SELECTOR_CHOICES, "condition")
        _require_member(self.kernel_class, KERNEL_CLASS_SELECTOR_CHOICES, "kernel_class")
        _require_member(self.scale_tier, SCALE_TIER_CHOICES, "scale_tier")
        _require_positive_int(self.n, "n")
        _require_non_empty_str(self.model_id, "model_id")
        model_revision = _normalize_required_hub_revision(
            self.model_revision,
            "model_revision",
        )
        tokenizer_revision = _normalize_required_hub_revision(
            self.tokenizer_revision,
            "tokenizer_revision",
        )
        object.__setattr__(self, "model_revision", model_revision)
        object.__setattr__(self, "tokenizer_revision", tokenizer_revision)
        _require_dtypes(self.dtypes)
        _require_non_negative_float(self.temperature, "temperature")
        _require_positive_int(self.max_new_tokens, "max_new_tokens")
        _require_budget(
            self.p_repair_budget,
            DEFAULT_P_REPAIR_BUDGET,
            "p_repair_budget",
        )
        _require_budget(
            self.c_repair_budget,
            DEFAULT_REPAIR_BUDGET,
            "c_repair_budget",
        )
        self.repair_history_config
        if self.modal_generation_gpu != DEFAULT_C2_MODAL_GENERATION_GPU:
            raise ValueError("modal_generation_gpu must match Cluster 2 default L4")
        if self.modal_eval_gpu != DEFAULT_C2_MODAL_EVAL_GPU:
            raise ValueError("modal_eval_gpu must match Cluster 2 default L4")
        _require_member(
            self.grammar_variant,
            tuple(GRAMMAR_PATHS_BY_VARIANT),
            "grammar_variant",
        )
        _require_non_empty_str(self.output, "output")
        _reject_cluster1_cluster2_output(self.output)
        _require_member(self.write_mode, ("overwrite", "resume"), "write_mode")
        _validate_diagnostic_seed_config(self)

    @property
    def conditions(self) -> tuple[str, ...]:
        return expand_condition_selector(self.condition)

    @property
    def kernel_classes(self) -> tuple[str, ...]:
        return expand_kernel_class_selector(self.kernel_class)

    @property
    def repair_history_config(self) -> RepairHistoryConfig:
        return RepairHistoryConfig(
            repair_history_policy=self.repair_history_policy,
            max_prompt_chars=self.repair_max_prompt_chars,
            include_latest_source=self.repair_include_latest_source,
        )

    @classmethod
    def from_namespace(cls, namespace: argparse.Namespace) -> "Cluster3RunnerConfig":
        return cls(
            condition=namespace.condition,
            p_repair_budget=namespace.p_repair_budget,
            c_repair_budget=namespace.c_repair_budget,
            repair_history_policy=namespace.repair_history_policy,
            repair_max_prompt_chars=namespace.repair_max_prompt_chars,
            repair_include_latest_source=namespace.repair_include_latest_source,
            modal_generation_gpu=namespace.modal_generation_gpu,
            modal_eval_gpu=namespace.modal_eval_gpu,
            model_id=namespace.model_id,
            model_revision=namespace.model_revision,
            tokenizer_revision=namespace.tokenizer_revision,
            max_new_tokens=namespace.max_new_tokens,
            temperature=namespace.temperature,
            output=namespace.output,
            scale_tier=namespace.scale_tier,
            kernel_class=namespace.kernel_class,
            n=namespace.n,
            dtypes=parse_dtypes(namespace.dtypes),
            grammar_variant=namespace.grammar_variant,
            write_mode="resume" if namespace.resume else "overwrite",
            diagnostic_seed_source=namespace.diagnostic_seed_source or None,
            diagnostic_expected_initial_failure=(
                namespace.diagnostic_expected_initial_failure or None
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RunnerDependencies:
    """Injectable runtime adapters used by tests and local orchestration."""

    generation: GenerationAdapter | None = None
    correctness: CorrectnessAdapter | None = None
    dispatcher: DispatcherAdapter | None = None
    pair_identity_validator: PairIdentityValidator | None = None
    no_p_control_resolver: ControlResolver | None = None
    p_repair_loop: PRepairLoopCallable | None = None
    c_loop_runner: CLoopRunnerCallable | None = None


@dataclass(frozen=True)
class ConditionRouteAudit:
    condition: str
    route: str
    generation_calls: int
    correctness_calls: int
    p_loop_calls: int
    c_loop_calls: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Cluster3RunResult:
    rows: tuple[Cluster3EvalRow, ...]
    route_audit: tuple[ConditionRouteAudit, ...]
    output: str
    write_mode: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "rows": [row.to_dict() for row in self.rows],
            "route_audit": [audit.to_dict() for audit in self.route_audit],
            "output": self.output,
            "write_mode": self.write_mode,
        }


@dataclass
class _ConditionRunStats:
    generation_calls: int = 0
    correctness_calls: int = 0
    p_loop_calls: int = 0
    c_loop_calls: int = 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_cluster3_modal",
        description="Run local Cluster 3 orchestration.",
    )
    parser.add_argument("--condition", required=True, choices=CONDITION_SELECTOR_CHOICES)
    parser.add_argument(
        "--kernel-class",
        default="elementwise",
        choices=KERNEL_CLASS_SELECTOR_CHOICES,
    )
    parser.add_argument("--scale-tier", default="smoke", choices=SCALE_TIER_CHOICES)
    parser.add_argument("--n", default=1, type=int)
    parser.add_argument("--model-id", default=MODEL_ID_DEFAULT)
    parser.add_argument("--model-revision", default=MODEL_REVISION_DEFAULT)
    parser.add_argument("--tokenizer-revision", default=TOKENIZER_REVISION_DEFAULT)
    parser.add_argument(
        "--grammar-variant",
        default=GRAMMAR_VARIANT_TASK_AGNOSTIC,
        choices=tuple(GRAMMAR_PATHS_BY_VARIANT),
    )
    parser.add_argument("--dtypes", default=",".join(DTYPE_NAMES))
    parser.add_argument("--temperature", default=0.2, type=float)
    parser.add_argument("--max-new-tokens", default=DEFAULT_MAX_NEW_TOKENS, type=int)
    parser.add_argument(
        "--p-repair-budget",
        default=DEFAULT_P_REPAIR_BUDGET,
        type=int,
    )
    parser.add_argument("--c-repair-budget", default=DEFAULT_REPAIR_BUDGET, type=int)
    parser.add_argument(
        "--repair-history-policy",
        default=P_HISTORY_POLICY_V1,
        choices=tuple(sorted(REPAIR_HISTORY_POLICIES_V1)),
    )
    parser.add_argument(
        "--repair-max-prompt-chars",
        default=AGENTIC_TRANSCRIPT_MAX_PROMPT_CHARS_V1,
        type=int,
    )
    parser.add_argument("--repair-include-latest-source", action="store_true")
    parser.add_argument("--modal-generation-gpu", default=DEFAULT_C2_MODAL_GENERATION_GPU)
    parser.add_argument("--modal-eval-gpu", default=DEFAULT_C2_MODAL_EVAL_GPU)
    parser.add_argument("--diagnostic-seed-source", default=None)
    parser.add_argument(
        "--diagnostic-expected-initial-failure",
        default=None,
        choices=DIAGNOSTIC_EXPECTED_INITIAL_FAILURES,
    )
    parser.add_argument("--output", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--overwrite", action="store_true")
    mode.add_argument("--resume", action="store_true")
    return parser


def parse_args(argv: Sequence[str] | None = None) -> Cluster3RunnerConfig:
    namespace = build_arg_parser().parse_args(argv)
    return Cluster3RunnerConfig.from_namespace(namespace)


def main(argv: Sequence[str] | None = None) -> Cluster3RunResult:
    config = parse_args(argv)
    # Seam A (Modal path): open an optional MLflow run around the local
    # orchestration. Modal returns records; the Cluster 3 JSONL writer's seam
    # logs c3.* metrics inside this run. No-op when tracking is disabled.
    from shared import tracking

    with tracking.run_context(
        run_config={
            "scale_tier": getattr(config, "scale_tier", None),
            "model_id": getattr(config, "model_id", None),
        },
        cli_args=config,
        backend="modal",
        cluster="cluster3",
    ):
        result = run_cluster3(config)
    print(
        json.dumps(
            {
                "rows": len(result.rows),
                "route_audit": [audit.to_dict() for audit in result.route_audit],
                "output": result.output,
                "write_mode": result.write_mode,
            },
            sort_keys=True,
        )
    )
    return result


def _modal_entrypoint_argv(
    *,
    condition: str,
    kernel_class: str,
    scale_tier: str,
    n: int,
    model_id: str,
    model_revision: str,
    tokenizer_revision: str,
    grammar_variant: str,
    dtypes: str,
    temperature: float,
    max_new_tokens: int,
    p_repair_budget: int,
    c_repair_budget: int,
    repair_history_policy: str,
    repair_max_prompt_chars: int,
    repair_include_latest_source: bool,
    modal_generation_gpu: str,
    modal_eval_gpu: str,
    diagnostic_seed_source: str | None,
    diagnostic_expected_initial_failure: str | None,
    output: str,
    overwrite: bool,
    resume: bool,
) -> list[str]:
    if overwrite and resume:
        raise ValueError("overwrite and resume are mutually exclusive")
    args = [
        "--condition",
        condition,
        "--kernel-class",
        kernel_class,
        "--scale-tier",
        scale_tier,
        "--n",
        str(n),
        "--model-id",
        model_id,
        "--model-revision",
        model_revision,
        "--tokenizer-revision",
        tokenizer_revision,
        "--grammar-variant",
        grammar_variant,
        "--dtypes",
        dtypes,
        "--temperature",
        str(temperature),
        "--max-new-tokens",
        str(max_new_tokens),
        "--p-repair-budget",
        str(p_repair_budget),
        "--c-repair-budget",
        str(c_repair_budget),
        "--repair-history-policy",
        repair_history_policy,
        "--repair-max-prompt-chars",
        str(repair_max_prompt_chars),
        "--modal-generation-gpu",
        modal_generation_gpu,
        "--modal-eval-gpu",
        modal_eval_gpu,
    ]
    if repair_include_latest_source:
        args.append("--repair-include-latest-source")
    if diagnostic_seed_source:
        args.extend(["--diagnostic-seed-source", diagnostic_seed_source])
    if diagnostic_expected_initial_failure:
        args.extend(
            [
                "--diagnostic-expected-initial-failure",
                diagnostic_expected_initial_failure,
            ]
        )
    args.extend(["--output", output, "--overwrite" if overwrite else "--resume"])
    return args


def modal_entrypoint(
    condition: str,
    kernel_class: str,
    scale_tier: str,
    n: int,
    output: str,
    model_id: str = MODEL_ID_DEFAULT,
    model_revision: str = MODEL_REVISION_DEFAULT,
    tokenizer_revision: str = TOKENIZER_REVISION_DEFAULT,
    grammar_variant: str = GRAMMAR_VARIANT_TASK_AGNOSTIC,
    dtypes: str = ",".join(DTYPE_NAMES),
    temperature: float = 0.2,
    max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS,
    p_repair_budget: int = DEFAULT_P_REPAIR_BUDGET,
    c_repair_budget: int = DEFAULT_REPAIR_BUDGET,
    repair_history_policy: str = P_HISTORY_POLICY_V1,
    repair_max_prompt_chars: int = AGENTIC_TRANSCRIPT_MAX_PROMPT_CHARS_V1,
    repair_include_latest_source: bool = False,
    modal_generation_gpu: str = DEFAULT_C2_MODAL_GENERATION_GPU,
    modal_eval_gpu: str = DEFAULT_C2_MODAL_EVAL_GPU,
    diagnostic_seed_source: str = "",
    diagnostic_expected_initial_failure: str = "",
    overwrite: bool = False,
    resume: bool = False,
) -> None:
    """Modal local entrypoint for running the ordinary Cluster 3 CLI."""

    main(
        _modal_entrypoint_argv(
            condition=condition,
            kernel_class=kernel_class,
            scale_tier=scale_tier,
            n=n,
            model_id=model_id,
            model_revision=model_revision,
            tokenizer_revision=tokenizer_revision,
            grammar_variant=grammar_variant,
            dtypes=dtypes,
            temperature=temperature,
            max_new_tokens=max_new_tokens,
            p_repair_budget=p_repair_budget,
            c_repair_budget=c_repair_budget,
            repair_history_policy=repair_history_policy,
            repair_max_prompt_chars=repair_max_prompt_chars,
            repair_include_latest_source=repair_include_latest_source,
            modal_generation_gpu=modal_generation_gpu,
            modal_eval_gpu=modal_eval_gpu,
            diagnostic_seed_source=diagnostic_seed_source or None,
            diagnostic_expected_initial_failure=(
                diagnostic_expected_initial_failure or None
            ),
            output=output,
            overwrite=overwrite,
            resume=resume,
        )
    )


def _register_modal_local_entrypoint_if_needed() -> None:
    """Expose ``modal run -m`` while preserving cheap normal imports."""

    if "modal" not in sys.modules:
        return

    from shared.modal_harness.app import app as _modal_app
    import cluster2.modal.correctness  # noqa: F401
    import cluster2.modal.generation  # noqa: F401

    globals()["cluster3_modal_entrypoint"] = _modal_app.local_entrypoint(
        name="cluster3_modal_entrypoint"
    )(modal_entrypoint)


_register_modal_local_entrypoint_if_needed()


def run_cluster3(
    config: Cluster3RunnerConfig,
    *,
    dependencies: RunnerDependencies | None = None,
) -> Cluster3RunResult:
    """Run requested Cluster 3 P conditions and append deterministic rows."""

    if not isinstance(config, Cluster3RunnerConfig):
        raise TypeError("config must be Cluster3RunnerConfig")
    deps = dependencies or RunnerDependencies()
    generation = deps.generation or _default_generation_call
    correctness = deps.correctness or _default_correctness_call
    dispatcher = deps.dispatcher or dispatch
    p_repair_loop = deps.p_repair_loop or run_p_repair_loop
    c_loop_runner = deps.c_loop_runner or run_cluster3_c_loop_from_f2
    pair_identity_validator = _resolve_pair_identity_validator(deps)

    rows: list[Cluster3EvalRow] = []
    audits: list[ConditionRouteAudit] = []
    run_id = _stable_run_id(config)
    content_hash_sidecar = _build_runner_content_hash_sidecar(config)
    hashes_by_condition = content_hash_sidecar.generated_condition_hashes

    with Cluster3JsonlAppendLogger(
        config.output,
        content_hash_sidecar=content_hash_sidecar,
        mode=config.write_mode,
        fsync=True,
    ) as result_logger:
        for condition in config.conditions:
            stats = _ConditionRunStats()
            before_rows = len(rows)
            for kernel_class in config.kernel_classes:
                kernel_name = get_shape_metadata(kernel_class).kernel_name
                for dtype in config.dtypes:
                    for base_seed in range(config.n):
                        row = _run_generated_cell(
                            condition=condition,
                            kernel_class=kernel_class,
                            kernel_name=kernel_name,
                            dtype=dtype,
                            base_seed=base_seed,
                            config=config,
                            run_id=run_id,
                            generation=generation,
                            correctness=correctness,
                            dispatcher=dispatcher,
                            p_repair_loop=p_repair_loop,
                            c_loop_runner=c_loop_runner,
                            c3_hashes=hashes_by_condition[condition],
                            stats=stats,
                        )
                        control_row = _resolve_control_row(
                            deps.no_p_control_resolver,
                            row,
                        )
                        if control_row is not None:
                            pair_identity_validator(row, control_row)
                        result_logger.append(row)
                        rows.append(row)
            audits.append(
                ConditionRouteAudit(
                    condition=condition,
                    route=_condition_route(rows[before_rows:]),
                    generation_calls=stats.generation_calls,
                    correctness_calls=stats.correctness_calls,
                    p_loop_calls=stats.p_loop_calls,
                    c_loop_calls=stats.c_loop_calls,
                )
            )

    return Cluster3RunResult(
        rows=tuple(rows),
        route_audit=tuple(audits),
        output=config.output,
        write_mode=config.write_mode,
    )


def expand_condition_selector(selector: str) -> tuple[str, ...]:
    if selector == "all":
        return CLUSTER3_CONDITIONS
    return (normalize_cluster3_condition(selector),)


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


def _run_generated_cell(
    *,
    condition: str,
    kernel_class: str,
    kernel_name: str,
    dtype: str,
    base_seed: int,
    config: Cluster3RunnerConfig,
    run_id: str,
    generation: GenerationAdapter,
    correctness: CorrectnessAdapter,
    dispatcher: DispatcherAdapter,
    p_repair_loop: PRepairLoopCallable,
    c_loop_runner: CLoopRunnerCallable,
    c3_hashes: dict[str, str],
    stats: _ConditionRunStats,
) -> Cluster3EvalRow:
    c2_generation_condition = cluster3_to_cluster2_generation_condition(condition)
    base_prompt = _build_base_prompt(kernel_class, dtype)
    prompt_hash = _sha256(base_prompt)
    initial_seed = base_seed
    diagnostic_source = _read_diagnostic_seed_source(config)
    if diagnostic_source is None:
        generation_payload = generation(
            identity=_c2_generation_identity(
                run_id=run_id,
                condition=c2_generation_condition,
                kernel_class=kernel_class,
                kernel_name=kernel_name,
                dtype=dtype,
                base_seed=base_seed,
                sample_index=base_seed,
                attempt_index=0,
            ),
            prompt=base_prompt,
            model_id=config.model_id,
            model_revision=config.model_revision,
            tokenizer_revision=config.tokenizer_revision,
            generation_seed=initial_seed,
            temperature=config.temperature,
            max_new_tokens=config.max_new_tokens,
            grammar_variant=(
                config.grammar_variant if c2_generation_condition == "G+C" else None
            ),
            modal_generation_gpu=config.modal_generation_gpu,
        )
        stats.generation_calls += 1
        initial_source = _extract_generated_source(generation_payload)
    else:
        generation_payload = {
            "source": diagnostic_source,
            "generation_identity": {"grammar_variant": config.grammar_variant},
        }
        initial_source = diagnostic_source
    initial_identity = _cluster3_identity(
        run_id=run_id,
        condition=condition,
        kernel_class=kernel_class,
        kernel_name=kernel_name,
        dtype=dtype,
        base_seed=base_seed,
        sample_index=base_seed,
        attempt_index=0,
    )
    initial_payload = correctness(
        Cluster3CorrectnessRequest(identity=initial_identity, source=initial_source)
    )
    stats.correctness_calls += 1
    initial_result = _augment_result_identity(
        _canonical_correctness_result(initial_payload, initial_identity),
        generation_seed=initial_seed,
        base_seed=base_seed,
        sample_index=base_seed,
        kernel_class=kernel_class,
        kernel_name=kernel_name,
        dtype=dtype,
        source_hash=_sha256(initial_source),
        prompt_hash=prompt_hash,
    )
    _validate_diagnostic_initial_failure(config, initial_result)
    decision = _dispatch(dispatcher, condition, initial_result)
    p_runtime = _PRuntime()
    p_result: PRepairLoopResult | None = None
    p_terminal_result: Mapping[str, Any] | None = None
    c_result: Cluster3CLoopResult | None = None

    if decision.route == "c_loop":
        c_result = _call_c_loop(
            c_loop_runner=c_loop_runner,
            condition=condition,
            c_loop_source="initial_f2",
            base_prompt=base_prompt,
            base_seed=base_seed,
            sample_index=base_seed,
            kernel_class=kernel_class,
            kernel_name=kernel_name,
            dtype=dtype,
            seed_candidate_source=initial_source,
            seed_candidate_generation_seed=initial_seed,
            seed_candidate_prompt_hash=prompt_hash,
            seed_candidate_prompt_hash_source="initial_prompt",
            seed_candidate_evaluation=initial_result,
            repair_budget=config.c_repair_budget,
            model_config=_model_config(
                config,
                generation=generation,
                correctness=correctness,
            ),
            repair_history_config=config.repair_history_config,
            provenance_base={"run_id": run_id},
            stats=stats,
        )
    elif decision.route == "p_loop":
        seed_attempt = _build_p_seed_attempt(
            source=initial_source,
            generation_seed=initial_seed,
            base_seed=base_seed,
            sample_index=base_seed,
            kernel_class=kernel_class,
            kernel_name=kernel_name,
            dtype=dtype,
            prompt=base_prompt,
            prompt_hash=prompt_hash,
            evaluation_result=initial_result,
        )
        p_result = _run_p_loop(
            p_repair_loop=p_repair_loop,
            condition=condition,
            c2_generation_condition=c2_generation_condition,
            base_prompt=base_prompt,
            base_seed=base_seed,
            sample_index=base_seed,
            kernel_class=kernel_class,
            kernel_name=kernel_name,
            dtype=dtype,
            config=config,
            run_id=run_id,
            generation=generation,
            correctness=correctness,
            seed_attempt=seed_attempt,
            runtime=p_runtime,
            stats=stats,
        )
        p_terminal_result = _terminal_p_result(p_result, p_runtime)
        if (
            p_result.status == "compile_repaired_f2_observed"
            and condition in {"C+P", "G+C+P"}
        ):
            c_result = _call_c_loop(
                c_loop_runner=c_loop_runner,
                condition=condition,
                c_loop_source="post_p_f2",
                base_prompt=base_prompt,
                base_seed=base_seed,
                sample_index=base_seed,
                kernel_class=kernel_class,
                kernel_name=kernel_name,
                dtype=dtype,
                seed_candidate_source=p_result.terminal_source,
                seed_candidate_generation_seed=p_result.terminal_generation_seed,
                seed_candidate_prompt_hash=_p_terminal_prompt_hash(
                    p_result,
                    p_runtime,
                ),
                seed_candidate_prompt_hash_source=(
                    "p_repair_prompt"
                    if _p_terminal_prompt_hash(p_result, p_runtime) is not None
                    else "seed_prompt_unavailable"
                ),
                seed_candidate_evaluation=p_terminal_result,
                repair_budget=config.c_repair_budget,
                model_config=_model_config(
                    config,
                    generation=generation,
                    correctness=correctness,
                ),
                repair_history_config=config.repair_history_config,
                provenance_base={"run_id": run_id},
                stats=stats,
            )

    grammar_metadata = _generation_grammar_metadata_from_payload(
        generation_payload,
        condition=condition,
        config=config,
    )
    return _build_row(
        condition=condition,
        kernel_class=kernel_class,
        kernel_name=kernel_name,
        dtype=dtype,
        base_seed=base_seed,
        initial_source=initial_source,
        initial_generation_seed=initial_seed,
        initial_prompt_hash=prompt_hash,
        initial_result=initial_result,
        p_result=p_result,
        p_terminal_result=p_terminal_result,
        p_runtime=p_runtime,
        c_result=c_result,
        config=config,
        c3_hashes=c3_hashes,
        grammar_metadata=grammar_metadata,
    )


@dataclass
class _PRuntime:
    prompt_hash_by_attempt: dict[int, str] | None = None
    result_by_attempt: dict[int, Mapping[str, Any]] | None = None

    def __post_init__(self) -> None:
        if self.prompt_hash_by_attempt is None:
            self.prompt_hash_by_attempt = {}
        if self.result_by_attempt is None:
            self.result_by_attempt = {}


def _run_p_loop(
    *,
    p_repair_loop: PRepairLoopCallable,
    condition: str,
    c2_generation_condition: str,
    base_prompt: str,
    base_seed: int,
    sample_index: int,
    kernel_class: str,
    kernel_name: str,
    dtype: str,
    config: Cluster3RunnerConfig,
    run_id: str,
    generation: GenerationAdapter,
    correctness: CorrectnessAdapter,
    seed_attempt: PSeedAttempt,
    runtime: _PRuntime,
    stats: _ConditionRunStats,
) -> PRepairLoopResult:
    assert runtime.prompt_hash_by_attempt is not None
    assert runtime.result_by_attempt is not None

    def generation_call(inputs: PRepairGenerationInput) -> str:
        runtime.prompt_hash_by_attempt[inputs.attempt_index] = _sha256(inputs.prompt)
        payload = generation(
            identity=_c2_generation_identity(
                run_id=run_id,
                condition=c2_generation_condition,
                kernel_class=kernel_class,
                kernel_name=kernel_name,
                dtype=dtype,
                base_seed=base_seed,
                sample_index=sample_index,
                attempt_index=inputs.attempt_index,
            ),
            prompt=inputs.prompt,
            model_id=config.model_id,
            model_revision=config.model_revision,
            tokenizer_revision=config.tokenizer_revision,
            generation_seed=inputs.generation_seed,
            temperature=config.temperature,
            max_new_tokens=config.max_new_tokens,
            grammar_variant=(
                config.grammar_variant if c2_generation_condition == "G+C" else None
            ),
            modal_generation_gpu=config.modal_generation_gpu,
        )
        stats.generation_calls += 1
        return _extract_generated_source(payload)

    def evaluation_call(inputs: PRepairEvaluationInput) -> Mapping[str, Any]:
        identity = _cluster3_identity(
            run_id=run_id,
            condition=condition,
            kernel_class=kernel_class,
            kernel_name=kernel_name,
            dtype=dtype,
            base_seed=base_seed,
            sample_index=sample_index,
            attempt_index=inputs.attempt_index,
        )
        payload = correctness(
            Cluster3CorrectnessRequest(identity=identity, source=inputs.source)
        )
        stats.correctness_calls += 1
        result = _augment_result_identity(
            _canonical_correctness_result(payload, identity),
            generation_seed=inputs.generation_seed,
            base_seed=base_seed,
            sample_index=sample_index,
            kernel_class=kernel_class,
            kernel_name=kernel_name,
            dtype=dtype,
            source_hash=_sha256(inputs.source),
            prompt_hash=runtime.prompt_hash_by_attempt.get(inputs.attempt_index),
        )
        runtime.result_by_attempt[inputs.attempt_index] = result
        return result

    stats.p_loop_calls += 1
    return p_repair_loop(
        base_prompt=base_prompt,
        base_seed=base_seed,
        generation=generation_call,
        evaluation=evaluation_call,
        seed_attempt=seed_attempt,
        repair_budget=config.p_repair_budget,
        repair_history_config=config.repair_history_config,
    )


def _call_c_loop(
    *,
    c_loop_runner: CLoopRunnerCallable,
    condition: str,
    c_loop_source: str,
    base_prompt: str,
    base_seed: int,
    sample_index: int,
    kernel_class: str,
    kernel_name: str,
    dtype: str,
    seed_candidate_source: str,
    seed_candidate_generation_seed: int,
    seed_candidate_prompt_hash: str | None,
    seed_candidate_prompt_hash_source: str,
    seed_candidate_evaluation: Mapping[str, Any],
    repair_budget: int,
    model_config: Mapping[str, Any],
    repair_history_config: RepairHistoryConfig,
    provenance_base: Mapping[str, Any],
    stats: _ConditionRunStats,
) -> Cluster3CLoopResult:
    stats.c_loop_calls += 1
    return c_loop_runner(
        outer_c3_condition=condition,
        c_loop_source=c_loop_source,
        base_prompt=base_prompt,
        base_seed=base_seed,
        sample_index=sample_index,
        kernel_class=kernel_class,
        kernel_name=kernel_name,
        dtype=dtype,
        seed_candidate_source=seed_candidate_source,
        seed_candidate_generation_seed=seed_candidate_generation_seed,
        seed_candidate_prompt_hash=seed_candidate_prompt_hash,
        seed_candidate_prompt_hash_source=seed_candidate_prompt_hash_source,
        seed_candidate_evaluation=seed_candidate_evaluation,
        feedback_builder=None,
        repair_budget=repair_budget,
        model_config=model_config,
        repair_history_config=repair_history_config,
        provenance_base=provenance_base,
    )


def _build_row(
    *,
    condition: str,
    kernel_class: str,
    kernel_name: str,
    dtype: str,
    base_seed: int,
    initial_source: str,
    initial_generation_seed: int,
    initial_prompt_hash: str,
    initial_result: Mapping[str, Any],
    p_result: PRepairLoopResult | None,
    p_terminal_result: Mapping[str, Any] | None,
    p_runtime: _PRuntime,
    c_result: Cluster3CLoopResult | None,
    config: Cluster3RunnerConfig,
    c3_hashes: dict[str, str],
    grammar_metadata: dict[str, Any],
) -> Cluster3EvalRow:
    p_attempted = p_result is not None
    p_attempt_count = max(0, p_result.attempts_executed - 1) if p_result else 0
    p_compile_repaired = (
        p_compile_repair_succeeded_from_result(p_result) if p_result else False
    )
    p_terminal_failure = p_result.final_failure_code if p_result else None
    p_prompt_metadata = (
        p_result.terminal_prompt_metadata
        if p_result is not None and p_result.terminal_prompt_metadata is not None
        else None
    )
    p_history_policy = (
        p_prompt_metadata.p_history_policy
        if p_prompt_metadata is not None
        else config.repair_history_config.repair_history_policy
    )
    p_changed = (
        _p_changed_terminal_class("F1_COMPILE", p_terminal_failure)
        if p_result
        else False
    )
    c_loop_fired = c_result is not None
    c_repair_trace = _c_repair_trace_from_result(c_result) if c_result else None

    if c_result is not None:
        final_source = c_result.terminal_source
        final_result = dict(c_result.terminal_correctness_result)
        terminal_source_hash = c_result.terminal_source_hash
        terminal_generation_seed = c_result.terminal_generation_seed
        terminal_prompt_hash = c_result.terminal_prompt_hash
        terminal_prompt_hash_source = c_result.terminal_prompt_hash_source
        if c_result.c_attempt_count > 0:
            terminal_source_stage = "c_attempt"
            terminal_attempt_index = c_result.terminal_attempt_index
        elif c_result.c_loop_source == "post_p_f2" and p_result is not None:
            if p_result.terminal_attempt_index > 0:
                terminal_source_stage = "p_attempt"
                terminal_attempt_index = p_result.terminal_attempt_index
            else:
                terminal_source_stage = "initial"
                terminal_attempt_index = 0
        else:
            terminal_source_stage = "initial"
            terminal_attempt_index = 0
    elif p_result is not None:
        final_source = p_result.terminal_source
        final_result = dict(p_terminal_result or _synthesize_p_terminal_result(p_result))
        terminal_source_hash = p_result.terminal_source_hash
        terminal_generation_seed = p_result.terminal_generation_seed
        if p_result.terminal_attempt_index > 0:
            terminal_source_stage = "p_attempt"
            terminal_attempt_index = p_result.terminal_attempt_index
            terminal_prompt_hash = _p_terminal_prompt_hash(p_result, p_runtime)
            terminal_prompt_hash_source = "p_repair_prompt"
        else:
            terminal_source_stage = "initial"
            terminal_attempt_index = 0
            terminal_prompt_hash = initial_prompt_hash
            terminal_prompt_hash_source = "initial_prompt"
    else:
        final_source = initial_source
        final_result = dict(initial_result)
        terminal_source_hash = _sha256(initial_source)
        terminal_generation_seed = initial_generation_seed
        terminal_source_stage = "initial"
        terminal_attempt_index = 0
        terminal_prompt_hash = initial_prompt_hash
        terminal_prompt_hash_source = "initial_prompt"

    failure_code = _optional_failure_code(final_result.get("failure_code"))
    compile_success = _compile_success_from_result(final_result)
    functional_success = bool(final_result.get("functional_success"))
    repair_set_success = bool(final_result.get("repair_set_success"))
    eval_set_success = bool(final_result.get("eval_set_success"))
    c_terminal_failure = c_result.c_terminal_failure_code if c_result else None
    c_terminal_level = c_result.c_terminal_level_reached if c_result else None
    c_loop_source = c_result.c_loop_source if c_result else "none"

    trace_summary = build_cluster3_trace_summary(
        condition=condition,
        initial_failure_code=_optional_failure_code(initial_result.get("failure_code")),
        final_failure_code=failure_code,
        initial_result=initial_result,
        p_loop_result=p_result,
        c_loop_result=c_result,
        p_loop_fired=p_attempted,
        p_attempt_count=p_attempt_count,
        p_terminal_failure_code=p_terminal_failure,
        p_compile_repair_succeeded=p_compile_repaired,
        c_loop_fired=c_loop_fired,
        c_loop_source=c_loop_source,
        c_attempt_count=len(c_repair_trace or ()),
        c_terminal_failure_code=c_terminal_failure,
        terminal_source_stage=terminal_source_stage,
        terminal_attempt_index=terminal_attempt_index,
        terminal_source_hash=terminal_source_hash,
        terminal_generation_seed=terminal_generation_seed,
        terminal_prompt_hash=terminal_prompt_hash,
        terminal_prompt_hash_source=terminal_prompt_hash_source,
        compile_success=compile_success,
        functional_success=functional_success,
        repair_set_success=repair_set_success,
        eval_set_success=eval_set_success,
        row_source_hash=_sha256(final_source),
        failure_path=_failure_path(
            initial_failure_code=_optional_failure_code(
                initial_result.get("failure_code")
            ),
            p_result=p_result,
            c_result=c_result,
            c_attempt_count=len(c_repair_trace or ()),
        ),
    )
    metadata_overrides = {
        **grammar_metadata,
        "initial_generation_seed": initial_generation_seed,
        "replay_pair_id": _replay_pair_id(condition, kernel_class, dtype, base_seed),
        "replay_control_condition": _metadata_replay_control_condition(condition),
        "replay_base_seed": base_seed,
        "replay_generation_seed": initial_generation_seed,
        "replay_source": "phase5_control_resolver_pending",
        "prompt_sha256": initial_prompt_hash,
        "model_id": config.model_id,
        "model_revision": config.model_revision,
        "tokenizer_revision": config.tokenizer_revision,
        "temperature": config.temperature,
        "max_new_tokens": config.max_new_tokens,
    }
    return generated_row(
        condition=condition,
        attempt_index=terminal_attempt_index or 0,
        kernel_class=kernel_class,
        kernel_name=kernel_name,
        dtype=dtype,
        base_seed=base_seed,
        source_hash=_sha256(final_source),
        grammar_active=condition in {"G+P", "G+C+P"},
        compile_success=compile_success,
        functional_success=functional_success,
        repair_set_success=repair_set_success,
        eval_set_success=eval_set_success,
        failure_code=failure_code,
        trace_summary=trace_summary,
        repair_trace=c_repair_trace if c_loop_fired else None,
        c3_generation_hashes=c3_hashes,
        generation_seed=terminal_generation_seed,
        initial_failure_code=_optional_failure_code(initial_result.get("failure_code")),
        p_repair_attempted=p_attempted,
        p_compile_repair_succeeded=p_compile_repaired,
        p_repair_changed_terminal_class=p_changed,
        p_repair_budget=config.p_repair_budget,
        p_repair_attempt_count=p_attempt_count,
        p_initial_failure_code=p_result.initial_failure_code if p_result else None,
        p_terminal_failure_code=p_terminal_failure,
        c_loop_fired=c_loop_fired,
        c_loop_source=c_loop_source,
        c_terminal_failure_code=c_terminal_failure,
        c_terminal_level_reached=c_terminal_level,
        p_compile_error_class=_p_compile_error_class(initial_result)
        if p_result
        else None,
        p_raw_error_excerpt_sha256=_p_error_excerpt_hash(initial_result)
        if p_result
        else None,
        p_repair_stop_reason=p_result.stop_reason if p_result else "p_not_applicable",
        p_feedback_format=P_FEEDBACK_FORMAT_V1,
        p_history_policy=p_history_policy,
        p_repair_prompt_template_version=(
            p_prompt_metadata.p_repair_prompt_template_version
            if p_prompt_metadata is not None
            else None
        ),
        p_repair_prompt_renderer_version=(
            p_prompt_metadata.p_repair_prompt_renderer_version
            if p_prompt_metadata is not None
            else None
        ),
        p_repair_anchor_attempt_index=(
            p_prompt_metadata.p_repair_anchor_attempt_index
            if p_prompt_metadata is not None
            else None
        ),
        p_repair_latest_attempt_index=(
            p_prompt_metadata.p_repair_latest_attempt_index
            if p_prompt_metadata is not None
            else None
        ),
        p_repair_history_attempt_count=(
            p_prompt_metadata.p_repair_history_attempt_count
            if p_prompt_metadata is not None
            else None
        ),
        p_repair_prompt_sha256=(
            p_prompt_metadata.p_repair_prompt_sha256
            if p_prompt_metadata is not None
            else None
        ),
        p_repair_prompt_char_count=(
            p_prompt_metadata.p_repair_prompt_char_count
            if p_prompt_metadata is not None
            else None
        ),
        p_repair_max_prompt_chars=(
            p_prompt_metadata.p_repair_max_prompt_chars
            if p_prompt_metadata is not None
            else None
        ),
        p_repair_include_latest_source=(
            p_prompt_metadata.p_repair_include_latest_source
            if p_prompt_metadata is not None
            else None
        ),
        p_repair_anchor_source_hash=(
            p_prompt_metadata.p_repair_anchor_source_hash
            if p_prompt_metadata is not None
            else None
        ),
        p_repair_latest_source_hash=(
            p_prompt_metadata.p_repair_latest_source_hash
            if p_prompt_metadata is not None
            else None
        ),
        p_repair_history_summary_sha256=(
            p_prompt_metadata.p_repair_history_summary_sha256
            if p_prompt_metadata is not None
            else None
        ),
        p_repair_history_error_code=(
            p_prompt_metadata.p_repair_history_error_code
            if p_prompt_metadata is not None
            else None
        ),
        p_repair_trace=p_result.attempts if p_result else None,
        terminal_source_stage=terminal_source_stage,
        terminal_generation_seed=terminal_generation_seed,
        terminal_attempt_index=terminal_attempt_index,
        terminal_source_hash=terminal_source_hash,
        terminal_prompt_hash=terminal_prompt_hash,
        terminal_prompt_hash_source=terminal_prompt_hash_source,
        terminal_source_matches_row_source=True,
        **metadata_overrides,
    )


def _build_p_seed_attempt(
    *,
    source: str,
    generation_seed: int,
    base_seed: int,
    sample_index: int,
    kernel_class: str,
    kernel_name: str,
    dtype: str,
    prompt: str,
    prompt_hash: str,
    evaluation_result: Mapping[str, Any],
) -> PSeedAttempt:
    return PSeedAttempt(
        source=source,
        generation_seed=generation_seed,
        base_seed=base_seed,
        sample_index=sample_index,
        kernel_class=kernel_class,
        kernel_name=kernel_name,
        dtype=dtype,
        source_hash=_sha256(source),
        prompt_hash=prompt_hash,
        prompt=prompt,
        evaluation_result=evaluation_result,
        failure_code="F1_COMPILE",
        compile_error=_compile_error_text(evaluation_result),
        compile_error_type=_p_compile_error_class(evaluation_result),
    )


def _terminal_p_result(
    p_result: PRepairLoopResult,
    runtime: _PRuntime,
) -> Mapping[str, Any]:
    assert runtime.result_by_attempt is not None
    result = runtime.result_by_attempt.get(p_result.terminal_attempt_index)
    if result is not None:
        return result
    return _synthesize_p_terminal_result(p_result)


def _synthesize_p_terminal_result(p_result: PRepairLoopResult) -> dict[str, Any]:
    failure_code = p_result.final_failure_code
    functional_success = failure_code is None
    return {
        "failure_code": failure_code,
        "level_reached": p_result.terminal_level_reached,
        "compile_success": p_result.terminal_compile_success,
        "functional_success": functional_success,
        "repair_set_success": functional_success,
        "eval_set_success": functional_success,
    }


def _p_terminal_prompt_hash(
    p_result: PRepairLoopResult,
    runtime: _PRuntime,
) -> str | None:
    assert runtime.prompt_hash_by_attempt is not None
    prompt_hash = runtime.prompt_hash_by_attempt.get(p_result.terminal_attempt_index)
    if prompt_hash is not None:
        return prompt_hash
    terminal_attempt = p_result.attempts[-1]
    return terminal_attempt.feedback_sha256


def _c_repair_trace_from_result(
    c_result: Cluster3CLoopResult | None,
) -> tuple[Any, ...] | None:
    if c_result is None:
        return None
    traces = generated_c_repair_traces(c_result)
    if len(traces) != c_result.c_attempt_count:
        raise ValueError(
            "C repair trace count must match c_attempt_count; "
            f"got {len(traces)} traces for {c_result.c_attempt_count} attempts"
        )
    return traces


def _failure_path(
    *,
    initial_failure_code: str | None,
    p_result: PRepairLoopResult | None,
    c_result: Cluster3CLoopResult | None,
    c_attempt_count: int,
) -> list[str]:
    path = [f"initial:{initial_failure_code or 'success'}"]
    if p_result is not None:
        for attempt in p_result.attempts:
            if attempt.attempt_index == 0:
                continue
            path.append(
                f"p_attempt:{attempt.attempt_index}:{attempt.failure_code or 'success'}"
            )
    if c_result is not None:
        seed_failure = (
            p_result.final_failure_code
            if c_result.c_loop_source == "post_p_f2" and p_result is not None
            else initial_failure_code
        )
        path.append(f"c_seed:{seed_failure or 'success'}")
        for attempt_index in range(1, c_attempt_count + 1):
            failure = (
                c_result.c_terminal_failure_code
                if attempt_index == c_attempt_count
                else "F2_NUMERIC_LARGE"
            )
            path.append(f"c_attempt:{attempt_index}:{failure or 'success'}")
    return path


def _condition_route(rows: Sequence[Cluster3EvalRow]) -> str:
    if any(row.c_loop_fired and row.p_repair_attempted for row in rows):
        return "p_loop_then_c_loop"
    if any(row.c_loop_fired for row in rows):
        return "initial_c_loop"
    if any(row.p_repair_attempted for row in rows):
        return "p_loop"
    return "initial_terminal"


def _resolve_pair_identity_validator(deps: RunnerDependencies) -> PairIdentityValidator:
    if deps.pair_identity_validator is not None:
        return deps.pair_identity_validator
    from cluster3.replay import no_p_pairs

    return no_p_pairs.validate_pair_identity


def _resolve_control_row(resolver: ControlResolver | None, row: Cluster3EvalRow) -> Any:
    if resolver is None:
        return None
    resolver_kwargs = {
        "condition": row.condition,
        "control_condition": pair_for_condition(row.condition),
        "kernel_class": row.kernel_class,
        "kernel_name": row.kernel_name,
        "dtype": row.dtype,
        "base_seed": row.base_seed,
    }
    resolver_signature = inspect.signature(resolver)
    accepts_row = _signature_accepts_call(resolver_signature, row)
    accepts_keywords = _signature_accepts_call(resolver_signature, **resolver_kwargs)
    if accepts_row and accepts_keywords:
        raise TypeError(
            "no_p_control_resolver must unambiguously accept either a single "
            "Cluster3EvalRow argument or the explicit pair identity keyword arguments"
        )
    if accepts_row:
        return resolver(row)
    if accepts_keywords:
        return resolver(
            **resolver_kwargs,
        )
    raise TypeError(
        "no_p_control_resolver must accept either a single Cluster3EvalRow argument "
        "or condition/control_condition/kernel_class/kernel_name/dtype/base_seed keywords"
    )


def _signature_accepts_call(
    resolver_signature: inspect.Signature,
    *args: Any,
    **kwargs: Any,
) -> bool:
    try:
        resolver_signature.bind(*args, **kwargs)
    except TypeError:
        return False
    return True


def _dispatch(
    dispatcher: DispatcherAdapter,
    condition: str,
    result: Mapping[str, Any],
) -> Any:
    return dispatcher(
        condition,
        result.get("failure_code"),
        result.get("level_reached"),
        functional_success=result.get("functional_success"),
    )


def _model_config(
    config: Cluster3RunnerConfig,
    *,
    generation: GenerationAdapter,
    correctness: CorrectnessAdapter,
) -> dict[str, Any]:
    return {
        "generation": generation,
        "correctness": correctness,
        "model_id": config.model_id,
        "model_revision": config.model_revision,
        "tokenizer_revision": config.tokenizer_revision,
        "temperature": config.temperature,
        "max_new_tokens": config.max_new_tokens,
        "grammar_variant": config.grammar_variant,
        "modal_generation_gpu": config.modal_generation_gpu,
    }


def _default_generation_call(**kwargs: Any) -> dict[str, Any]:
    from cluster2.generation.modal_generate_c2 import generate_source_c2_modal

    return generate_source_c2_modal(**kwargs)


def _default_correctness_call(request: Cluster3CorrectnessRequest) -> dict[str, Any]:
    from cluster3.modal.correctness_runner import run_cluster3_correctness

    return run_cluster3_correctness(request)


def _c2_generation_identity(
    *,
    run_id: str,
    condition: str,
    kernel_class: str,
    kernel_name: str,
    dtype: str,
    base_seed: int,
    sample_index: int,
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
        sample_index=sample_index,
        base_seed=base_seed,
        attempt_index=attempt_index,
    )


def _cluster3_identity(
    *,
    run_id: str,
    condition: str,
    kernel_class: str,
    kernel_name: str,
    dtype: str,
    base_seed: int,
    sample_index: int,
    attempt_index: int,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "condition": condition,
        "source_class": source_class_for_cluster3_condition(condition),
        "generation_mode": generation_mode_for_cluster3_condition(condition),
        "kernel_class": kernel_class,
        "kernel_name": kernel_name,
        "dtype": dtype,
        "sample_index": sample_index,
        "base_seed": base_seed,
        "attempt_index": attempt_index,
    }


def _canonical_correctness_result(payload: Any, identity: Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(payload, Mapping) and "correctness_result" not in payload:
        if "failure_code" in payload or "functional_success" in payload:
            result = dict(payload)
            result.setdefault("identity", dict(identity))
            result.setdefault("level_reached", 0)
            result.setdefault("functional_success", False)
            result.setdefault("repair_set_success", False)
            result.setdefault("eval_set_success", False)
            result.setdefault("compile_success", _compile_success_from_result(result))
            return result
    return extract_or_synthesize_cluster3_correctness_result_dict(payload, identity)


def _augment_result_identity(
    result: Mapping[str, Any],
    *,
    generation_seed: int,
    base_seed: int,
    sample_index: int,
    kernel_class: str,
    kernel_name: str,
    dtype: str,
    source_hash: str,
    prompt_hash: str | None,
) -> dict[str, Any]:
    augmented = dict(result)
    augmented.update(
        {
            "generation_seed": generation_seed,
            "base_seed": base_seed,
            "sample_index": sample_index,
            "kernel_class": kernel_class,
            "kernel_name": kernel_name,
            "dtype": dtype,
            "source_hash": source_hash,
            "prompt_hash": prompt_hash,
            "prompt_sha256": prompt_hash,
        }
    )
    return augmented


def _build_base_prompt(kernel_class: str, dtype: str) -> str:
    from cluster1.data.kernels import KERNEL_SPECS
    from cluster1.data.prompts.prompt_contract import build_prompt

    return build_prompt(KERNEL_SPECS[kernel_class], dtype)


def _extract_generated_source(payload: Any) -> str:
    if isinstance(payload, str):
        source = payload
    elif isinstance(payload, Mapping):
        source = payload.get("source")
    else:
        source = getattr(payload, "source", None)
    if not isinstance(source, str) or not source:
        raise ValueError("generation payload must contain non-empty source")
    return source


def _generation_grammar_metadata_from_payload(
    payload: Any,
    *,
    condition: str,
    config: Cluster3RunnerConfig,
) -> dict[str, Any]:
    if condition not in {"G+P", "G+C+P"}:
        return {
            "grammar_variant": None,
            "grammar_path": None,
            "grammar_sha": None,
            "grammar_claim_scope": None,
            "gbnf_parse_valid": None,
            "semantic_valid": None,
            "grammar_valid": None,
            "rejection_layer": None,
            "stop_reason": UNKNOWN,
            "xgrammar_version": UNKNOWN,
            "transformers_version": UNKNOWN,
            "tokenizers_version": UNKNOWN,
            "modal_image_sha": UNKNOWN,
            "generation_metadata_schema_version": 0,
        }
    generation_identity = payload.get("generation_identity") if isinstance(payload, Mapping) else None
    grammar_variant = _field(generation_identity, "grammar_variant") or config.grammar_variant
    return {
        "grammar_variant": grammar_variant,
        "grammar_path": GRAMMAR_PATHS_BY_VARIANT[grammar_variant],
        "grammar_sha": _field(generation_identity, "grammar_sha"),
        "grammar_claim_scope": GRAMMAR_CLAIM_SCOPE_BY_VARIANT[grammar_variant],
        "gbnf_parse_valid": _field(generation_identity, "gbnf_parse_valid"),
        "semantic_valid": _field(generation_identity, "semantic_valid"),
        "grammar_valid": _field(generation_identity, "grammar_valid"),
        "rejection_layer": _field(generation_identity, "rejection_layer"),
        "stop_reason": _field(generation_identity, "stop_reason") or UNKNOWN,
        "xgrammar_version": _field(generation_identity, "xgrammar_version") or UNKNOWN,
        "transformers_version": _field(generation_identity, "transformers_version")
        or UNKNOWN,
        "tokenizers_version": _field(generation_identity, "tokenizers_version")
        or UNKNOWN,
        "modal_image_sha": _field(generation_identity, "modal_image_sha") or UNKNOWN,
        "generation_metadata_schema_version": 0,
    }


def _build_runner_content_hash_sidecar(
    config: Cluster3RunnerConfig,
) -> Cluster3ContentHashSidecar:
    hashes = _collect_cluster3_generation_hashes()
    return Cluster3ContentHashSidecar(
        schema_version=CLUSTER3_RESULTS_SCHEMA_VERSION,
        eval_pipeline_hashes=hashes,
        generated_condition_hashes={
            condition: hashes for condition in config.conditions
        },
        replay_control_hashes={},
        external_pins={
            "model_id": config.model_id,
            "model_revision": config.model_revision,
            "tokenizer_revision": config.tokenizer_revision,
        },
    )


def _collect_cluster3_generation_hashes() -> dict[str, str]:
    paths = (
        "cluster3/experiments/run_cluster3_modal.py",
        "cluster3/feedback/c_loop_adapter.py",
        "cluster3/feedback/compile_error_repair.py",
        "cluster3/feedback/condition_adapters.py",
        "cluster3/feedback/dispatcher.py",
        "cluster3/modal/correctness_runner.py",
        "cluster3/modal/result_extraction.py",
        "cluster3/results/dataclass.py",
        "cluster3/results/logger.py",
    )
    return {
        path: _file_sha256(REPO_ROOT / path)
        for path in paths
        if (REPO_ROOT / path).exists()
    }


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _compile_success_from_result(result: Mapping[str, Any]) -> bool:
    value = result.get("compile_success")
    if isinstance(value, bool):
        return value
    if result.get("functional_success") is True:
        return True
    failure_code = result.get("failure_code")
    if isinstance(failure_code, str):
        if failure_code.startswith(("F0_", "F1_")):
            return False
        if failure_code.startswith("F2_"):
            return True
    level_reached = result.get("level_reached")
    if isinstance(level_reached, int) and not isinstance(level_reached, bool):
        return level_reached >= 2
    return False


def _compile_error_text(result: Mapping[str, Any]) -> str | None:
    value = result.get("compile_error") or result.get("compile_error_excerpt")
    return value if isinstance(value, str) and value else None


def _p_compile_error_class(result: Mapping[str, Any]) -> str | None:
    value = result.get("compile_error_type") or result.get("error_type")
    return value if isinstance(value, str) and value else None


def _p_error_excerpt_hash(result: Mapping[str, Any]) -> str:
    text = _compile_error_text(result) or _p_compile_error_class(result)
    if not text:
        raise ValueError("active P rows require compile-error text or class")
    return _sha256(text)


def _optional_failure_code(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("failure_code must be a string when present")
    return value


def _p_changed_terminal_class(
    p_initial_failure_code: str | None,
    p_terminal_failure_code: str | None,
) -> bool:
    return (
        p_initial_failure_code != p_terminal_failure_code
        or (p_initial_failure_code is not None and p_terminal_failure_code is None)
    )


def _replay_pair_id(
    condition: str,
    kernel_class: str,
    dtype: str,
    base_seed: int,
) -> str:
    return f"{condition}:{kernel_class}:{dtype}:{base_seed}"


def _metadata_replay_control_condition(condition: str) -> str | None:
    paired = pair_for_condition(condition)
    return paired if paired in {"none", "G"} else None


def _stable_run_id(config: Cluster3RunnerConfig) -> str:
    payload = json.dumps(config.to_dict(), sort_keys=True, separators=(",", ":"))
    return "cluster3-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _read_diagnostic_seed_source(config: Cluster3RunnerConfig) -> str | None:
    if config.diagnostic_seed_source is None:
        return None
    return (REPO_ROOT / config.diagnostic_seed_source).read_text(encoding="utf-8")


def _validate_diagnostic_initial_failure(
    config: Cluster3RunnerConfig,
    result: Mapping[str, Any],
) -> None:
    expected = config.diagnostic_expected_initial_failure
    if expected is None:
        return
    actual = _optional_failure_code(result.get("failure_code"))
    if actual != expected:
        rendered = actual or "success"
        raise RuntimeError(
            "diagnostic seed expected initial failure "
            f"{expected}; got {rendered}"
        )


def _validate_diagnostic_seed_config(config: Cluster3RunnerConfig) -> None:
    seed_source = config.diagnostic_seed_source
    expected = config.diagnostic_expected_initial_failure
    if seed_source is None and expected is None:
        return
    if seed_source is None or expected is None:
        raise ValueError(
            "diagnostic_seed_source and diagnostic_expected_initial_failure "
            "must be provided together"
        )
    _require_member(
        expected,
        DIAGNOSTIC_EXPECTED_INITIAL_FAILURES,
        "diagnostic_expected_initial_failure",
    )
    if expected == "F1_COMPILE":
        allowed_conditions = DIAGNOSTIC_F1_SEED_CONDITIONS
        max_n = 2
        condition_message = (
            "diagnostic_seed_source for F1_COMPILE is allowed only for condition P or G+P"
        )
    else:
        allowed_conditions = DIAGNOSTIC_F2_SEED_CONDITIONS
        max_n = 1
        condition_message = (
            "diagnostic_seed_source for F2_NUMERIC_LARGE is allowed only for condition "
            "C+P or G+C+P"
        )
    if config.condition not in allowed_conditions:
        raise ValueError(condition_message)
    if config.scale_tier != "smoke":
        raise ValueError("diagnostic_seed_source is allowed only for smoke scale_tier")
    if config.n > max_n:
        raise ValueError(
            f"diagnostic_seed_source for {expected} requires n <= {max_n}"
        )
    if config.kernel_class == "all":
        raise ValueError("diagnostic_seed_source requires one kernel_class")
    if len(config.dtypes) != 1:
        raise ValueError("diagnostic_seed_source requires exactly one dtype")
    relative_source = _resolve_repo_relative_file(seed_source, "diagnostic_seed_source")
    object.__setattr__(
        config,
        "diagnostic_seed_source",
        relative_source.as_posix(),
    )


def _resolve_repo_relative_file(value: str, field_name: str) -> Path:
    _require_non_empty_str(value, field_name)
    candidate = Path(value)
    resolved = (
        candidate.resolve()
        if candidate.is_absolute()
        else (REPO_ROOT / candidate).resolve()
    )
    try:
        relative = resolved.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise ValueError(f"{field_name} must resolve under the repository root") from exc
    if not resolved.is_file():
        raise ValueError(f"{field_name} must point to an existing file")
    return relative


def _normalize_required_hub_revision(value: str | None, field_name: str) -> str:
    revision = normalize_immutable_hub_revision(value, field_name=field_name)
    if revision is None:
        raise ValueError(f"{field_name} must be a non-empty immutable Hub revision")
    return revision


def _require_budget(value: int, maximum: int, field_name: str) -> None:
    _require_non_negative_int(value, field_name)
    if value > maximum:
        raise ValueError(f"{field_name} must be <= {maximum}")


def _require_dtypes(values: tuple[str, ...]) -> None:
    if not isinstance(values, tuple) or not values:
        raise ValueError("dtypes must be a non-empty tuple")
    for value in values:
        _require_member(value, DTYPE_NAMES, "dtype")


def _require_member(value: Any, choices: Sequence[str], field_name: str) -> None:
    if value not in choices:
        allowed = ", ".join(choices)
        raise ValueError(f"{field_name} must be one of: {allowed}; got {value!r}")


def _require_non_empty_str(value: Any, field_name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_positive_int(value: Any, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field_name} must be an int")
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")


def _require_non_negative_int(value: Any, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field_name} must be an int")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")


def _require_non_negative_float(value: Any, field_name: str) -> None:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise TypeError(f"{field_name} must be numeric")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")


def _reject_cluster1_cluster2_output(output: str) -> None:
    path = Path(output)
    parts = path.parts
    for cluster_name in ("cluster1", "cluster2"):
        if "outputs" in parts and cluster_name in parts:
            raise ValueError("Cluster 3 output must not be under outputs/cluster1 or outputs/cluster2")


def _field(container: Any, field_name: str) -> Any:
    if isinstance(container, Mapping):
        return container.get(field_name)
    return getattr(container, field_name, None)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


__all__ = [
    "Cluster3RunResult",
    "Cluster3RunnerConfig",
    "RunnerDependencies",
    "build_arg_parser",
    "main",
    "modal_entrypoint",
    "parse_args",
    "run_cluster3",
]


if __name__ == "__main__":
    main()
