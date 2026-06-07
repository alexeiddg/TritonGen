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
import os
import subprocess
import sys
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
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
    CLUSTER3_C_ACTIVE_CONDITIONS,
    CLUSTER3_CONDITIONS,
    CLUSTER3_G_ACTIVE_CONDITIONS,
    CLUSTER3_P_ACTIVE_CONDITIONS,
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
from cluster3.planning.grammar_mode_matrix import (
    L1A_EXPERIMENT_ID,
    L1A_GRAMMAR_MODE_CP_SELECTOR,
    L1A_OUTPUT_ROOT,
    L1A_OBSERVABILITY_ROOT,
    L1A_PATH_COLLISION_POLICY,
    L1A_RUN_ID_PREFIX,
    L1A_EXECUTABLE_SELECTOR_SUPPORT_STATUS,
    L1A_SIGNED_AUTHORIZATION_PLACEHOLDER,
    L1B_OUTPUT_ROOT,
    L1B_OBSERVABILITY_ROOT,
    L1B_RUN_ID_PREFIX,
    L1B_SIGNED_AUTHORIZATION_PLACEHOLDER,
    L2_EXECUTABLE_SELECTOR_SUPPORT_STATUS,
    L2B_EXECUTABLE_SELECTOR_SUPPORT_STATUS,
    L2B_N2_EXECUTABLE_SELECTOR_SUPPORT_STATUS,
    L2B_N20_OBSERVABILITY_ROOT,
    L2B_N20_OUTPUT_ROOT,
    L2B_N20_RUN_ID_PREFIX,
    L2B_N20_SELECTOR_PROFILE_ID,
    L2B_N2_OBSERVABILITY_ROOT,
    L2B_N2_OUTPUT_ROOT,
    L2B_N2_RUN_ID_PREFIX,
    L2B_N2_SELECTOR_PROFILE_ID,
    L2B_N2_SIGNATURE_STATUS,
    L2B_N2_SIGNED_AUTHORIZATION_TOKEN,
    L2B_SIGNED_AUTHORIZATION_PLACEHOLDER,
    L2_OUTPUT_ROOT,
    L2_OBSERVABILITY_ROOT,
    L2_RUN_ID_PREFIX,
    L2_SIGNED_AUTHORIZATION_PLACEHOLDER,
    GrammarModeLauncherCellPlan,
    L2BFullCoverageShardPlan,
    build_l1a_launcher_dry_plan,
    build_l1a_launcher_executable_plan,
    build_l2b_full_coverage_shard_plan,
    l1a_grammar_mode_cell_selector_choices,
    l2b_full_coverage_shard_ids,
    l2b_full_coverage_stage_choices,
    l2b_full_coverage_stage_spec,
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
from shared.observability import (
    ObservabilityArtifactIdentity,
    ObservabilityAttemptIdentity,
    ObservabilityCostEstimate,
    ObservabilityErrorSummary,
    ObservabilityEvent,
    ObservabilityJsonlAppendLogger,
    ObservabilityModalContext,
    ObservabilityPaths,
    ObservabilityRowIdentity,
    ObservabilitySummary,
    ObservabilityTokenCounts,
    file_sha256,
    load_observability_events,
    resolve_observability_paths,
)
from shared.observability.logger import (
    estimated_cost_summary as observability_estimated_cost_summary,
    event_counts as observability_event_counts,
    stage_durations_ns as observability_stage_durations_ns,
    token_totals as observability_token_totals,
)
from shared.modal_harness.runtime import (
    get_modal_runtime_context_or_unavailable,
    normalize_modal_context,
)
from shared.repair_history.policies import RepairHistoryConfig


MODEL_ID_DEFAULT = "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"
MODEL_REVISION_DEFAULT = "8e8ed243bbe6f9a5aff549a0924562fc719b2b8a"
TOKENIZER_REVISION_DEFAULT = MODEL_REVISION_DEFAULT
GRAMMAR_VARIANT_TASK_AGNOSTIC = "task_agnostic"
CONDITION_SELECTOR_CHOICES: tuple[str, ...] = (
    *CLUSTER3_CONDITIONS,
    "all",
    L1A_GRAMMAR_MODE_CP_SELECTOR,
)
KERNEL_CLASS_SELECTOR_CHOICES: tuple[str, ...] = (*LOCKED_KERNEL_CLASSES, "all")
SCALE_TIER_CHOICES: tuple[str, ...] = ("smoke", "development", "paper")
REPO_ROOT = Path(__file__).resolve().parents[2]
CLUSTER3_RUNNER_PATH = "cluster3/experiments/run_cluster3_modal.py"
OBSERVABILITY_MODE_CHOICES: tuple[str, ...] = ("off", "best_effort", "required")
L1A_DRY_PLAN_PLACEHOLDER_OUTPUT = f"{L1A_OUTPUT_ROOT}/__dry_plan__.jsonl"
L1A_EXECUTION_SELECTOR_PLACEHOLDER_OUTPUT = f"{L1A_OUTPUT_ROOT}/__selector__.jsonl"
L1A_SIGNED_AUTHORIZATION_TOKEN = (
    "FULL_PIPELINE_GRAMMAR_MODE_CP_L1A_N1_AUTHORIZATION_PACKET_V1"
)
L1B_EXECUTION_SELECTOR_PLACEHOLDER_OUTPUT = f"{L1B_OUTPUT_ROOT}/__selector__.jsonl"
L1B_SIGNED_AUTHORIZATION_TOKEN = (
    "FULL_PIPELINE_GRAMMAR_MODE_CP_L1B_N5_AUTHORIZATION_GOAL_20260606"
)
L2_DRY_PLAN_PLACEHOLDER_OUTPUT = f"{L2_OUTPUT_ROOT}/__dry_plan__.jsonl"
L2_EXECUTION_SELECTOR_PLACEHOLDER_OUTPUT = f"{L2_OUTPUT_ROOT}/__selector__.jsonl"
L2_SIGNED_AUTHORIZATION_TOKEN = (
    "FULL_PIPELINE_GRAMMAR_MODE_CP_L2_N20_AUTHORIZATION_PACKET_V1"
)
L2B_N2_DRY_PLAN_PLACEHOLDER_OUTPUT = f"{L2B_N2_OUTPUT_ROOT}/__dry_plan__.jsonl"
L2B_N2_EXECUTION_SELECTOR_PLACEHOLDER_OUTPUT = (
    f"{L2B_N2_OUTPUT_ROOT}/__selector__.jsonl"
)
L2B_N20_DRY_PLAN_PLACEHOLDER_OUTPUT = f"{L2B_N20_OUTPUT_ROOT}/__dry_plan__.jsonl"
L2B_N20_EXECUTION_SELECTOR_PLACEHOLDER_OUTPUT = (
    f"{L2B_N20_OUTPUT_ROOT}/__selector__.jsonl"
)
DIAGNOSTIC_F1_SEED_CONDITIONS: tuple[str, ...] = ("P", "G+P")
DIAGNOSTIC_F2_SEED_CONDITIONS: tuple[str, ...] = ("C+P", "G+C+P")
DIAGNOSTIC_EXPECTED_INITIAL_FAILURES: tuple[str, ...] = (
    "F1_COMPILE",
    "F2_NUMERIC_LARGE",
)
L2B_N2_SIGNED_WALL_CLOCK_SECONDS_PER_CELL = 1800.0

GenerationAdapter = Callable[..., Any]
CorrectnessAdapter = Callable[[Cluster3CorrectnessRequest], Any]
DispatcherAdapter = Callable[..., Any]
PairIdentityValidator = Callable[[Any, Any], None]
ControlResolver = Callable[..., Any]
PRepairLoopCallable = Callable[..., PRepairLoopResult]
CLoopRunnerCallable = Callable[..., Cluster3CLoopResult]
ObservabilityLoggerFactory = Callable[..., ObservabilityJsonlAppendLogger]
ModalContextProvider = Callable[[], Mapping[str, Any] | ObservabilityModalContext | None]
TokenCountsProvider = Callable[
    [Mapping[str, Any]], Mapping[str, Any] | ObservabilityTokenCounts | None
]
CostEstimateProvider = Callable[
    [Mapping[str, Any]], Mapping[str, Any] | ObservabilityCostEstimate | None
]


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
    observability_mode: str = "off"
    observability_experiment_id: str | None = None
    observability_run_id: str | None = None
    observability_output: str | None = None
    scale_tier: str = "smoke"
    kernel_class: str = "elementwise"
    n: int = 1
    dtypes: tuple[str, ...] = ("fp32",)
    grammar_variant: str = GRAMMAR_VARIANT_TASK_AGNOSTIC
    write_mode: str = "overwrite"
    dry_plan: bool = False
    execution_plan: bool = False
    grammar_mode_cell: str = "all"
    l2b_stage: str | None = None
    l2b_shard_selector: str = "all"
    signed_l1a_authorization: str | None = None
    diagnostic_seed_source: str | None = None
    diagnostic_expected_initial_failure: str | None = None

    def __post_init__(self) -> None:
        _require_member(self.condition, CONDITION_SELECTOR_CHOICES, "condition")
        _require_member(
            self.grammar_mode_cell,
            l1a_grammar_mode_cell_selector_choices(),
            "grammar_mode_cell",
        )
        if self.dry_plan and self.execution_plan:
            raise ValueError("dry_plan and execution_plan are mutually exclusive")
        if self.l2b_stage is not None:
            _require_member(
                self.l2b_stage,
                l2b_full_coverage_stage_choices(),
                "l2b_stage",
            )
            stage = l2b_full_coverage_stage_spec(self.l2b_stage)
            if self.condition != L1A_GRAMMAR_MODE_CP_SELECTOR:
                raise ValueError(
                    "--l2b-stage is only supported for "
                    f"--condition {L1A_GRAMMAR_MODE_CP_SELECTOR}"
                )
            if self.scale_tier != stage.scale_tier:
                raise ValueError(
                    f"{self.l2b_stage} requires --scale-tier {stage.scale_tier}"
                )
            if self.n != stage.n:
                raise ValueError(f"{self.l2b_stage} requires --n {stage.n}")
            if (
                self.l2b_shard_selector != "all"
                and not self.l2b_shard_selector.startswith("wave:")
                and self.l2b_shard_selector not in l2b_full_coverage_shard_ids()
            ):
                allowed = ", ".join(
                    ("all", *l2b_full_coverage_shard_ids(), "wave:<start>:<count>")
                )
                raise ValueError(
                    "l2b_shard_selector must be one of: "
                    f"{allowed}; got {self.l2b_shard_selector!r}"
                )
        elif self.l2b_shard_selector != "all":
            raise ValueError("--l2b-shard-selector requires --l2b-stage")
        if (
            (self.dry_plan or self.execution_plan)
            and self.condition != L1A_GRAMMAR_MODE_CP_SELECTOR
        ):
            raise ValueError(
                "--dry-plan and --execution-plan are only supported for "
                f"--condition {L1A_GRAMMAR_MODE_CP_SELECTOR}"
            )
        if self.condition != L1A_GRAMMAR_MODE_CP_SELECTOR:
            if self.grammar_mode_cell != "all":
                raise ValueError(
                    "--grammar-mode-cell is only supported for "
                    f"--condition {L1A_GRAMMAR_MODE_CP_SELECTOR}"
                )
            if self.signed_l1a_authorization is not None:
                raise ValueError(
                    "signed selector authorization is only supported for "
                    f"--condition {L1A_GRAMMAR_MODE_CP_SELECTOR}"
                )
        if self.signed_l1a_authorization is not None:
            _require_non_empty_str(
                self.signed_l1a_authorization,
                "signed_l1a_authorization",
            )
        if (
            self.condition == L1A_GRAMMAR_MODE_CP_SELECTOR
            and not self.dry_plan
            and not self.execution_plan
            and self.signed_l1a_authorization is None
        ):
            raise ValueError(
                f"{L1A_GRAMMAR_MODE_CP_SELECTOR} execution requires "
                "--signed-l1a-authorization, --signed-l1b-authorization, or "
                "--signed-l2-authorization, or --signed-l2b-authorization; "
                "use --dry-plan or --execution-plan for local no-execution "
                "planning"
            )
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
        _require_member(
            self.write_mode,
            ("overwrite", "resume", "dry_plan", "execution_plan"),
            "write_mode",
        )
        if self.dry_plan and self.write_mode != "dry_plan":
            raise ValueError("dry_plan configs require write_mode='dry_plan'")
        if self.execution_plan and self.write_mode != "execution_plan":
            raise ValueError(
                "execution_plan configs require write_mode='execution_plan'"
            )
        if not self.dry_plan and self.write_mode == "dry_plan":
            raise ValueError("write_mode='dry_plan' requires dry_plan=True")
        if not self.execution_plan and self.write_mode == "execution_plan":
            raise ValueError("write_mode='execution_plan' requires execution_plan=True")
        _validate_observability_config(self)
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
            output=_output_from_namespace(namespace),
            observability_mode=namespace.observability_mode,
            observability_experiment_id=namespace.observability_experiment_id,
            observability_run_id=namespace.observability_run_id,
            observability_output=namespace.observability_output,
            scale_tier=namespace.scale_tier,
            kernel_class=namespace.kernel_class,
            n=namespace.n,
            dtypes=parse_dtypes(namespace.dtypes),
            grammar_variant=namespace.grammar_variant,
            write_mode=(
                "dry_plan"
                if namespace.dry_plan
                else "execution_plan"
                if namespace.execution_plan
                else "resume"
                if namespace.resume
                else "overwrite"
            ),
            dry_plan=namespace.dry_plan,
            execution_plan=namespace.execution_plan,
            grammar_mode_cell=namespace.grammar_mode_cell,
            l2b_stage=namespace.l2b_stage or None,
            l2b_shard_selector=namespace.l2b_shard_selector,
            signed_l1a_authorization=namespace.signed_l1a_authorization or None,
            diagnostic_seed_source=namespace.diagnostic_seed_source or None,
            diagnostic_expected_initial_failure=(
                namespace.diagnostic_expected_initial_failure or None
            ),
        )

    def to_dict(self, *, include_observability: bool = True) -> dict[str, Any]:
        payload = asdict(self)
        if not include_observability:
            for key in (
                "observability_mode",
                "observability_experiment_id",
                "observability_run_id",
                "observability_output",
                "signed_l1a_authorization",
            ):
                payload.pop(key, None)
        return payload


@dataclass(frozen=True)
class _GrammarModeSelectorProfile:
    profile_id: str
    label: str
    signed_authorization_token: str | None
    signed_authorization_placeholder: str
    signed_authorization_option: str | None
    output_root: str
    observability_root: str
    run_id_prefix: str
    selector_placeholder_output: str
    scale_tier: str
    n: int
    expected_planned_rows: int
    kernel_class_selector: str = "elementwise"
    dtypes: tuple[str, ...] = ("fp32",)
    runtime_execution_enabled: bool = True
    runtime_block_reason: str | None = None
    support_status: str = L1A_EXECUTABLE_SELECTOR_SUPPORT_STATUS


L1A_SELECTOR_PROFILE = _GrammarModeSelectorProfile(
    profile_id="l1a_n1_grammar_mode_cp",
    label="L1a n=1 smoke",
    signed_authorization_token=L1A_SIGNED_AUTHORIZATION_TOKEN,
    signed_authorization_placeholder=L1A_SIGNED_AUTHORIZATION_PLACEHOLDER,
    signed_authorization_option="--signed-l1a-authorization",
    output_root=L1A_OUTPUT_ROOT,
    observability_root=L1A_OBSERVABILITY_ROOT,
    run_id_prefix=L1A_RUN_ID_PREFIX,
    selector_placeholder_output=L1A_EXECUTION_SELECTOR_PLACEHOLDER_OUTPUT,
    scale_tier="smoke",
    n=1,
    expected_planned_rows=12,
)
L1B_SELECTOR_PROFILE = _GrammarModeSelectorProfile(
    profile_id="l1b_n5_grammar_mode_cp",
    label="L1b n=5 development",
    signed_authorization_token=L1B_SIGNED_AUTHORIZATION_TOKEN,
    signed_authorization_placeholder=L1B_SIGNED_AUTHORIZATION_PLACEHOLDER,
    signed_authorization_option="--signed-l1b-authorization",
    output_root=L1B_OUTPUT_ROOT,
    observability_root=L1B_OBSERVABILITY_ROOT,
    run_id_prefix=L1B_RUN_ID_PREFIX,
    selector_placeholder_output=L1B_EXECUTION_SELECTOR_PLACEHOLDER_OUTPUT,
    scale_tier="development",
    n=5,
    expected_planned_rows=60,
)
L2_SELECTOR_PROFILE = _GrammarModeSelectorProfile(
    profile_id="l2_n20_grammar_mode_cp",
    label="L2 n=20 paper",
    signed_authorization_token=L2_SIGNED_AUTHORIZATION_TOKEN,
    signed_authorization_placeholder=L2_SIGNED_AUTHORIZATION_PLACEHOLDER,
    signed_authorization_option="--signed-l2-authorization",
    output_root=L2_OUTPUT_ROOT,
    observability_root=L2_OBSERVABILITY_ROOT,
    run_id_prefix=L2_RUN_ID_PREFIX,
    selector_placeholder_output=L2_EXECUTION_SELECTOR_PLACEHOLDER_OUTPUT,
    scale_tier="paper",
    n=20,
    expected_planned_rows=240,
    support_status=L2_EXECUTABLE_SELECTOR_SUPPORT_STATUS,
)
L2B_N2_SELECTOR_PROFILE = _GrammarModeSelectorProfile(
    profile_id=L2B_N2_SELECTOR_PROFILE_ID,
    label="L2b-2 n=2 sharded full coverage signed runtime gate",
    signed_authorization_token=L2B_N2_SIGNED_AUTHORIZATION_TOKEN,
    signed_authorization_placeholder=L2B_N2_SIGNED_AUTHORIZATION_TOKEN,
    signed_authorization_option="--signed-l2b-authorization",
    output_root=L2B_N2_OUTPUT_ROOT,
    observability_root=L2B_N2_OBSERVABILITY_ROOT,
    run_id_prefix=L2B_N2_RUN_ID_PREFIX,
    selector_placeholder_output=L2B_N2_EXECUTION_SELECTOR_PLACEHOLDER_OUTPUT,
    scale_tier="development",
    n=2,
    expected_planned_rows=216,
    kernel_class_selector="all",
    dtypes=DTYPE_NAMES,
    runtime_execution_enabled=True,
    runtime_block_reason=None,
    support_status=L2B_N2_EXECUTABLE_SELECTOR_SUPPORT_STATUS,
)
L2B_N20_SELECTOR_PROFILE = _GrammarModeSelectorProfile(
    profile_id=L2B_N20_SELECTOR_PROFILE_ID,
    label="L2b-4 n=20 sharded full coverage unsigned blocked plan",
    signed_authorization_token=None,
    signed_authorization_placeholder=L2B_SIGNED_AUTHORIZATION_PLACEHOLDER,
    signed_authorization_option="--signed-l2b-authorization",
    output_root=L2B_N20_OUTPUT_ROOT,
    observability_root=L2B_N20_OBSERVABILITY_ROOT,
    run_id_prefix=L2B_N20_RUN_ID_PREFIX,
    selector_placeholder_output=L2B_N20_EXECUTION_SELECTOR_PLACEHOLDER_OUTPUT,
    scale_tier="paper",
    n=20,
    expected_planned_rows=2160,
    kernel_class_selector="all",
    dtypes=DTYPE_NAMES,
    runtime_execution_enabled=False,
    runtime_block_reason=(
        "L2b-4 is unsigned and blocked until L2b-2 completes and validates"
    ),
    support_status=L2B_EXECUTABLE_SELECTOR_SUPPORT_STATUS,
)
SELECTOR_PROFILES: tuple[_GrammarModeSelectorProfile, ...] = (
    L1A_SELECTOR_PROFILE,
    L1B_SELECTOR_PROFILE,
    L2_SELECTOR_PROFILE,
    L2B_N2_SELECTOR_PROFILE,
    L2B_N20_SELECTOR_PROFILE,
)


def _output_from_namespace(namespace: argparse.Namespace) -> str:
    if namespace.output is not None:
        return namespace.output
    if namespace.dry_plan:
        if namespace.condition == L1A_GRAMMAR_MODE_CP_SELECTOR:
            if namespace.l2b_stage:
                profile = _l2b_selector_profile_for_stage(namespace.l2b_stage)
                return f"{profile.output_root}/__dry_plan__.jsonl"
            profile = _selector_profile_for_namespace(
                scale_tier=namespace.scale_tier,
                n=namespace.n,
                kernel_class=namespace.kernel_class,
                dtypes=parse_dtypes(namespace.dtypes),
            )
            return f"{profile.output_root}/__dry_plan__.jsonl"
        return L1A_DRY_PLAN_PLACEHOLDER_OUTPUT
    if namespace.condition == L1A_GRAMMAR_MODE_CP_SELECTOR:
        if namespace.l2b_stage:
            return _l2b_selector_profile_for_stage(
                namespace.l2b_stage
            ).selector_placeholder_output
        signed_authorization = getattr(namespace, "signed_l1a_authorization", None)
        if signed_authorization:
            for profile in SELECTOR_PROFILES:
                if (
                    profile.signed_authorization_token is not None
                    and signed_authorization == profile.signed_authorization_token
                ):
                    return profile.selector_placeholder_output
        return _selector_profile_for_namespace(
            scale_tier=namespace.scale_tier,
            n=namespace.n,
            kernel_class=namespace.kernel_class,
            dtypes=parse_dtypes(namespace.dtypes),
        ).selector_placeholder_output
    return ""


def _selector_profile_for_config(
    config: Cluster3RunnerConfig,
) -> _GrammarModeSelectorProfile:
    if config.l2b_stage is not None:
        return _l2b_selector_profile_for_stage(config.l2b_stage)
    return _selector_profile_for_namespace(
        scale_tier=config.scale_tier,
        n=config.n,
        kernel_class=config.kernel_class,
        dtypes=config.dtypes,
    )


def _selector_profile_for_namespace(
    *,
    scale_tier: str,
    n: int,
    kernel_class: str,
    dtypes: tuple[str, ...],
) -> _GrammarModeSelectorProfile:
    return _selector_profile_for_scale(scale_tier=scale_tier, n=n)


def _l2b_selector_profile_for_stage(stage_id: str) -> _GrammarModeSelectorProfile:
    for profile in SELECTOR_PROFILES:
        if profile.profile_id == stage_id:
            return profile
    allowed = ", ".join(l2b_full_coverage_stage_choices())
    raise ValueError(f"l2b_stage must be one of: {allowed}; got {stage_id!r}")


def _selector_profile_for_scale(
    *,
    scale_tier: str,
    n: int,
) -> _GrammarModeSelectorProfile:
    for profile in SELECTOR_PROFILES:
        if (
            profile.runtime_execution_enabled is True
            and profile.profile_id
            not in (L2B_N2_SELECTOR_PROFILE_ID, L2B_N20_SELECTOR_PROFILE_ID)
            and scale_tier == profile.scale_tier
            and n == profile.n
        ):
            return profile
    supported = ", ".join(
        f"{profile.scale_tier}/n={profile.n}"
        for profile in SELECTOR_PROFILES
        if profile.runtime_execution_enabled is True
    )
    raise ValueError(
        f"{L1A_GRAMMAR_MODE_CP_SELECTOR} supports only {supported}; "
        f"got {scale_tier}/n={n}"
    )


def _selector_profile_for_authorization(
    config: Cluster3RunnerConfig,
) -> _GrammarModeSelectorProfile:
    for profile in SELECTOR_PROFILES:
        if (
            profile.signed_authorization_token is not None
            and config.signed_l1a_authorization == profile.signed_authorization_token
        ):
            return profile
    supported = ", ".join(
        profile.signed_authorization_token
        for profile in SELECTOR_PROFILES
        if profile.signed_authorization_token is not None
    )
    raise ValueError(
        "signed selector authorization must match one of the approved tokens: "
        f"{supported}"
    )


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
    observability_logger_factory: ObservabilityLoggerFactory | None = None
    modal_context_provider: ModalContextProvider | None = None
    token_counts_provider: TokenCountsProvider | None = None
    cost_estimate_provider: CostEstimateProvider | None = None


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


@dataclass
class _Cluster3ObservabilityRuntime:
    config: Cluster3RunnerConfig
    mode: str
    paths: ObservabilityPaths | None = None
    logger: ObservabilityJsonlAppendLogger | None = None
    git_commit: str | None = None
    branch: str | None = None
    clock_scope_id: str = ""
    next_event_sequence: int = 0
    modal_context: ObservabilityModalContext | None = None
    token_counts_provider: TokenCountsProvider | None = None
    cost_estimate_provider: CostEstimateProvider | None = None
    disabled_reason: str | None = None

    @property
    def enabled(self) -> bool:
        return self.mode != "off" and self.logger is not None

    def close(self) -> None:
        if self.logger is not None:
            self.logger.close()

    def record_run_started(self, *, monotonic_ns: int) -> None:
        if not self.enabled:
            return
        self._append(
            event_type="run_started",
            severity="info",
            status="started",
            monotonic_ns=monotonic_ns,
            attributes={
                "runner": CLUSTER3_RUNNER_PATH,
                "condition": self.config.condition,
                "scale_tier": self.config.scale_tier,
                "write_mode": self.config.write_mode,
                "observability_mode": self.mode,
            },
        )

    def record_run_completed(
        self,
        *,
        row_count: int,
        start_monotonic_ns: int,
        end_monotonic_ns: int,
    ) -> None:
        if not self.enabled:
            return
        self._append(
            event_type="run_completed",
            severity="info",
            status="succeeded",
            monotonic_ns=end_monotonic_ns,
            start_monotonic_ns=start_monotonic_ns,
            end_monotonic_ns=end_monotonic_ns,
            attributes={
                "runner": CLUSTER3_RUNNER_PATH,
                "row_count": row_count,
                "condition": self.config.condition,
            },
        )

    def record_run_failed(
        self,
        *,
        error: BaseException,
        start_monotonic_ns: int,
        end_monotonic_ns: int,
    ) -> None:
        if not self.enabled:
            return
        self._append(
            event_type="run_failed",
            severity="error",
            status="failed",
            monotonic_ns=end_monotonic_ns,
            start_monotonic_ns=start_monotonic_ns,
            end_monotonic_ns=end_monotonic_ns,
            error_summary={
                "public_failure_code": "runner_failed",
                "bounded_public_error_class": type(error).__name__,
                "message": type(error).__name__,
            },
            attributes={
                "runner": CLUSTER3_RUNNER_PATH,
                "condition": self.config.condition,
            },
        )

    def record_row_started(
        self,
        *,
        row_index: int,
        condition: str,
        kernel_class: str,
        kernel_name: str,
        dtype: str,
        base_seed: int,
        monotonic_ns: int,
    ) -> None:
        if not self.enabled:
            return
        self._append(
            event_type="row_started",
            severity="info",
            status="started",
            monotonic_ns=monotonic_ns,
            row_identity=_observability_row_identity(
                condition=condition,
                kernel_class=kernel_class,
                kernel_name=kernel_name,
                dtype=dtype,
                base_seed=base_seed,
            ),
            attributes={
                "row_index": row_index,
                "condition": condition,
                "kernel_class": kernel_class,
                "dtype": dtype,
            },
        )

    def record_row_completed(
        self,
        *,
        row_index: int,
        row: Cluster3EvalRow,
        start_monotonic_ns: int,
        end_monotonic_ns: int,
    ) -> None:
        if not self.enabled:
            return
        self._append(
            event_type="row_completed",
            severity="info",
            status="succeeded",
            monotonic_ns=end_monotonic_ns,
            start_monotonic_ns=start_monotonic_ns,
            end_monotonic_ns=end_monotonic_ns,
            row_identity=_observability_row_identity_from_row(row),
            attempt=_observability_attempt_identity_from_row(row),
            attributes={
                "row_index": row_index,
                "condition": row.condition,
                "kernel_class": row.kernel_class,
                "dtype": row.dtype,
                "p_repair_attempted": row.p_repair_attempted,
                "c_loop_fired": row.c_loop_fired,
                "failure_code": row.failure_code,
            },
        )

    def record_stage_started(
        self,
        *,
        stage: str,
        row_index: int,
        row: Cluster3EvalRow,
        monotonic_ns: int,
    ) -> None:
        self.record_stage_started_for_identity(
            stage=stage,
            row_index=row_index,
            row_identity=_observability_row_identity_from_row(row),
            attempt=_observability_attempt_identity_from_row(row),
            condition=row.condition,
            monotonic_ns=monotonic_ns,
        )

    def record_stage_started_for_identity(
        self,
        *,
        stage: str,
        row_index: int,
        row_identity: ObservabilityRowIdentity,
        attempt: ObservabilityAttemptIdentity,
        condition: str,
        monotonic_ns: int,
    ) -> None:
        if not self.enabled:
            return
        self._append(
            event_type="stage_started",
            severity="info",
            status="started",
            stage=stage,
            monotonic_ns=monotonic_ns,
            row_identity=row_identity,
            attempt=attempt,
            attributes={
                "row_index": row_index,
                "condition": condition,
                "stage": stage,
            },
        )

    def record_stage_completed(
        self,
        *,
        stage: str,
        row_index: int,
        row: Cluster3EvalRow,
        start_monotonic_ns: int,
        end_monotonic_ns: int,
    ) -> None:
        self.record_stage_completed_for_identity(
            stage=stage,
            row_index=row_index,
            row_identity=_observability_row_identity_from_row(row),
            attempt=_observability_attempt_identity_from_row(row),
            condition=row.condition,
            start_monotonic_ns=start_monotonic_ns,
            end_monotonic_ns=end_monotonic_ns,
        )

    def record_stage_completed_for_identity(
        self,
        *,
        stage: str,
        row_index: int,
        row_identity: ObservabilityRowIdentity,
        attempt: ObservabilityAttemptIdentity,
        condition: str,
        start_monotonic_ns: int,
        end_monotonic_ns: int,
    ) -> None:
        if not self.enabled:
            return
        self._append(
            event_type="stage_completed",
            severity="info",
            status="succeeded",
            stage=stage,
            monotonic_ns=end_monotonic_ns,
            start_monotonic_ns=start_monotonic_ns,
            end_monotonic_ns=end_monotonic_ns,
            row_identity=row_identity,
            attempt=attempt,
            attributes={
                "row_index": row_index,
                "condition": condition,
                "stage": stage,
            },
        )

    def record_stage_failed(
        self,
        *,
        stage: str,
        row_index: int,
        row: Cluster3EvalRow,
        error: BaseException,
        start_monotonic_ns: int,
        end_monotonic_ns: int,
    ) -> None:
        self.record_stage_failed_for_identity(
            stage=stage,
            row_index=row_index,
            row_identity=_observability_row_identity_from_row(row),
            attempt=_observability_attempt_identity_from_row(row),
            condition=row.condition,
            error=error,
            start_monotonic_ns=start_monotonic_ns,
            end_monotonic_ns=end_monotonic_ns,
        )

    def record_stage_failed_for_identity(
        self,
        *,
        stage: str,
        row_index: int,
        row_identity: ObservabilityRowIdentity,
        attempt: ObservabilityAttemptIdentity,
        condition: str,
        error: BaseException,
        start_monotonic_ns: int,
        end_monotonic_ns: int,
    ) -> None:
        if not self.enabled:
            return
        self._append(
            event_type="stage_failed",
            severity="error",
            status="failed",
            stage=stage,
            monotonic_ns=end_monotonic_ns,
            start_monotonic_ns=start_monotonic_ns,
            end_monotonic_ns=end_monotonic_ns,
            row_identity=row_identity,
            attempt=attempt,
            error_summary={
                "public_failure_code": "stage_failed",
                "bounded_public_error_class": type(error).__name__,
                "message": type(error).__name__,
            },
            attributes={
                "row_index": row_index,
                "condition": condition,
                "stage": stage,
            },
        )

    def write_summary(self, *, row_count: int) -> None:
        if not self.enabled:
            return
        assert self.paths is not None
        assert self.git_commit is not None
        assert self.branch is not None
        events = load_observability_events(self.paths.event_path)
        token_totals = observability_token_totals(events)
        cost_summary = observability_estimated_cost_summary(events)
        caveats = [
            "O2 Modal context is optional and unavailable-safe; real remote "
            "context remains unproven until an approved execution packet.",
            "O3 token telemetry is count/status-only and does not execute "
            "tokenizers, models, or generation paths.",
            "O4 estimated cost telemetry is supplied/unavailable sidecar metadata "
            "only and does not query billing, pricing APIs, invoices, or dashboards.",
            "Actual billing reconciliation remains future O5 work.",
        ]
        if token_totals["events_with_available_token_counts"] == 0:
            caveats.append(
                "Real token counts remain unavailable in this local runner path "
                "until an approved existing count source is supplied."
            )
        if not cost_summary["cost_estimate_available"]:
            caveats.append(
                "Real estimated cost remains unavailable until an approved supplied "
                "or static pricing source is provided."
            )
        summary = ObservabilitySummary(
            experiment_id=self.config.observability_experiment_id or "",
            run_id=self.config.observability_run_id or "",
            result_path=self.config.output,
            observability_event_path=str(self.paths.event_path),
            observability_summary_path=str(self.paths.summary_path),
            generated_at_utc=_utc_now(),
            git_commit=self.git_commit,
            branch=self.branch,
            workspace=".",
            row_counts={"total": row_count},
            event_counts=observability_event_counts(events),
            stage_durations_ns=observability_stage_durations_ns(events),
            token_totals=token_totals,
            modal_context_summary=_observability_modal_context_summary(events),
            estimated_cost_summary=cost_summary,
            actual_billing_status="not_implemented",
            completeness_status="complete",
            caveats=caveats,
            source_event_sha256=file_sha256(self.paths.event_path),
            summary_sha256=None,
        )
        self._call_logger(lambda logger: logger.write_summary(summary))

    def _append(
        self,
        *,
        event_type: str,
        severity: str,
        status: str,
        monotonic_ns: int,
        stage: str | None = None,
        row_identity: ObservabilityRowIdentity | None = None,
        attempt: ObservabilityAttemptIdentity | None = None,
        start_monotonic_ns: int | None = None,
        end_monotonic_ns: int | None = None,
        error_summary: Mapping[str, Any] | None = None,
        attributes: Mapping[str, Any] | None = None,
    ) -> None:
        if not self.enabled:
            return
        assert self.paths is not None
        try:
            duration_ns = None
            duration_source = "not_applicable"
            if start_monotonic_ns is not None and end_monotonic_ns is not None:
                duration_ns = end_monotonic_ns - start_monotonic_ns
                duration_source = "local_monotonic"
            safe_error_summary = (
                ObservabilityErrorSummary.model_validate(dict(error_summary))
                if error_summary is not None
                else None
            )
            event = ObservabilityEvent(
                event_id=str(uuid.uuid4()),
                event_sequence=self.next_event_sequence,
                event_type=event_type,
                severity=severity,
                timestamp_utc=_utc_now(),
                timestamp_unix_ns=time.time_ns(),
                monotonic_ns=monotonic_ns,
                clock_scope_id=self.clock_scope_id,
                experiment_id=self.config.observability_experiment_id or "",
                run_id=self.config.observability_run_id or "",
                artifact=ObservabilityArtifactIdentity(
                    result_path=self.config.output,
                    observability_event_path=str(self.paths.event_path),
                    observability_summary_path=str(self.paths.summary_path),
                    git_commit=self.git_commit,
                ),
                row_identity=row_identity or ObservabilityRowIdentity(),
                stage=stage,
                attempt=attempt or ObservabilityAttemptIdentity(),
                status=status,
                duration_ns=duration_ns,
                duration_source=duration_source,
                start_monotonic_ns=start_monotonic_ns,
                end_monotonic_ns=end_monotonic_ns,
                token_counts=self._token_counts_for_event(
                    event_type=event_type,
                    stage=stage,
                    status=status,
                ),
                modal_context=self.modal_context,
                cost_estimate=self._cost_estimate_for_event(
                    event_type=event_type,
                    stage=stage,
                    status=status,
                ),
                error_summary=safe_error_summary,
                attributes=dict(attributes or {}),
            )
        except Exception as exc:
            if self.mode == "required":
                raise
            self.disabled_reason = type(exc).__name__
            self.close()
            self.logger = None
            return
        self._append_event(event)

    def _token_counts_for_event(
        self,
        *,
        event_type: str,
        stage: str | None,
        status: str,
    ) -> ObservabilityTokenCounts:
        if self.token_counts_provider is None:
            return _unavailable_observability_token_counts()
        payload = self.token_counts_provider(
            {
                "event_sequence": self.next_event_sequence,
                "event_type": event_type,
                "stage": stage,
                "status": status,
                "condition": self.config.condition,
            }
        )
        if payload is None:
            return _unavailable_observability_token_counts()
        if isinstance(payload, ObservabilityTokenCounts):
            return ObservabilityTokenCounts.model_validate(payload.model_dump(mode="json"))
        return ObservabilityTokenCounts.model_validate(dict(payload))

    def _cost_estimate_for_event(
        self,
        *,
        event_type: str,
        stage: str | None,
        status: str,
    ) -> ObservabilityCostEstimate:
        if self.cost_estimate_provider is None:
            return _unavailable_observability_cost_estimate()
        payload = self.cost_estimate_provider(
            {
                "event_sequence": self.next_event_sequence,
                "event_type": event_type,
                "stage": stage,
                "status": status,
                "condition": self.config.condition,
            }
        )
        if payload is None:
            return _unavailable_observability_cost_estimate()
        if isinstance(payload, ObservabilityCostEstimate):
            return ObservabilityCostEstimate.model_validate(payload.model_dump(mode="json"))
        return ObservabilityCostEstimate.model_validate(dict(payload))

    def _append_event(self, event: ObservabilityEvent) -> None:
        if self.logger is None:
            return
        try:
            self.logger.append(event)
        except Exception as exc:
            if self.mode == "required":
                raise
            self.disabled_reason = type(exc).__name__
            self.close()
            self.logger = None
        else:
            self.next_event_sequence += 1

    def _call_logger(self, operation: Callable[[ObservabilityJsonlAppendLogger], Any]) -> None:
        if self.logger is None:
            return
        try:
            operation(self.logger)
        except Exception as exc:
            if self.mode == "required":
                raise
            self.disabled_reason = type(exc).__name__
            self.close()
            self.logger = None


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
    parser.add_argument(
        "--observability-mode",
        default="off",
        choices=OBSERVABILITY_MODE_CHOICES,
    )
    parser.add_argument("--observability-experiment-id", default=None)
    parser.add_argument("--observability-run-id", default=None)
    parser.add_argument("--observability-output", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument(
        "--grammar-mode-cell",
        default="all",
        choices=l1a_grammar_mode_cell_selector_choices(),
    )
    parser.add_argument(
        "--l2b-stage",
        default=None,
        choices=l2b_full_coverage_stage_choices(),
    )
    parser.add_argument("--l2b-shard-selector", default="all")
    parser.add_argument("--signed-l1a-authorization", default=None)
    parser.add_argument(
        "--signed-l1b-authorization",
        dest="signed_l1a_authorization",
        default=None,
    )
    parser.add_argument(
        "--signed-l2-authorization",
        dest="signed_l1a_authorization",
        default=None,
    )
    parser.add_argument(
        "--signed-l2b-authorization",
        dest="signed_l1a_authorization",
        default=None,
    )
    mode = parser.add_mutually_exclusive_group(required=False)
    mode.add_argument("--overwrite", action="store_true")
    mode.add_argument("--resume", action="store_true")
    mode.add_argument("--dry-plan", action="store_true")
    mode.add_argument("--execution-plan", action="store_true")
    return parser


def parse_args(argv: Sequence[str] | None = None) -> Cluster3RunnerConfig:
    parser = build_arg_parser()
    namespace = parser.parse_args(argv)
    _validate_cli_namespace(parser, namespace)
    return Cluster3RunnerConfig.from_namespace(namespace)


def _validate_cli_namespace(
    parser: argparse.ArgumentParser,
    namespace: argparse.Namespace,
) -> None:
    if namespace.dry_plan or namespace.execution_plan:
        if namespace.output is not None:
            parser.error("--output is not used with --dry-plan or --execution-plan")
        if namespace.signed_l1a_authorization is not None:
            parser.error(
                "signed selector authorization is not used with local planning modes"
            )
        if namespace.condition != L1A_GRAMMAR_MODE_CP_SELECTOR:
            parser.error(
                "--dry-plan and --execution-plan require "
                f"--condition {L1A_GRAMMAR_MODE_CP_SELECTOR}"
            )
        return
    if namespace.condition == L1A_GRAMMAR_MODE_CP_SELECTOR:
        if not namespace.overwrite:
            parser.error(
                f"--condition {L1A_GRAMMAR_MODE_CP_SELECTOR} requires --overwrite "
                "for future fail-if-existing execution planning"
            )
        return
    if namespace.output is None:
        parser.error("--output is required unless --dry-plan")
    if not namespace.overwrite and not namespace.resume:
        parser.error("one of --overwrite or --resume is required unless --dry-plan")


def build_l1a_dry_plan_payload(config: Cluster3RunnerConfig) -> dict[str, Any]:
    if not config.dry_plan:
        raise ValueError("build_l1a_dry_plan_payload requires dry_plan=True")
    if config.l2b_stage is not None:
        return build_l2b_full_coverage_plan_payload(config)
    profile = _selector_profile_for_config(config)
    cells = build_l1a_launcher_dry_plan(
        repair_history_policy=config.repair_history_policy,
        cell_selector=config.grammar_mode_cell,
        output_root=profile.output_root,
        observability_root=profile.observability_root,
        run_id_prefix=profile.run_id_prefix,
        scale_tier=profile.scale_tier,
        n=profile.n,
        kernel_class_selector=profile.kernel_class_selector,
        dtypes=profile.dtypes,
        repo_root=REPO_ROOT,
    )
    return {
        "selector": L1A_GRAMMAR_MODE_CP_SELECTOR,
        "dry_plan_only": True,
        "cell_selector": config.grammar_mode_cell,
        "cell_count": len(cells),
        "planned_rows": _planned_rows(config, cells),
        "authorization_profile": profile.label,
        "scale_tier": profile.scale_tier,
        "n": profile.n,
        "kernel_class_selector": profile.kernel_class_selector,
        "kernel_classes": config.kernel_classes,
        "dtypes": profile.dtypes,
        "expected_planned_rows": profile.expected_planned_rows,
        "experiment_id": L1A_EXPERIMENT_ID,
        "output_root": profile.output_root,
        "observability_root": profile.observability_root,
        "path_collision_policy": L1A_PATH_COLLISION_POLICY,
        "execution_authorized": False,
        "runtime_execution_enabled": profile.runtime_execution_enabled,
        "runtime_block_reason": profile.runtime_block_reason,
        "signed_authorization_available": (
            profile.signed_authorization_token is not None
        ),
        "writes_outputs": False,
        "writes_artifacts": False,
        "writes_mlruns": False,
        "cells": [cell.to_dict() for cell in cells],
    }


def build_l1a_execution_plan_payload(config: Cluster3RunnerConfig) -> dict[str, Any]:
    if not config.execution_plan:
        raise ValueError(
            "build_l1a_execution_plan_payload requires execution_plan=True"
        )
    if config.l2b_stage is not None:
        return build_l2b_full_coverage_plan_payload(config)
    profile = _selector_profile_for_config(config)
    cells = build_l1a_launcher_executable_plan(
        repair_history_policy=config.repair_history_policy,
        cell_selector=config.grammar_mode_cell,
        output_root=profile.output_root,
        observability_root=profile.observability_root,
        run_id_prefix=profile.run_id_prefix,
        scale_tier=profile.scale_tier,
        n=profile.n,
        kernel_class_selector=profile.kernel_class_selector,
        dtypes=profile.dtypes,
        repo_root=REPO_ROOT,
        signed_authorization_placeholder=profile.signed_authorization_placeholder,
        signed_authorization_option=profile.signed_authorization_option
        or "--signed-l1a-authorization",
        support_status=profile.support_status,
    )
    return {
        "selector": L1A_GRAMMAR_MODE_CP_SELECTOR,
        "execution_plan_only": True,
        "dry_plan_only": False,
        "cell_selector": config.grammar_mode_cell,
        "cell_count": len(cells),
        "planned_rows": _planned_rows(config, cells),
        "authorization_profile": profile.label,
        "scale_tier": profile.scale_tier,
        "n": profile.n,
        "kernel_class_selector": profile.kernel_class_selector,
        "kernel_classes": config.kernel_classes,
        "dtypes": profile.dtypes,
        "expected_planned_rows": profile.expected_planned_rows,
        "experiment_id": L1A_EXPERIMENT_ID,
        "output_root": profile.output_root,
        "observability_root": profile.observability_root,
        "path_collision_policy": L1A_PATH_COLLISION_POLICY,
        "execution_authorized": False,
        "runtime_execution_enabled": profile.runtime_execution_enabled,
        "runtime_block_reason": profile.runtime_block_reason,
        "requires_signed_authorization": (
            profile.signed_authorization_token is not None
        ),
        "signed_authorization_available": (
            profile.signed_authorization_token is not None
        ),
        "requires_signed_l1a_authorization": (
            profile is L1A_SELECTOR_PROFILE
        ),
        "signed_authorization_option": profile.signed_authorization_option,
        "writes_outputs": False,
        "writes_artifacts": False,
        "writes_mlruns": False,
        "cells": [cell.to_dict() for cell in cells],
    }


def build_l2b_full_coverage_plan_payload(
    config: Cluster3RunnerConfig,
) -> dict[str, Any]:
    if config.l2b_stage is None:
        raise ValueError("build_l2b_full_coverage_plan_payload requires l2b_stage")
    if not config.dry_plan and not config.execution_plan:
        raise ValueError("L2b full-coverage payloads require a local planning mode")
    profile = _selector_profile_for_config(config)
    stage = l2b_full_coverage_stage_spec(config.l2b_stage)
    command_mode = "dry_plan" if config.dry_plan else "executable"
    shards = build_l2b_full_coverage_shard_plan(
        stage_id=config.l2b_stage,
        shard_selector=config.l2b_shard_selector,
        repair_history_policy=config.repair_history_policy,
        command_mode=command_mode,
        repo_root=REPO_ROOT,
        signed_authorization_placeholder=profile.signed_authorization_placeholder,
        signed_authorization_option=profile.signed_authorization_option
        or "--signed-l2b-authorization",
    )
    selected_shard_count = len(shards)
    total_planned_rows = selected_shard_count * stage.rows_per_shard
    return {
        "selector": L1A_GRAMMAR_MODE_CP_SELECTOR,
        "selector_profile_id": profile.profile_id,
        "authorization_profile": profile.label,
        "l2b_stage": stage.selector_profile_id,
        "l2b_rung": stage.rung,
        "dry_plan_only": config.dry_plan,
        "execution_plan_only": config.execution_plan,
        "cell_selector": config.grammar_mode_cell,
        "shard_selector": config.l2b_shard_selector,
        "total_shards": stage.total_shards,
        "selected_shard_count": selected_shard_count,
        "planned_cells_per_shard": stage.planned_cells_per_shard,
        "rows_per_shard": stage.rows_per_shard,
        "total_planned_rows": total_planned_rows,
        "full_matrix_planned_rows": stage.full_matrix_planned_rows,
        "expected_planned_rows": profile.expected_planned_rows,
        "scale_tier": stage.scale_tier,
        "n": stage.n,
        "kernel_class_selector": profile.kernel_class_selector,
        "kernel_classes": LOCKED_KERNEL_CLASSES,
        "dtypes": DTYPE_NAMES,
        "backend": stage.backend,
        "future_backend_todo": "fireworks_api",
        "experiment_id": L1A_EXPERIMENT_ID,
        "output_root": stage.output_root,
        "observability_root": stage.observability_root,
        "analysis_root": stage.analysis_root,
        "reports_root": stage.reports_root,
        "billing_root": stage.billing_root,
        "path_collision_policy": L1A_PATH_COLLISION_POLICY,
        "fail_if_any_target_path_exists": True,
        "execution_authorized": False,
        "runtime_execution_enabled": stage.runtime_execution_enabled,
        "runtime_block_reason": stage.runtime_block_reason,
        "signed_authorization_available": stage.signed_authorization_available,
        "signature_status": stage.signature_status,
        "dependency_gate": stage.dependency_gate,
        "requires_signed_authorization": config.execution_plan,
        "signed_authorization_option": profile.signed_authorization_option,
        "support_status": profile.support_status,
        "concurrency_limits": dict(stage.concurrency_limits),
        "timing_observability": dict(stage.timing_observability),
        "slow_cell_stop_policy": dict(stage.slow_cell_stop_policy),
        "writes_outputs": False,
        "writes_artifacts": False,
        "writes_mlruns": False,
        "shards": [shard.to_dict() for shard in shards],
    }


def _planned_rows(
    config: Cluster3RunnerConfig,
    cells: Sequence[GrammarModeLauncherCellPlan],
) -> int:
    return len(cells) * len(config.kernel_classes) * len(config.dtypes) * config.n


def main(argv: Sequence[str] | None = None) -> Cluster3RunResult | dict[str, Any]:
    config = parse_args(argv)
    if config.dry_plan:
        payload = build_l1a_dry_plan_payload(config)
        print(json.dumps(payload, sort_keys=True))
        return payload
    if config.execution_plan:
        payload = build_l1a_execution_plan_payload(config)
        print(json.dumps(payload, sort_keys=True))
        return payload
    l1a_cells: tuple[GrammarModeLauncherCellPlan, ...] | None = None
    l2b_shards: tuple[L2BFullCoverageShardPlan, ...] | None = None
    if config.condition == L1A_GRAMMAR_MODE_CP_SELECTOR:
        if config.l2b_stage is not None:
            l2b_shards = _validate_l2b_runtime_authorization(config)
        else:
            l1a_cells = _validate_l1a_runtime_authorization(config)

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
        if l2b_shards is not None:
            result = _run_signed_l2b_selector_with_modal_context(
                config,
                shards=l2b_shards,
            )
        elif l1a_cells is not None:
            result = _run_signed_l1a_selector_with_modal_context(
                config,
                cells=l1a_cells,
            )
        else:
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


def _run_signed_l1a_selector_with_modal_context(
    config: Cluster3RunnerConfig,
    *,
    cells: tuple[GrammarModeLauncherCellPlan, ...],
) -> Cluster3RunResult:
    """Run the signed selector under a hydrated Modal app context."""

    with _signed_l1a_modal_app_context():
        return _run_signed_l1a_selector(config, cells=cells)


def _run_signed_l2b_selector_with_modal_context(
    config: Cluster3RunnerConfig,
    *,
    shards: tuple[L2BFullCoverageShardPlan, ...],
) -> Cluster3RunResult:
    """Run the signed L2b-2 selector under a hydrated Modal app context."""

    with _signed_l2b_modal_app_context():
        return _run_signed_l2b_selector(config, shards=shards)


def _signed_l2b_modal_app_context() -> Any:
    """Return the same Modal app context used by signed selector launches."""

    return _signed_l1a_modal_app_context()


def _signed_l1a_modal_app_context() -> Any:
    """Return an app.run context with existing C2 Modal surfaces registered."""

    import cluster2.modal.correctness  # noqa: F401
    import cluster2.modal.generation  # noqa: F401
    from shared.modal_harness.app import app as _modal_app

    return _modal_app.run()


def _run_signed_l1a_selector(
    config: Cluster3RunnerConfig,
    *,
    cells: tuple[GrammarModeLauncherCellPlan, ...],
    dependencies: RunnerDependencies | None = None,
) -> Cluster3RunResult:
    """Expand the signed L1a selector into its 12 existing runner cells."""

    if config.condition != L1A_GRAMMAR_MODE_CP_SELECTOR:
        raise ValueError("signed L1a selector runner requires grammar_mode_cp_12cell")
    if len(cells) != 12:
        raise ValueError("signed L1a selector runner requires exactly 12 cells")

    rows: list[Cluster3EvalRow] = []
    audits: list[ConditionRouteAudit] = []
    for cell in cells:
        runtime_config = _l1a_cell_runtime_config(config, cell)
        run_kwargs = {"dependencies": dependencies} if dependencies is not None else {}
        cell_result = run_cluster3(runtime_config, **run_kwargs)
        rows.extend(cell_result.rows)
        audits.extend(cell_result.route_audit)
    return Cluster3RunResult(
        rows=tuple(rows),
        route_audit=tuple(audits),
        output=_selector_output_root_from_cells(cells),
        write_mode=config.write_mode,
    )


def _run_signed_l2b_selector(
    config: Cluster3RunnerConfig,
    *,
    shards: tuple[L2BFullCoverageShardPlan, ...],
    dependencies: RunnerDependencies | None = None,
) -> Cluster3RunResult:
    """Expand the signed L2b-2 selector into validated shard/cell runs."""

    if config.condition != L1A_GRAMMAR_MODE_CP_SELECTOR:
        raise ValueError("signed L2b selector runner requires grammar_mode_cp_12cell")
    if config.l2b_stage != L2B_N2_SELECTOR_PROFILE_ID:
        raise ValueError(f"signed L2b selector requires {L2B_N2_SELECTOR_PROFILE_ID}")
    if not shards:
        raise ValueError("signed L2b selector requires at least one shard")

    stage = l2b_full_coverage_stage_spec(config.l2b_stage)
    max_workers = _signed_l2b_max_shard_workers(stage=stage, selected=len(shards))
    results: list[Cluster3RunResult | None] = [None] * len(shards)

    if max_workers == 1:
        for index, shard in enumerate(shards):
            results[index] = _run_signed_l2b_shard(
                config,
                shard,
                dependencies=dependencies,
            )
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _run_signed_l2b_shard,
                    config,
                    shard,
                    dependencies=dependencies,
                ): index
                for index, shard in enumerate(shards)
            }
            for future in as_completed(futures):
                results[futures[future]] = future.result()

    rows: list[Cluster3EvalRow] = []
    audits: list[ConditionRouteAudit] = []
    for result in results:
        if result is None:
            raise RuntimeError("signed L2b selector shard result missing")
        rows.extend(result.rows)
        audits.extend(result.route_audit)

    return Cluster3RunResult(
        rows=tuple(rows),
        route_audit=tuple(audits),
        output=_selector_output_root_from_shards(shards),
        write_mode=config.write_mode,
    )


def _run_signed_l2b_shard(
    config: Cluster3RunnerConfig,
    shard: L2BFullCoverageShardPlan,
    *,
    dependencies: RunnerDependencies | None = None,
) -> Cluster3RunResult:
    cells = _l2b_cell_plans_for_shard(config, shard)
    shard_config = replace(
        config,
        kernel_class=shard.kernel_class,
        dtypes=(shard.dtype_variant,),
        l2b_stage=None,
        l2b_shard_selector="all",
    )

    rows: list[Cluster3EvalRow] = []
    audits: list[ConditionRouteAudit] = []
    for cell in cells:
        runtime_config = _l1a_cell_runtime_config(shard_config, cell)
        run_kwargs = {"dependencies": dependencies} if dependencies is not None else {}
        cell_start = time.perf_counter()
        cell_result = run_cluster3(runtime_config, **run_kwargs)
        cell_elapsed = time.perf_counter() - cell_start
        rows.extend(cell_result.rows)
        audits.extend(cell_result.route_audit)
        if cell_elapsed > L2B_N2_SIGNED_WALL_CLOCK_SECONDS_PER_CELL:
            raise RuntimeError(
                "SLOW_CELL_BUDGET_EXCEEDED: signed L2b shard "
                f"{shard.shard_id} cell {cell.condition_id} took "
                f"{cell_elapsed:.3f}s, exceeding "
                f"{L2B_N2_SIGNED_WALL_CLOCK_SECONDS_PER_CELL:.0f}s"
            )

    if len(rows) != shard.planned_rows:
        raise RuntimeError(
            f"signed L2b shard {shard.shard_id} produced {len(rows)} rows; "
            f"expected {shard.planned_rows}"
        )
    return Cluster3RunResult(
        rows=tuple(rows),
        route_audit=tuple(audits),
        output=shard.output_namespace,
        write_mode=config.write_mode,
    )


def _signed_l2b_max_shard_workers(*, stage: Any, selected: int) -> int:
    limit = int(stage.concurrency_limits.get("max_gpu_concurrency", 1))
    if limit < 1:
        raise ValueError("signed L2b-2 requires max_gpu_concurrency >= 1")
    if limit > 4:
        raise ValueError("signed L2b-2 requires max_gpu_concurrency <= 4")
    return max(1, min(selected, limit))


def _l2b_cell_plans_for_shard(
    config: Cluster3RunnerConfig,
    shard: L2BFullCoverageShardPlan,
) -> tuple[GrammarModeLauncherCellPlan, ...]:
    if config.l2b_stage != L2B_N2_SELECTOR_PROFILE_ID:
        raise ValueError(f"signed L2b cell plans require {L2B_N2_SELECTOR_PROFILE_ID}")
    stage = l2b_full_coverage_stage_spec(config.l2b_stage)
    cells = build_l1a_launcher_executable_plan(
        repair_history_policy=config.repair_history_policy,
        cell_selector="all",
        output_root=shard.output_namespace,
        observability_root=shard.artifact_namespace,
        run_id_prefix=f"{stage.run_id_prefix}__{shard.shard_id}",
        scale_tier=stage.scale_tier,
        n=stage.n,
        kernel_class_selector=shard.kernel_class,
        dtypes=(shard.dtype_variant,),
        repo_root=REPO_ROOT,
        signed_authorization_placeholder=L2B_N2_SIGNED_AUTHORIZATION_TOKEN,
        signed_authorization_option="--signed-l2b-authorization",
        support_status=L2B_N2_EXECUTABLE_SELECTOR_SUPPORT_STATUS,
    )
    if len(cells) != shard.planned_cells:
        raise ValueError("signed L2b shard cell count mismatch")
    if len(cells) * stage.n != shard.planned_rows:
        raise ValueError("signed L2b shard planned row mismatch")
    if tuple(cell.executable_command for cell in cells) != shard.cell_commands:
        raise ValueError("signed L2b shard cell command mismatch")
    if tuple(cell.output_path for cell in cells) != tuple(
        shard.output_paths["result_files"]
    ):
        raise ValueError("signed L2b shard output path mismatch")
    if tuple(cell.observability_event_path for cell in cells) != tuple(
        shard.artifact_paths["observability_event_files"]
    ):
        raise ValueError("signed L2b shard observability path mismatch")
    return cells


def _l1a_cell_runtime_config(
    config: Cluster3RunnerConfig,
    cell: GrammarModeLauncherCellPlan,
) -> Cluster3RunnerConfig:
    """Build the per-cell runtime config after signed selector validation."""

    grammar_variant = (
        cell.grammar_variant
        if cell.runner_condition in CLUSTER3_G_ACTIVE_CONDITIONS
        else config.grammar_variant
    )
    return replace(
        config,
        condition=cell.runner_condition,
        output=cell.output_path,
        observability_mode="best_effort",
        observability_experiment_id=cell.observability_experiment_id,
        observability_run_id=cell.observability_join_key,
        observability_output=cell.observability_event_path,
        grammar_variant=grammar_variant,
        grammar_mode_cell="all",
        l2b_stage=None,
        l2b_shard_selector="all",
        signed_l1a_authorization=None,
    )


def _validate_l1a_runtime_authorization(
    config: Cluster3RunnerConfig,
) -> tuple[GrammarModeLauncherCellPlan, ...]:
    """Validate the exact signed grammar-mode selector command before launch."""

    if config.condition != L1A_GRAMMAR_MODE_CP_SELECTOR:
        raise ValueError("selector authorization is only valid for grammar_mode_cp_12cell")
    profile = _selector_profile_for_authorization(config)
    if not profile.runtime_execution_enabled:
        raise RuntimeError(profile.runtime_block_reason or f"{profile.label} is blocked")
    if os.environ.get("TRITONGEN_MLFLOW") != "0":
        raise RuntimeError(f"TRITONGEN_MLFLOW=0 is required for signed {profile.label}")
    if config.write_mode != "overwrite":
        raise ValueError(f"signed {profile.label} requires --overwrite and forbids resume")
    if config.output != profile.selector_placeholder_output:
        raise ValueError("signed selector command must not override --output")
    if config.grammar_mode_cell != "all":
        raise ValueError(f"signed {profile.label} selector command must plan all 12 cells")
    if config.scale_tier != profile.scale_tier:
        raise ValueError(
            f"signed {profile.label} requires --scale-tier {profile.scale_tier}"
        )
    if config.n != profile.n:
        raise ValueError(f"signed {profile.label} requires --n {profile.n}")
    if config.kernel_class != profile.kernel_class_selector:
        raise ValueError(
            f"signed {profile.label} requires "
            f"--kernel-class {profile.kernel_class_selector}"
        )
    if config.dtypes != profile.dtypes:
        raise ValueError(
            f"signed {profile.label} requires --dtypes {','.join(profile.dtypes)}"
        )
    if config.repair_history_policy != "agentic_transcript_v1":
        raise ValueError(
            f"signed {profile.label} requires "
            "--repair-history-policy agentic_transcript_v1"
        )
    if config.dry_plan or config.execution_plan:
        raise ValueError("runtime authorization does not apply to planning modes")
    if config.observability_mode != "off":
        raise ValueError("selector-level signed command must not override observability")
    if (
        config.observability_experiment_id is not None
        or config.observability_run_id is not None
        or config.observability_output is not None
    ):
        raise ValueError("selector-level signed command must not set observability paths")

    cells = build_l1a_launcher_executable_plan(
        repair_history_policy=config.repair_history_policy,
        cell_selector=config.grammar_mode_cell,
        output_root=profile.output_root,
        observability_root=profile.observability_root,
        run_id_prefix=profile.run_id_prefix,
        scale_tier=profile.scale_tier,
        n=profile.n,
        kernel_class_selector=profile.kernel_class_selector,
        dtypes=profile.dtypes,
        repo_root=REPO_ROOT,
        signed_authorization_placeholder=profile.signed_authorization_token,
        signed_authorization_option=profile.signed_authorization_option
        or "--signed-l1a-authorization",
    )
    if len(cells) != 12:
        raise ValueError(f"signed {profile.label} requires exactly 12 planned cells")
    planned_rows = _planned_rows(config, cells)
    if planned_rows != profile.expected_planned_rows:
        raise ValueError(
            f"signed {profile.label} requires exactly "
            f"{profile.expected_planned_rows} planned rows"
        )

    condition_ids = {cell.condition_id for cell in cells}
    if len(condition_ids) != 12:
        raise ValueError(f"signed {profile.label} requires 12 unique planned cells")

    for cell in cells:
        if cell.selector != L1A_GRAMMAR_MODE_CP_SELECTOR:
            raise ValueError("signed selector plan contains an unexpected selector")
        if cell.path_collision_policy != L1A_PATH_COLLISION_POLICY:
            raise ValueError("signed selector plan must fail if target paths exist")
        if cell.output_path != f"{profile.output_root}/{cell.condition_id}.jsonl":
            raise ValueError("signed selector plan output path does not match namespace")
        _require_l1a_path(cell.output_path, root=profile.output_root, label="output")
        _require_l1a_path(
            cell.content_hash_sidecar_path,
            root=profile.output_root,
            label="content hash sidecar",
        )
        _require_l1a_path(
            cell.observability_event_path,
            root=profile.observability_root,
            label="observability event sidecar",
        )
        _require_l1a_path(
            cell.observability_summary_path,
            root=profile.observability_root,
            label="observability summary sidecar",
        )
        _require_l1a_path(
            cell.observability_hash_path,
            root=profile.observability_root,
            label="observability hash sidecar",
        )
        _require_absent_target(cell.output_path, label="output")
        _require_absent_target(cell.content_hash_sidecar_path, label="content hash sidecar")
        _require_absent_target(
            cell.observability_event_path,
            label="observability event sidecar",
        )
        _require_absent_target(
            cell.observability_summary_path,
            label="observability summary sidecar",
        )
        _require_absent_target(
            cell.observability_hash_path,
            label="observability hash sidecar",
        )
    return cells


def _validate_l2b_runtime_authorization(
    config: Cluster3RunnerConfig,
) -> tuple[L2BFullCoverageShardPlan, ...]:
    """Validate the exact signed L2b-2 shard selector before launch."""

    if config.condition != L1A_GRAMMAR_MODE_CP_SELECTOR:
        raise ValueError("L2b authorization is only valid for grammar_mode_cp_12cell")
    if config.l2b_stage == L2B_N20_SELECTOR_PROFILE_ID:
        raise RuntimeError("L2b-4 remains unsigned and blocked on L2b-2 validation")
    if config.l2b_stage != L2B_N2_SELECTOR_PROFILE_ID:
        raise ValueError(f"signed L2b-2 requires --l2b-stage {L2B_N2_SELECTOR_PROFILE_ID}")

    profile = _selector_profile_for_authorization(config)
    if (
        profile.profile_id != L2B_N2_SELECTOR_PROFILE_ID
        or config.signed_l1a_authorization != L2B_N2_SIGNED_AUTHORIZATION_TOKEN
    ):
        raise ValueError(
            "signed L2b-2 requires --signed-l2b-authorization "
            f"{L2B_N2_SIGNED_AUTHORIZATION_TOKEN}"
        )
    stage = l2b_full_coverage_stage_spec(config.l2b_stage)
    if not stage.runtime_execution_enabled:
        raise RuntimeError(stage.runtime_block_reason or "L2b-2 runtime gate is blocked")
    if not stage.signed_authorization_available:
        raise RuntimeError("signed L2b-2 runtime gate requires signed authorization")
    if stage.signature_status != L2B_N2_SIGNATURE_STATUS:
        raise RuntimeError(f"signed L2b-2 requires signature status {L2B_N2_SIGNATURE_STATUS}")
    if stage.total_shards != 9:
        raise ValueError("signed L2b-2 requires exactly 9 total shards")
    if stage.rows_per_shard != 24:
        raise ValueError("signed L2b-2 requires exactly 24 rows per shard")
    if stage.full_matrix_planned_rows != 216:
        raise ValueError("signed L2b-2 requires exactly 216 total planned rows")
    if LOCKED_KERNEL_CLASSES != ("elementwise", "reduction", "matmul"):
        raise ValueError("signed L2b-2 requires elementwise/reduction/matmul kernels")
    if DTYPE_NAMES != ("fp32", "fp16", "bf16"):
        raise ValueError("signed L2b-2 requires fp32/fp16/bf16 dtype variants")
    if l2b_full_coverage_shard_ids() != (
        "elementwise__fp32",
        "elementwise__fp16",
        "elementwise__bf16",
        "reduction__fp32",
        "reduction__fp16",
        "reduction__bf16",
        "matmul__fp32",
        "matmul__fp16",
        "matmul__bf16",
    ):
        raise ValueError("signed L2b-2 shard ids do not match the signed packet")

    limits = stage.concurrency_limits
    if limits.get("max_gpu_concurrency", 0) > 4:
        raise ValueError("signed L2b-2 requires max_gpu_concurrency <= 4")
    if limits.get("max_container_concurrency", 0) > 40:
        raise ValueError("signed L2b-2 requires max_container_concurrency <= 40")
    if os.environ.get("TRITONGEN_MLFLOW") != "0":
        raise RuntimeError("TRITONGEN_MLFLOW=0 is required for signed L2b-2")
    if config.write_mode != "overwrite":
        raise ValueError("signed L2b-2 requires --overwrite and forbids resume")
    if config.output != profile.selector_placeholder_output:
        raise ValueError("signed L2b-2 selector command must not override --output")
    if config.grammar_mode_cell != "all":
        raise ValueError("signed L2b-2 selector command must plan all 12 cells")
    if config.scale_tier != stage.scale_tier:
        raise ValueError(f"signed L2b-2 requires --scale-tier {stage.scale_tier}")
    if config.n != 2:
        raise ValueError("signed L2b-2 requires --n 2")
    if config.repair_history_policy != "agentic_transcript_v1":
        raise ValueError(
            "signed L2b-2 requires --repair-history-policy agentic_transcript_v1"
        )
    if config.dry_plan or config.execution_plan:
        raise ValueError("runtime authorization does not apply to planning modes")
    if config.observability_mode != "off":
        raise ValueError("selector-level signed L2b-2 must not override observability")
    if (
        config.observability_experiment_id is not None
        or config.observability_run_id is not None
        or config.observability_output is not None
    ):
        raise ValueError("selector-level signed L2b-2 must not set observability paths")

    shards = build_l2b_full_coverage_shard_plan(
        stage_id=config.l2b_stage,
        shard_selector=config.l2b_shard_selector,
        repair_history_policy=config.repair_history_policy,
        command_mode="executable",
        repo_root=REPO_ROOT,
        signed_authorization_placeholder=L2B_N2_SIGNED_AUTHORIZATION_TOKEN,
        signed_authorization_option=profile.signed_authorization_option
        or "--signed-l2b-authorization",
    )
    if not shards:
        raise ValueError("signed L2b-2 requires a non-empty shard plan")
    if config.l2b_shard_selector == "all":
        if config.kernel_class != "all":
            raise ValueError("signed L2b-2 all-shards command requires --kernel-class all")
        if config.dtypes != DTYPE_NAMES:
            raise ValueError("signed L2b-2 all-shards command requires all signed dtypes")
        if len(shards) != stage.total_shards:
            raise ValueError("signed L2b-2 all-shards command requires exactly 9 shards")
        if sum(shard.planned_rows for shard in shards) != stage.full_matrix_planned_rows:
            raise ValueError("signed L2b-2 all-shards command requires 216 planned rows")
    elif config.l2b_shard_selector.startswith("wave:"):
        if config.kernel_class != "all":
            raise ValueError("signed L2b-2 wave command requires --kernel-class all")
        if config.dtypes != DTYPE_NAMES:
            raise ValueError("signed L2b-2 wave command requires all signed dtypes")
    else:
        if len(shards) != 1:
            raise ValueError("signed L2b-2 one-shard command requires exactly one shard")
        shard = shards[0]
        if config.kernel_class != shard.kernel_class:
            raise ValueError(
                "signed L2b-2 one-shard command requires matching --kernel-class"
            )
        if config.dtypes != (shard.dtype_variant,):
            raise ValueError("signed L2b-2 one-shard command requires matching --dtypes")

    for shard in shards:
        _validate_l2b_runtime_shard_plan(stage=stage, shard=shard)
    return shards


def _validate_l2b_runtime_shard_plan(
    *,
    stage: Any,
    shard: L2BFullCoverageShardPlan,
) -> None:
    expected_output_namespace = f"{stage.output_root}/{shard.shard_id}"
    expected_artifact_namespace = f"{stage.observability_root}/{shard.shard_id}"
    if shard.shard_id != f"{shard.kernel_class}__{shard.dtype_variant}":
        raise ValueError("signed L2b-2 shard id must equal kernel_class__dtype_variant")
    if shard.planned_cells != 12:
        raise ValueError("signed L2b-2 requires 12 planned cells per shard")
    if shard.planned_rows != 24:
        raise ValueError("signed L2b-2 requires 24 planned rows per shard")
    if shard.backend != "modal_local_model":
        raise ValueError("signed L2b-2 requires backend=modal_local_model")
    if shard.output_namespace != expected_output_namespace:
        raise ValueError("signed L2b-2 output namespace does not match shard id")
    if shard.artifact_namespace != expected_artifact_namespace:
        raise ValueError("signed L2b-2 artifact namespace does not match shard id")
    if not shard.fail_if_any_target_path_exists:
        raise ValueError("signed L2b-2 requires fail_if_any_target_path_exists=true")
    if shard.path_collision_policy != L1A_PATH_COLLISION_POLICY:
        raise ValueError("signed L2b-2 shard plan must fail if target paths exist")
    if shard.concurrency_limits.get("max_gpu_concurrency", 0) > 4:
        raise ValueError("signed L2b-2 shard requires max_gpu_concurrency <= 4")
    if shard.concurrency_limits.get("max_container_concurrency", 0) > 40:
        raise ValueError("signed L2b-2 shard requires max_container_concurrency <= 40")
    if shard.timing_observability.get("performance_evidence_authorized") is not False:
        raise ValueError("signed L2b-2 timing observability is sidecar-only")
    if shard.slow_cell_stop_policy.get("automatic_retry_authorized") is not False:
        raise ValueError("signed L2b-2 forbids automatic retry")
    if shard.slow_cell_stop_policy.get("automatic_resume_authorized") is not False:
        raise ValueError("signed L2b-2 forbids automatic resume")
    if L2B_N2_SIGNED_AUTHORIZATION_TOKEN not in shard.future_command:
        raise ValueError("signed L2b-2 future command must contain the signed token")

    _require_l1a_path(shard.output_namespace, root=stage.output_root, label="output root")
    _require_l1a_path(
        shard.artifact_namespace,
        root=stage.observability_root,
        label="observability root",
    )
    _require_absent_target(shard.output_namespace, label="output root")
    _require_absent_target(shard.artifact_namespace, label="observability root")

    for path in shard.output_paths["result_files"]:
        expected_prefix = f"{expected_output_namespace}/"
        if not str(path).startswith(expected_prefix):
            raise ValueError("signed L2b-2 result path is outside shard namespace")
        _require_l1a_path(str(path), root=expected_output_namespace, label="result")
        _require_absent_target(str(path), label="result")
    for path in shard.output_paths["content_hash_sidecars"]:
        expected_prefix = f"{expected_output_namespace}/"
        if not str(path).startswith(expected_prefix):
            raise ValueError("signed L2b-2 hash sidecar is outside shard namespace")
        _require_l1a_path(str(path), root=expected_output_namespace, label="hash sidecar")
        _require_absent_target(str(path), label="hash sidecar")
    for path in shard.artifact_paths["observability_event_files"]:
        expected_prefix = f"{expected_artifact_namespace}/"
        if not str(path).startswith(expected_prefix):
            raise ValueError("signed L2b-2 observability path is outside shard namespace")
        _require_l1a_path(
            str(path),
            root=expected_artifact_namespace,
            label="observability event",
        )
        _require_absent_target(str(path), label="observability event")
    for path in shard.artifact_paths["observability_summary_files"]:
        _require_l1a_path(
            str(path),
            root=expected_artifact_namespace,
            label="observability summary",
        )
        _require_absent_target(str(path), label="observability summary")
    for path in shard.artifact_paths["observability_hash_sidecars"]:
        _require_l1a_path(
            str(path),
            root=expected_artifact_namespace,
            label="observability hash sidecar",
        )
        _require_absent_target(str(path), label="observability hash sidecar")

    for label, root in (
        ("analysis", stage.analysis_root),
        ("reports", stage.reports_root),
        ("billing", stage.billing_root),
    ):
        path = str(shard.artifact_paths[f"{label}_namespace_glob"])
        if not path.startswith(f"{root}/{shard.shard_id}"):
            raise ValueError(f"signed L2b-2 {label} path is outside shard namespace")


def _selector_output_root_from_cells(
    cells: tuple[GrammarModeLauncherCellPlan, ...],
) -> str:
    roots = {Path(cell.output_path).parent.as_posix() for cell in cells}
    if len(roots) != 1:
        raise ValueError("signed selector cells must share one output root")
    return next(iter(roots))


def _selector_output_root_from_shards(
    shards: tuple[L2BFullCoverageShardPlan, ...],
) -> str:
    roots = {Path(shard.output_namespace).parent.as_posix() for shard in shards}
    if len(roots) != 1:
        raise ValueError("signed L2b selector shards must share one output root")
    return next(iter(roots))


def _require_l1a_path(path: str, *, root: str, label: str) -> None:
    target = (REPO_ROOT / path).resolve()
    allowed_root = (REPO_ROOT / root).resolve()
    try:
        target.relative_to(allowed_root)
    except ValueError as exc:
        raise ValueError(f"signed selector {label} path is outside {root}") from exc


def _require_absent_target(path: str, *, label: str) -> None:
    target = REPO_ROOT / path
    if target.exists():
        raise FileExistsError(
            f"signed selector {label} target already exists: {path}; "
            "retry/resume/delete is not authorized"
        )


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
    """Run requested Cluster 3 conditions and append deterministic rows."""

    if not isinstance(config, Cluster3RunnerConfig):
        raise TypeError("config must be Cluster3RunnerConfig")
    if config.dry_plan:
        raise ValueError("dry_plan configs must be handled by main before run_cluster3")
    if config.execution_plan:
        raise ValueError(
            "execution_plan configs must be handled by main before run_cluster3"
        )
    if config.condition == L1A_GRAMMAR_MODE_CP_SELECTOR:
        raise RuntimeError(
            f"{L1A_GRAMMAR_MODE_CP_SELECTOR} execution is not enabled by this "
            "local support branch"
        )
    deps = dependencies or RunnerDependencies()
    generation = deps.generation or _default_generation_call
    correctness = deps.correctness or _default_correctness_call
    dispatcher = deps.dispatcher or dispatch
    p_repair_loop = deps.p_repair_loop or run_p_repair_loop
    c_loop_runner = deps.c_loop_runner or run_cluster3_c_loop_from_f2
    pair_identity_validator = _resolve_pair_identity_validator(deps)

    rows: list[Cluster3EvalRow] = []
    audits: list[ConditionRouteAudit] = []
    observability = _open_observability_runtime(config, deps)
    run_start_monotonic_ns = time.perf_counter_ns()
    run_id = _stable_run_id(config)
    content_hash_sidecar = _build_runner_content_hash_sidecar(config)
    hashes_by_condition = content_hash_sidecar.generated_condition_hashes

    try:
        observability.record_run_started(monotonic_ns=run_start_monotonic_ns)
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
                            row_index = len(rows)
                            row_start_monotonic_ns = time.perf_counter_ns()
                            observability.record_row_started(
                                row_index=row_index,
                                condition=condition,
                                kernel_class=kernel_class,
                                kernel_name=kernel_name,
                                dtype=dtype,
                                base_seed=base_seed,
                                monotonic_ns=row_start_monotonic_ns,
                            )
                            row = _run_generated_cell(
                                condition=condition,
                                kernel_class=kernel_class,
                                kernel_name=kernel_name,
                                dtype=dtype,
                                base_seed=base_seed,
                                row_index=row_index,
                                config=config,
                                run_id=run_id,
                                generation=generation,
                                correctness=correctness,
                                dispatcher=dispatcher,
                                p_repair_loop=p_repair_loop,
                                c_loop_runner=c_loop_runner,
                                c3_hashes=hashes_by_condition[condition],
                                stats=stats,
                                observability=observability,
                            )
                            control_row = _resolve_control_row(
                                deps.no_p_control_resolver,
                                row,
                            )
                            if control_row is not None:
                                pair_identity_validator(row, control_row)
                            append_start_monotonic_ns = time.perf_counter_ns()
                            observability.record_stage_started(
                                stage="row_append",
                                row_index=row_index,
                                row=row,
                                monotonic_ns=append_start_monotonic_ns,
                            )
                            try:
                                result_logger.append(row)
                            except BaseException as exc:
                                observability.record_stage_failed(
                                    stage="row_append",
                                    row_index=row_index,
                                    row=row,
                                    error=exc,
                                    start_monotonic_ns=append_start_monotonic_ns,
                                    end_monotonic_ns=time.perf_counter_ns(),
                                )
                                raise
                            append_end_monotonic_ns = time.perf_counter_ns()
                            observability.record_stage_completed(
                                stage="row_append",
                                row_index=row_index,
                                row=row,
                                start_monotonic_ns=append_start_monotonic_ns,
                                end_monotonic_ns=append_end_monotonic_ns,
                            )
                            rows.append(row)
                            observability.record_row_completed(
                                row_index=row_index,
                                row=row,
                                start_monotonic_ns=row_start_monotonic_ns,
                                end_monotonic_ns=time.perf_counter_ns(),
                            )
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
    except BaseException as exc:
        observability.record_run_failed(
            error=exc,
            start_monotonic_ns=run_start_monotonic_ns,
            end_monotonic_ns=time.perf_counter_ns(),
        )
        raise
    else:
        observability.record_run_completed(
            row_count=len(rows),
            start_monotonic_ns=run_start_monotonic_ns,
            end_monotonic_ns=time.perf_counter_ns(),
        )
        observability.write_summary(row_count=len(rows))
    finally:
        observability.close()

    return Cluster3RunResult(
        rows=tuple(rows),
        route_audit=tuple(audits),
        output=config.output,
        write_mode=config.write_mode,
    )


def expand_condition_selector(selector: str) -> tuple[str, ...]:
    if selector == "all":
        return CLUSTER3_CONDITIONS
    if selector == L1A_GRAMMAR_MODE_CP_SELECTOR:
        raise ValueError(f"{L1A_GRAMMAR_MODE_CP_SELECTOR} is dry-plan only")
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


def _open_observability_runtime(
    config: Cluster3RunnerConfig,
    deps: RunnerDependencies,
) -> _Cluster3ObservabilityRuntime:
    if config.observability_mode == "off":
        return _Cluster3ObservabilityRuntime(config=config, mode="off")

    try:
        paths = _resolve_runner_observability_paths(config)
        git_commit = _git_stdout("rev-parse", "HEAD").lower()
        branch = _git_stdout("branch", "--show-current") or "detached"
        modal_context = _resolve_observability_modal_context(config, deps)
        logger_factory = deps.observability_logger_factory or ObservabilityJsonlAppendLogger
        logger = logger_factory(
            paths.event_path,
            experiment_id=config.observability_experiment_id or "",
            run_id=config.observability_run_id or "",
            result_path=config.output,
            summary_path=paths.summary_path,
            hash_path=paths.hash_path,
            git_commit=git_commit,
            mode=config.write_mode,
            fsync=True,
        )
        logger.open()
        next_event_sequence = 0
        if config.write_mode == "resume":
            next_event_sequence = len(load_observability_events(paths.event_path))
        return _Cluster3ObservabilityRuntime(
            config=config,
            mode=config.observability_mode,
            paths=paths,
            logger=logger,
            git_commit=git_commit,
            branch=branch,
            clock_scope_id=str(uuid.uuid4()),
            next_event_sequence=next_event_sequence,
            modal_context=modal_context,
            token_counts_provider=deps.token_counts_provider,
            cost_estimate_provider=deps.cost_estimate_provider,
        )
    except Exception as exc:
        if config.observability_mode == "required":
            raise
        return _Cluster3ObservabilityRuntime(
            config=config,
            mode=config.observability_mode,
            disabled_reason=type(exc).__name__,
        )


def _resolve_runner_observability_paths(
    config: Cluster3RunnerConfig,
) -> ObservabilityPaths:
    return resolve_observability_paths(
        config.output,
        event_path=config.observability_output,
        summary_path=_l1a_observability_summary_path(config),
    )


def _l1a_observability_summary_path(config: Cluster3RunnerConfig) -> Path | None:
    if (
        config.observability_experiment_id != L1A_EXPERIMENT_ID
        or config.observability_output is None
    ):
        return None
    output_stem = Path(config.output).stem
    return Path(config.observability_output).with_name(
        f"{output_stem}.observability.summary.json"
    )


def _resolve_observability_modal_context(
    config: Cluster3RunnerConfig,
    deps: RunnerDependencies,
) -> ObservabilityModalContext:
    try:
        if deps.modal_context_provider is None:
            raw_context = get_modal_runtime_context_or_unavailable(
                collect_current_ids=False
            )
        else:
            raw_context = normalize_modal_context(deps.modal_context_provider())
        return ObservabilityModalContext.model_validate(raw_context)
    except Exception:
        if config.observability_mode == "required":
            raise
        return ObservabilityModalContext.model_validate(
            get_modal_runtime_context_or_unavailable(collect_current_ids=False)
        )


def _observability_modal_context_summary(
    events: Sequence[ObservabilityEvent],
) -> dict[str, Any]:
    contexts = [event.modal_context for event in events if event.modal_context is not None]
    available_contexts = [
        context for context in contexts if context.modal_context_available
    ]
    return {
        "context_status": "available" if available_contexts else "unavailable",
        "events_with_modal_context": len(contexts),
        "events_with_available_context": len(available_contexts),
        "modal_context_sources": sorted(
            {context.modal_context_source for context in contexts}
        ),
    }


def _unavailable_observability_token_counts() -> ObservabilityTokenCounts:
    return ObservabilityTokenCounts(
        token_counts_available=False,
        token_count_source="unavailable",
        token_count_status="unavailable",
    )


def _unavailable_observability_cost_estimate() -> ObservabilityCostEstimate:
    return ObservabilityCostEstimate(
        cost_estimate_available=False,
        cost_estimate_status="unavailable",
        cost_estimate_method="unavailable",
    )


def _observability_row_identity(
    *,
    condition: str,
    kernel_class: str,
    kernel_name: str,
    dtype: str,
    base_seed: int,
    generation_seed: int | None = None,
    attempt_index: int | None = None,
    terminal_attempt_index: int | None = None,
    source_hash: str | None = None,
    row_sha256: str | None = None,
) -> ObservabilityRowIdentity:
    return ObservabilityRowIdentity(
        cluster="cluster3",
        condition=condition,
        kernel_class=kernel_class,
        kernel_name=kernel_name,
        dtype=dtype,
        base_seed=base_seed,
        generation_seed=generation_seed,
        attempt_index=attempt_index,
        terminal_attempt_index=terminal_attempt_index,
        source_hash=source_hash,
        row_sha256=row_sha256,
    )


def _observability_row_identity_from_row(row: Cluster3EvalRow) -> ObservabilityRowIdentity:
    row_json = row.to_json()
    return _observability_row_identity(
        condition=row.condition,
        kernel_class=row.kernel_class,
        kernel_name=row.kernel_name,
        dtype=row.dtype,
        base_seed=row.base_seed,
        generation_seed=row.terminal_generation_seed,
        attempt_index=row.attempt_index,
        terminal_attempt_index=row.terminal_attempt_index,
        source_hash=row.source_hash,
        row_sha256=_sha256(row_json),
    )


def _observability_attempt_identity_from_row(row: Cluster3EvalRow) -> ObservabilityAttemptIdentity:
    return ObservabilityAttemptIdentity(
        attempt_index=row.attempt_index,
        terminal_attempt_index=row.terminal_attempt_index,
        condition=row.condition,
    )


def _run_generated_cell(
    *,
    condition: str,
    kernel_class: str,
    kernel_name: str,
    dtype: str,
    base_seed: int,
    row_index: int,
    config: Cluster3RunnerConfig,
    run_id: str,
    generation: GenerationAdapter,
    correctness: CorrectnessAdapter,
    dispatcher: DispatcherAdapter,
    p_repair_loop: PRepairLoopCallable,
    c_loop_runner: CLoopRunnerCallable,
    c3_hashes: dict[str, str],
    stats: _ConditionRunStats,
    observability: _Cluster3ObservabilityRuntime,
) -> Cluster3EvalRow:
    c2_generation_condition = cluster3_to_cluster2_generation_condition(condition)
    base_prompt = _build_base_prompt(kernel_class, dtype)
    prompt_hash = _sha256(base_prompt)
    initial_seed = base_seed
    initial_attempt = ObservabilityAttemptIdentity(
        attempt_index=0,
        condition=condition,
    )
    initial_row_identity = _observability_row_identity(
        condition=condition,
        kernel_class=kernel_class,
        kernel_name=kernel_name,
        dtype=dtype,
        base_seed=base_seed,
        generation_seed=initial_seed,
        attempt_index=0,
    )
    diagnostic_source = _read_diagnostic_seed_source(config)
    if diagnostic_source is None:
        generation_start_monotonic_ns = time.perf_counter_ns()
        observability.record_stage_started_for_identity(
            stage="generation",
            row_index=row_index,
            row_identity=initial_row_identity,
            attempt=initial_attempt,
            condition=condition,
            monotonic_ns=generation_start_monotonic_ns,
        )
        try:
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
        except BaseException as exc:
            observability.record_stage_failed_for_identity(
                stage="generation",
                row_index=row_index,
                row_identity=initial_row_identity,
                attempt=initial_attempt,
                condition=condition,
                error=exc,
                start_monotonic_ns=generation_start_monotonic_ns,
                end_monotonic_ns=time.perf_counter_ns(),
            )
            raise
        observability.record_stage_completed_for_identity(
            stage="generation",
            row_index=row_index,
            row_identity=initial_row_identity,
            attempt=initial_attempt,
            condition=condition,
            start_monotonic_ns=generation_start_monotonic_ns,
            end_monotonic_ns=time.perf_counter_ns(),
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
    correctness_row_identity = _observability_row_identity(
        condition=condition,
        kernel_class=kernel_class,
        kernel_name=kernel_name,
        dtype=dtype,
        base_seed=base_seed,
        generation_seed=initial_seed,
        attempt_index=0,
        source_hash=_sha256(initial_source),
    )
    correctness_start_monotonic_ns = time.perf_counter_ns()
    observability.record_stage_started_for_identity(
        stage="correctness_eval",
        row_index=row_index,
        row_identity=correctness_row_identity,
        attempt=initial_attempt,
        condition=condition,
        monotonic_ns=correctness_start_monotonic_ns,
    )
    try:
        initial_payload = correctness(
            Cluster3CorrectnessRequest(identity=initial_identity, source=initial_source)
        )
    except BaseException as exc:
        observability.record_stage_failed_for_identity(
            stage="correctness_eval",
            row_index=row_index,
            row_identity=correctness_row_identity,
            attempt=initial_attempt,
            condition=condition,
            error=exc,
            start_monotonic_ns=correctness_start_monotonic_ns,
            end_monotonic_ns=time.perf_counter_ns(),
        )
        raise
    observability.record_stage_completed_for_identity(
        stage="correctness_eval",
        row_index=row_index,
        row_identity=correctness_row_identity,
        attempt=initial_attempt,
        condition=condition,
        start_monotonic_ns=correctness_start_monotonic_ns,
        end_monotonic_ns=time.perf_counter_ns(),
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
        c_result = _timed_call_c_loop(
            observability=observability,
            row_index=row_index,
            row_identity=correctness_row_identity,
            attempt=initial_attempt,
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
        p_result = _timed_run_p_loop(
            observability=observability,
            row_index=row_index,
            row_identity=correctness_row_identity,
            attempt=initial_attempt,
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
            and condition in CLUSTER3_C_ACTIVE_CONDITIONS
        ):
            c_result = _timed_call_c_loop(
                observability=observability,
                row_index=row_index,
                row_identity=correctness_row_identity,
                attempt=initial_attempt,
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


def _timed_run_p_loop(
    *,
    observability: _Cluster3ObservabilityRuntime,
    row_index: int,
    row_identity: ObservabilityRowIdentity,
    attempt: ObservabilityAttemptIdentity,
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
    start_monotonic_ns = time.perf_counter_ns()
    observability.record_stage_started_for_identity(
        stage="p_repair",
        row_index=row_index,
        row_identity=row_identity,
        attempt=attempt,
        condition=condition,
        monotonic_ns=start_monotonic_ns,
    )
    try:
        result = _run_p_loop(
            p_repair_loop=p_repair_loop,
            condition=condition,
            c2_generation_condition=c2_generation_condition,
            base_prompt=base_prompt,
            base_seed=base_seed,
            sample_index=sample_index,
            kernel_class=kernel_class,
            kernel_name=kernel_name,
            dtype=dtype,
            config=config,
            run_id=run_id,
            generation=generation,
            correctness=correctness,
            seed_attempt=seed_attempt,
            runtime=runtime,
            stats=stats,
        )
    except BaseException as exc:
        observability.record_stage_failed_for_identity(
            stage="p_repair",
            row_index=row_index,
            row_identity=row_identity,
            attempt=attempt,
            condition=condition,
            error=exc,
            start_monotonic_ns=start_monotonic_ns,
            end_monotonic_ns=time.perf_counter_ns(),
        )
        raise
    observability.record_stage_completed_for_identity(
        stage="p_repair",
        row_index=row_index,
        row_identity=row_identity,
        attempt=attempt,
        condition=condition,
        start_monotonic_ns=start_monotonic_ns,
        end_monotonic_ns=time.perf_counter_ns(),
    )
    return result


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


def _timed_call_c_loop(
    *,
    observability: _Cluster3ObservabilityRuntime,
    row_index: int,
    row_identity: ObservabilityRowIdentity,
    attempt: ObservabilityAttemptIdentity,
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
    start_monotonic_ns = time.perf_counter_ns()
    observability.record_stage_started_for_identity(
        stage="c_repair",
        row_index=row_index,
        row_identity=row_identity,
        attempt=attempt,
        condition=condition,
        monotonic_ns=start_monotonic_ns,
    )
    try:
        result = _call_c_loop(
            c_loop_runner=c_loop_runner,
            condition=condition,
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
            repair_budget=repair_budget,
            model_config=model_config,
            repair_history_config=repair_history_config,
            provenance_base=provenance_base,
            stats=stats,
        )
    except BaseException as exc:
        observability.record_stage_failed_for_identity(
            stage="c_repair",
            row_index=row_index,
            row_identity=row_identity,
            attempt=attempt,
            condition=condition,
            error=exc,
            start_monotonic_ns=start_monotonic_ns,
            end_monotonic_ns=time.perf_counter_ns(),
        )
        raise
    observability.record_stage_completed_for_identity(
        stage="c_repair",
        row_index=row_index,
        row_identity=row_identity,
        attempt=attempt,
        condition=condition,
        start_monotonic_ns=start_monotonic_ns,
        end_monotonic_ns=time.perf_counter_ns(),
    )
    return result


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


def _c_terminal_prompt_metadata(c_result: Cluster3CLoopResult | None) -> Any | None:
    if c_result is None:
        return None
    repair_result = c_result.cluster2_repair_result
    return _metadata_attr(repair_result, "terminal_prompt_metadata")


def _metadata_attr(metadata: Any | None, field_name: str) -> Any | None:
    if metadata is None:
        return None
    if isinstance(metadata, Mapping):
        return metadata.get(field_name)
    return getattr(metadata, field_name, None)


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
    c_prompt_metadata = _c_terminal_prompt_metadata(c_result)
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
        "c_history_policy": _metadata_attr(
            c_prompt_metadata,
            "repair_history_policy",
        ),
        "c_repair_prompt_template_version": _metadata_attr(
            c_prompt_metadata,
            "repair_prompt_template_version",
        ),
        "c_repair_prompt_renderer_version": _metadata_attr(
            c_prompt_metadata,
            "repair_prompt_renderer_version",
        ),
        "c_repair_anchor_attempt_index": _metadata_attr(
            c_prompt_metadata,
            "repair_anchor_attempt_index",
        ),
        "c_repair_latest_attempt_index": _metadata_attr(
            c_prompt_metadata,
            "repair_latest_attempt_index",
        ),
        "c_repair_history_attempt_count": _metadata_attr(
            c_prompt_metadata,
            "repair_history_attempt_count",
        ),
        "c_repair_prompt_sha256": _metadata_attr(
            c_prompt_metadata,
            "repair_prompt_sha256",
        ),
        "c_repair_prompt_char_count": _metadata_attr(
            c_prompt_metadata,
            "repair_prompt_char_count",
        ),
        "c_repair_max_prompt_chars": _metadata_attr(
            c_prompt_metadata,
            "repair_max_prompt_chars",
        ),
        "c_repair_include_latest_source": _metadata_attr(
            c_prompt_metadata,
            "repair_include_latest_source",
        ),
        "c_repair_anchor_source_hash": _metadata_attr(
            c_prompt_metadata,
            "repair_anchor_source_hash",
        ),
        "c_repair_latest_source_hash": _metadata_attr(
            c_prompt_metadata,
            "repair_latest_source_hash",
        ),
        "c_repair_history_summary_sha256": _metadata_attr(
            c_prompt_metadata,
            "repair_history_summary_sha256",
        ),
        "c_repair_history_error_code": _metadata_attr(
            c_prompt_metadata,
            "repair_history_error_code",
        ),
    }
    return generated_row(
        condition=condition,
        attempt_index=terminal_attempt_index or 0,
        kernel_class=kernel_class,
        kernel_name=kernel_name,
        dtype=dtype,
        base_seed=base_seed,
        source_hash=_sha256(final_source),
        grammar_active=condition in CLUSTER3_G_ACTIVE_CONDITIONS,
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
    if condition not in CLUSTER3_G_ACTIVE_CONDITIONS:
        return {
            "grammar_mode": "grammar_off",
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
        "grammar_mode": grammar_variant,
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
    if condition not in CLUSTER3_P_ACTIVE_CONDITIONS:
        return None
    paired = pair_for_condition(condition)
    return paired if paired in {"none", "G"} else None


def _stable_run_id(config: Cluster3RunnerConfig) -> str:
    payload = json.dumps(
        config.to_dict(include_observability=False),
        sort_keys=True,
        separators=(",", ":"),
    )
    return "cluster3-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _git_stdout(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


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


def _validate_observability_config(config: Cluster3RunnerConfig) -> None:
    _require_member(
        config.observability_mode,
        OBSERVABILITY_MODE_CHOICES,
        "observability_mode",
    )
    if config.dry_plan or config.execution_plan:
        return
    if config.observability_mode == "off":
        return
    _require_non_empty_str(
        config.observability_experiment_id,
        "observability_experiment_id",
    )
    _require_non_empty_str(config.observability_run_id, "observability_run_id")
    if config.write_mode == "resume":
        raise ValueError(
            "observability resume is not supported in O1; use observability_mode='off' "
            "or start a new overwrite sidecar"
        )
    if config.observability_output is not None:
        _require_non_empty_str(config.observability_output, "observability_output")


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
