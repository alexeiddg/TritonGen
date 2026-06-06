"""Local 12-cell grammar-mode x C x P planning matrix.

This module is intentionally planning-only. It defines labels and expected
metadata for future launch packets but does not invoke generation, Modal,
correctness evaluation, output writing, tracking, or artifact refreshes.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path

from cluster3.constants import P_HISTORY_POLICY_V1
from shared.factors.cells import FactorCell, require_valid_factor_cell
from shared.factors.grammar_modes import (
    GRAMMAR_MODE_VALUES,
    GrammarMode,
    grammar_mode_config,
)


@dataclass(frozen=True)
class GrammarModeCellSpec:
    """One planned L1a grammar-mode/C/P cell."""

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
L1A_PATH_COLLISION_POLICY = "fail_if_any_target_path_exists"
L1A_SIGNED_AUTHORIZATION_PLACEHOLDER = "SIGNED_L1A_PACKET_ID_REQUIRED"
L1A_EXECUTABLE_SELECTOR_SUPPORT_STATUS = (
    "EXECUTABLE_SELECTOR_PRESENT_AUTHORIZATION_REQUIRED_NO_EXECUTION"
)


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
    repo_root: str | Path | None = None,
) -> tuple[GrammarModeLauncherCellPlan, ...]:
    """Return deterministic dry-plan entries for the 12-cell L1a selector."""

    return _build_l1a_launcher_plan(
        repair_history_policy=repair_history_policy,
        cell_selector=cell_selector,
        output_root=output_root,
        observability_root=observability_root,
        repo_root=repo_root,
        command_mode="dry_plan",
    )


def build_l1a_launcher_executable_plan(
    *,
    repair_history_policy: str = P_HISTORY_POLICY_V1,
    cell_selector: str = "all",
    output_root: str | Path = L1A_OUTPUT_ROOT,
    observability_root: str | Path = L1A_OBSERVABILITY_ROOT,
    repo_root: str | Path | None = None,
    signed_authorization_placeholder: str = L1A_SIGNED_AUTHORIZATION_PLACEHOLDER,
) -> tuple[GrammarModeLauncherCellPlan, ...]:
    """Return executable-selector command plans without running them."""

    return _build_l1a_launcher_plan(
        repair_history_policy=repair_history_policy,
        cell_selector=cell_selector,
        output_root=output_root,
        observability_root=observability_root,
        repo_root=repo_root,
        command_mode="executable",
        signed_authorization_placeholder=signed_authorization_placeholder,
    )


def _build_l1a_launcher_plan(
    *,
    repair_history_policy: str,
    cell_selector: str,
    output_root: str | Path,
    observability_root: str | Path,
    repo_root: str | Path | None,
    command_mode: str,
    signed_authorization_placeholder: str | None = None,
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
            repo_root=resolved_repo_root,
            command_mode=command_mode,
            signed_authorization_placeholder=signed_authorization_placeholder,
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
    cell_selector: str,
) -> tuple[GrammarModeCellSpec, ...]:
    if cell_selector == "all":
        return cells
    selected = tuple(cell for cell in cells if cell.output_namespace_suffix == cell_selector)
    if not selected:
        allowed = ", ".join(l1a_grammar_mode_cell_selector_choices())
        raise ValueError(
            f"grammar_mode_cell must be one of: {allowed}; got {cell_selector!r}"
        )
    return selected


def _launcher_plan_for_cell(
    cell: GrammarModeCellSpec,
    *,
    repair_history_policy: str,
    output_base: Path,
    observability_base: Path,
    repo_root: Path,
    command_mode: str,
    signed_authorization_placeholder: str | None,
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
        repair_history_policy=repair_history_policy,
        signed_authorization_placeholder=signed_authorization_placeholder,
    )
    support_status = (
        "DRY_PLAN_SELECTOR_PRESENT_NO_EXECUTION"
        if command_mode == "dry_plan"
        else L1A_EXECUTABLE_SELECTOR_SUPPORT_STATUS
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
        observability_join_key=f"{L1A_RUN_ID_PREFIX}__{condition_id}",
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
        support_status=support_status,
        expected_eligibility_notes=cell.expected_eligibility_notes,
    )


def _command_selector_for_cell(
    *,
    condition_id: str,
    command_mode: str,
    command_grammar_argument: str | None,
    output_path: str,
    observability_event_path: str,
    repair_history_policy: str,
    signed_authorization_placeholder: str | None,
) -> str:
    if command_mode == "dry_plan":
        return (
            f"--condition {L1A_GRAMMAR_MODE_CP_SELECTOR} "
            f"--dry-plan --grammar-mode-cell {condition_id}"
        )
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
        "elementwise",
        "--scale-tier",
        "smoke",
        "--n",
        "1",
        "--dtypes",
        "fp32",
        "--repair-history-policy",
        repair_history_policy,
        "--observability-mode",
        "best_effort",
        "--observability-experiment-id",
        L1A_EXPERIMENT_ID,
        "--observability-run-id",
        f"{L1A_RUN_ID_PREFIX}__{condition_id}",
        "--observability-output",
        observability_event_path,
        "--signed-l1a-authorization",
        signed_authorization_placeholder,
        "--output",
        output_path,
        "--overwrite",
    ]
    if command_grammar_argument is not None:
        parts.extend(command_grammar_argument.split(" "))
    return " ".join(parts)


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
