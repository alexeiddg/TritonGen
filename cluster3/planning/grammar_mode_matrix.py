"""Local 12-cell grammar-mode x C x P planning matrix.

This module defines labels, paths, and selector command metadata for launch
packets. It does not invoke generation, Modal, correctness evaluation, output
writing, tracking, or artifact refreshes.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path

from cluster2.constants import DTYPE_NAMES
from cluster3.constants import P_HISTORY_POLICY_V1
from shared.eval.correctness_shapes import LOCKED_KERNEL_CLASSES
from shared.factors.cells import FactorCell, require_valid_factor_cell
from shared.factors.grammar_modes import (
    GRAMMAR_MODE_VALUES,
    GrammarMode,
    grammar_mode_config,
)


@dataclass(frozen=True)
class GrammarModeCellSpec:
    """One planned grammar-mode/C/P cell."""

    condition_name: str
    factor_cell: FactorCell
    grammar_mode: GrammarMode
    grammar_active: bool
    grammar_variant: str | None
    grammar_path: str | None
    grammar_claim_scope: str | None
    correctness_feedback_active: bool
    compile_feedback_active: bool
    repair_history_policy: str
    output_namespace_suffix: str
    expected_eligibility_notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


L1A_GRAMMAR_MODE_CP_SELECTOR = "grammar_mode_cp_12cell"
L1A_EXPERIMENT_ID = "full_pipeline_grammar_mode_cp_factorial_v1"
L1A_SCALE_NAMESPACE = "l1a_n1"
L1A_OUTPUT_ROOT = (
    "outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1"
)
L1A_OBSERVABILITY_ROOT = (
    "artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1"
)
L1A_RUN_ID_PREFIX = "full_pipeline_grammar_mode_cp_factorial_v1_l1a_n1"
L1B_SCALE_NAMESPACE = "l1b_n5"
L1B_OUTPUT_ROOT = (
    "outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1b_n5"
)
L1B_OBSERVABILITY_ROOT = (
    "artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1b_n5"
)
L1B_RUN_ID_PREFIX = "full_pipeline_grammar_mode_cp_factorial_v1_l1b_n5"
L2_SCALE_NAMESPACE = "l2_n20"
L2_OUTPUT_ROOT = (
    "outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20"
)
L2_OBSERVABILITY_ROOT = (
    "artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20"
)
L2_RUN_ID_PREFIX = "full_pipeline_grammar_mode_cp_factorial_v1_l2_n20"
L2B_N2_SELECTOR_PROFILE_ID = "l2b_n2_full_coverage"
L2B_N20_SELECTOR_PROFILE_ID = "l2b_n20_full_coverage"
L2B_N20_ATTEMPT2_SELECTOR_PROFILE_ID = "l2b_n20_attempt2_full_coverage"
L2B_SELECTOR_PROFILE_IDS = (
    L2B_N2_SELECTOR_PROFILE_ID,
    L2B_N20_SELECTOR_PROFILE_ID,
    L2B_N20_ATTEMPT2_SELECTOR_PROFILE_ID,
)
L2B_N2_SCALE_NAMESPACE = "l2b_n2"
L2B_N20_SCALE_NAMESPACE = "l2b_n20"
L2B_N20_ATTEMPT2_SCALE_NAMESPACE = "l2b_n20_attempt2"
L2B_N2_OUTPUT_ROOT = (
    "outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2"
)
L2B_N20_OUTPUT_ROOT = (
    "outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20"
)
L2B_N20_ATTEMPT2_OUTPUT_ROOT = (
    "outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2"
)
L2B_N2_OBSERVABILITY_ROOT = (
    "artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2"
)
L2B_N20_OBSERVABILITY_ROOT = (
    "artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/"
    "l2b_n20"
)
L2B_N20_ATTEMPT2_OBSERVABILITY_ROOT = (
    "artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/"
    "l2b_n20_attempt2"
)
L2B_N2_ANALYSIS_ROOT = (
    "artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2"
)
L2B_N20_ANALYSIS_ROOT = (
    "artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20"
)
L2B_N20_ATTEMPT2_ANALYSIS_ROOT = (
    "artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2"
)
L2B_N2_REPORTS_ROOT = (
    "artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2"
)
L2B_N20_REPORTS_ROOT = (
    "artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20"
)
L2B_N20_ATTEMPT2_REPORTS_ROOT = (
    "artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2"
)
L2B_N2_BILLING_ROOT = (
    "artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2"
)
L2B_N20_BILLING_ROOT = (
    "artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20"
)
L2B_N20_ATTEMPT2_BILLING_ROOT = (
    "artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2"
)
L2B_N2_RUN_ID_PREFIX = (
    "full_pipeline_grammar_mode_cp_factorial_v1_l2b_n2_full_coverage"
)
L2B_N20_RUN_ID_PREFIX = (
    "full_pipeline_grammar_mode_cp_factorial_v1_l2b_n20_full_coverage"
)
L2B_N20_ATTEMPT2_RUN_ID_PREFIX = (
    "full_pipeline_grammar_mode_cp_factorial_v1_l2b_n20_attempt2_full_coverage"
)
L2B_N2_SIGNED_AUTHORIZATION_TOKEN = (
    "FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N2_FULL_COVERAGE_AUTHORIZATION_PACKET_V1"
)
L2B_N20_SIGNED_AUTHORIZATION_TOKEN = (
    "FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_FULL_COVERAGE_AUTHORIZATION_PACKET_V1"
)
L2B_N20_ATTEMPT2_SIGNED_AUTHORIZATION_TOKEN = (
    "FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_ATTEMPT2_AUTHORIZATION_PACKET_V1"
)
L2B_N2_RECOVERY_MISSING28_AUTHORIZATION_MARKER = "RECOVERY_MISSING28"
L2B_N2_SIGNATURE_STATUS = "SIGNED_FOR_L2B_N2_ONLY"
L2B_N20_SIGNATURE_STATUS = "SIGNED_FOR_L2B_N20_ONLY"
L2B_N20_ATTEMPT2_SIGNATURE_STATUS = "SIGNED_FOR_L2B_N20_ATTEMPT2_ONLY"
L1A_PATH_COLLISION_POLICY = "fail_if_any_target_path_exists"
L1A_SIGNED_AUTHORIZATION_PLACEHOLDER = "SIGNED_L1A_PACKET_ID_REQUIRED"
L1B_SIGNED_AUTHORIZATION_PLACEHOLDER = "SIGNED_L1B_PACKET_ID_REQUIRED"
L2_SIGNED_AUTHORIZATION_PLACEHOLDER = "SIGNED_L2_PACKET_ID_REQUIRED"
L2B_SIGNED_AUTHORIZATION_PLACEHOLDER = "SIGNED_L2B_PACKET_NOT_APPROVED"
L1A_EXECUTABLE_SELECTOR_SUPPORT_STATUS = (
    "EXECUTABLE_SELECTOR_PRESENT_AUTHORIZATION_REQUIRED_NO_EXECUTION"
)
L2_EXECUTABLE_SELECTOR_SUPPORT_STATUS = (
    "L2_SIGNED_RUNTIME_GATE_ENABLED_NO_EXECUTION"
)
L2B_N2_EXECUTABLE_SELECTOR_SUPPORT_STATUS = (
    "L2B_N2_SIGNED_RUNTIME_GATE_ENABLED_NO_EXECUTION"
)
L2B_N20_EXECUTABLE_SELECTOR_SUPPORT_STATUS = (
    "L2B_N20_SIGNED_RUNTIME_GATE_ENABLED_NO_EXECUTION"
)
L2B_N20_ATTEMPT2_EXECUTABLE_SELECTOR_SUPPORT_STATUS = (
    "L2B_N20_ATTEMPT2_SIGNED_RUNTIME_GATE_ENABLED_NO_EXECUTION"
)
L2B_EXECUTABLE_SELECTOR_SUPPORT_STATUS = (
    "L2B_LOCAL_PLAN_ONLY_RUNTIME_DISABLED_NO_SIGNED_TOKEN"
)
L2B_BACKEND_CURRENT = "modal_local_model"
L2B_BACKEND_TODO = "fireworks_api"
L2B_TOTAL_SHARDS = len(LOCKED_KERNEL_CLASSES) * len(DTYPE_NAMES)
L2B_PLANNED_CELLS_PER_SHARD = 12
L2B_TIMING_OBSERVABILITY_REQUIRED_DIAGNOSTICS = (
    "wall_clock_seconds_per_row",
    "generation_attempt_count",
    "compile_attempt_count",
    "correctness_call_count",
    "p_repair_attempt_count",
    "c_repair_attempt_count",
    "terminal_failure_type",
    "timeout_or_stop_reason",
)
L2B_KNOWN_HIGH_COST_CELL_ID = "task_agnostic__c_on__p_on"
L2B_KNOWN_HIGH_COST_CELL_RISK_NOTE = (
    "task_agnostic__c_on__p_on is expected to be the slowest cell because it "
    "combines the broadest grammar mode with both P and C repair pathways. "
    "L2b budget estimates must not assume uniform row time across cells, and "
    "this is another reason sharding is mandatory so one slow path does not "
    "block every kernel/dtype result."
)
L2B_SLOW_CELL_STOP_CLASSIFICATION = "SLOW_CELL_BUDGET_EXCEEDED"


def l2b_timing_observability_contract() -> dict[str, object]:
    """Return the sidecar-only L2b timing metadata contract."""

    return {
        "scope": "per_cell_and_per_shard_sidecar_metadata_only",
        "required_diagnostics": L2B_TIMING_OBSERVABILITY_REQUIRED_DIAGNOSTICS,
        "scientific_result_row_schema_mutation": False,
        "performance_evidence_authorized": False,
        "allowed_uses": (
            "operational_budgeting",
            "slow_cell_identification",
        ),
        "disallowed_uses": (
            "speedup_claims",
            "performance_claims",
            "paper_evidence",
        ),
        "known_high_cost_cell": L2B_KNOWN_HIGH_COST_CELL_ID,
        "known_high_cost_cell_risk_note": L2B_KNOWN_HIGH_COST_CELL_RISK_NOTE,
    }


def l2b_slow_cell_stop_policy() -> dict[str, object]:
    """Return the signed-runtime stop policy for slow L2b cells."""

    return {
        "signed_wall_clock_budget_required": True,
        "budget_value": "REQUIRED_IN_SIGNED_PACKET",
        "trigger": "any_single_cell_exceeds_signed_wall_clock_budget",
        "active_row_policy": "finish_active_row_if_safe_then_stop_shard",
        "classification": L2B_SLOW_CELL_STOP_CLASSIFICATION,
        "automatic_retry_authorized": False,
        "automatic_resume_authorized": False,
        "preserve_partial_shard_audit": True,
    }


@dataclass(frozen=True)
class GrammarModeLauncherCellPlan:
    """One local dry-plan entry for a future 12-cell L1a launcher."""

    selector: str
    condition_name: str
    condition_id: str
    factor_cell: FactorCell
    runner_condition: FactorCell
    grammar_mode: GrammarMode
    grammar_active: bool
    grammar_variant: str | None
    grammar_path: str | None
    grammar_sha256: str | None
    grammar_claim_scope: str | None
    correctness_feedback_active: bool
    compile_feedback_active: bool
    repair_history_policy: str
    output_namespace_suffix: str
    output_path: str
    content_hash_sidecar_path: str
    observability_event_path: str
    observability_summary_path: str
    observability_hash_path: str
    observability_experiment_id: str
    observability_run_id_suffix: str
    observability_join_key: str
    path_collision_policy: str
    write_mode_required: str
    command_mode: str
    command_selector: str
    command_grammar_argument: str | None
    executable_command: str
    signed_authorization_placeholder: str | None
    execution_role: str
    support_status: str
    expected_eligibility_notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class L2BFullCoverageStageSpec:
    """One compressed L2b full-coverage planning stage."""

    selector_profile_id: str
    rung: str
    label: str
    scale_tier: str
    n: int
    scale_namespace: str
    output_root: str
    observability_root: str
    analysis_root: str
    reports_root: str
    billing_root: str
    run_id_prefix: str
    total_shards: int
    planned_cells_per_shard: int
    rows_per_shard: int
    full_matrix_planned_rows: int
    backend: str
    runtime_execution_enabled: bool
    runtime_block_reason: str
    signed_authorization_available: bool
    signature_status: str
    dependency_gate: str
    concurrency_limits: Mapping[str, object]
    timing_observability: Mapping[str, object]
    slow_cell_stop_policy: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class L2BFullCoverageShardPlan:
    """One deterministic L2b kernel_class x dtype shard plan."""

    shard_id: str
    kernel_class: str
    dtype_variant: str
    planned_cells: int
    planned_rows: int
    backend: str
    scale_namespace: str
    output_namespace: str
    artifact_namespace: str
    output_paths: Mapping[str, object]
    artifact_paths: Mapping[str, object]
    future_command: str
    cell_commands: tuple[str, ...]
    concurrency_limits: Mapping[str, object]
    timing_observability: Mapping[str, object]
    slow_cell_stop_policy: Mapping[str, object]
    fail_if_any_target_path_exists: bool
    path_collision_policy: str
    support_status: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_l1a_grammar_mode_cp_matrix(
    *,
    repair_history_policy: str = P_HISTORY_POLICY_V1,
) -> tuple[GrammarModeCellSpec, ...]:
    """Return the 12 local specs for ``grammar_mode x C x P`` L1a planning."""

    cells: list[GrammarModeCellSpec] = []
    for grammar_mode in GRAMMAR_MODE_VALUES:
        for correctness_feedback_active, compile_feedback_active in (
            (False, False),
            (True, False),
            (False, True),
            (True, True),
        ):
            config = grammar_mode_config(grammar_mode)
            factor_parts: list[str] = []
            if config.grammar_active:
                factor_parts.append("G")
            if correctness_feedback_active:
                factor_parts.append("C")
            if compile_feedback_active:
                factor_parts.append("P")
            factor_cell = require_valid_factor_cell(
                "+".join(factor_parts) if factor_parts else "none"
            )
            cells.append(
                GrammarModeCellSpec(
                    condition_name=_condition_name(
                        grammar_mode=grammar_mode,
                        correctness_feedback_active=correctness_feedback_active,
                        compile_feedback_active=compile_feedback_active,
                    ),
                    factor_cell=factor_cell,
                    grammar_mode=config.grammar_mode,
                    grammar_active=config.grammar_active,
                    grammar_variant=config.grammar_variant,
                    grammar_path=config.grammar_path,
                    grammar_claim_scope=config.grammar_claim_scope,
                    correctness_feedback_active=correctness_feedback_active,
                    compile_feedback_active=compile_feedback_active,
                    repair_history_policy=repair_history_policy,
                    output_namespace_suffix=_output_namespace_suffix(
                        grammar_mode=grammar_mode,
                        correctness_feedback_active=correctness_feedback_active,
                        compile_feedback_active=compile_feedback_active,
                    ),
                    expected_eligibility_notes=_eligibility_notes(
                        grammar_active=config.grammar_active,
                        correctness_feedback_active=correctness_feedback_active,
                        compile_feedback_active=compile_feedback_active,
                    ),
                )
            )
    _validate_unique_specs(cells)
    return tuple(cells)


def build_l1a_launcher_dry_plan(
    *,
    repair_history_policy: str = P_HISTORY_POLICY_V1,
    cell_selector: str = "all",
    output_root: str | Path = L1A_OUTPUT_ROOT,
    observability_root: str | Path = L1A_OBSERVABILITY_ROOT,
    run_id_prefix: str = L1A_RUN_ID_PREFIX,
    scale_tier: str = "smoke",
    n: int = 1,
    kernel_class_selector: str = "elementwise",
    dtypes: tuple[str, ...] = ("fp32",),
    repo_root: str | Path | None = None,
) -> tuple[GrammarModeLauncherCellPlan, ...]:
    """Return deterministic dry-plan entries for the 12-cell selector."""

    return _build_l1a_launcher_plan(
        repair_history_policy=repair_history_policy,
        cell_selector=cell_selector,
        output_root=output_root,
        observability_root=observability_root,
        run_id_prefix=run_id_prefix,
        scale_tier=scale_tier,
        n=n,
        kernel_class_selector=kernel_class_selector,
        dtypes=dtypes,
        repo_root=repo_root,
        command_mode="dry_plan",
    )


def build_l1a_launcher_executable_plan(
    *,
    repair_history_policy: str = P_HISTORY_POLICY_V1,
    cell_selector: str = "all",
    output_root: str | Path = L1A_OUTPUT_ROOT,
    observability_root: str | Path = L1A_OBSERVABILITY_ROOT,
    run_id_prefix: str = L1A_RUN_ID_PREFIX,
    scale_tier: str = "smoke",
    n: int = 1,
    kernel_class_selector: str = "elementwise",
    dtypes: tuple[str, ...] = ("fp32",),
    repo_root: str | Path | None = None,
    signed_authorization_placeholder: str = L1A_SIGNED_AUTHORIZATION_PLACEHOLDER,
    signed_authorization_option: str = "--signed-l1a-authorization",
    support_status: str = L1A_EXECUTABLE_SELECTOR_SUPPORT_STATUS,
) -> tuple[GrammarModeLauncherCellPlan, ...]:
    """Return executable-selector command plans without running them."""

    return _build_l1a_launcher_plan(
        repair_history_policy=repair_history_policy,
        cell_selector=cell_selector,
        output_root=output_root,
        observability_root=observability_root,
        run_id_prefix=run_id_prefix,
        scale_tier=scale_tier,
        n=n,
        kernel_class_selector=kernel_class_selector,
        dtypes=dtypes,
        repo_root=repo_root,
        command_mode="executable",
        signed_authorization_placeholder=signed_authorization_placeholder,
        signed_authorization_option=signed_authorization_option,
        support_status=support_status,
    )


def l2b_full_coverage_stage_choices() -> tuple[str, ...]:
    """Return accepted compressed L2b selector/profile identifiers."""

    return L2B_SELECTOR_PROFILE_IDS


def l2b_full_coverage_shard_ids() -> tuple[str, ...]:
    """Return deterministic shard ids in repo-backed kernel/dtype order."""

    return tuple(
        _l2b_shard_id(kernel_class, dtype_variant)
        for kernel_class in LOCKED_KERNEL_CLASSES
        for dtype_variant in DTYPE_NAMES
    )


def l2b_full_coverage_stage_spec(stage_id: str) -> L2BFullCoverageStageSpec:
    """Return the local-only L2b stage spec or raise ``ValueError``."""

    if stage_id == L2B_N2_SELECTOR_PROFILE_ID:
        n = 2
        rows_per_shard = L2B_PLANNED_CELLS_PER_SHARD * n
        return L2BFullCoverageStageSpec(
            selector_profile_id=L2B_N2_SELECTOR_PROFILE_ID,
            rung="L2b-2",
            label="L2b-2 n=2 sharded full coverage signed-ready plan",
            scale_tier="development",
            n=n,
            scale_namespace=L2B_N2_SCALE_NAMESPACE,
            output_root=L2B_N2_OUTPUT_ROOT,
            observability_root=L2B_N2_OBSERVABILITY_ROOT,
            analysis_root=L2B_N2_ANALYSIS_ROOT,
            reports_root=L2B_N2_REPORTS_ROOT,
            billing_root=L2B_N2_BILLING_ROOT,
            run_id_prefix=L2B_N2_RUN_ID_PREFIX,
            total_shards=L2B_TOTAL_SHARDS,
            planned_cells_per_shard=L2B_PLANNED_CELLS_PER_SHARD,
            rows_per_shard=rows_per_shard,
            full_matrix_planned_rows=L2B_TOTAL_SHARDS * rows_per_shard,
            backend=L2B_BACKEND_CURRENT,
            runtime_execution_enabled=True,
            runtime_block_reason=None,
            signed_authorization_available=True,
            signature_status=L2B_N2_SIGNATURE_STATUS,
            dependency_gate="L2b-0 local planning selector support",
            concurrency_limits={
                "max_gpu_concurrency": 4,
                "max_container_concurrency": 40,
                "policy": "aggressive_but_bounded_smoke_parallelism",
                "backend": L2B_BACKEND_CURRENT,
            },
            timing_observability=l2b_timing_observability_contract(),
            slow_cell_stop_policy=l2b_slow_cell_stop_policy(),
        )
    if stage_id == L2B_N20_SELECTOR_PROFILE_ID:
        n = 20
        rows_per_shard = L2B_PLANNED_CELLS_PER_SHARD * n
        return L2BFullCoverageStageSpec(
            selector_profile_id=L2B_N20_SELECTOR_PROFILE_ID,
            rung="L2b-4",
            label="L2b-4 n=20 sharded full coverage signed-ready plan",
            scale_tier="paper",
            n=n,
            scale_namespace=L2B_N20_SCALE_NAMESPACE,
            output_root=L2B_N20_OUTPUT_ROOT,
            observability_root=L2B_N20_OBSERVABILITY_ROOT,
            analysis_root=L2B_N20_ANALYSIS_ROOT,
            reports_root=L2B_N20_REPORTS_ROOT,
            billing_root=L2B_N20_BILLING_ROOT,
            run_id_prefix=L2B_N20_RUN_ID_PREFIX,
            total_shards=L2B_TOTAL_SHARDS,
            planned_cells_per_shard=L2B_PLANNED_CELLS_PER_SHARD,
            rows_per_shard=rows_per_shard,
            full_matrix_planned_rows=L2B_TOTAL_SHARDS * rows_per_shard,
            backend=L2B_BACKEND_CURRENT,
            runtime_execution_enabled=True,
            runtime_block_reason=None,
            signed_authorization_available=True,
            signature_status=L2B_N20_SIGNATURE_STATUS,
            dependency_gate="L2b-2 recovery completion and clean n20 authorization",
            concurrency_limits={
                "max_gpu_concurrency": 4,
                "max_container_concurrency": 40,
                "wave_1_max_gpu_concurrency": 4,
                "wave_1_max_container_concurrency": 40,
                "wave_2_max_gpu_concurrency": 4,
                "wave_2_max_container_concurrency": 40,
                "wave_3_max_gpu_concurrency": 4,
                "wave_3_max_container_concurrency": 40,
                "wave_4_max_gpu_concurrency": 2,
                "wave_4_max_container_concurrency": 20,
                "max_estimated_cost_usd": 400,
                "max_reconciled_billing_cost_usd": 500,
                "backend": L2B_BACKEND_CURRENT,
            },
            timing_observability=l2b_timing_observability_contract(),
            slow_cell_stop_policy=l2b_slow_cell_stop_policy(),
        )
    if stage_id == L2B_N20_ATTEMPT2_SELECTOR_PROFILE_ID:
        n = 20
        rows_per_shard = L2B_PLANNED_CELLS_PER_SHARD * n
        return L2BFullCoverageStageSpec(
            selector_profile_id=L2B_N20_ATTEMPT2_SELECTOR_PROFILE_ID,
            rung="L2b-4",
            label="L2b-4 n=20 attempt2 sharded full coverage signed plan",
            scale_tier="paper",
            n=n,
            scale_namespace=L2B_N20_ATTEMPT2_SCALE_NAMESPACE,
            output_root=L2B_N20_ATTEMPT2_OUTPUT_ROOT,
            observability_root=L2B_N20_ATTEMPT2_OBSERVABILITY_ROOT,
            analysis_root=L2B_N20_ATTEMPT2_ANALYSIS_ROOT,
            reports_root=L2B_N20_ATTEMPT2_REPORTS_ROOT,
            billing_root=L2B_N20_ATTEMPT2_BILLING_ROOT,
            run_id_prefix=L2B_N20_ATTEMPT2_RUN_ID_PREFIX,
            total_shards=L2B_TOTAL_SHARDS,
            planned_cells_per_shard=L2B_PLANNED_CELLS_PER_SHARD,
            rows_per_shard=rows_per_shard,
            full_matrix_planned_rows=L2B_TOTAL_SHARDS * rows_per_shard,
            backend=L2B_BACKEND_CURRENT,
            runtime_execution_enabled=True,
            runtime_block_reason=None,
            signed_authorization_available=True,
            signature_status=L2B_N20_ATTEMPT2_SIGNATURE_STATUS,
            dependency_gate=(
                "L2b-2 recovery completion and archived l2b_n20 partial attempt"
            ),
            concurrency_limits={
                "max_gpu_concurrency": 4,
                "max_container_concurrency": 40,
                "wave_1_max_gpu_concurrency": 4,
                "wave_1_max_container_concurrency": 40,
                "wave_2_max_gpu_concurrency": 4,
                "wave_2_max_container_concurrency": 40,
                "wave_3_max_gpu_concurrency": 4,
                "wave_3_max_container_concurrency": 40,
                "wave_4_max_gpu_concurrency": 2,
                "wave_4_max_container_concurrency": 20,
                "max_estimated_cost_usd": 400,
                "max_reconciled_billing_cost_usd": 500,
                "backend": L2B_BACKEND_CURRENT,
            },
            timing_observability=l2b_timing_observability_contract(),
            slow_cell_stop_policy=l2b_slow_cell_stop_policy(),
        )
    allowed = ", ".join(l2b_full_coverage_stage_choices())
    raise ValueError(f"l2b_stage must be one of: {allowed}; got {stage_id!r}")


def build_l2b_full_coverage_shard_plan(
    *,
    stage_id: str,
    shard_selector: str = "all",
    cell_selector: str | tuple[str, ...] = "all",
    repair_history_policy: str = P_HISTORY_POLICY_V1,
    command_mode: str = "executable",
    repo_root: str | Path | None = None,
    output_root: str | Path | None = None,
    observability_root: str | Path | None = None,
    analysis_root: str | Path | None = None,
    reports_root: str | Path | None = None,
    billing_root: str | Path | None = None,
    signed_authorization_placeholder: str = L2B_SIGNED_AUTHORIZATION_PLACEHOLDER,
    signed_authorization_option: str = "--signed-l2b-authorization",
) -> tuple[L2BFullCoverageShardPlan, ...]:
    """Return deterministic sharded L2b plans without executing them."""

    if command_mode not in {"dry_plan", "executable"}:
        raise ValueError(f"unsupported command_mode {command_mode!r}")
    stage = l2b_full_coverage_stage_spec(stage_id)
    if (
        stage_id == L2B_N2_SELECTOR_PROFILE_ID
        and signed_authorization_placeholder == L2B_SIGNED_AUTHORIZATION_PLACEHOLDER
    ):
        signed_authorization_placeholder = L2B_N2_SIGNED_AUTHORIZATION_TOKEN
    if (
        stage_id == L2B_N20_SELECTOR_PROFILE_ID
        and signed_authorization_placeholder == L2B_SIGNED_AUTHORIZATION_PLACEHOLDER
    ):
        signed_authorization_placeholder = L2B_N20_SIGNED_AUTHORIZATION_TOKEN
    if (
        stage_id == L2B_N20_ATTEMPT2_SELECTOR_PROFILE_ID
        and signed_authorization_placeholder == L2B_SIGNED_AUTHORIZATION_PLACEHOLDER
    ):
        signed_authorization_placeholder = L2B_N20_ATTEMPT2_SIGNED_AUTHORIZATION_TOKEN
    effective_output_root = (
        str(output_root) if output_root is not None else str(stage.output_root)
    )
    effective_observability_root = (
        str(observability_root)
        if observability_root is not None
        else str(stage.observability_root)
    )
    effective_analysis_root = (
        str(analysis_root) if analysis_root is not None else str(stage.analysis_root)
    )
    effective_reports_root = (
        str(reports_root) if reports_root is not None else str(stage.reports_root)
    )
    effective_billing_root = (
        str(billing_root) if billing_root is not None else str(stage.billing_root)
    )
    selected_shards = _select_l2b_shards(shard_selector)
    resolved_repo_root = Path(repo_root) if repo_root is not None else _default_repo_root()
    plans: list[L2BFullCoverageShardPlan] = []
    for kernel_class, dtype_variant in selected_shards:
        shard_id = _l2b_shard_id(kernel_class, dtype_variant)
        output_namespace = f"{effective_output_root}/{shard_id}"
        artifact_namespace = f"{effective_observability_root}/{shard_id}"
        cell_plans = build_l1a_launcher_executable_plan(
            repair_history_policy=repair_history_policy,
            cell_selector=cell_selector,
            output_root=output_namespace,
            observability_root=artifact_namespace,
            run_id_prefix=f"{stage.run_id_prefix}__{shard_id}",
            scale_tier=stage.scale_tier,
            n=stage.n,
            kernel_class_selector=kernel_class,
            dtypes=(dtype_variant,),
            repo_root=resolved_repo_root,
            signed_authorization_placeholder=signed_authorization_placeholder,
            signed_authorization_option=signed_authorization_option,
            support_status=(
                L2B_N2_EXECUTABLE_SELECTOR_SUPPORT_STATUS
                if stage_id == L2B_N2_SELECTOR_PROFILE_ID
                else L2B_N20_ATTEMPT2_EXECUTABLE_SELECTOR_SUPPORT_STATUS
                if stage_id == L2B_N20_ATTEMPT2_SELECTOR_PROFILE_ID
                else L2B_N20_EXECUTABLE_SELECTOR_SUPPORT_STATUS
                if stage_id == L2B_N20_SELECTOR_PROFILE_ID
                else L2B_EXECUTABLE_SELECTOR_SUPPORT_STATUS
            ),
        )
        plans.append(
            L2BFullCoverageShardPlan(
                shard_id=shard_id,
                kernel_class=kernel_class,
                dtype_variant=dtype_variant,
                planned_cells=len(cell_plans),
                planned_rows=len(cell_plans) * stage.n,
                backend=stage.backend,
                scale_namespace=stage.scale_namespace,
                output_namespace=output_namespace,
                artifact_namespace=artifact_namespace,
                output_paths={
                    "result_root": output_namespace,
                    "result_files": tuple(cell.output_path for cell in cell_plans),
                    "content_hash_sidecars": tuple(
                        cell.content_hash_sidecar_path for cell in cell_plans
                    ),
                },
                artifact_paths={
                    "observability_root": artifact_namespace,
                    "observability_event_files": tuple(
                        cell.observability_event_path for cell in cell_plans
                    ),
                    "observability_summary_files": tuple(
                        cell.observability_summary_path for cell in cell_plans
                    ),
                    "observability_hash_sidecars": tuple(
                        cell.observability_hash_path for cell in cell_plans
                    ),
                    "analysis_namespace_glob": (
                        f"{effective_analysis_root}/{shard_id}*"
                    ),
                    "reports_namespace_glob": f"{effective_reports_root}/{shard_id}*",
                    "billing_namespace_glob": f"{effective_billing_root}/{shard_id}*",
                },
                future_command=_l2b_future_selector_command(
                stage=stage,
                shard_id=shard_id,
                kernel_class=kernel_class,
                dtype_variant=dtype_variant,
                repair_history_policy=repair_history_policy,
                cell_selector=cell_selector,
                command_mode=command_mode,
                signed_authorization_placeholder=signed_authorization_placeholder,
                signed_authorization_option=signed_authorization_option,
                ),
                cell_commands=tuple(cell.executable_command for cell in cell_plans),
                concurrency_limits=stage.concurrency_limits,
                timing_observability=stage.timing_observability,
                slow_cell_stop_policy=stage.slow_cell_stop_policy,
                fail_if_any_target_path_exists=True,
                path_collision_policy=L1A_PATH_COLLISION_POLICY,
                support_status=(
                    L2B_N2_EXECUTABLE_SELECTOR_SUPPORT_STATUS
                    if stage_id == L2B_N2_SELECTOR_PROFILE_ID
                    else L2B_N20_ATTEMPT2_EXECUTABLE_SELECTOR_SUPPORT_STATUS
                    if stage_id == L2B_N20_ATTEMPT2_SELECTOR_PROFILE_ID
                    else L2B_N20_EXECUTABLE_SELECTOR_SUPPORT_STATUS
                    if stage_id == L2B_N20_SELECTOR_PROFILE_ID
                    else L2B_EXECUTABLE_SELECTOR_SUPPORT_STATUS
                ),
            )
        )
    return tuple(plans)


def _l2b_shard_id(kernel_class: str, dtype_variant: str) -> str:
    return f"{kernel_class}__{dtype_variant}"


def _select_l2b_shards(shard_selector: str) -> tuple[tuple[str, str], ...]:
    all_shards = tuple(
        (kernel_class, dtype_variant)
        for kernel_class in LOCKED_KERNEL_CLASSES
        for dtype_variant in DTYPE_NAMES
    )
    if shard_selector == "all":
        return all_shards

    by_id = {
        _l2b_shard_id(kernel_class, dtype_variant): (kernel_class, dtype_variant)
        for kernel_class, dtype_variant in all_shards
    }
    if shard_selector in by_id:
        return (by_id[shard_selector],)

    if shard_selector.startswith("wave:"):
        parts = shard_selector.split(":")
        if len(parts) != 3:
            raise ValueError(
                "l2b shard wave selector must use wave:<start>:<count>"
            )
        try:
            start = int(parts[1])
            count = int(parts[2])
        except ValueError as exc:
            raise ValueError(
                "l2b shard wave selector start and count must be integers"
            ) from exc
        if start < 0 or count <= 0:
            raise ValueError("l2b shard wave selector requires start>=0 and count>0")
        end = start + count
        if start >= len(all_shards) or end > len(all_shards):
            raise ValueError(
                f"l2b shard wave selector must stay within {len(all_shards)} shards"
            )
        return all_shards[start:end]

    allowed = ", ".join(("all", *by_id, "wave:<start>:<count>"))
    raise ValueError(
        f"l2b_shard_selector must be one of: {allowed}; got {shard_selector!r}"
    )


def _l2b_future_selector_command(
    *,
    stage: L2BFullCoverageStageSpec,
    shard_id: str,
    kernel_class: str,
    dtype_variant: str,
    repair_history_policy: str,
    cell_selector: str | tuple[str, ...] = "all",
    command_mode: str,
    signed_authorization_placeholder: str,
    signed_authorization_option: str,
) -> str:
    parts = [
        "TRITONGEN_MLFLOW=0",
        ".venv/bin/python",
        "-m",
        "cluster3.experiments.run_cluster3_modal",
        "--condition",
        L1A_GRAMMAR_MODE_CP_SELECTOR,
        "--l2b-stage",
        stage.selector_profile_id,
        "--l2b-shard-selector",
        shard_id,
        "--kernel-class",
        kernel_class,
        "--scale-tier",
        stage.scale_tier,
        "--n",
        str(stage.n),
        "--dtypes",
        dtype_variant,
        "--repair-history-policy",
        repair_history_policy,
    ]
    if command_mode == "dry_plan":
        parts.append("--dry-plan")
    else:
        parts.extend([signed_authorization_option, signed_authorization_placeholder])
        if not _is_l2b_create_only_signed_placeholder(signed_authorization_placeholder):
            parts.append("--overwrite")
    if cell_selector != "all":
        selectors = (
            (cell_selector,) if isinstance(cell_selector, str) else tuple(cell_selector)
        )
        if selectors:
            parts.extend(["--l2b-recovery-cells", ",".join(selectors)])
    return " ".join(parts)


def _build_l1a_launcher_plan(
    *,
    repair_history_policy: str,
    cell_selector: str,
    output_root: str | Path,
    observability_root: str | Path,
    run_id_prefix: str,
    scale_tier: str,
    n: int,
    kernel_class_selector: str,
    dtypes: tuple[str, ...],
    repo_root: str | Path | None,
    command_mode: str,
    signed_authorization_placeholder: str | None = None,
    signed_authorization_option: str = "--signed-l1a-authorization",
    support_status: str = L1A_EXECUTABLE_SELECTOR_SUPPORT_STATUS,
) -> tuple[GrammarModeLauncherCellPlan, ...]:
    selected = _select_cells(
        build_l1a_grammar_mode_cp_matrix(repair_history_policy=repair_history_policy),
        cell_selector=cell_selector,
    )
    resolved_repo_root = Path(repo_root) if repo_root is not None else _default_repo_root()
    output_base = Path(output_root)
    observability_base = Path(observability_root)
    return tuple(
        _launcher_plan_for_cell(
            cell,
            repair_history_policy=repair_history_policy,
            output_base=output_base,
            observability_base=observability_base,
            run_id_prefix=run_id_prefix,
            scale_tier=scale_tier,
            n=n,
            kernel_class_selector=kernel_class_selector,
            dtypes=dtypes,
            repo_root=resolved_repo_root,
            command_mode=command_mode,
            signed_authorization_placeholder=signed_authorization_placeholder,
            signed_authorization_option=signed_authorization_option,
            support_status=support_status,
        )
        for cell in selected
    )


def l1a_grammar_mode_cell_selector_choices() -> tuple[str, ...]:
    """Return accepted dry-plan cell selectors."""

    return ("all",) + tuple(
        cell.output_namespace_suffix for cell in build_l1a_grammar_mode_cp_matrix()
    )


def _select_cells(
    cells: tuple[GrammarModeCellSpec, ...],
    *,
    cell_selector: str | tuple[str, ...],
) -> tuple[GrammarModeCellSpec, ...]:
    if cell_selector == "all":
        return cells
    selectors = (cell_selector,) if isinstance(cell_selector, str) else tuple(cell_selector)
    if len(selectors) != len(set(selectors)):
        raise ValueError(
            "grammar_mode_cell selectors must be unique; duplicate selector found"
        )
    selected: list[GrammarModeCellSpec] = []
    allowed = ", ".join(l1a_grammar_mode_cell_selector_choices())
    for selector in selectors:
        matched = tuple(
            cell for cell in cells if cell.output_namespace_suffix == selector
        )
        if not matched:
            raise ValueError(
                f"grammar_mode_cell must be one of: {allowed}; got {selector!r}"
            )
        selected.extend(matched)
    if len(selected) != len(set(selectors)):
        raise ValueError("grammar_mode_cell selectors must not include duplicates")
    return tuple(selected)


def _launcher_plan_for_cell(
    cell: GrammarModeCellSpec,
    *,
    repair_history_policy: str,
    output_base: Path,
    observability_base: Path,
    run_id_prefix: str,
    scale_tier: str,
    n: int,
    kernel_class_selector: str,
    dtypes: tuple[str, ...],
    repo_root: Path,
    command_mode: str,
    signed_authorization_placeholder: str | None,
    signed_authorization_option: str,
    support_status: str,
) -> GrammarModeLauncherCellPlan:
    condition_id = cell.output_namespace_suffix
    output_path = output_base / f"{condition_id}.jsonl"
    observability_event_path = observability_base / f"{condition_id}.observability.jsonl"
    observability_summary_path = (
        observability_base / f"{condition_id}.observability.summary.json"
    )
    observability_hash_path = observability_base / (
        f"{condition_id}.observability.jsonl.hashes.json"
    )
    effective_repair_policy = (
        repair_history_policy
        if cell.correctness_feedback_active or cell.compile_feedback_active
        else "not_applicable"
    )
    command_grammar_argument = (
        f"--grammar-variant {cell.grammar_variant}"
        if cell.grammar_variant is not None
        else None
    )
    command_selector = _command_selector_for_cell(
        condition_id=condition_id,
        command_mode=command_mode,
        command_grammar_argument=command_grammar_argument,
        output_path=output_path.as_posix(),
        observability_event_path=observability_event_path.as_posix(),
        run_id_prefix=run_id_prefix,
        scale_tier=scale_tier,
        n=n,
        kernel_class_selector=kernel_class_selector,
        dtypes=dtypes,
        repair_history_policy=repair_history_policy,
        signed_authorization_placeholder=signed_authorization_placeholder,
        signed_authorization_option=signed_authorization_option,
    )
    resolved_support_status = (
        "DRY_PLAN_SELECTOR_PRESENT_NO_EXECUTION"
        if command_mode == "dry_plan"
        else support_status
    )
    return GrammarModeLauncherCellPlan(
        selector=L1A_GRAMMAR_MODE_CP_SELECTOR,
        condition_name=cell.condition_name,
        condition_id=condition_id,
        factor_cell=cell.factor_cell,
        runner_condition=cell.factor_cell,
        grammar_mode=cell.grammar_mode,
        grammar_active=cell.grammar_active,
        grammar_variant=cell.grammar_variant,
        grammar_path=cell.grammar_path,
        grammar_sha256=_grammar_sha256(cell.grammar_path, repo_root=repo_root),
        grammar_claim_scope=cell.grammar_claim_scope,
        correctness_feedback_active=cell.correctness_feedback_active,
        compile_feedback_active=cell.compile_feedback_active,
        repair_history_policy=effective_repair_policy,
        output_namespace_suffix=condition_id,
        output_path=output_path.as_posix(),
        content_hash_sidecar_path=_result_hash_path(output_path).as_posix(),
        observability_event_path=observability_event_path.as_posix(),
        observability_summary_path=observability_summary_path.as_posix(),
        observability_hash_path=observability_hash_path.as_posix(),
        observability_experiment_id=L1A_EXPERIMENT_ID,
        observability_run_id_suffix=condition_id,
        observability_join_key=f"{run_id_prefix}__{condition_id}",
        path_collision_policy=L1A_PATH_COLLISION_POLICY,
        write_mode_required="fail_if_existing_before_signed_execution",
        command_mode=command_mode,
        command_selector=command_selector,
        command_grammar_argument=command_grammar_argument,
        executable_command=f".venv/bin/python -m cluster3.experiments.run_cluster3_modal {command_selector}",
        signed_authorization_placeholder=signed_authorization_placeholder,
        execution_role=(
            "p_enabled_generated_cell"
            if cell.compile_feedback_active
            else "no_p_control_cell"
        ),
        support_status=resolved_support_status,
        expected_eligibility_notes=cell.expected_eligibility_notes,
    )


def _command_selector_for_cell(
    *,
    condition_id: str,
    command_mode: str,
    command_grammar_argument: str | None,
    output_path: str,
    observability_event_path: str,
    run_id_prefix: str,
    scale_tier: str,
    n: int,
    kernel_class_selector: str,
    dtypes: tuple[str, ...],
    repair_history_policy: str,
    signed_authorization_placeholder: str | None,
    signed_authorization_option: str,
) -> str:
    if command_mode == "dry_plan":
        parts = [
            "--condition",
            L1A_GRAMMAR_MODE_CP_SELECTOR,
            "--grammar-mode-cell",
            condition_id,
            "--kernel-class",
            kernel_class_selector,
            "--scale-tier",
            scale_tier,
            "--n",
            str(n),
            "--dtypes",
            ",".join(dtypes),
            "--repair-history-policy",
            repair_history_policy,
            "--dry-plan",
        ]
        return " ".join(parts)
    if command_mode != "executable":
        raise ValueError(f"unsupported command_mode {command_mode!r}")
    if not signed_authorization_placeholder:
        raise ValueError("signed authorization placeholder is required")
    parts = [
        "--condition",
        L1A_GRAMMAR_MODE_CP_SELECTOR,
        "--grammar-mode-cell",
        condition_id,
        "--kernel-class",
        kernel_class_selector,
        "--scale-tier",
        scale_tier,
        "--n",
        str(n),
        "--dtypes",
        ",".join(dtypes),
        "--repair-history-policy",
        repair_history_policy,
        "--observability-mode",
        "best_effort",
        "--observability-experiment-id",
        L1A_EXPERIMENT_ID,
        "--observability-run-id",
        f"{run_id_prefix}__{condition_id}",
        "--observability-output",
        observability_event_path,
        signed_authorization_option,
        signed_authorization_placeholder,
        "--output",
        output_path,
    ]
    if not _is_l2b_create_only_signed_placeholder(signed_authorization_placeholder):
        parts.append("--overwrite")
    if command_grammar_argument is not None:
        parts.extend(command_grammar_argument.split(" "))
    return " ".join(parts)


def _is_l2b_n2_recovery_missing28_placeholder(value: str | None) -> bool:
    return bool(value and L2B_N2_RECOVERY_MISSING28_AUTHORIZATION_MARKER in value)


def _is_l2b_create_only_signed_placeholder(value: str | None) -> bool:
    return (
        _is_l2b_n2_recovery_missing28_placeholder(value)
        or value == L2B_N20_SIGNED_AUTHORIZATION_TOKEN
        or value == L2B_N20_ATTEMPT2_SIGNED_AUTHORIZATION_TOKEN
    )


def _result_hash_path(result_path: Path) -> Path:
    return result_path.with_name(f"{result_path.name}.hashes.json")


def _grammar_sha256(grammar_path: str | None, *, repo_root: Path) -> str | None:
    if grammar_path is None:
        return None
    return hashlib.sha256((repo_root / grammar_path).read_bytes()).hexdigest()


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _condition_name(
    *,
    grammar_mode: str,
    correctness_feedback_active: bool,
    compile_feedback_active: bool,
) -> str:
    parts = [grammar_mode]
    if correctness_feedback_active:
        parts.append("C")
    if compile_feedback_active:
        parts.append("P")
    return "+".join(parts)


def _output_namespace_suffix(
    *,
    grammar_mode: str,
    correctness_feedback_active: bool,
    compile_feedback_active: bool,
) -> str:
    return (
        f"{grammar_mode}__c_{_on_off(correctness_feedback_active)}"
        f"__p_{_on_off(compile_feedback_active)}"
    )


def _on_off(value: bool) -> str:
    return "on" if value else "off"


def _eligibility_notes(
    *,
    grammar_active: bool,
    correctness_feedback_active: bool,
    compile_feedback_active: bool,
) -> tuple[str, ...]:
    notes = [
        (
            "grammar metadata required for active grammar rows"
            if grammar_active
            else "grammar metadata must be absent for grammar_off rows"
        )
    ]
    notes.append(
        "C loop eligible only for F2 failures"
        if correctness_feedback_active
        else "C loop must not fire"
    )
    notes.append(
        "P loop eligible only for F1_COMPILE failures"
        if compile_feedback_active
        else "P loop must not fire"
    )
    return tuple(notes)


def _validate_unique_specs(cells: list[GrammarModeCellSpec]) -> None:
    condition_names = [cell.condition_name for cell in cells]
    if len(condition_names) != len(set(condition_names)):
        raise ValueError("duplicate grammar-mode condition_name values")
    suffixes = [cell.output_namespace_suffix for cell in cells]
    if len(suffixes) != len(set(suffixes)):
        raise ValueError("duplicate grammar-mode output namespace suffixes")
