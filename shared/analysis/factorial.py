"""Factorial analysis for current Cluster 2 metric semantics.

The paper-primary Cluster 2 path uses Level 2 ``functional_success`` and
paired-by-seed replay-control comparisons. Compile success remains available as
a secondary structural-validity diagnostic. The current populated design is the
temporary 2² subset over G and C: ``none``, ``G``, ``C``, and ``G+C``.
P-containing cells are deferred for this iteration and reported as not
populated until Cluster 3 data exists. The full 2³ factorial remains the
defined project goal.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, is_dataclass
from pathlib import Path
from statistics import NormalDist
from typing import Any

import numpy as np
import pandas as pd

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.eval.constants import (
    BOOTSTRAP_SAMPLES,
    BOOTSTRAP_SEED,
    CI_LEVEL,
    LOGISTIC_ETA_CLIP,
    LOGISTIC_MAX_ITERATIONS,
    LOGISTIC_MIN_WEIGHT,
    LOGISTIC_SEPARATION_COEFFICIENT,
    LOGISTIC_TOLERANCE,
    MULTIPLE_TESTING_METHOD,
    SIGNIFICANCE_ALPHA,
)
from shared.eval.reporting.grammar_language import grammar_condition_label_for_variants
from shared.repair_history.policies import (
    AGENTIC_TRANSCRIPT_REPAIR_HISTORY_POLICY_V1,
    LAST_ATTEMPT_ONLY_REPAIR_HISTORY_POLICY_V1,
    REPAIR_HISTORY_POLICIES_V1,
    UNKNOWN_LEGACY_REPAIR_HISTORY_POLICY,
)


CANONICAL_CONDITIONS = (
    "none",
    "G",
    "C",
    "P",
    "G+C",
    "G+P",
    "C+P",
    "G+C+P",
)
CURRENT_FOUR_CELL_CONDITIONS = ("none", "G", "C", "G+C")
P_CONDITIONS = ("P", "G+P", "C+P", "G+C+P")
FACTOR_NAMES = ("G", "C", "P")
FACTOR_COLUMNS = (
    "grammar_active",
    "compiler_feedback_active",
    "perf_feedback_active",
    "compile_feedback_active",
)
PRIMARY_RESPONSE_VARIABLE = "functional_success"
SECONDARY_RESPONSE_VARIABLE = "compile_success"
ANALYZER_VERSION = "factorial_alignment_v3_f3_eval_pipeline_policy"
INPUT_ROLE_ALIASES = {
    "none": "none",
    "g": "G",
    "G": "G",
    "c": "C",
    "C": "C",
    "gc": "G+C",
    "g+c": "G+C",
    "G+C": "G+C",
}
CLUSTER1_COMPILE_ONLY_CONDITIONS = frozenset({"none", "G"})
CLUSTER2_GENERATED_CONDITIONS = frozenset({"C", "G+C"})
CLUSTER2_EVAL_PIPELINE_FAILURE_CODE = "F3_EVAL_PIPELINE"
_MISSING_FIELD = object()
SCALE_TIER_SOURCE_COLUMN = "_scale_tier_source"
RAW_SCALE_TIER_COLUMN = "_raw_scale_tier_before_annotation"
RAW_SCALE_TIER_EXPLICIT_COLUMN = "_raw_scale_tier_explicit"
REQUESTED_SCALE_TIER_COLUMN = "_requested_scale_tier"
SCALE_TIER_SOURCE_RAW = "raw_row"
SCALE_TIER_SOURCE_MISSING_DEFAULT = "raw_missing_default_unspecified"
SCALE_TIER_SOURCE_ANALYSIS_ANNOTATION = "analysis_cli_annotation"
REPAIR_HISTORY_POLICY_COLUMN = "repair_history_policy"
REPAIR_HISTORY_POLICY_STATE_COLUMN = "repair_history_policy_state"
RAW_REPAIR_HISTORY_POLICY_COLUMN = "_raw_repair_history_policy"
REPAIR_HISTORY_POLICY_EXPLICIT_COLUMN = "_repair_history_policy_explicit"
REPAIR_HISTORY_MISSING_METADATA_COLUMN = "repair_history_missing_agentic_metadata"
REPAIR_HISTORY_STATE_KNOWN_LEGACY_MISSING = "known_legacy_missing_policy"
REPAIR_HISTORY_STATE_EXPLICIT_LEGACY = "explicit_last_attempt_only"
REPAIR_HISTORY_STATE_EXPLICIT_AGENTIC = "explicit_agentic_transcript"
REPAIR_HISTORY_STATE_UNKNOWN_POLICY = "unknown_policy"
REPAIR_HISTORY_STATE_MIXED_POLICY_ARTIFACT = "mixed_policy_artifact"
REPAIR_HISTORY_STATE_INCOMPLETE_AGENTIC = "incomplete_agentic_metadata"
REPAIR_HISTORY_GROUPING_COLUMNS = (
    REPAIR_HISTORY_POLICY_COLUMN,
    "repair_prompt_template_version",
    "repair_prompt_renderer_version",
    "repair_max_prompt_chars",
    "repair_include_latest_source",
)
REPAIR_HISTORY_ARTIFACT_HOMOGENEITY_COLUMNS = (
    "repair_prompt_template_version",
    "repair_prompt_renderer_version",
    "repair_max_prompt_chars",
    "repair_include_latest_source",
)
REPAIR_HISTORY_ATTEMPT_INDEX_SIGNAL_FIELDS = (
    "attempt_index",
    "generation_index",
    "terminal_attempt_index",
    "p_repair_attempt_count",
    "c_attempt_count",
)
REPAIR_HISTORY_ATTEMPT_BOOL_SIGNAL_FIELDS = (
    "p_repair_attempted",
)
REPAIR_HISTORY_AGENTIC_REQUIRED_METADATA = (
    "repair_prompt_template_version",
    "repair_prompt_renderer_version",
    "repair_anchor_attempt_index",
    "repair_latest_attempt_index",
    "repair_history_attempt_count",
    "repair_prompt_sha256",
    "repair_prompt_char_count",
    "repair_max_prompt_chars",
    "repair_include_latest_source",
    "repair_anchor_source_hash",
    "repair_latest_source_hash",
    "repair_history_summary_sha256",
)
REPAIR_HISTORY_FIELD_ALIASES = {
    REPAIR_HISTORY_POLICY_COLUMN: (
        "repair_history_policy",
        "c_history_policy",
        "p_history_policy",
    ),
    "repair_prompt_template_version": (
        "repair_prompt_template_version",
        "c_repair_prompt_template_version",
        "p_repair_prompt_template_version",
    ),
    "repair_prompt_renderer_version": (
        "repair_prompt_renderer_version",
        "c_repair_prompt_renderer_version",
        "p_repair_prompt_renderer_version",
    ),
    "repair_anchor_attempt_index": (
        "repair_anchor_attempt_index",
        "c_repair_anchor_attempt_index",
        "p_repair_anchor_attempt_index",
    ),
    "repair_latest_attempt_index": (
        "repair_latest_attempt_index",
        "c_repair_latest_attempt_index",
        "p_repair_latest_attempt_index",
    ),
    "repair_history_attempt_count": (
        "repair_history_attempt_count",
        "c_repair_history_attempt_count",
        "p_repair_history_attempt_count",
    ),
    "repair_prompt_sha256": (
        "repair_prompt_sha256",
        "c_repair_prompt_sha256",
        "p_repair_prompt_sha256",
    ),
    "repair_prompt_char_count": (
        "repair_prompt_char_count",
        "c_repair_prompt_char_count",
        "p_repair_prompt_char_count",
    ),
    "repair_max_prompt_chars": (
        "repair_max_prompt_chars",
        "c_repair_max_prompt_chars",
        "p_repair_max_prompt_chars",
    ),
    "repair_include_latest_source": (
        "repair_include_latest_source",
        "c_repair_include_latest_source",
        "p_repair_include_latest_source",
    ),
    "repair_anchor_source_hash": (
        "repair_anchor_source_hash",
        "c_repair_anchor_source_hash",
        "p_repair_anchor_source_hash",
    ),
    "repair_latest_source_hash": (
        "repair_latest_source_hash",
        "c_repair_latest_source_hash",
        "p_repair_latest_source_hash",
    ),
    "repair_history_summary_sha256": (
        "repair_history_summary_sha256",
        "c_repair_history_summary_sha256",
        "p_repair_history_summary_sha256",
    ),
    "repair_history_error_code": (
        "repair_history_error_code",
        "c_repair_history_error_code",
        "p_repair_history_error_code",
    ),
}
REPAIR_HISTORY_ANALYZER_COLUMNS = (
    REPAIR_HISTORY_POLICY_COLUMN,
    REPAIR_HISTORY_POLICY_STATE_COLUMN,
    RAW_REPAIR_HISTORY_POLICY_COLUMN,
    REPAIR_HISTORY_POLICY_EXPLICIT_COLUMN,
    REPAIR_HISTORY_MISSING_METADATA_COLUMN,
    *(
        field
        for field in REPAIR_HISTORY_FIELD_ALIASES
        if field != REPAIR_HISTORY_POLICY_COLUMN
    ),
)

PAIRED_REPLAY_COMPARISONS = {"C": "none", "G+C": "G"}
P_PAIRED_REPLAY_COMPARISONS: dict[str, str] = {
    "P": "none",
    "G+P": "G",
    "C+P": "C",
    "G+C+P": "G+C",
}
SECONDARY_COMPILE_COMPARISONS = {"G": "none", "G+C": "C"}
PAIR_KEY_COLUMNS = ("kernel_class", "kernel_id", "dtype", "base_seed")
P_PAIR_COVERAGE_WARNING_FLAG = "missing_p_pair_controls"
_MISSING_PAIR_KEY = object()
UNAVAILABLE_FROZEN_REVISION = "unavailable_in_frozen_cluster1_artifact"
MODE_COLLAPSE_FLAG = "mode_collapse_warning"
MODE_COLLAPSE_TEXT = (
    "this cell shows mode collapse - interpret as template instantiation "
    "control, not as evidence of grammar-constrained generation"
)
CURRENT_SUBSET_ANALYSIS_LABEL = "current 2² subset analysis over G and C"
FULL_FACTORIAL_ANALYSIS_LABEL = "full 2³ factorial analysis"
PARTIAL_FACTORIAL_ANALYSIS_LABEL = "partial factorial analysis"
CURRENT_ITERATION_SCOPE_STATEMENT = (
    "The current iteration analyzes a temporary 2² subset over G and C: "
    "none, G, C, and G+C."
)
FULL_FACTORIAL_GOAL_STATEMENT = (
    "The full 2³ factorial over G, C, and P remains the defined project goal."
)
P_CELL_DEFERRAL_STATEMENT = (
    "P-containing cells are deferred for this iteration and are not included "
    "in current paper-claiming outputs."
)
CURRENT_STATUS_SCOPE_STATEMENT = (
    "This is a current-status scope statement, not a methodology realignment."
)


def effective_paired_replay_comparisons(
    populated_cells: Sequence[str],
) -> dict[str, str]:
    """Return paired primary comparisons enabled by the populated condition cells."""

    populated = set(populated_cells)
    comparisons = dict(PAIRED_REPLAY_COMPARISONS)
    for treatment_condition, control_condition in P_PAIRED_REPLAY_COMPARISONS.items():
        if treatment_condition in populated and control_condition in populated:
            comparisons[treatment_condition] = control_condition
    return comparisons


def load_results(
    jsonl_path: Path,
    *,
    input_role: str | None = None,
    scale_tier_annotation: str | None = None,
    missing_repair_history_policy_artifact_kind: str = "known_legacy",
) -> pd.DataFrame:
    """Load and normalize one EvalResult-shaped JSONL file."""

    rows = [
        json.loads(line)
        for line in jsonl_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return normalize_result_rows(
        rows,
        source_path=str(jsonl_path),
        input_role=input_role,
        scale_tier_annotation=scale_tier_annotation,
        missing_repair_history_policy_artifact_kind=(
            missing_repair_history_policy_artifact_kind
        ),
    )


def load_result_paths(
    paths: Sequence[Path],
    *,
    input_roles: Sequence[str | None] | None = None,
    scale_tier_annotation: str | None = None,
    missing_repair_history_policy_artifact_kind: str = "known_legacy",
) -> pd.DataFrame:
    """Load and normalize one or more EvalResult JSONL paths."""

    role_list: Sequence[str | None]
    if input_roles is None:
        role_list = [None] * len(paths)
    else:
        if len(input_roles) != len(paths):
            raise ValueError("input_roles length must match input paths length")
        role_list = input_roles
    frames = [
        load_results(
            path,
            input_role=input_role,
            scale_tier_annotation=scale_tier_annotation,
            missing_repair_history_policy_artifact_kind=(
                missing_repair_history_policy_artifact_kind
            ),
        )
        for path, input_role in zip(paths, role_list, strict=True)
    ]
    if not frames:
        raise ValueError("at least one input path is required")
    return pd.concat(frames, ignore_index=True)


def merge_cluster_results(
    cluster1_path: Path | None = None,
    cluster2_path: Path | None = None,
    cluster3_path: Path | None = None,
) -> pd.DataFrame:
    """Merge result files from available clusters into one normalized DataFrame."""

    paths = [path for path in (cluster1_path, cluster2_path, cluster3_path) if path]
    existing_paths = [path for path in paths if path.exists()]
    if not existing_paths:
        raise ValueError("No result files provided.")
    return load_result_paths(existing_paths)


def normalize_result_rows(
    rows: Iterable[Mapping[str, Any] | Any],
    *,
    source_path: str | None = None,
    input_role: str | None = None,
    scale_tier_annotation: str | None = None,
    missing_repair_history_policy_artifact_kind: str = "known_legacy",
) -> pd.DataFrame:
    """Normalize current EvalResult and Cluster 2 row shapes for analysis."""

    normalized: list[dict[str, Any]] = []
    input_role_condition = _normalize_input_role(input_role)
    requested_scale_tier = _normalize_requested_scale_tier(scale_tier_annotation)
    for row_index, row in enumerate(rows):
        payload = _row_to_dict(row)
        generated_metadata = _metadata_dict(payload.get("generated_metadata"))
        replay_metadata = _metadata_dict(payload.get("replay_metadata"))
        raw_scale_tier, raw_scale_tier_explicit = _raw_scale_tier_from_payload(
            payload,
            generated_metadata,
            replay_metadata,
            source_path=source_path,
            row_index=row_index,
        )
        scale_tier, scale_tier_source = _resolve_scale_tier(
            raw_scale_tier=raw_scale_tier,
            raw_scale_tier_explicit=raw_scale_tier_explicit,
            requested_scale_tier=requested_scale_tier,
            source_path=source_path,
            row_index=row_index,
        )
        dtype = _first_present(payload, "dtype", "dtype_tested")
        base_seed = _first_present(
            payload,
            "base_seed",
            "generation_seed",
            "seed",
            "sample_index",
        )
        attempt_index = _first_present(
            payload,
            "attempt_index",
            "generation_index",
            default=0,
        )
        condition = _normalize_condition(
            payload,
            input_role_condition=input_role_condition,
        )
        functional_success = _bool_or_none(payload.get("functional_success"))
        if _is_cluster1_compile_only_scope(
            condition=condition,
            input_role_condition=input_role_condition,
            source_path=source_path,
        ):
            # Cluster 1 is compile-only and does not run Level 2 correctness. For
            # factorial functional-success analysis, Cluster 1 rows normalize to
            # functional_success=False; compile_success is preserved separately
            # as a compile metric.
            functional_success = False
        compile_success = _normalize_compile_success(
            payload,
            condition=condition,
            functional_success=functional_success,
            source_path=source_path,
            row_index=row_index,
        )
        cluster3_diagnostics = _normalize_cluster3_diagnostic_fields(
            payload,
            generated_metadata=generated_metadata,
            condition=condition,
            source_path=source_path,
            row_index=row_index,
        )
        repair_history_metadata = _repair_history_metadata_from_payload(
            payload,
            generated_metadata=generated_metadata,
            replay_metadata=replay_metadata,
            source_path=source_path,
            row_index=row_index,
            missing_policy_artifact_kind=(
                missing_repair_history_policy_artifact_kind
            ),
        )
        record = dict(payload)
        record.update(
            {
                "condition": condition,
                "kernel_class": payload.get("kernel_class"),
                "kernel_id": _first_present(
                    payload,
                    "kernel_id",
                    "kernel_name",
                    default=None,
                ),
                "kernel_name": payload.get("kernel_name"),
                "dtype": dtype,
                "dtype_original": dtype,
                "base_seed": _int_or_none(base_seed),
                "sample_index": _int_or_none(
                    _metadata_first_present(
                        payload,
                        generated_metadata,
                        replay_metadata,
                        "sample_index",
                        default=None,
                    )
                ),
                "replay_pair_id": _metadata_first_present(
                    payload,
                    generated_metadata,
                    replay_metadata,
                    "replay_pair_id",
                    default=None,
                ),
                "attempt_index": _int_or_none(attempt_index),
                "compile_success": compile_success,
                "functional_success": functional_success,
                "scale_tier": scale_tier,
                RAW_SCALE_TIER_COLUMN: raw_scale_tier,
                RAW_SCALE_TIER_EXPLICIT_COLUMN: raw_scale_tier_explicit,
                SCALE_TIER_SOURCE_COLUMN: scale_tier_source,
                REQUESTED_SCALE_TIER_COLUMN: requested_scale_tier,
                "grammar_variant": _first_present(
                    payload,
                    "grammar_variant",
                    nested=generated_metadata,
                    default=None,
                ),
                "grammar_claim_scope": _first_present(
                    payload,
                    "grammar_claim_scope",
                    nested=generated_metadata,
                    default=None,
                ),
                "grammar_valid": _bool_or_none(
                    _first_present(
                        payload,
                        "grammar_valid",
                        nested=generated_metadata,
                        default=None,
                    )
                ),
                "gbnf_parse_valid": _bool_or_none(
                    _first_present(
                        payload,
                        "gbnf_parse_valid",
                        nested=generated_metadata,
                        default=None,
                    )
                ),
                "semantic_valid": _bool_or_none(
                    _first_present(
                        payload,
                        "semantic_valid",
                        nested=generated_metadata,
                        default=None,
                    )
                ),
                "rejection_layer": _first_present(
                    payload,
                    "rejection_layer",
                    nested=generated_metadata,
                    default=None,
                ),
                "stop_reason": _first_present(
                    payload,
                    "stop_reason",
                    nested=generated_metadata,
                    default="unknown",
                ),
                "unique_ratio_ast": _float_or_none(payload.get("unique_ratio_ast")),
                "repair_traces": _first_present(
                    payload,
                    "repair_trace",
                    "repair_traces",
                    "RepairTrace",
                    "trace_summary",
                    default=None,
                ),
                "generated_metadata": generated_metadata,
                "replay_metadata": replay_metadata,
                "source_path": source_path,
                "source_row_index": row_index,
                **cluster3_diagnostics,
                **repair_history_metadata,
            }
        )
        for factor, active in _condition_factors(condition).items():
            record[factor] = active
        normalized.append(record)
    df = pd.DataFrame(normalized)
    return _validate_repair_history_artifacts(df)


def analyze_factorial(
    rows: pd.DataFrame | Iterable[Mapping[str, Any] | Any],
    *,
    response_variable: str = PRIMARY_RESPONSE_VARIABLE,
    analysis_scope: str | None = None,
    allow_mixed_scale: bool = False,
    scale_tier_annotation: str | None = None,
    bootstrap_samples: int = BOOTSTRAP_SAMPLES,
    bootstrap_seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    """Return structured factorial output for paper tables and diagnostics."""

    if bootstrap_samples <= 0:
        raise ValueError("bootstrap_samples must be positive")
    if response_variable not in {PRIMARY_RESPONSE_VARIABLE, SECONDARY_RESPONSE_VARIABLE}:
        raise ValueError(
            "response_variable must be functional_success or compile_success"
        )
    scope = _resolve_analysis_scope(response_variable, analysis_scope)
    df = (
        rows.copy()
        if isinstance(rows, pd.DataFrame)
        else normalize_result_rows(rows, scale_tier_annotation=scale_tier_annotation)
    )
    if df.empty:
        raise ValueError("factorial analysis requires at least one row")
    if "dtype_original" not in df:
        df = normalize_result_rows(
            df.to_dict("records"),
            scale_tier_annotation=scale_tier_annotation,
        )
    elif scale_tier_annotation is not None or not _has_scale_tier_metadata_columns(df):
        df = _apply_scale_tier_annotation_to_dataframe(
            df,
            scale_tier_annotation=scale_tier_annotation,
        )
    df = _ensure_pair_identity_columns(df)
    df = _ensure_cluster3_analysis_columns(df)
    df = _ensure_repair_history_analysis_columns(df)
    df = _validate_repair_history_artifacts(df)
    _validate_single_repair_history_analysis_group(df)

    _validate_conditions(df)
    scale_tiers = _validate_scale_tiers(df, allow_mixed_scale=allow_mixed_scale)
    scale_tier_metadata = _scale_tier_metadata(df, normalized_scale_tiers=scale_tiers)
    _validate_response(df, response_variable, scope)
    _validate_prompt_parity(df)

    populated_cells = tuple(
        condition
        for condition in CANONICAL_CONDITIONS
        if condition in set(df["condition"])
    )
    missing_cells = tuple(
        condition for condition in CANONICAL_CONDITIONS if condition not in populated_cells
    )
    cell_status = {
        condition: ("populated" if condition in populated_cells else "not_populated")
        for condition in CANONICAL_CONDITIONS
    }
    global_flags = []
    if any(condition in missing_cells for condition in P_CONDITIONS):
        global_flags.append("p_cells_not_populated")
    p_pair_control_warnings = _missing_p_pair_control_entries(df, populated_cells)
    if p_pair_control_warnings:
        global_flags.append(P_PAIR_COVERAGE_WARNING_FLAG)

    if scope == "primary_functional":
        _require_current_primary_cells(populated_cells)

    cell_outcomes = _cell_outcome_frame(df, response_variable=response_variable)
    summary_variables = [response_variable]
    if _should_emit_secondary_compile_summary(df, response_variable=response_variable):
        summary_variables.append(SECONDARY_RESPONSE_VARIABLE)
    cell_summaries = [
        row
        for variable in summary_variables
        for row in _cell_summaries(
            _summary_dataframe_for_response(df, variable),
            response_variable=variable,
        )
    ]

    paired_comparisons = _paired_comparison_rows(
        df,
        response_variable=response_variable,
        scope=scope,
        populated_cells=populated_cells,
        bootstrap_samples=bootstrap_samples,
        bootstrap_seed=bootstrap_seed,
    )
    paired_comparisons = _apply_paired_holm(paired_comparisons)
    if _should_emit_secondary_compile_summary(df, response_variable=response_variable):
        secondary_compile_comparisons = _secondary_compile_comparison_rows(
            df,
            populated_cells=populated_cells,
            bootstrap_samples=bootstrap_samples,
            bootstrap_seed=bootstrap_seed,
        )
        paired_comparisons.extend(
            _apply_paired_holm(
                secondary_compile_comparisons,
            )
        )

    factorial_model = _factorial_model(
        cell_outcomes,
        response_variable=response_variable,
        populated_cells=populated_cells,
    )
    diagnostics = _diagnostics(
        df,
        response_variable=response_variable,
        scope=scope,
        missing_cells=missing_cells,
        global_flags=global_flags,
    )
    scope_metadata = _scope_metadata(populated_cells, missing_cells)
    metadata = {
        "analyzer_version": ANALYZER_VERSION,
        "response_variable": response_variable,
        "analysis_scope": scope,
        **scope_metadata,
        "primary_response_variable": PRIMARY_RESPONSE_VARIABLE,
        "secondary_response_variable": SECONDARY_RESPONSE_VARIABLE,
        "paired_primary_comparisons": [
            {
                "treatment_condition": treatment,
                "control_condition": control,
            }
            for treatment, control in effective_paired_replay_comparisons(
                populated_cells
            ).items()
        ],
        "scale_tiers": scale_tiers,
        **scale_tier_metadata,
        **_repair_history_policy_metadata(df),
        "cells_populated": list(populated_cells),
        "cells_missing": list(missing_cells),
        "cells_status": cell_status,
        "constants": {
            "bootstrap_samples": bootstrap_samples,
            "bootstrap_seed": bootstrap_seed,
            "ci_level": CI_LEVEL,
            "multiple_testing_method": MULTIPLE_TESTING_METHOD,
            "significance_alpha": SIGNIFICANCE_ALPHA,
        },
        "reportable": _is_reportable_output(
            scope=scope,
            scale_tiers=scale_tiers,
            allow_mixed_scale=allow_mixed_scale,
            populated_cells=populated_cells,
        ),
        "interpretation_flags": global_flags,
        **_f3_and_coverage_metadata(df),
    }
    if p_pair_control_warnings:
        metadata["p_paired_control_warnings"] = p_pair_control_warnings
    if set(CANONICAL_CONDITIONS).issubset(set(populated_cells)):
        metadata["three_way_interaction"] = {
            "formula": (
                "(rate_GCP - rate_GC) - (rate_GP - rate_G) - "
                "(rate_CP - rate_C) + (rate_P - rate_none)"
            ),
            "reportable": True,
            "response_variable": response_variable,
        }
    elif any(condition in populated_cells for condition in P_CONDITIONS):
        metadata["three_way_interaction"] = {
            "reportable": False,
            "reason": "requires_all_eight_cells",
            "response_variable": response_variable,
        }
    result = {
        "metadata": metadata,
        "condition_rates": _condition_rate_summaries(df),
        "cell_summaries": cell_summaries,
        "paired_comparisons": paired_comparisons,
        "factorial_model": factorial_model,
        "diagnostics": diagnostics,
    }
    result["paper_tables"] = _paper_tables(result)
    return _json_safe(result)


def factorial_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Return secondary compile-only pass@1 diagnostics by factor combination."""

    normalized = df if "dtype_original" in df else normalize_result_rows(df.to_dict("records"))
    normalized = _ensure_cluster3_analysis_columns(normalized)
    normalized = _validate_repair_history_artifacts(
        _ensure_repair_history_analysis_columns(normalized)
    )
    _validate_response(normalized, SECONDARY_RESPONSE_VARIABLE, "secondary_compile_diagnostic")
    summary_frame = _repair_history_effective_group_frame(normalized)
    group_cols = _factorial_summary_group_columns(summary_frame)
    group_cols.extend(["kernel_class", "dtype"])
    return (
        summary_frame.groupby(group_cols, dropna=False)[SECONDARY_RESPONSE_VARIABLE]
        .agg(["sum", "count"])
        .rename(columns={"sum": "n_correct", "count": "n_total"})
        .assign(pass_at_1=lambda frame: frame["n_correct"] / frame["n_total"])
        .reset_index()
    )


def validate_paired_replay_dataframe(
    df: pd.DataFrame,
    *,
    treatment_condition: str,
    control_condition: str | None = None,
    response_variable: str = PRIMARY_RESPONSE_VARIABLE,
) -> None:
    """Reject primary comparisons that are not paired by seed and metadata."""

    df = _ensure_pair_identity_columns(df)
    expected_control = PAIRED_REPLAY_COMPARISONS.get(treatment_condition)
    if expected_control is None:
        raise ValueError(f"{treatment_condition!r} is not a paired generated condition")
    resolved_control = expected_control if control_condition is None else control_condition
    if resolved_control != expected_control:
        raise ValueError(
            f"{treatment_condition!r} must pair with {expected_control!r}; "
            f"got {resolved_control!r}"
        )
    _require_columns(
        df,
        ("condition", response_variable, "attempt_index", *PAIR_KEY_COLUMNS),
    )
    _require_non_missing_pair_keys(df)
    subset = df[df["condition"].isin({treatment_condition, resolved_control})]
    if subset[response_variable].isna().any():
        raise ValueError(
            f"missing {response_variable} values in paired replay dataframe"
        )
    treatment = subset[subset["condition"] == treatment_condition]
    control = subset[subset["condition"] == resolved_control]
    if treatment.empty or control.empty:
        raise ValueError("paired replay analysis requires both treatment and control rows")

    _require_replay_attempt_zero(control)
    _require_generated_attempt_zero(treatment)
    treatment_keys = _unique_pair_keys(treatment, allow_repeated_attempts=True)
    control_keys = _unique_pair_keys(control, allow_repeated_attempts=False)
    if treatment_keys != control_keys:
        raise ValueError(
            "paired replay dataframe has unmatched seed rows: "
            f"missing_control={sorted(treatment_keys - control_keys)}, "
            f"missing_treatment={sorted(control_keys - treatment_keys)}"
        )
    _validate_pair_metadata_columns(
        treatment,
        control,
        expected_control_condition=resolved_control,
    )


def paired_replay_summary(
    df: pd.DataFrame,
    *,
    treatment_condition: str,
    control_condition: str | None = None,
    response_variable: str = PRIMARY_RESPONSE_VARIABLE,
) -> pd.DataFrame:
    """Return paired binary outcomes for one generated-vs-replay comparison."""

    df = _ensure_pair_identity_columns(df)
    expected_control = PAIRED_REPLAY_COMPARISONS[treatment_condition]
    resolved_control = expected_control if control_condition is None else control_condition
    validate_paired_replay_dataframe(
        df,
        treatment_condition=treatment_condition,
        control_condition=resolved_control,
        response_variable=response_variable,
    )
    treatment = (
        df[df["condition"] == treatment_condition]
        .groupby(list(PAIR_KEY_COLUMNS), dropna=False)[response_variable]
        .any()
        .rename("treatment_success")
    )
    control = (
        df[df["condition"] == resolved_control]
        .groupby(list(PAIR_KEY_COLUMNS), dropna=False)[response_variable]
        .any()
        .rename("control_success")
    )
    paired = pd.concat([treatment, control], axis=1).reset_index()
    paired["paired_lift"] = paired["treatment_success"].astype(int) - paired[
        "control_success"
    ].astype(int)
    paired["treatment_condition"] = treatment_condition
    paired["control_condition"] = resolved_control
    paired["response_variable"] = response_variable
    return paired


def paired_condition_summary(
    df: pd.DataFrame,
    *,
    treatment_condition: str,
    control_condition: str,
    response_variable: str,
    allow_incomplete_coverage: bool = False,
    pair_key_columns: Sequence[str] | None = None,
    nullable_pair_key_columns: Sequence[str] = (),
) -> pd.DataFrame:
    """Return paired binary outcomes for arbitrary tuple-matched conditions."""

    df = _ensure_pair_identity_columns(df)
    key_columns = tuple(pair_key_columns or PAIR_KEY_COLUMNS)
    _require_columns(
        df,
        ("condition", response_variable, "attempt_index", *key_columns),
    )
    subset = df[df["condition"].isin({treatment_condition, control_condition})]
    non_nullable_key_columns = tuple(
        column for column in key_columns if column not in set(nullable_pair_key_columns)
    )
    _require_non_missing_pair_keys(
        subset,
        pair_key_columns=non_nullable_key_columns,
    )
    if subset[response_variable].isna().any():
        raise ValueError(
            f"missing {response_variable} values in paired condition dataframe"
        )
    treatment = subset[subset["condition"] == treatment_condition]
    control = subset[subset["condition"] == control_condition]
    if treatment.empty or control.empty:
        raise ValueError("paired condition analysis requires both treatment and control rows")

    treatment_keys = _unique_pair_keys(
        treatment,
        allow_repeated_attempts=True,
        pair_key_columns=key_columns,
    )
    control_keys = _unique_pair_keys(
        control,
        allow_repeated_attempts=True,
        pair_key_columns=key_columns,
    )
    if treatment_keys != control_keys:
        missing_control = treatment_keys - control_keys
        missing_treatment = control_keys - treatment_keys
        if not allow_incomplete_coverage:
            raise ValueError(
                "paired condition dataframe has unmatched seed rows: "
                f"missing_control={sorted(missing_control, key=_pair_key_sort_key)}, "
                f"missing_treatment={sorted(missing_treatment, key=_pair_key_sort_key)}"
            )
        common_keys = treatment_keys & control_keys
        if not common_keys:
            raise ValueError(
                "paired condition dataframe has no matched seed rows after "
                "coverage filtering: "
                f"missing_control={sorted(missing_control, key=_pair_key_sort_key)}, "
                f"missing_treatment={sorted(missing_treatment, key=_pair_key_sort_key)}"
            )
        treatment = _filter_pair_keys(
            treatment,
            common_keys,
            pair_key_columns=key_columns,
        )
        control = _filter_pair_keys(
            control,
            common_keys,
            pair_key_columns=key_columns,
        )
    else:
        missing_control = set()
        missing_treatment = set()
    treatment_outcomes = (
        treatment.groupby(list(key_columns), dropna=False)[response_variable]
        .any()
        .rename("treatment_success")
    )
    control_outcomes = (
        control.groupby(list(key_columns), dropna=False)[response_variable]
        .any()
        .rename("control_success")
    )
    paired = pd.concat([treatment_outcomes, control_outcomes], axis=1).reset_index()
    paired["paired_lift"] = paired["treatment_success"].astype(int) - paired[
        "control_success"
    ].astype(int)
    paired["treatment_condition"] = treatment_condition
    paired["control_condition"] = control_condition
    paired["response_variable"] = response_variable
    paired.attrs["missing_control_pairs"] = sorted(missing_control, key=_pair_key_sort_key)
    paired.attrs["missing_treatment_pairs"] = sorted(
        missing_treatment,
        key=_pair_key_sort_key,
    )
    paired.attrs["pair_key_columns"] = key_columns
    return paired


def paired_p_factor_summary(
    df: pd.DataFrame,
    *,
    treatment_condition: str,
    control_condition: str,
    response_variable: str,
    allow_incomplete_coverage: bool = False,
    allow_mixed_grammar_variant: bool = False,
) -> pd.DataFrame:
    """Return paired P/no-P outcomes for a Cluster 3 comparison."""

    expected_control = P_PAIRED_REPLAY_COMPARISONS.get(treatment_condition)
    if expected_control is None:
        raise ValueError(f"{treatment_condition!r} is not a P paired condition")
    if control_condition != expected_control:
        raise ValueError(
            f"{treatment_condition!r} must pair with {expected_control!r}; "
            f"got {control_condition!r}"
        )
    normalized = _ensure_p_pair_metadata_columns(
        _ensure_cluster3_analysis_columns(_ensure_pair_identity_columns(df))
    )
    subset = normalized[
        normalized["condition"].isin({treatment_condition, control_condition})
    ]
    if subset.empty:
        raise ValueError("paired P analysis requires treatment and control rows")
    pair_key_columns = _p_pair_key_columns(subset)
    _validate_p_pair_grammar_variant(
        subset,
        treatment_condition=treatment_condition,
        control_condition=control_condition,
        pair_key_columns=pair_key_columns,
        allow_mixed_grammar_variant=allow_mixed_grammar_variant,
    )
    return paired_condition_summary(
        normalized,
        treatment_condition=treatment_condition,
        control_condition=control_condition,
        response_variable=response_variable,
        allow_incomplete_coverage=allow_incomplete_coverage,
        pair_key_columns=pair_key_columns,
        nullable_pair_key_columns=_p_nullable_pair_key_columns(pair_key_columns),
    )


def _p_pair_key_columns(df: pd.DataFrame) -> tuple[str, ...]:
    columns: list[str] = ["kernel_class"]
    if "kernel_name" in df.columns and not df["kernel_name"].map(_is_missing_value).any():
        columns.append("kernel_name")
    else:
        columns.append("kernel_id")
    columns.extend(["dtype", "base_seed"])
    for optional in ("sample_index", "replay_pair_id"):
        if optional in df.columns and not df[optional].map(_is_missing_value).all():
            columns.append(optional)
    return tuple(columns)


def _p_nullable_pair_key_columns(pair_key_columns: Sequence[str]) -> tuple[str, ...]:
    return tuple(
        column
        for column in pair_key_columns
        if column in {"sample_index", "replay_pair_id"}
    )


P_PAIR_GRAMMAR_METADATA_COLUMNS: tuple[str, ...] = (
    "grammar_variant",
    "grammar_claim_scope",
    "grammar_sha",
    "grammar_sha256",
    "grammar_path",
)


def _ensure_p_pair_metadata_columns(df: pd.DataFrame) -> pd.DataFrame:
    normalized = _ensure_p_pair_identity_columns(df)
    for column in P_PAIR_GRAMMAR_METADATA_COLUMNS:
        extracted_values = [
            _p_pair_metadata_value(row.to_dict(), column)
            for _, row in normalized.iterrows()
        ]
        if column not in normalized.columns:
            normalized[column] = extracted_values
            continue
        normalized[column] = [
            existing if not _is_missing_value(existing) else extracted
            for existing, extracted in zip(
                normalized[column].tolist(),
                extracted_values,
                strict=True,
            )
        ]
    return normalized


def _ensure_p_pair_identity_columns(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    for column in ("sample_index", "replay_pair_id"):
        extracted_values = [
            _p_pair_identity_value(row.to_dict(), column)
            for _, row in normalized.iterrows()
        ]
        if column not in normalized.columns:
            normalized[column] = extracted_values
            continue
        normalized[column] = [
            existing if not _is_missing_value(existing) else extracted
            for existing, extracted in zip(
                normalized[column].tolist(),
                extracted_values,
                strict=True,
            )
        ]
    return normalized


def _p_pair_identity_value(payload: Mapping[str, Any], column: str) -> Any:
    generated_metadata = _metadata_dict(payload.get("generated_metadata"))
    replay_metadata = _metadata_dict(payload.get("replay_metadata"))
    value = _metadata_first_present(
        payload,
        generated_metadata,
        replay_metadata,
        column,
        default=None,
    )
    if column == "sample_index":
        return _int_or_none(value)
    return value


def _p_pair_metadata_value(payload: Mapping[str, Any], column: str) -> Any:
    generated_metadata = _metadata_dict(payload.get("generated_metadata"))
    replay_metadata = _metadata_dict(payload.get("replay_metadata"))
    return _metadata_first_present(
        payload,
        generated_metadata,
        replay_metadata,
        column,
        default=None,
    )


def _validate_p_pair_grammar_variant(
    df: pd.DataFrame,
    *,
    treatment_condition: str,
    control_condition: str,
    pair_key_columns: Sequence[str],
    allow_mixed_grammar_variant: bool,
) -> None:
    if allow_mixed_grammar_variant:
        return
    if "G" not in _condition_factor_labels(treatment_condition) and "G" not in (
        _condition_factor_labels(control_condition)
    ):
        return
    for column in (
        "grammar_variant",
        "grammar_claim_scope",
        "grammar_sha",
        "grammar_sha256",
        "grammar_path",
    ):
        if column not in df.columns:
            continue
        treatment_values = _single_values_by_pair_key(
            df[df["condition"] == treatment_condition],
            column=column,
            pair_key_columns=pair_key_columns,
        )
        control_values = _single_values_by_pair_key(
            df[df["condition"] == control_condition],
            column=column,
            pair_key_columns=pair_key_columns,
        )
        for key in sorted(
            set(treatment_values) & set(control_values),
            key=_pair_key_sort_key,
        ):
            if treatment_values[key] != control_values[key]:
                raise ValueError(
                    "mixed grammar variants in paired P comparison"
                    f" for {treatment_condition} vs {control_condition}: "
                    f"{column} differs at pair {key!r}"
                )


def _single_values_by_pair_key(
    df: pd.DataFrame,
    *,
    column: str,
    pair_key_columns: Sequence[str],
) -> dict[tuple[object, ...], object]:
    values_by_key: dict[tuple[object, ...], object] = {}
    for key, group in df.groupby(list(pair_key_columns), sort=True, dropna=False):
        raw_key_tuple = key if isinstance(key, tuple) else (key,)
        key_tuple = _canonical_pair_key_tuple(raw_key_tuple)
        values = {
            None if _is_missing_value(value) else value
            for value in group[column].tolist()
        }
        if len(values) > 1:
            raise ValueError(
                f"metadata mismatch within paired P dataframe for {column}: "
                f"{key_tuple!r}"
            )
        values_by_key[key_tuple] = next(iter(values)) if values else None
    return values_by_key


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", nargs="+", type=Path)
    parser.add_argument("--none", dest="none_input", type=Path)
    parser.add_argument("--g", dest="g_input", type=Path)
    parser.add_argument("--c", dest="c_input", type=Path)
    parser.add_argument("--gc", dest="gc_input", type=Path)
    parser.add_argument(
        "--input-roles",
        nargs="+",
        default=None,
        help="Optional per-input roles: none, g, c, gc.",
    )
    parser.add_argument(
        "--response-variable",
        choices=(PRIMARY_RESPONSE_VARIABLE, SECONDARY_RESPONSE_VARIABLE),
        default=PRIMARY_RESPONSE_VARIABLE,
    )
    parser.add_argument("--analysis-scope", default=None)
    parser.add_argument("--allow-mixed-scale", action="store_true")
    parser.add_argument(
        "--scale-tier",
        default=None,
        help=(
            "Analysis-level scale-tier annotation for rows that lack an explicit "
            "raw scale_tier. Explicit conflicting raw tiers are rejected."
        ),
    )
    parser.add_argument(
        "--missing-repair-history-policy-artifact-kind",
        choices=("known_legacy", "unknown"),
        default="known_legacy",
        help=(
            "How to classify artifacts whose rows omit repair_history_policy. "
            "The default preserves known legacy analyzer compatibility; unknown "
            "artifacts are quarantined."
        ),
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--bootstrap-samples", type=int, default=BOOTSTRAP_SAMPLES)
    parser.add_argument("--bootstrap-seed", type=int, default=BOOTSTRAP_SEED)
    args = parser.parse_args(argv)

    input_paths, input_roles = _cli_input_paths_and_roles(parser, args)
    df = load_result_paths(
        input_paths,
        input_roles=input_roles,
        scale_tier_annotation=args.scale_tier,
        missing_repair_history_policy_artifact_kind=(
            args.missing_repair_history_policy_artifact_kind
        ),
    )
    result = analyze_factorial(
        df,
        response_variable=args.response_variable,
        analysis_scope=args.analysis_scope,
        allow_mixed_scale=args.allow_mixed_scale,
        scale_tier_annotation=args.scale_tier,
        bootstrap_samples=args.bootstrap_samples,
        bootstrap_seed=args.bootstrap_seed,
    )
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    else:
        print(json.dumps(result, sort_keys=True, indent=2))
    if args.markdown_output is not None:
        from shared.eval.reporting.tables import render_factorial_markdown_report

        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(
            render_factorial_markdown_report(result) + "\n",
            encoding="utf-8",
        )
    # Seam D: optionally mirror analyzer aggregates into MLflow (post-hoc,
    # opt-in). The analyzer output written above is the source of truth; this
    # never changes it. Imported locally so the analyzer stays
    # infrastructure-agnostic and the pure functions never touch tracking.
    from shared import tracking

    with tracking.run_context(backend="local"):
        meta = result.get("metadata", {})
        tags = {"kind": "factorial_analysis"}
        for field in ("response_variable", "analysis_scope", "analyzer_version"):
            value = meta.get(field)
            if value:
                tags[field] = str(value)
        tracking.set_tags(tags)
        tracking.log_factorial_summary(result)
    return 0


def _cli_input_paths_and_roles(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> tuple[list[Path], Sequence[str | None] | None]:
    role_inputs = [
        ("none", args.none_input),
        ("g", args.g_input),
        ("c", args.c_input),
        ("gc", args.gc_input),
    ]
    supplied_role_inputs = [(role, path) for role, path in role_inputs if path is not None]
    if supplied_role_inputs:
        if args.inputs is not None or args.input_roles is not None:
            parser.error("use either --inputs/--input-roles or --none/--g/--c/--gc")
        missing_roles = [role for role, path in role_inputs if path is None]
        if missing_roles:
            parser.error(
                "condition-specific input flags require --none, --g, --c, and --gc; "
                f"missing: {', '.join(missing_roles)}"
            )
        return [path for _, path in role_inputs if path is not None], [
            role for role, _ in role_inputs
        ]
    if args.inputs is None:
        parser.error("one of --inputs or --none/--g/--c/--gc is required")
    return list(args.inputs), args.input_roles


def _resolve_analysis_scope(response_variable: str, analysis_scope: str | None) -> str:
    if analysis_scope is None:
        if response_variable == PRIMARY_RESPONSE_VARIABLE:
            return "primary_functional"
        return "secondary_compile_diagnostic"
    if analysis_scope == "primary_functional" and response_variable != PRIMARY_RESPONSE_VARIABLE:
        raise ValueError("primary_functional analysis requires functional_success")
    if response_variable == SECONDARY_RESPONSE_VARIABLE and "secondary" not in analysis_scope:
        raise ValueError("compile_success analysis must be labeled secondary diagnostic")
    return analysis_scope


def _row_to_dict(row: Mapping[str, Any] | Any) -> dict[str, Any]:
    if isinstance(row, Mapping):
        return dict(row)
    if hasattr(row, "to_dict"):
        return dict(row.to_dict())
    if is_dataclass(row):
        return asdict(row)
    raise TypeError("factorial analysis rows must be mappings or dataclass rows")


def _metadata_dict(value: object) -> dict[str, Any] | None:
    if value is None or _is_missing_value(value):
        return None
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        return dict(value.to_dict())
    if is_dataclass(value):
        return asdict(value)
    raise TypeError("metadata fields must be mappings when present")


def _normalize_input_role(input_role: str | None) -> str | None:
    if input_role is None:
        return None
    key = str(input_role).strip()
    if not key:
        raise ValueError("input_role must not be empty")
    normalized = INPUT_ROLE_ALIASES.get(key, INPUT_ROLE_ALIASES.get(key.lower()))
    if normalized is None:
        raise ValueError(f"unexpected analyzer input role: {input_role!r}")
    return normalized


def _normalize_condition(
    payload: Mapping[str, Any],
    *,
    input_role_condition: str | None = None,
) -> str:
    condition = payload.get("condition")
    if not _is_missing_value(condition):
        condition_text = str(condition)
        if condition_text not in CANONICAL_CONDITIONS:
            raise ValueError(f"unexpected non-canonical condition: {condition_text!r}")
        if input_role_condition is not None and input_role_condition != condition_text:
            raise ValueError(
                f"input role {input_role_condition!r} does not match row "
                f"condition {condition_text!r}"
            )
        return condition_text
    if input_role_condition is not None:
        return input_role_condition
    factors = {
        "G": bool(payload.get("grammar_active", False)),
        "C": bool(payload.get("compiler_feedback_active", False)),
        "P": bool(payload.get("compile_feedback_active", False))
        or bool(payload.get("perf_feedback_active", False)),
    }
    return _factors_to_condition(factors)


def _is_cluster1_compile_only_scope(
    *,
    condition: str,
    input_role_condition: str | None,
    source_path: str | None,
) -> bool:
    if input_role_condition in CLUSTER1_COMPILE_ONLY_CONDITIONS:
        return True
    if input_role_condition in {"C", "G+C"}:
        return False
    return (
        condition in CLUSTER1_COMPILE_ONLY_CONDITIONS
        and source_path is not None
        and "cluster1" in Path(source_path).parts
    )


def _normalize_compile_success(
    payload: Mapping[str, Any],
    *,
    condition: str,
    functional_success: bool | None,
    source_path: str | None,
    row_index: int,
) -> bool | None:
    raw_compile_success = payload.get("compile_success")
    if condition not in CLUSTER2_GENERATED_CONDITIONS:
        return _bool_or_none(raw_compile_success)

    raw_failure_code = payload.get("failure_code", _MISSING_FIELD)

    # For Cluster 2 rows, compile_success is derived only from unambiguous
    # terminal evidence when absent. F2 failures prove Level 2 was reached, but
    # F3_EVAL_PIPELINE is a malformed eval-payload/infrastructure failure and
    # does not by itself prove Level 1 compile success.
    if _is_missing_value(raw_compile_success):
        if raw_failure_code is _MISSING_FIELD:
            raise ValueError(
                "Cluster 2 compile_success is missing and cannot be derived "
                "without failure_code"
                f" for condition={condition!r}, source_path={source_path!r}, "
                f"row_index={row_index}"
            )
        resolved = _cluster2_compile_success_from_failure_code(
            raw_failure_code,
            payload=payload,
        )
    else:
        resolved = _bool_or_none(raw_compile_success)
        _validate_cluster2_compile_success_consistency(
            compile_success=resolved,
            failure_code=raw_failure_code,
            payload=payload,
            condition=condition,
            source_path=source_path,
            row_index=row_index,
        )

    if functional_success is True and resolved is False:
        raise ValueError(
            "Cluster 2 functional_success=True requires compile_success=True"
            f" for condition={condition!r}, source_path={source_path!r}, "
            f"row_index={row_index}"
        )
    return resolved


def _normalize_cluster3_diagnostic_fields(
    payload: Mapping[str, Any],
    *,
    generated_metadata: Mapping[str, Any] | None,
    condition: str,
    source_path: str | None,
    row_index: int,
) -> dict[str, Any]:
    has_p_factor = "P" in _condition_factor_labels(condition)
    if not has_p_factor and _has_active_p_diagnostic_field(payload, generated_metadata):
        raise ValueError(
            "non-P analyzer row must not carry active Cluster 3 P diagnostic fields"
            f" for condition={condition!r}, source_path={source_path!r}, "
            f"row_index={row_index}"
        )

    p_repair_attempted = _bool_with_default(
        _first_present(
            payload,
            "p_repair_attempted",
            nested=generated_metadata,
            default=False,
        ),
        default=False,
    )
    p_compile_repair_succeeded = _bool_with_default(
        _first_present(
            payload,
            "p_compile_repair_succeeded",
            nested=generated_metadata,
            default=False,
        ),
        default=False,
    )
    p_repair_changed_terminal_class = _bool_with_default(
        _first_present(
            payload,
            "p_repair_changed_terminal_class",
            nested=generated_metadata,
            default=False,
        ),
        default=False,
    )
    c_loop_fired = _bool_with_default(
        _first_present(
            payload,
            "c_loop_fired",
            nested=generated_metadata,
            default=False,
        ),
        default=False,
    )
    failure_code = payload.get("failure_code")
    return {
        "p_repair_attempted": p_repair_attempted,
        "p_compile_repair_succeeded": p_compile_repair_succeeded,
        "p_repair_changed_terminal_class": p_repair_changed_terminal_class,
        "p_repair_trace_summary": (
            _first_present(
                payload,
                "p_repair_trace_summary",
                "trace_summary",
                "p_repair_trace",
                nested=generated_metadata,
                default=None,
            )
            if has_p_factor
            else None
        ),
        "c_loop_fired": c_loop_fired,
        "c_loop_source": _first_present(
            payload,
            "c_loop_source",
            nested=generated_metadata,
            default="none",
        ),
        "c_terminal_failure_code": _first_present(
            payload,
            "c_terminal_failure_code",
            nested=generated_metadata,
            default=None,
        ),
        # Conservative v1 diagnostic only. The research predicate for whether
        # P "helped" remains pending; do not treat terminal-class change as help.
        "p_helped": bool(p_repair_attempted and failure_code is None),
    }


def _has_active_p_diagnostic_field(
    payload: Mapping[str, Any],
    generated_metadata: Mapping[str, Any] | None,
) -> bool:
    if generated_metadata is None:
        generated_metadata = _metadata_dict(payload.get("generated_metadata"))
    for field in (
        "p_repair_attempted",
        "p_compile_repair_succeeded",
        "p_repair_changed_terminal_class",
    ):
        value = _first_present(payload, field, nested=generated_metadata, default=None)
        if not _is_missing_value(value) and _bool_or_none(value) is True:
            return True
    attempt_count = _first_present(
        payload,
        "p_repair_attempt_count",
        nested=generated_metadata,
        default=None,
    )
    if not _is_missing_value(attempt_count) and int(attempt_count) > 0:
        return True
    for field in (
        "p_initial_failure_code",
        "p_terminal_failure_code",
        "p_compile_error_class",
        "p_raw_error_excerpt_sha256",
        "p_repair_trace_summary",
        "p_repair_trace",
    ):
        value = _first_present(payload, field, nested=generated_metadata, default=None)
        if not _is_missing_value(value):
            return True
    stop_reason = _first_present(
        payload,
        "p_repair_stop_reason",
        nested=generated_metadata,
        default=None,
    )
    return not _is_missing_value(stop_reason) and stop_reason != "p_not_applicable"


def _bool_with_default(value: object, *, default: bool) -> bool:
    resolved = _bool_or_none(value)
    return default if resolved is None else resolved


def _cluster2_compile_success_from_failure_code(
    failure_code: object,
    *,
    payload: Mapping[str, Any] | None = None,
) -> bool:
    if _is_missing_value(failure_code) or failure_code == "":
        return True
    if not isinstance(failure_code, str):
        raise ValueError(
            "Cluster 2 failure_code must be a string, null, or empty string; "
            f"got {failure_code!r}"
        )
    if failure_code.startswith(("F0_", "F1_")):
        return False
    if failure_code.startswith("F2_"):
        return True
    if failure_code == CLUSTER2_EVAL_PIPELINE_FAILURE_CODE:
        return _cluster2_has_level1_compile_evidence(payload)
    return False


def _validate_cluster2_compile_success_consistency(
    *,
    compile_success: bool | None,
    failure_code: object,
    payload: Mapping[str, Any],
    condition: str,
    source_path: str | None,
    row_index: int,
) -> None:
    if compile_success is None or failure_code is _MISSING_FIELD:
        return
    derived = _cluster2_hard_compile_requirement_from_failure_code(failure_code)
    if derived is not None and compile_success != derived:
        _raise_cluster2_compile_success_conflict(
            compile_success=compile_success,
            failure_code=failure_code,
            derived=derived,
            condition=condition,
            source_path=source_path,
            row_index=row_index,
        )
    if (
        failure_code == CLUSTER2_EVAL_PIPELINE_FAILURE_CODE
        and compile_success is False
        and _cluster2_has_level1_compile_evidence(
            payload,
            include_explicit_compile_success=False,
        )
    ):
        _raise_cluster2_compile_success_conflict(
            compile_success=compile_success,
            failure_code=failure_code,
            derived=True,
            condition=condition,
            source_path=source_path,
            row_index=row_index,
        )


def _cluster2_hard_compile_requirement_from_failure_code(
    failure_code: object,
) -> bool | None:
    if _is_missing_value(failure_code) or failure_code == "":
        return True
    if not isinstance(failure_code, str):
        raise ValueError(
            "Cluster 2 failure_code must be a string, null, or empty string; "
            f"got {failure_code!r}"
        )
    if failure_code.startswith(("F0_", "F1_")):
        return False
    if failure_code.startswith("F2_"):
        return True
    if failure_code == CLUSTER2_EVAL_PIPELINE_FAILURE_CODE:
        return None
    return False


def _raise_cluster2_compile_success_conflict(
    *,
    compile_success: bool,
    failure_code: object,
    derived: bool,
    condition: str,
    source_path: str | None,
    row_index: int,
) -> None:
    raise ValueError(
        "Cluster 2 compile_success conflicts with failure_code-derived "
        "semantics"
        f" for condition={condition!r}, source_path={source_path!r}, "
        f"row_index={row_index}: compile_success={compile_success!r}, "
        f"failure_code={failure_code!r}, derived_compile_success={derived!r}"
    )


def _cluster2_has_level1_compile_evidence(
    payload: Mapping[str, Any] | None,
    *,
    include_explicit_compile_success: bool = True,
) -> bool:
    if payload is None:
        return False
    if include_explicit_compile_success and payload.get("compile_success") is True:
        return True
    if payload.get("level1_success") is True:
        return True
    if _level_reached_at_least_two(payload.get("level_reached")):
        return True
    if _level_reached_at_least_two(payload.get("reached_level")):
        return True
    if _eval_stage_reached_level2(payload.get("eval_stage")):
        return True
    for key in ("compile_result", "correctness_result"):
        value = payload.get(key)
        if isinstance(value, Mapping) and _mapping_has_level1_compile_evidence(value):
            return True
    return False


def _mapping_has_level1_compile_evidence(value: Mapping[str, Any]) -> bool:
    if value.get("compile_success") is True:
        return True
    if value.get("success") is True:
        return True
    if value.get("level1_success") is True:
        return True
    if _level_reached_at_least_two(value.get("level_reached")):
        return True
    if _level_reached_at_least_two(value.get("reached_level")):
        return True
    return _eval_stage_reached_level2(value.get("eval_stage"))


def _level_reached_at_least_two(value: object) -> bool:
    if _is_missing_value(value) or isinstance(value, bool):
        return False
    if isinstance(value, (int, np.integer)):
        return int(value) >= 2
    return False


def _eval_stage_reached_level2(value: object) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.strip().lower().replace("-", "_")
    return normalized in {
        "level2",
        "level_2",
        "level2_correctness",
        "level_2_correctness",
        "correctness",
    }


def _condition_factors(condition: str) -> dict[str, bool]:
    parts = set() if condition == "none" else set(condition.split("+"))
    return {
        "grammar_active": "G" in parts,
        "compiler_feedback_active": "C" in parts,
        "perf_feedback_active": "P" in parts,
        "compile_feedback_active": "P" in parts,
    }


def _factors_to_condition(factors: Mapping[str, bool]) -> str:
    labels = []
    if factors.get("G"):
        labels.append("G")
    if factors.get("C"):
        labels.append("C")
    if factors.get("P"):
        labels.append("P")
    return "+".join(labels) if labels else "none"


def _validate_conditions(df: pd.DataFrame) -> None:
    _require_columns(df, ("condition", *PAIR_KEY_COLUMNS))
    invalid = sorted(set(df["condition"]) - set(CANONICAL_CONDITIONS))
    if invalid:
        raise ValueError(f"unexpected non-canonical condition labels: {invalid}")
    required_missing = [
        column
        for column in PAIR_KEY_COLUMNS
        if df[column].isna().any()
    ]
    if required_missing:
        raise ValueError(
            "missing required analyzer fields: " + ", ".join(required_missing)
        )


def _ensure_cluster3_analysis_columns(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    if "condition" not in normalized.columns:
        return normalized
    derived_factors = [
        _condition_factors(str(condition)) for condition in normalized["condition"]
    ]
    for factor in FACTOR_COLUMNS:
        derived_values = [factors[factor] for factors in derived_factors]
        if factor not in normalized.columns:
            normalized[factor] = derived_values
            continue
        resolved_values = []
        for raw_value, derived_value in zip(
            normalized[factor].tolist(),
            derived_values,
            strict=True,
        ):
            value = _bool_or_none(raw_value)
            if value is None:
                resolved_values.append(derived_value)
            elif value != derived_value:
                raise ValueError(
                    f"{factor} conflicts with canonical condition-derived factors"
                )
            else:
                resolved_values.append(value)
        normalized[factor] = resolved_values

    if "p_helped" in normalized.columns:
        normalized = normalized.drop(columns=["p_helped"])
    for column, default in (
        ("p_repair_attempted", False),
        ("p_compile_repair_succeeded", False),
        ("p_repair_changed_terminal_class", False),
        ("c_loop_fired", False),
    ):
        normalized[column] = [
            _cluster3_bool_diagnostic_value(row.to_dict(), column, default=default)
            for _, row in normalized.iterrows()
        ]
    for column, default in (
        ("p_repair_trace_summary", None),
        ("c_loop_source", "none"),
        ("c_terminal_failure_code", None),
    ):
        normalized[column] = [
            _cluster3_scalar_diagnostic_value(row.to_dict(), column, default=default)
            for _, row in normalized.iterrows()
        ]

    for row_index, row in normalized.iterrows():
        condition = str(row["condition"])
        if (
            "P" not in _condition_factor_labels(condition)
            and _has_active_p_diagnostic_field(row.to_dict(), None)
        ):
            raise ValueError(
                "non-P analyzer row must not carry active Cluster 3 P diagnostic fields"
                f" for condition={condition!r}, row_index={row_index}"
            )

    failure_codes = (
        normalized["failure_code"]
        if "failure_code" in normalized.columns
        else pd.Series([None] * len(normalized), index=normalized.index)
    )
    normalized["p_helped"] = [
        bool(attempted and failure_code is None)
        for attempted, failure_code in zip(
            normalized["p_repair_attempted"].tolist(),
            failure_codes.tolist(),
            strict=True,
        )
    ]
    return normalized


def _cluster3_bool_diagnostic_value(
    payload: Mapping[str, Any],
    column: str,
    *,
    default: bool,
) -> bool:
    generated_metadata = _metadata_dict(payload.get("generated_metadata"))
    return _bool_with_default(
        _first_present(
            payload,
            column,
            nested=generated_metadata,
            default=default,
        ),
        default=default,
    )


def _cluster3_scalar_diagnostic_value(
    payload: Mapping[str, Any],
    column: str,
    *,
    default: Any,
) -> Any:
    generated_metadata = _metadata_dict(payload.get("generated_metadata"))
    if column == "p_repair_trace_summary":
        condition = str(payload.get("condition", "none"))
        fields = ("p_repair_trace_summary", "p_repair_trace")
        if "P" in _condition_factor_labels(condition):
            fields = ("p_repair_trace_summary", "trace_summary", "p_repair_trace")
        return _first_present(
            payload,
            *fields,
            nested=generated_metadata,
            default=default,
        )
    return _first_present(
        payload,
        column,
        nested=generated_metadata,
        default=default,
    )


def _repair_history_metadata_from_payload(
    payload: Mapping[str, Any],
    *,
    generated_metadata: Mapping[str, Any] | None,
    replay_metadata: Mapping[str, Any] | None,
    source_path: str | None,
    row_index: int,
    missing_policy_artifact_kind: str,
) -> dict[str, Any]:
    if missing_policy_artifact_kind not in {"known_legacy", "unknown"}:
        raise ValueError(
            "missing_repair_history_policy_artifact_kind must be known_legacy "
            "or unknown"
        )

    values = {
        field: _repair_history_alias_value(
            payload,
            generated_metadata=generated_metadata,
            replay_metadata=replay_metadata,
            field=field,
            source_path=source_path,
            row_index=row_index,
        )
        for field in REPAIR_HISTORY_FIELD_ALIASES
    }
    raw_policy = values[REPAIR_HISTORY_POLICY_COLUMN]
    explicit_policy = not _is_missing_value(raw_policy)
    policy, state = _classify_repair_history_policy(
        raw_policy,
        missing_policy_artifact_kind=missing_policy_artifact_kind,
    )
    missing_agentic_metadata: list[str] = []
    if (
        policy == AGENTIC_TRANSCRIPT_REPAIR_HISTORY_POLICY_V1
        and (
            _has_rendered_repair_history_metadata(values)
            or _row_requires_rendered_repair_history_metadata(
                payload,
                generated_metadata=generated_metadata,
                replay_metadata=replay_metadata,
            )
        )
    ):
        missing_agentic_metadata = [
            field
            for field in REPAIR_HISTORY_AGENTIC_REQUIRED_METADATA
            if _is_missing_value(values.get(field))
        ]
        if missing_agentic_metadata:
            state = REPAIR_HISTORY_STATE_INCOMPLETE_AGENTIC

    result = {
        REPAIR_HISTORY_POLICY_COLUMN: policy,
        REPAIR_HISTORY_POLICY_STATE_COLUMN: state,
        RAW_REPAIR_HISTORY_POLICY_COLUMN: (
            None if _is_missing_value(raw_policy) else str(raw_policy)
        ),
        REPAIR_HISTORY_POLICY_EXPLICIT_COLUMN: explicit_policy,
        REPAIR_HISTORY_MISSING_METADATA_COLUMN: missing_agentic_metadata,
    }
    for field, value in values.items():
        if field == REPAIR_HISTORY_POLICY_COLUMN:
            continue
        result[field] = _normalize_repair_history_field_value(field, value)
    return result


def _repair_history_alias_value(
    payload: Mapping[str, Any],
    *,
    generated_metadata: Mapping[str, Any] | None,
    replay_metadata: Mapping[str, Any] | None,
    field: str,
    source_path: str | None,
    row_index: int,
) -> Any:
    candidates = REPAIR_HISTORY_FIELD_ALIASES[field]
    values: list[Any] = []
    for candidate in candidates:
        value = payload.get(candidate)
        if not _is_missing_value(value):
            values.append(value)
        for nested in (generated_metadata, replay_metadata):
            if nested is None:
                continue
            value = nested.get(candidate)
            if not _is_missing_value(value):
                values.append(value)
    unique = {_repair_history_comparable_value(value) for value in values}
    if len(unique) > 1:
        raise ValueError(
            "conflicting repair-history metadata aliases"
            f" for field={field!r}, source_path={source_path!r}, "
            f"row_index={row_index}: {sorted(unique)}"
        )
    return values[0] if values else None


def _repair_history_comparable_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    return str(value)


def _has_rendered_repair_history_metadata(values: Mapping[str, Any]) -> bool:
    return any(
        not _is_missing_value(values.get(field))
        for field in REPAIR_HISTORY_AGENTIC_REQUIRED_METADATA
    )


def _row_requires_rendered_repair_history_metadata(
    payload: Mapping[str, Any],
    *,
    generated_metadata: Mapping[str, Any] | None,
    replay_metadata: Mapping[str, Any] | None,
) -> bool:
    for field in REPAIR_HISTORY_ATTEMPT_INDEX_SIGNAL_FIELDS:
        value = _metadata_first_present(
            payload,
            generated_metadata,
            replay_metadata,
            field,
            default=None,
        )
        if _is_missing_value(value):
            continue
        if int(value) > 0:
            return True
    for field in REPAIR_HISTORY_ATTEMPT_BOOL_SIGNAL_FIELDS:
        value = _metadata_first_present(
            payload,
            generated_metadata,
            replay_metadata,
            field,
            default=None,
        )
        if _is_missing_value(value):
            continue
        if _bool_or_none(value) is True:
            return True
    return False


def _classify_repair_history_policy(
    raw_policy: Any,
    *,
    missing_policy_artifact_kind: str,
) -> tuple[str, str]:
    if _is_missing_value(raw_policy):
        if missing_policy_artifact_kind == "known_legacy":
            return (
                LAST_ATTEMPT_ONLY_REPAIR_HISTORY_POLICY_V1,
                REPAIR_HISTORY_STATE_KNOWN_LEGACY_MISSING,
            )
        return (
            UNKNOWN_LEGACY_REPAIR_HISTORY_POLICY,
            REPAIR_HISTORY_STATE_UNKNOWN_POLICY,
        )
    if not isinstance(raw_policy, str):
        return (str(raw_policy), REPAIR_HISTORY_STATE_UNKNOWN_POLICY)
    if raw_policy == LAST_ATTEMPT_ONLY_REPAIR_HISTORY_POLICY_V1:
        return (raw_policy, REPAIR_HISTORY_STATE_EXPLICIT_LEGACY)
    if raw_policy == AGENTIC_TRANSCRIPT_REPAIR_HISTORY_POLICY_V1:
        return (raw_policy, REPAIR_HISTORY_STATE_EXPLICIT_AGENTIC)
    if raw_policy not in REPAIR_HISTORY_POLICIES_V1:
        return (raw_policy, REPAIR_HISTORY_STATE_UNKNOWN_POLICY)
    return (raw_policy, REPAIR_HISTORY_STATE_UNKNOWN_POLICY)


def _normalize_repair_history_field_value(field: str, value: Any) -> Any:
    if _is_missing_value(value):
        return None
    if field in {
        "repair_anchor_attempt_index",
        "repair_latest_attempt_index",
        "repair_history_attempt_count",
        "repair_prompt_char_count",
        "repair_max_prompt_chars",
    }:
        return int(value)
    if field == "repair_include_latest_source":
        return _bool_or_none(value)
    return str(value)


def _ensure_repair_history_analysis_columns(df: pd.DataFrame) -> pd.DataFrame:
    if all(column in df.columns for column in REPAIR_HISTORY_ANALYZER_COLUMNS):
        return df.copy()

    updated = df.copy()
    rows: list[dict[str, Any]] = []
    for row_index, (_, row) in enumerate(updated.iterrows()):
        payload = row.to_dict()
        rows.append(
            _repair_history_metadata_from_payload(
                payload,
                generated_metadata=_metadata_dict(payload.get("generated_metadata")),
                replay_metadata=_metadata_dict(payload.get("replay_metadata")),
                source_path=(
                    str(payload.get("source_path"))
                    if not _is_missing_value(payload.get("source_path"))
                    else None
                ),
                row_index=row_index,
                missing_policy_artifact_kind="known_legacy",
            )
        )
    for column in REPAIR_HISTORY_ANALYZER_COLUMNS:
        updated[column] = [row[column] for row in rows]
    return updated


def _validate_repair_history_artifacts(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    normalized = _ensure_repair_history_analysis_columns(df)
    for artifact_key, artifact in _repair_history_artifact_groups(normalized):
        state_values = _repair_history_distinct_values(
            artifact[REPAIR_HISTORY_POLICY_STATE_COLUMN]
        )
        if REPAIR_HISTORY_STATE_UNKNOWN_POLICY in state_values:
            raise ValueError(
                "quarantined repair-history artifact has unknown repair_history_policy"
                f" for artifact={artifact_key!r}: {state_values}"
            )
        if REPAIR_HISTORY_STATE_INCOMPLETE_AGENTIC in state_values:
            missing = _missing_agentic_metadata_by_artifact(artifact)
            raise ValueError(
                "quarantined repair-history artifact has incomplete "
                "agentic_transcript_v1 metadata"
                f" for artifact={artifact_key!r}: {missing}"
            )
        non_missing_states = [
            state
            for state in state_values
            if not _is_missing_value(state)
        ]
        if len(non_missing_states) > 1:
            normalized.loc[
                artifact.index,
                REPAIR_HISTORY_POLICY_STATE_COLUMN,
            ] = REPAIR_HISTORY_STATE_MIXED_POLICY_ARTIFACT
            raise ValueError(
                "quarantined mixed_policy_artifact repair_history_policy artifact"
                f" for artifact={artifact_key!r}: {non_missing_states}"
            )
        for column in REPAIR_HISTORY_ARTIFACT_HOMOGENEITY_COLUMNS:
            values = _repair_history_distinct_values(artifact[column])
            if len(values) > 1:
                raise ValueError(
                    "quarantined mixed repair-history prompt metadata"
                    f" for artifact={artifact_key!r}, column={column!r}: {values}"
                )
    return normalized


def _repair_history_artifact_groups(
    df: pd.DataFrame,
) -> Iterable[tuple[str, pd.DataFrame]]:
    if "source_path" not in df.columns:
        yield "<in_memory_rows>", df
        return
    artifact_keys = [
        "<in_memory_rows>"
        if _is_missing_value(value)
        else str(value)
        for value in df["source_path"].tolist()
    ]
    for artifact_key in sorted(set(artifact_keys)):
        mask = [key == artifact_key for key in artifact_keys]
        yield artifact_key, df.loc[mask]


def _repair_history_distinct_values(series: pd.Series) -> list[Any]:
    values = {
        _repair_history_group_value(value)
        for value in series.tolist()
        if not _is_missing_value(value)
    }
    return sorted(values, key=lambda value: str(value))


def _repair_history_group_value(value: Any) -> Any:
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    return value


def _missing_agentic_metadata_by_artifact(artifact: pd.DataFrame) -> dict[int, list[str]]:
    result: dict[int, list[str]] = {}
    for row_index, row in artifact.iterrows():
        missing = row.get(REPAIR_HISTORY_MISSING_METADATA_COLUMN)
        if _is_missing_value(missing):
            continue
        missing_values = list(missing)
        if missing_values:
            result[int(row_index)] = missing_values
    return result


def _repair_history_group_columns(df: pd.DataFrame) -> list[str]:
    return [
        column
        for column in REPAIR_HISTORY_GROUPING_COLUMNS
        if column in df.columns
    ]


def _repair_history_group_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    group_frame = _repair_history_effective_group_frame(df)
    group_columns = _repair_history_group_columns(group_frame)
    groups: list[dict[str, Any]] = []
    if group_columns:
        for key, group in group_frame.groupby(group_columns, sort=True, dropna=False):
            key_tuple = key if isinstance(key, tuple) else (key,)
            record = {
                column: _repair_history_output_value(value)
                for column, value in zip(group_columns, key_tuple, strict=True)
            }
            record["n_rows"] = int(len(group))
            groups.append(record)
    return groups


def _repair_history_effective_group_frame(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.copy()
    if grouped.empty:
        return grouped
    for _, artifact in _repair_history_artifact_groups(grouped):
        _fill_missing_repair_history_group_values(grouped, artifact.index)
    if REPAIR_HISTORY_POLICY_COLUMN in grouped.columns:
        for _, policy_group in grouped.groupby(
            REPAIR_HISTORY_POLICY_COLUMN,
            sort=True,
            dropna=False,
        ):
            _fill_missing_repair_history_group_values(grouped, policy_group.index)
    return grouped


def _fill_missing_repair_history_group_values(
    grouped: pd.DataFrame,
    index: pd.Index,
) -> None:
    for column in REPAIR_HISTORY_ARTIFACT_HOMOGENEITY_COLUMNS:
        if column not in grouped.columns:
            continue
        values = _repair_history_distinct_values(grouped.loc[index, column])
        if len(values) != 1:
            continue
        fill_value = values[0]
        missing_mask = [
            _is_missing_value(value)
            for value in grouped.loc[index, column].tolist()
        ]
        if any(missing_mask):
            grouped.loc[index[missing_mask], column] = fill_value


def _validate_single_repair_history_analysis_group(df: pd.DataFrame) -> None:
    groups = _repair_history_group_records(df)
    if len(groups) <= 1:
        return
    raise ValueError(
        "quarantined mixed repair-history analysis groups; analyze each "
        f"repair-history group separately: {groups}"
    )


def _repair_history_policy_metadata(df: pd.DataFrame) -> dict[str, Any]:
    group_columns = _repair_history_group_columns(df)
    groups = _repair_history_group_records(df)
    return {
        "repair_history_policy_states": _repair_history_distinct_values(
            df[REPAIR_HISTORY_POLICY_STATE_COLUMN]
        ),
        "repair_history_policies": _repair_history_distinct_values(
            df[REPAIR_HISTORY_POLICY_COLUMN]
        ),
        "repair_history_group_columns": group_columns,
        "repair_history_groups": groups,
        "repair_history_policy_quarantine": "reject_by_default",
    }


def _repair_history_output_value(value: Any) -> Any:
    if _is_missing_value(value):
        return None
    return _repair_history_group_value(value)


def _factorial_summary_group_columns(df: pd.DataFrame) -> list[str]:
    group_cols: list[str] = []
    for column in (
        "grammar_active",
        "compiler_feedback_active",
        "perf_feedback_active",
        "compile_feedback_active",
    ):
        if column in df.columns:
            group_cols.append(column)
    group_cols.extend(_repair_history_group_columns(df))
    return group_cols


def _validate_scale_tiers(
    df: pd.DataFrame,
    *,
    allow_mixed_scale: bool,
) -> list[str]:
    if "scale_tier" not in df.columns:
        return ["unspecified"]
    tiers = _scale_tier_values(df["scale_tier"])
    if not tiers:
        tiers = ["unspecified"]
    if len(tiers) > 1 and not allow_mixed_scale:
        raise ValueError(
            "mixed scale_tier inputs are diagnostic-only; pass allow_mixed_scale "
            f"to override: {tiers}"
        )
    return tiers


def _has_scale_tier_metadata_columns(df: pd.DataFrame) -> bool:
    return all(
        column in df.columns
        for column in (
            RAW_SCALE_TIER_COLUMN,
            RAW_SCALE_TIER_EXPLICIT_COLUMN,
            SCALE_TIER_SOURCE_COLUMN,
            REQUESTED_SCALE_TIER_COLUMN,
        )
    )


def _raw_scale_tier_from_payload(
    payload: Mapping[str, Any],
    generated_metadata: Mapping[str, Any] | None,
    replay_metadata: Mapping[str, Any] | None,
    *,
    source_path: str | None,
    row_index: int,
) -> tuple[str, bool]:
    values = []
    for container in (payload, generated_metadata, replay_metadata):
        if (
            container is not None
            and "scale_tier" in container
            and not _is_missing_value(container.get("scale_tier"))
        ):
            values.append(_normalize_scale_tier(container["scale_tier"]))
    tiers = sorted(set(values))
    if len(tiers) > 1:
        raise ValueError(
            "conflicting raw scale_tier values"
            f" for source_path={source_path!r}, row_index={row_index}: {tiers}"
        )
    if tiers:
        return tiers[0], True
    return "unspecified", False


def _normalize_requested_scale_tier(value: object) -> str | None:
    if _is_missing_value(value):
        return None
    tier = str(value).strip()
    if not tier:
        raise ValueError("scale_tier annotation must not be empty")
    return tier


def _resolve_scale_tier(
    *,
    raw_scale_tier: object,
    raw_scale_tier_explicit: bool,
    requested_scale_tier: str | None,
    source_path: str | None,
    row_index: int,
) -> tuple[str, str]:
    raw_tier = _normalize_scale_tier(raw_scale_tier)
    if requested_scale_tier is None:
        source = (
            SCALE_TIER_SOURCE_RAW
            if raw_scale_tier_explicit
            else SCALE_TIER_SOURCE_MISSING_DEFAULT
        )
        return raw_tier, source
    if raw_scale_tier_explicit:
        if raw_tier != requested_scale_tier:
            raise ValueError(
                "scale_tier annotation conflicts with explicit raw scale_tier"
                f" for source_path={source_path!r}, row_index={row_index}: "
                f"raw={raw_tier!r}, requested={requested_scale_tier!r}"
            )
        return raw_tier, SCALE_TIER_SOURCE_RAW
    return requested_scale_tier, SCALE_TIER_SOURCE_ANALYSIS_ANNOTATION


def _apply_scale_tier_annotation_to_dataframe(
    df: pd.DataFrame,
    *,
    scale_tier_annotation: str | None,
) -> pd.DataFrame:
    requested_scale_tier = _normalize_requested_scale_tier(scale_tier_annotation)
    updated = df.copy()
    scale_tiers: list[str] = []
    raw_scale_tiers: list[str] = []
    raw_explicit_values: list[bool] = []
    scale_tier_sources: list[str] = []
    requested_scale_tiers: list[str | None] = []
    for row_index, (_, row) in enumerate(updated.iterrows()):
        if RAW_SCALE_TIER_COLUMN in updated.columns and not _is_missing_value(
            row.get(RAW_SCALE_TIER_COLUMN)
        ):
            raw_scale_tier = row.get(RAW_SCALE_TIER_COLUMN)
            if RAW_SCALE_TIER_EXPLICIT_COLUMN in updated.columns and not _is_missing_value(
                row.get(RAW_SCALE_TIER_EXPLICIT_COLUMN)
            ):
                raw_scale_tier_explicit = bool(row.get(RAW_SCALE_TIER_EXPLICIT_COLUMN))
            else:
                raw_scale_tier_explicit = False
        else:
            payload = row.to_dict()
            raw_scale_tier, raw_scale_tier_explicit = _raw_scale_tier_from_payload(
                payload,
                _metadata_dict(payload.get("generated_metadata")),
                _metadata_dict(payload.get("replay_metadata")),
                source_path=None,
                row_index=row_index,
            )

        scale_tier, scale_tier_source = _resolve_scale_tier(
            raw_scale_tier=raw_scale_tier,
            raw_scale_tier_explicit=raw_scale_tier_explicit,
            requested_scale_tier=requested_scale_tier,
            source_path=None,
            row_index=row_index,
        )
        scale_tiers.append(scale_tier)
        raw_scale_tiers.append(_normalize_scale_tier(raw_scale_tier))
        raw_explicit_values.append(raw_scale_tier_explicit)
        scale_tier_sources.append(scale_tier_source)
        requested_scale_tiers.append(requested_scale_tier)

    updated["scale_tier"] = scale_tiers
    updated[RAW_SCALE_TIER_COLUMN] = raw_scale_tiers
    updated[RAW_SCALE_TIER_EXPLICIT_COLUMN] = raw_explicit_values
    updated[SCALE_TIER_SOURCE_COLUMN] = scale_tier_sources
    updated[REQUESTED_SCALE_TIER_COLUMN] = requested_scale_tiers
    return updated


def _scale_tier_metadata(
    df: pd.DataFrame,
    *,
    normalized_scale_tiers: Sequence[str],
) -> dict[str, Any]:
    if RAW_SCALE_TIER_COLUMN in df.columns:
        raw_scale_tiers = _scale_tier_values(df[RAW_SCALE_TIER_COLUMN])
    else:
        raw_scale_tiers = list(normalized_scale_tiers)
    if not raw_scale_tiers:
        raw_scale_tiers = ["unspecified"]

    scale_tier_sources = (
        _non_missing_sorted_text_values(df[SCALE_TIER_SOURCE_COLUMN])
        if SCALE_TIER_SOURCE_COLUMN in df.columns
        else [SCALE_TIER_SOURCE_RAW]
    )
    if not scale_tier_sources:
        scale_tier_sources = [SCALE_TIER_SOURCE_RAW]
    if len(scale_tier_sources) == 1:
        scale_tier_source: str | list[str] = scale_tier_sources[0]
    else:
        scale_tier_source = "mixed:" + ",".join(scale_tier_sources)

    requested_values = (
        _non_missing_sorted_text_values(df[REQUESTED_SCALE_TIER_COLUMN])
        if REQUESTED_SCALE_TIER_COLUMN in df.columns
        else []
    )
    if len(requested_values) == 0:
        requested_scale_tier: str | list[str] | None = None
    elif len(requested_values) == 1:
        requested_scale_tier = requested_values[0]
    else:
        requested_scale_tier = requested_values

    return {
        "scale_tier_source": scale_tier_source,
        "scale_tier_sources": scale_tier_sources,
        "requested_scale_tier": requested_scale_tier,
        "raw_scale_tiers_before_annotation": raw_scale_tiers,
        "normalized_scale_tiers": list(normalized_scale_tiers),
    }


def _non_missing_sorted_text_values(series: pd.Series) -> list[str]:
    return sorted(
        {
            str(value)
            for value in series
            if not _is_missing_value(value)
        }
    )


def _is_reportable_output(
    *,
    scope: str,
    scale_tiers: Sequence[str],
    allow_mixed_scale: bool,
    populated_cells: Sequence[str],
) -> bool:
    base_reportable = (
        scope == "primary_functional"
        and not allow_mixed_scale
        and tuple(scale_tiers) == ("paper",)
    )
    if not base_reportable:
        return False
    populated = set(populated_cells)
    has_any_p = any(condition in populated for condition in P_CONDITIONS)
    if has_any_p:
        return set(CANONICAL_CONDITIONS).issubset(populated)
    return set(CURRENT_FOUR_CELL_CONDITIONS).issubset(populated)


def _validate_response(df: pd.DataFrame, response_variable: str, scope: str) -> None:
    _require_columns(df, (response_variable,))
    missing = df[response_variable].isna()
    if missing.any():
        if response_variable == PRIMARY_RESPONSE_VARIABLE and scope == "primary_functional":
            raise ValueError(
                "missing functional_success for primary Cluster 2 factorial analysis"
            )
        raise ValueError(f"missing {response_variable} for requested analysis")


def _should_emit_secondary_compile_summary(
    df: pd.DataFrame,
    *,
    response_variable: str,
) -> bool:
    return (
        response_variable == PRIMARY_RESPONSE_VARIABLE
        and SECONDARY_RESPONSE_VARIABLE in df.columns
        and df[SECONDARY_RESPONSE_VARIABLE].notna().all()
    )


def _require_current_primary_cells(populated_cells: Sequence[str]) -> None:
    missing = [
        condition
        for condition in CURRENT_FOUR_CELL_CONDITIONS
        if condition not in set(populated_cells)
    ]
    if missing:
        raise ValueError(
            "primary functional factorial analysis requires the current four-cell "
            f"design; missing: {', '.join(missing)}"
        )


def _cell_outcome_frame(
    df: pd.DataFrame,
    *,
    response_variable: str,
) -> pd.DataFrame:
    _require_columns(df, ("condition", *PAIR_KEY_COLUMNS, response_variable))
    rows: list[dict[str, Any]] = []
    group_cols = ["condition", *PAIR_KEY_COLUMNS]
    for key, group in df.groupby(group_cols, sort=True, dropna=False):
        condition, kernel_class, kernel_id, dtype, base_seed = key
        if group.duplicated(["attempt_index"]).any():
            raise ValueError(f"duplicate attempt_index values for cell {key}")
        source_classes = set(group.get("source_class", pd.Series(dtype=object)).dropna())
        is_replay_control = source_classes == {"replay_control_row"}
        if is_replay_control:
            attempt_zero = group[group["attempt_index"] == 0]
            if len(attempt_zero) != 1:
                raise ValueError(f"replay cell {key} must have exactly one attempt_index 0 row")
            success = bool(attempt_zero.iloc[0][response_variable])
            attempts_considered = 1
        else:
            success = bool(group[response_variable].astype(bool).any())
            attempts_considered = len(group)
        rows.append(
            {
                "condition": condition,
                "kernel_class": kernel_class,
                "kernel_id": kernel_id,
                "dtype": dtype,
                "base_seed": int(base_seed),
                **_condition_factors(str(condition)),
                "response_variable": response_variable,
                "success": success,
                "attempts_observed": len(group),
                "attempts_considered": attempts_considered,
            }
        )
    return pd.DataFrame(rows)


def _cell_summaries(
    df: pd.DataFrame,
    *,
    response_variable: str,
) -> list[dict[str, Any]]:
    if response_variable not in df.columns or not df[response_variable].notna().any():
        return []
    outcomes = _cell_outcome_frame(df, response_variable=response_variable)
    rows: list[dict[str, Any]] = []
    for summary_level, group_cols in (
        ("condition", ["condition"]),
        ("condition_kernel_dtype", ["condition", "kernel_class", "dtype"]),
    ):
        for key, group in outcomes.groupby(group_cols, sort=True, dropna=False):
            key_tuple = key if isinstance(key, tuple) else (key,)
            record = dict(zip(group_cols, key_tuple, strict=True))
            subset = _summary_subset(df, group_cols, key_tuple)
            flags = _summary_flags(subset, response_variable)
            successes = int(group["success"].sum())
            n_cells = int(len(group))
            condition = str(record["condition"])
            rows.append(
                {
                    "metric_name": _metric_name(response_variable),
                    "response_variable": response_variable,
                    "analysis_role": _analysis_role(response_variable),
                    "summary_level": summary_level,
                    "scale_tier": _summary_scale_tier(subset),
                    "cell_status": "populated",
                    **record,
                    "condition_label": _condition_label_from_subset(
                        condition,
                        subset,
                    ),
                    "n_cells": n_cells,
                    "successes": successes,
                    "success_rate": successes / n_cells if n_cells else None,
                    "interpretation_flags": flags,
                }
            )
    return rows


def _summary_dataframe_for_response(
    df: pd.DataFrame,
    response_variable: str,
) -> pd.DataFrame:
    if response_variable == SECONDARY_RESPONSE_VARIABLE:
        return _compile_success_rate_dataframe(df)
    return df


def _compile_success_rate_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if "failure_code" not in df.columns:
        return df
    return df[df["failure_code"] != CLUSTER2_EVAL_PIPELINE_FAILURE_CODE]


def _condition_rate_summaries(df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    summaries: dict[str, dict[str, Any]] = {}
    functional = (
        _cell_outcome_frame(df, response_variable=PRIMARY_RESPONSE_VARIABLE)
        if PRIMARY_RESPONSE_VARIABLE in df.columns
        and df[PRIMARY_RESPONSE_VARIABLE].notna().all()
        else pd.DataFrame()
    )
    compile_complete = (
        SECONDARY_RESPONSE_VARIABLE in df.columns
        and df[SECONDARY_RESPONSE_VARIABLE].notna().all()
    )
    compile_outcomes = (
        _cell_outcome_frame(
            _compile_success_rate_dataframe(df),
            response_variable=SECONDARY_RESPONSE_VARIABLE,
        )
        if compile_complete
        else pd.DataFrame()
    )
    compile_matched_outcomes = (
        _cell_outcome_frame(df, response_variable=SECONDARY_RESPONSE_VARIABLE)
        if compile_complete
        else pd.DataFrame()
    )
    f3_counts = _f3_excluded_counts(df)
    for condition in sorted(set(df["condition"]), key=CANONICAL_CONDITIONS.index):
        record: dict[str, Any] = {"condition": condition}
        if functional.empty:
            functional_successes = None
            functional_n = 0
            functional_rate = None
            functional_ci = None
        else:
            functional_group = functional[functional["condition"] == condition]
            functional_successes = int(functional_group["success"].sum())
            functional_n = int(len(functional_group))
            functional_rate = (
                functional_successes / functional_n if functional_n else None
            )
            functional_ci = _wilson_ci(functional_successes, functional_n)
        record.update(
            {
                "functional_success_successes": functional_successes,
                "functional_success_n": functional_n,
                "functional_success_rate": functional_rate,
                "functional_success_wilson_ci_95": functional_ci,
            }
        )

        if not compile_complete:
            record.update(
                {
                    "compile_success_successes": None,
                    "compile_success_n": 0,
                    "compile_success_rate": None,
                    "compile_success_wilson_ci_95": None,
                    "compile_success_f3_excluded": f3_counts.get(condition, 0),
                    "compile_success_matched_analysis_successes": None,
                    "compile_success_matched_analysis_n": 0,
                    "compile_success_matched_analysis_rate": None,
                }
            )
        else:
            if compile_outcomes.empty:
                compile_successes = 0
                compile_n = 0
            else:
                compile_group = compile_outcomes[
                    compile_outcomes["condition"] == condition
                ]
                compile_successes = int(compile_group["success"].sum())
                compile_n = int(len(compile_group))
            compile_group_all = compile_matched_outcomes[
                compile_matched_outcomes["condition"] == condition
            ]
            compile_all_successes = int(compile_group_all["success"].sum())
            compile_all_n = int(len(compile_group_all))
            compile_ci = _wilson_ci(compile_successes, compile_n)
            record.update(
                {
                    "compile_success_successes": compile_successes,
                    "compile_success_n": compile_n,
                    "compile_success_rate": (
                        compile_successes / compile_n if compile_n else None
                    ),
                    "compile_success_wilson_ci_95": compile_ci,
                    "compile_success_f3_excluded": f3_counts.get(condition, 0),
                    "compile_success_matched_analysis_successes": compile_all_successes,
                    "compile_success_matched_analysis_n": compile_all_n,
                    "compile_success_matched_analysis_rate": (
                        compile_all_successes / compile_all_n if compile_all_n else None
                    ),
                }
            )
        summaries[condition] = record
    return summaries


def _wilson_ci(successes: int, n: int) -> list[float] | None:
    if n == 0:
        return None
    confidence = CI_LEVEL
    alpha = 1.0 - confidence
    z = NormalDist().inv_cdf(1.0 - alpha / 2.0)
    phat = successes / n
    z2 = z * z
    denominator = 1.0 + z2 / n
    center = (phat + z2 / (2.0 * n)) / denominator
    half_width = (
        z
        * math.sqrt((phat * (1.0 - phat) / n) + (z2 / (4.0 * n * n)))
        / denominator
    )
    return [max(0.0, center - half_width), min(1.0, center + half_width)]


def _summary_subset(
    df: pd.DataFrame,
    group_cols: Sequence[str],
    key_tuple: Sequence[object],
) -> pd.DataFrame:
    mask = pd.Series([True] * len(df), index=df.index)
    for column, value in zip(group_cols, key_tuple, strict=True):
        mask &= df[column] == value
    return df[mask]


def _summary_scale_tier(subset: pd.DataFrame) -> str:
    if "scale_tier" not in subset.columns:
        return "unspecified"
    tiers = _scale_tier_values(subset["scale_tier"])
    if not tiers:
        return "unspecified"
    if len(tiers) == 1:
        return tiers[0]
    return "mixed:" + ",".join(tiers)


def _scale_tier_values(series: pd.Series) -> list[str]:
    return sorted({_normalize_scale_tier(value) for value in series})


def _normalize_scale_tier(value: object) -> str:
    if _is_missing_value(value):
        return "unspecified"
    return str(value)


def _summary_flags(
    subset: pd.DataFrame,
    response_variable: str,
) -> list[str]:
    flags: list[str] = []
    if response_variable == SECONDARY_RESPONSE_VARIABLE:
        flags.extend(["diagnostic_only", "strict_surface_metric"])
    collapse = subset[_mode_collapse_mask(subset)]
    if not collapse.empty:
        flags.append(MODE_COLLAPSE_FLAG)
    return flags


def _paired_comparison_rows(
    df: pd.DataFrame,
    *,
    response_variable: str,
    scope: str,
    populated_cells: Sequence[str],
    bootstrap_samples: int,
    bootstrap_seed: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for treatment_condition, control_condition in effective_paired_replay_comparisons(
        populated_cells
    ).items():
        is_p_pair = treatment_condition in P_PAIRED_REPLAY_COMPARISONS
        if treatment_condition not in populated_cells or control_condition not in populated_cells:
            if scope == "primary_functional" and not is_p_pair:
                raise ValueError(
                    "paired primary comparison cannot be constructed because "
                    f"{treatment_condition} or {control_condition} is missing"
                )
            continue
        try:
            if is_p_pair:
                paired = paired_p_factor_summary(
                    df,
                    treatment_condition=treatment_condition,
                    control_condition=control_condition,
                    response_variable=response_variable,
                    allow_incomplete_coverage=True,
                )
            else:
                paired = paired_replay_summary(
                    df,
                    treatment_condition=treatment_condition,
                    control_condition=control_condition,
                    response_variable=response_variable,
                )
        except ValueError as exc:
            if is_p_pair and _is_skippable_p_pair_error(exc):
                continue
            raise
        flags = []
        if response_variable == SECONDARY_RESPONSE_VARIABLE:
            flags.extend(["diagnostic_only", "strict_surface_metric"])
        if is_p_pair:
            flags.append("p_paired_comparison")
        if paired.attrs.get("missing_control_pairs") or paired.attrs.get(
            "missing_treatment_pairs"
        ):
            flags.append("coverage_warning_skip_missing")
        if any(condition not in populated_cells for condition in P_CONDITIONS):
            flags.append("p_cells_not_populated")
        rows.append(
            _paired_comparison_record(
                df,
                paired=paired,
                treatment_condition=treatment_condition,
                control_condition=control_condition,
                response_variable=response_variable,
                populated_cells=populated_cells,
                bootstrap_samples=bootstrap_samples,
                bootstrap_seed=bootstrap_seed,
                interpretation_flags=flags,
                comparison_role=(
                    "primary"
                    if response_variable == PRIMARY_RESPONSE_VARIABLE
                    else "secondary_diagnostic"
                ),
            )
        )
    return rows


def _secondary_compile_comparison_rows(
    df: pd.DataFrame,
    *,
    populated_cells: Sequence[str],
    bootstrap_samples: int,
    bootstrap_seed: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for treatment_condition, control_condition in SECONDARY_COMPILE_COMPARISONS.items():
        if treatment_condition not in populated_cells or control_condition not in populated_cells:
            continue
        paired = paired_condition_summary(
            df,
            treatment_condition=treatment_condition,
            control_condition=control_condition,
            response_variable=SECONDARY_RESPONSE_VARIABLE,
            allow_incomplete_coverage=True,
        )
        flags = ["diagnostic_only", "strict_surface_metric"]
        if paired.attrs.get("missing_control_pairs") or paired.attrs.get(
            "missing_treatment_pairs"
        ):
            flags.append("coverage_warning_skip_missing")
        if any(condition not in populated_cells for condition in P_CONDITIONS):
            flags.append("p_cells_not_populated")
        rows.append(
            _paired_comparison_record(
                df,
                paired=paired,
                treatment_condition=treatment_condition,
                control_condition=control_condition,
                response_variable=SECONDARY_RESPONSE_VARIABLE,
                populated_cells=populated_cells,
                bootstrap_samples=bootstrap_samples,
                bootstrap_seed=bootstrap_seed,
                interpretation_flags=flags,
                comparison_role="secondary_diagnostic",
            )
        )
    return rows


def _is_skippable_p_pair_error(exc: ValueError) -> bool:
    text = str(exc)
    return (
        "requires treatment and control rows" in text
        or "requires both treatment and control rows" in text
        or "no matched seed rows" in text
    )


def _paired_comparison_record(
    df: pd.DataFrame,
    *,
    paired: pd.DataFrame,
    treatment_condition: str,
    control_condition: str,
    response_variable: str,
    populated_cells: Sequence[str],
    bootstrap_samples: int,
    bootstrap_seed: int,
    interpretation_flags: Sequence[str],
    comparison_role: str,
) -> dict[str, Any]:
    treatment_values = paired["treatment_success"].astype(bool).tolist()
    control_values = paired["control_success"].astype(bool).tolist()
    n_pairs = len(paired)
    treatment_rate = sum(treatment_values) / n_pairs
    control_rate = sum(control_values) / n_pairs
    absolute_lift = treatment_rate - control_rate
    ci_low, ci_high = _paired_bootstrap_ci(
        treatment_values,
        control_values,
        samples=bootstrap_samples,
        seed=bootstrap_seed,
    )
    treatment_only = sum(t and not c for t, c in zip(treatment_values, control_values))
    control_only = sum(c and not t for t, c in zip(treatment_values, control_values))
    treatment_label = _condition_label_from_df(df, treatment_condition)
    control_label = _condition_label_from_df(df, control_condition)
    pair_key_columns = tuple(paired.attrs.get("pair_key_columns", PAIR_KEY_COLUMNS))
    return {
        "metric_name": _metric_name(response_variable),
        "response_variable": response_variable,
        "comparison_role": comparison_role,
        "comparison": f"{treatment_condition} vs {control_condition}",
        "comparison_label": f"{treatment_label} vs {control_label}",
        "condition_a": control_condition,
        "condition_b": treatment_condition,
        "control_condition": control_condition,
        "treatment_condition": treatment_condition,
        "n_pairs": n_pairs,
        "success_rate_a": control_rate,
        "success_rate_b": treatment_rate,
        "control_rate": control_rate,
        "treatment_rate": treatment_rate,
        "absolute_lift": absolute_lift,
        "relative_lift": None if control_rate == 0 else absolute_lift / control_rate,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "ci_level": CI_LEVEL,
        "p_value": _mcnemar_exact_p_value(treatment_only, control_only),
        "p_value_holm": None,
        "multiple_testing_method": MULTIPLE_TESTING_METHOD,
        "paired_analysis": True,
        "discordant_treatment_only": treatment_only,
        "discordant_control_only": control_only,
        "concordant_success": sum(
            t and c for t, c in zip(treatment_values, control_values)
        ),
        "concordant_failure": sum(
            not t and not c for t, c in zip(treatment_values, control_values)
        ),
        "missing_control_pairs": [
            _pair_key_to_dict(key, pair_key_columns=pair_key_columns)
            for key in paired.attrs.get("missing_control_pairs", [])
        ],
        "missing_treatment_pairs": [
            _pair_key_to_dict(key, pair_key_columns=pair_key_columns)
            for key in paired.attrs.get("missing_treatment_pairs", [])
        ],
        "bootstrap_samples": bootstrap_samples,
        "bootstrap_seed": bootstrap_seed,
        "cells_populated": list(populated_cells),
        "cells_missing": [
            condition
            for condition in CANONICAL_CONDITIONS
            if condition not in populated_cells
        ],
        "interpretation_flags": list(interpretation_flags),
    }


def _condition_label_from_df(df: pd.DataFrame, condition: str) -> str:
    subset = df[df["condition"] == condition]
    return _condition_label_from_subset(condition, subset)


def _condition_label_from_subset(condition: str, subset: pd.DataFrame) -> str:
    if "grammar_variant" not in subset.columns:
        return grammar_condition_label_for_variants(condition, ())
    variants = (
        None if _is_missing_value(value) else str(value)
        for value in subset["grammar_variant"].tolist()
    )
    return grammar_condition_label_for_variants(condition, variants)


def _apply_paired_holm(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return rows
    if MULTIPLE_TESTING_METHOD != "holm":
        raise ValueError(f"unsupported multiple testing method: {MULTIPLE_TESTING_METHOD}")
    adjusted = _holm_adjust([row["p_value"] for row in rows])
    for row, p_value_holm in zip(rows, adjusted, strict=True):
        row["p_value_holm"] = p_value_holm
        row["significant_holm"] = p_value_holm < SIGNIFICANCE_ALPHA
    return rows


def _factorial_model(
    cell_outcomes: pd.DataFrame,
    *,
    response_variable: str,
    populated_cells: Sequence[str],
) -> dict[str, Any]:
    if cell_outcomes.empty:
        return {
            "response_variable": response_variable,
            "model_type": "not_fit",
            "terms": [],
            "warnings": ["no_cell_outcomes"],
        }
    has_all_eight = set(CANONICAL_CONDITIONS).issubset(set(populated_cells))
    has_p = any(condition in populated_cells for condition in P_CONDITIONS)
    has_current_four = set(CURRENT_FOUR_CELL_CONDITIONS).issubset(set(populated_cells))
    if has_all_eight:
        model_type = "full_eight_cell"
        factor_terms = ("G", "C", "P", "G:C", "G:P", "C:P", "G:C:P")
        formula = (
            f"{response_variable} ~ G + C + P + G:C + G:P + C:P + G:C:P "
            "+ kernel_class + dtype"
        )
    elif not has_p and has_current_four:
        model_type = "reduced_four_cell"
        factor_terms = ("G", "C", "G:C")
        formula = f"{response_variable} ~ G + C + G:C + kernel_class + dtype"
    elif not has_p:
        return {
            "response_variable": response_variable,
            "model_type": "partial_four_cell_not_reportable",
            "model_family": "binary_logistic_irls",
            "model_fit_status": "not_fit",
            "formula": (
                f"{response_variable} ~ G + C + G:C + kernel_class + dtype"
            ),
            "controls": ["kernel_class", "dtype"],
            "n_observations": int(len(cell_outcomes)),
            "rank": None,
            "iterations": 0,
            "terms": [],
            "control_terms": [],
            "warnings": [
                "partial_four_cell_coverage_blocks_reduced_factorial_model",
                "p_cells_not_populated",
            ],
        }
    else:
        model_type = "partial_eight_cell_not_reportable"
        factor_terms = ("G", "C", "P", "G:C", "G:P", "C:P", "G:C:P")
        formula = (
            f"{response_variable} ~ G + C + P + G:C + G:P + C:P + G:C:P "
            "+ kernel_class + dtype"
        )

    design, column_names = _design_matrix(cell_outcomes, factor_terms=factor_terms)
    y = cell_outcomes["success"].astype(float).to_numpy()
    rank = int(np.linalg.matrix_rank(design))
    warnings: list[str] = []
    if rank < len(column_names):
        warnings.append("model_design_rank_deficient")
    if len(cell_outcomes) <= len(column_names):
        warnings.append("model_underpowered")
    if not has_all_eight:
        warnings.append("p_cells_not_populated")
    if model_type == "partial_eight_cell_not_reportable":
        warnings.append("partial_p_cell_coverage_blocks_full_factorial_claims")
    fit_result = _fit_binary_logistic_irls(design, y, column_names)
    warnings.extend(fit_result["warnings"])
    coefficient_map = fit_result["coefficients"]
    standard_error_map = fit_result.get("standard_errors", {})
    logistic_interaction_ci = _logistic_coefficient_ci(
        coefficient_map.get("G:C"),
        standard_error_map.get("G:C"),
    )

    result = {
        "response_variable": response_variable,
        "model_type": model_type,
        "model_family": "binary_logistic_irls",
        "model_fit_status": fit_result["status"],
        "formula": formula,
        "controls": ["kernel_class", "dtype"],
        "n_observations": int(len(cell_outcomes)),
        "rank": rank,
        "iterations": fit_result["iterations"],
        "interaction_logistic_coefficient": coefficient_map.get("G:C"),
        "interaction_logistic_ci_95": logistic_interaction_ci,
        "interaction_additive_did": _additive_difference_in_differences(
            cell_outcomes,
        ),
        "terms": [
            {
                "term": term,
                "coefficient": coefficient_map.get(term),
                "ci_95": _logistic_coefficient_ci(
                    coefficient_map.get(term),
                    standard_error_map.get(term),
                ),
                "direction": _direction(coefficient_map.get(term)),
            }
            for term in factor_terms
        ],
        "control_terms": [
            {
                "term": name,
                "coefficient": value,
            }
            for name, value in coefficient_map.items()
            if name.startswith("kernel_class=") or name.startswith("dtype=")
        ],
        "warnings": warnings,
    }
    if has_all_eight:
        result["three_way_interaction_additive"] = _additive_three_way_interaction(
            cell_outcomes,
        )
        result["three_way_interaction_formula"] = (
            "(rate_GCP - rate_GC) - (rate_GP - rate_G) - "
            "(rate_CP - rate_C) + (rate_P - rate_none)"
        )
        result["three_way_interaction_reportable"] = True
    elif has_p:
        result["three_way_interaction_reportable"] = False
    return result


def _fit_binary_logistic_irls(
    design: np.ndarray,
    y: np.ndarray,
    column_names: Sequence[str],
) -> dict[str, Any]:
    unavailable = {column: None for column in column_names}
    if len(set(y.astype(int).tolist())) < 2:
        return {
            "status": "not_fit",
            "coefficients": unavailable,
            "standard_errors": unavailable,
            "iterations": 0,
            "warnings": ["model_outcome_has_single_class"],
        }
    if np.linalg.matrix_rank(design) < design.shape[1]:
        return {
            "status": "not_fit",
            "coefficients": unavailable,
            "standard_errors": unavailable,
            "iterations": 0,
            "warnings": ["model_design_rank_deficient"],
        }

    coefficients = np.zeros(design.shape[1], dtype=float)
    for iteration in range(1, LOGISTIC_MAX_ITERATIONS + 1):
        eta = np.clip(design @ coefficients, -LOGISTIC_ETA_CLIP, LOGISTIC_ETA_CLIP)
        probabilities = 1.0 / (1.0 + np.exp(-eta))
        weights = np.maximum(probabilities * (1.0 - probabilities), LOGISTIC_MIN_WEIGHT)
        adjusted_response = eta + (y - probabilities) / weights
        weighted_design = design * np.sqrt(weights)[:, None]
        weighted_response = adjusted_response * np.sqrt(weights)
        next_coefficients, _, _, _ = np.linalg.lstsq(
            weighted_design,
            weighted_response,
            rcond=None,
        )
        if np.max(np.abs(next_coefficients)) > LOGISTIC_SEPARATION_COEFFICIENT:
            return {
                "status": "not_fit",
                "coefficients": unavailable,
                "standard_errors": unavailable,
                "iterations": iteration,
                "warnings": ["model_separation_detected"],
            }
        if np.max(np.abs(next_coefficients - coefficients)) < LOGISTIC_TOLERANCE:
            standard_errors, se_warnings = _logistic_standard_errors(
                design,
                next_coefficients,
                column_names,
            )
            return {
                "status": "fit",
                "coefficients": {
                    column: float(value)
                    for column, value in zip(
                        column_names,
                        next_coefficients,
                        strict=True,
                    )
                },
                "standard_errors": standard_errors,
                "iterations": iteration,
                "warnings": se_warnings,
            }
        coefficients = next_coefficients

    return {
        "status": "not_fit",
        "coefficients": unavailable,
        "standard_errors": unavailable,
        "iterations": LOGISTIC_MAX_ITERATIONS,
        "warnings": ["model_logistic_fit_did_not_converge"],
    }


def _logistic_standard_errors(
    design: np.ndarray,
    coefficients: np.ndarray,
    column_names: Sequence[str],
) -> tuple[dict[str, float | None], list[str]]:
    eta = np.clip(design @ coefficients, -LOGISTIC_ETA_CLIP, LOGISTIC_ETA_CLIP)
    probabilities = 1.0 / (1.0 + np.exp(-eta))
    weights = np.maximum(probabilities * (1.0 - probabilities), LOGISTIC_MIN_WEIGHT)
    information = design.T @ (design * weights[:, None])
    try:
        covariance = np.linalg.inv(information)
    except np.linalg.LinAlgError:
        return {column: None for column in column_names}, ["model_ci_unavailable"]
    standard_errors = np.sqrt(np.maximum(np.diag(covariance), 0.0))
    return {
        column: float(value)
        for column, value in zip(column_names, standard_errors, strict=True)
    }, []


def _logistic_coefficient_ci(
    coefficient: float | None,
    standard_error: float | None,
) -> list[float] | None:
    if coefficient is None or standard_error is None:
        return None
    alpha = 1.0 - CI_LEVEL
    z = NormalDist().inv_cdf(1.0 - alpha / 2.0)
    return [coefficient - z * standard_error, coefficient + z * standard_error]


def _additive_difference_in_differences(cell_outcomes: pd.DataFrame) -> float | None:
    rates: dict[str, float] = {}
    for condition in CURRENT_FOUR_CELL_CONDITIONS:
        subset = cell_outcomes[cell_outcomes["condition"] == condition]
        if subset.empty:
            return None
        rates[condition] = float(subset["success"].mean())
    return (rates["G+C"] - rates["G"]) - (rates["C"] - rates["none"])


def _additive_three_way_interaction(cell_outcomes: pd.DataFrame) -> float | None:
    rates: dict[str, float] = {}
    for condition in CANONICAL_CONDITIONS:
        subset = cell_outcomes[cell_outcomes["condition"] == condition]
        if subset.empty:
            return None
        rates[condition] = float(subset["success"].mean())
    return (
        (rates["G+C+P"] - rates["G+C"])
        - (rates["G+P"] - rates["G"])
        - (rates["C+P"] - rates["C"])
        + (rates["P"] - rates["none"])
    )


def _design_matrix(
    cell_outcomes: pd.DataFrame,
    *,
    factor_terms: Sequence[str],
) -> tuple[np.ndarray, list[str]]:
    columns: list[str] = ["intercept", *factor_terms]
    kernel_classes = sorted(cell_outcomes["kernel_class"].dropna().unique())
    dtypes = sorted(cell_outcomes["dtype"].dropna().unique())
    control_columns = [
        *(f"kernel_class={value}" for value in kernel_classes[1:]),
        *(f"dtype={value}" for value in dtypes[1:]),
    ]
    columns.extend(control_columns)
    matrix: list[list[float]] = []
    for _, row in cell_outcomes.iterrows():
        values = [1.0]
        for term in factor_terms:
            term_parts = term.split(":")
            values.append(float(all(_model_factor_active(row, part) for part in term_parts)))
        values.extend(
            float(row["kernel_class"] == value) for value in kernel_classes[1:]
        )
        values.extend(float(row["dtype"] == value) for value in dtypes[1:])
        matrix.append(values)
    return np.asarray(matrix, dtype=float), columns


def _model_factor_active(row: pd.Series, factor: str) -> bool:
    column_by_factor = {
        "G": "grammar_active",
        "C": "compiler_feedback_active",
        "P": "compile_feedback_active",
    }
    column = column_by_factor[factor]
    if column in row and not _is_missing_value(row[column]):
        return bool(row[column])
    return factor in _condition_factor_labels(str(row["condition"]))


def _condition_factor_labels(condition: str) -> set[str]:
    if condition == "none":
        return set()
    return set(condition.split("+"))


def _diagnostics(
    df: pd.DataFrame,
    *,
    response_variable: str,
    scope: str,
    missing_cells: Sequence[str],
    global_flags: Sequence[str],
) -> dict[str, Any]:
    mode_collapse_rows = df[_mode_collapse_mask(df)]
    return {
        "analysis_scope": scope,
        "response_variable": response_variable,
        "rows_loaded": int(len(df)),
        "missing_cells": list(missing_cells),
        **_scope_metadata(
            [condition for condition in CANONICAL_CONDITIONS if condition not in missing_cells],
            missing_cells,
        ),
        "unpaired_primary_comparisons_allowed": False,
        "mixed_scale_policy": "reject_by_default",
        "interpretation_flags": list(global_flags),
        "secondary_compile_summary": _secondary_compile_summary_diagnostic(
            df,
            response_variable=response_variable,
        ),
        "grammar_acceptance_summary": _grammar_acceptance_summary(df),
        "rejection_layer_breakdown": _value_breakdown(
            df,
            column="rejection_layer",
            condition_filter="G",
        ),
        "stop_reason_breakdown": _value_breakdown(df, column="stop_reason"),
        "mode_collapse_warning_rows": int(len(mode_collapse_rows)),
        "mode_collapse_warning_text": (
            MODE_COLLAPSE_TEXT if not mode_collapse_rows.empty else None
        ),
    }


def _f3_and_coverage_metadata(df: pd.DataFrame) -> dict[str, Any]:
    return {
        "f3_eval_pipeline_policy": (
            "F3_EVAL_PIPELINE rows excluded from compile_success rate calculations; "
            "treated as compile_success=False in matched-pair analysis when "
            "independent compile-pass evidence is absent."
        ),
        "f3_excluded_counts": _f3_excluded_counts(df),
        "g_replay_coverage": _g_replay_coverage_statement(df),
    }


def _f3_excluded_counts(df: pd.DataFrame) -> dict[str, int]:
    if "failure_code" not in df.columns:
        return {}
    f3 = df[df["failure_code"] == CLUSTER2_EVAL_PIPELINE_FAILURE_CODE]
    if f3.empty:
        return {}
    return {
        str(condition): int(count)
        for condition, count in f3.groupby("condition", sort=True).size().items()
    }


def _f3_pair_keys_by_condition(df: pd.DataFrame) -> dict[str, set[tuple[object, ...]]]:
    if "failure_code" not in df.columns:
        return {}
    f3 = df[df["failure_code"] == CLUSTER2_EVAL_PIPELINE_FAILURE_CODE]
    result: dict[str, set[tuple[object, ...]]] = {}
    for condition, group in f3.groupby("condition", sort=True):
        result[str(condition)] = {
            tuple(row[column] for column in PAIR_KEY_COLUMNS)
            for _, row in group.iterrows()
        }
    return result


def _g_replay_coverage_statement(df: pd.DataFrame) -> str | None:
    if not {"none", "G"}.issubset(set(df["condition"])):
        return None
    none_keys = _condition_pair_keys(df, "none")
    g_keys = _condition_pair_keys(df, "G")
    missing = sorted(none_keys - g_keys, key=_pair_key_sort_key)
    if not missing:
        return (
            f"{len(g_keys)}/{len(none_keys)} task-agnostic G replay rows; "
            "0 rows missing. Policy: COVERAGE_WARNING_SKIP_MISSING."
        )
    missing_text = ", ".join(
        f"{kernel_class}/{dtype}/base_seed={base_seed}"
        for kernel_class, _kernel_id, dtype, base_seed in missing
    )
    return (
        f"{len(g_keys)}/{len(none_keys)} task-agnostic G replay rows; "
        f"{len(missing)} {missing[0][0]} rows missing ({missing_text}). "
        "Policy: COVERAGE_WARNING_SKIP_MISSING."
    )


def _condition_pair_keys(
    df: pd.DataFrame,
    condition: str,
    *,
    pair_key_columns: Sequence[str] = PAIR_KEY_COLUMNS,
) -> set[tuple[object, ...]]:
    subset = df[df["condition"] == condition]
    return {
        _pair_key_from_row(row, pair_key_columns=pair_key_columns)
        for _, row in subset.iterrows()
    }


def _missing_p_pair_control_entries(
    df: pd.DataFrame,
    populated_cells: Sequence[str],
) -> list[dict[str, Any]]:
    df = _ensure_p_pair_identity_columns(df)
    populated = set(populated_cells)
    entries: list[dict[str, Any]] = []
    for treatment_condition, control_condition in P_PAIRED_REPLAY_COMPARISONS.items():
        if treatment_condition not in populated:
            continue
        if control_condition not in populated:
            entries.append(
                {
                    "treatment_condition": treatment_condition,
                    "control_condition": control_condition,
                    "reason": "control_cell_missing",
                    "missing_control_pairs": [],
                }
            )
            continue
        subset = df[df["condition"].isin({treatment_condition, control_condition})]
        pair_key_columns = _p_pair_key_columns(subset)
        treatment_keys = _condition_pair_keys(
            subset,
            treatment_condition,
            pair_key_columns=pair_key_columns,
        )
        control_keys = _condition_pair_keys(
            subset,
            control_condition,
            pair_key_columns=pair_key_columns,
        )
        missing_keys = sorted(treatment_keys - control_keys, key=_pair_key_sort_key)
        if missing_keys:
            entries.append(
                {
                    "treatment_condition": treatment_condition,
                    "control_condition": control_condition,
                    "reason": "control_pair_keys_missing",
                    "missing_control_pairs": [
                        _pair_key_to_dict(key, pair_key_columns=pair_key_columns)
                        for key in missing_keys
                    ],
                }
            )
    return entries


def _pair_key_from_row(
    row: pd.Series,
    *,
    pair_key_columns: Sequence[str] = PAIR_KEY_COLUMNS,
) -> tuple[object, ...]:
    return _canonical_pair_key_tuple(row[column] for column in pair_key_columns)


def _pair_key_to_dict(
    key: tuple[object, ...],
    *,
    pair_key_columns: Sequence[str] = PAIR_KEY_COLUMNS,
) -> dict[str, Any]:
    return dict(
        zip(
            pair_key_columns,
            (_pair_key_output_value(value) for value in key),
            strict=True,
        )
    )


def _pair_key_sort_key(key: tuple[object, ...]) -> tuple[object, ...]:
    if len(key) != len(PAIR_KEY_COLUMNS) or any(
        _is_canonical_missing_pair_key(value) for value in key
    ):
        return tuple(_pair_key_sort_value(value) for value in key)
    kernel_class, kernel_id, dtype, base_seed = key
    dtype_order = {"fp32": 0, "fp16": 1, "bf16": 2}
    dtype_text = str(dtype)
    return (
        str(kernel_class),
        str(kernel_id),
        f"{dtype_order.get(dtype_text, 99):02d}:{dtype_text}",
        int(base_seed),
    )


def _canonical_pair_key_tuple(values: Iterable[object]) -> tuple[object, ...]:
    return tuple(_canonical_pair_key_value(value) for value in values)


def _canonical_pair_key_value(value: object) -> object:
    if _is_missing_value(value):
        return _MISSING_PAIR_KEY
    return value


def _is_canonical_missing_pair_key(value: object) -> bool:
    return value is _MISSING_PAIR_KEY or _is_missing_value(value)


def _pair_key_output_value(value: object) -> Any:
    if _is_canonical_missing_pair_key(value):
        return None
    return value


def _pair_key_sort_value(value: object) -> str:
    if _is_canonical_missing_pair_key(value):
        return ""
    return str(value)


def _grammar_acceptance_summary(df: pd.DataFrame) -> list[dict[str, Any]]:
    if "grammar_valid" not in df.columns:
        return []
    grammar_rows = df[df["condition"].astype(str).str.contains("G", regex=False)]
    grammar_rows = grammar_rows[grammar_rows["grammar_valid"].notna()]
    if grammar_rows.empty:
        return []
    rows: list[dict[str, Any]] = []
    for condition, group in grammar_rows.groupby("condition", sort=True):
        rows.append(
            {
                "condition": condition,
                "n_rows": int(len(group)),
                "grammar_valid_count": int(group["grammar_valid"].sum()),
                "grammar_valid_rate": float(group["grammar_valid"].mean()),
                "gbnf_parse_valid_rate": _nullable_bool_mean(
                    group,
                    "gbnf_parse_valid",
                ),
                "semantic_valid_rate": _nullable_bool_mean(
                    group,
                    "semantic_valid",
                ),
            }
        )
    return rows


def _nullable_bool_mean(df: pd.DataFrame, column: str) -> float | None:
    if column not in df.columns or not df[column].notna().any():
        return None
    return float(df[column].dropna().astype(bool).mean())


def _value_breakdown(
    df: pd.DataFrame,
    *,
    column: str,
    condition_filter: str | None = None,
) -> list[dict[str, Any]]:
    if column not in df.columns:
        return []
    subset = df
    if condition_filter is not None:
        subset = subset[subset["condition"].astype(str).str.contains(condition_filter, regex=False)]
    subset = subset[subset[column].notna()]
    if subset.empty:
        return []
    grouped = subset.groupby(["condition", column], sort=True).size()
    return [
        {"condition": condition, column: value, "count": int(count)}
        for (condition, value), count in grouped.items()
    ]


def _scope_metadata(
    populated_cells: Sequence[str],
    missing_cells: Sequence[str],
) -> dict[str, Any]:
    populated = set(populated_cells)
    missing = set(missing_cells)
    has_current_four = populated == set(CURRENT_FOUR_CELL_CONDITIONS)
    has_all_eight = set(CANONICAL_CONDITIONS).issubset(populated)
    p_cells_populated = any(condition in populated for condition in P_CONDITIONS)
    p_cells_missing = any(condition in missing for condition in P_CONDITIONS)
    if has_all_eight:
        analysis_label = FULL_FACTORIAL_ANALYSIS_LABEL
        scope_kind = "full_2^3_factorial"
        p_cell_status = "P-containing cells are populated."
        statements = [FULL_FACTORIAL_GOAL_STATEMENT]
    elif has_current_four:
        analysis_label = CURRENT_SUBSET_ANALYSIS_LABEL
        scope_kind = "temporary_2^2_subset"
        p_cell_status = P_CELL_DEFERRAL_STATEMENT
        statements = [
            CURRENT_ITERATION_SCOPE_STATEMENT,
            FULL_FACTORIAL_GOAL_STATEMENT,
            P_CELL_DEFERRAL_STATEMENT,
            CURRENT_STATUS_SCOPE_STATEMENT,
        ]
    else:
        analysis_label = PARTIAL_FACTORIAL_ANALYSIS_LABEL
        scope_kind = "partial_factorial"
        if p_cells_populated and p_cells_missing:
            p_cell_status = (
                "P-containing cell coverage is partial; current outputs must not "
                "be described as full 2³ factorial completion."
            )
        elif p_cells_missing:
            p_cell_status = P_CELL_DEFERRAL_STATEMENT
        else:
            p_cell_status = (
                "P-containing cells are populated, but canonical non-P cell "
                "coverage is partial."
            )
        statements = [
            FULL_FACTORIAL_GOAL_STATEMENT,
            p_cell_status,
        ]
    return {
        "analysis_label": analysis_label,
        "scope_kind": scope_kind,
        "scope_statements": statements,
        "full_factorial_goal": FULL_FACTORIAL_GOAL_STATEMENT,
        "p_cell_status": p_cell_status,
        "current_status_scope": CURRENT_STATUS_SCOPE_STATEMENT,
    }


def _secondary_compile_summary_diagnostic(
    df: pd.DataFrame,
    *,
    response_variable: str,
) -> dict[str, Any]:
    if response_variable != PRIMARY_RESPONSE_VARIABLE:
        return {
            "response_variable": SECONDARY_RESPONSE_VARIABLE,
            "status": "not_applicable",
            "missing_rows": 0,
            "total_rows": int(len(df)),
        }
    if SECONDARY_RESPONSE_VARIABLE not in df.columns:
        return {
            "response_variable": SECONDARY_RESPONSE_VARIABLE,
            "status": "not_available",
            "missing_rows": int(len(df)),
            "total_rows": int(len(df)),
        }
    missing_rows = int(df[SECONDARY_RESPONSE_VARIABLE].isna().sum())
    if missing_rows:
        return {
            "response_variable": SECONDARY_RESPONSE_VARIABLE,
            "status": "not_emitted_partial_missing",
            "missing_rows": missing_rows,
            "total_rows": int(len(df)),
        }
    return {
        "response_variable": SECONDARY_RESPONSE_VARIABLE,
        "status": "emitted",
        "missing_rows": 0,
        "total_rows": int(len(df)),
    }


def _mode_collapse_mask(df: pd.DataFrame) -> pd.Series:
    grammar_variant = _series_or_default(df, "grammar_variant", None)
    unique_ratio_ast = pd.to_numeric(
        _series_or_default(df, "unique_ratio_ast", 1.0),
        errors="coerce",
    ).fillna(1.0)
    return (grammar_variant == "template_upper_bound") & (unique_ratio_ast < 0.1)


def _series_or_default(
    df: pd.DataFrame,
    column: str,
    default: object,
) -> pd.Series:
    if column in df.columns:
        return df[column]
    return pd.Series([default] * len(df), index=df.index)


def _paper_tables(result: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    model = result["factorial_model"]
    return {
        "table_1_cell_summaries": list(result["cell_summaries"]),
        "table_2_paired_comparisons": list(result["paired_comparisons"]),
        "table_3_factorial_terms": _factorial_table_rows(model),
    }


def _factorial_table_rows(model: Mapping[str, Any]) -> list[dict[str, Any]]:
    model_fields = {
        "response_variable": model.get("response_variable"),
        "model_type": model.get("model_type"),
        "model_family": model.get("model_family"),
        "model_fit_status": model.get("model_fit_status"),
        "model_warnings": list(model.get("warnings", [])),
    }
    terms = list(model.get("terms", []))
    if not terms:
        return [
            {
                **model_fields,
                "term": None,
                "coefficient": None,
                "direction": "unavailable",
            }
        ]
    return [
        {
            **model_fields,
            **dict(term),
        }
        for term in terms
    ]


def _metric_name(response_variable: str) -> str:
    if response_variable == PRIMARY_RESPONSE_VARIABLE:
        return "level2_functional_success_rate"
    if response_variable == SECONDARY_RESPONSE_VARIABLE:
        return "level1_compile_success_rate"
    return response_variable


def _analysis_role(response_variable: str) -> str:
    if response_variable == PRIMARY_RESPONSE_VARIABLE:
        return "primary"
    return "secondary_diagnostic"


def _paired_bootstrap_ci(
    treatment_values: Sequence[bool],
    control_values: Sequence[bool],
    *,
    samples: int,
    seed: int,
) -> tuple[float, float]:
    if len(treatment_values) != len(control_values):
        raise ValueError("paired bootstrap requires matched treatment/control lengths")
    n_pairs = len(treatment_values)
    if n_pairs == 0:
        raise ValueError("paired bootstrap requires at least one pair")
    differences = [
        float(treatment) - float(control)
        for treatment, control in zip(treatment_values, control_values, strict=True)
    ]
    rng = random.Random(seed)
    bootstrap_values = []
    for _ in range(samples):
        total = 0.0
        for _ in range(n_pairs):
            total += rng.choice(differences)
        bootstrap_values.append(total / n_pairs)
    bootstrap_values.sort()
    alpha = 1.0 - CI_LEVEL
    return (
        _percentile(bootstrap_values, alpha / 2.0),
        _percentile(bootstrap_values, 1.0 - alpha / 2.0),
    )


def _percentile(sorted_values: Sequence[float], percentile: float) -> float:
    if not sorted_values:
        raise ValueError("percentile requires at least one value")
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def _mcnemar_exact_p_value(treatment_only: int, control_only: int) -> float:
    discordant = treatment_only + control_only
    if discordant == 0:
        return 1.0
    smaller = min(treatment_only, control_only)
    cumulative = sum(
        math.comb(discordant, index) * (0.5**discordant)
        for index in range(smaller + 1)
    )
    return min(1.0, 2.0 * cumulative)


def _holm_adjust(p_values: Sequence[float]) -> list[float]:
    indexed = sorted(enumerate(p_values), key=lambda item: item[1])
    adjusted = [1.0] * len(p_values)
    running_max = 0.0
    total = len(p_values)
    for rank, (index, p_value) in enumerate(indexed):
        value = min(1.0, (total - rank) * p_value)
        running_max = max(running_max, value)
        adjusted[index] = running_max
    return adjusted


def _direction(value: float | None) -> str:
    if value is None:
        return "unavailable"
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "zero"


def _require_columns(df: pd.DataFrame, columns: Sequence[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")


def _ensure_pair_identity_columns(df: pd.DataFrame) -> pd.DataFrame:
    if "kernel_name" not in df.columns:
        return df
    normalized = df.copy()
    if "kernel_id" not in normalized.columns:
        normalized["kernel_id"] = normalized["kernel_name"]
    else:
        missing_kernel_id = normalized["kernel_id"].map(_is_missing_value)
        if missing_kernel_id.any():
            normalized.loc[missing_kernel_id, "kernel_id"] = normalized.loc[
                missing_kernel_id,
                "kernel_name",
            ]
    return normalized


def _require_non_missing_pair_keys(
    df: pd.DataFrame,
    *,
    pair_key_columns: Sequence[str] = PAIR_KEY_COLUMNS,
) -> None:
    missing = [
        column
        for column in pair_key_columns
        if df[column].map(_is_missing_value).any()
    ]
    if missing:
        raise ValueError(
            "missing required paired identity fields: " + ", ".join(missing)
        )


def _unique_pair_keys(
    df: pd.DataFrame,
    *,
    allow_repeated_attempts: bool,
    pair_key_columns: Sequence[str] = PAIR_KEY_COLUMNS,
) -> set[tuple[object, ...]]:
    key_cols = list(pair_key_columns)
    if not allow_repeated_attempts and df.duplicated(key_cols).any():
        raise ValueError("duplicate replay pair in dataframe")
    if allow_repeated_attempts and "attempt_index" in df.columns:
        if df.duplicated([*key_cols, "attempt_index"]).any():
            raise ValueError("duplicate generated pair attempt in dataframe")
    return {
        _canonical_pair_key_tuple(row)
        for row in df[key_cols].itertuples(index=False, name=None)
    }


def _filter_pair_keys(
    df: pd.DataFrame,
    keys: set[tuple[object, ...]],
    *,
    pair_key_columns: Sequence[str] = PAIR_KEY_COLUMNS,
) -> pd.DataFrame:
    if not keys:
        return df.iloc[0:0]
    mask = df.apply(
        lambda row: _pair_key_from_row(row, pair_key_columns=pair_key_columns) in keys,
        axis=1,
    )
    return df[mask]


def _require_replay_attempt_zero(control: pd.DataFrame) -> None:
    nonzero = control[control["attempt_index"] != 0]
    if not nonzero.empty:
        raise ValueError("paired replay control rows must use attempt_index 0")


def _require_generated_attempt_zero(treatment: pd.DataFrame) -> None:
    missing = []
    for key, group in treatment.groupby(list(PAIR_KEY_COLUMNS), sort=True):
        if 0 not in set(group["attempt_index"]) and not _group_has_repair_attempt(
            group,
            attempt_index=0,
        ):
            missing.append(key)
    if missing:
        raise ValueError(
            "paired replay treatment rows must include attempt_index 0: "
            f"{missing}"
        )


def _group_has_repair_attempt(group: pd.DataFrame, *, attempt_index: int) -> bool:
    for _, row in group.iterrows():
        for column in ("repair_trace", "repair_traces", "trace_summary"):
            if column in row and attempt_index in _trace_attempt_indexes(row[column]):
                return True
    return False


def _trace_attempt_indexes(value: object) -> set[int]:
    if _is_missing_value(value):
        return set()
    if isinstance(value, Mapping):
        raw_index = value.get("attempt_index")
        if _is_missing_value(raw_index):
            return set()
        return {int(raw_index)}
    if isinstance(value, (list, tuple, set)):
        indexes: set[int] = set()
        for item in value:
            indexes.update(_trace_attempt_indexes(item))
        return indexes
    if hasattr(value, "to_dict"):
        return _trace_attempt_indexes(value.to_dict())
    if is_dataclass(value):
        return _trace_attempt_indexes(asdict(value))
    return set()


def _validate_pair_metadata_columns(
    treatment: pd.DataFrame,
    control: pd.DataFrame,
    *,
    expected_control_condition: str,
) -> None:
    required_metadata_columns = (
        "replay_pair_id",
        "replay_base_seed",
        "replay_generation_seed",
        "prompt_sha256",
        "model_id",
        "temperature",
        "max_new_tokens",
    )
    paired_identity_columns = tuple(
        column for column in required_metadata_columns if column != "max_new_tokens"
    )
    revision_columns = ("model_revision", "tokenizer_revision")
    treatment_meta = _pair_metadata_frame(
        treatment,
        metadata_column="generated_metadata",
        required_metadata_fields=required_metadata_columns,
        optional_metadata_fields=revision_columns,
    )
    _validate_seed_metadata_matches_pair_key(treatment_meta)
    _validate_generated_seed_metadata(
        treatment,
        expected_control_condition=expected_control_condition,
    )
    if _control_has_replay_metadata(
        control,
        metadata_fields=(
            "replay_pair_id",
            "replay_base_seed",
            "replay_generation_seed",
        ),
    ):
        control_meta = _pair_metadata_frame(
            control,
            metadata_column="replay_metadata",
            required_metadata_fields=required_metadata_columns,
            optional_metadata_fields=revision_columns,
        )
        if not treatment_meta[list(paired_identity_columns)].equals(
            control_meta[list(paired_identity_columns)]
        ):
            raise ValueError("metadata mismatch in paired replay dataframe")
        _validate_seed_metadata_matches_pair_key(control_meta)
        _validate_known_revision_metadata(treatment_meta, control_meta)
        return

    _validate_cluster1_raw_control_identity(control)
    _validate_prompt_parity(pd.concat([treatment, control], ignore_index=True))


def _control_has_replay_metadata(
    control: pd.DataFrame,
    *,
    metadata_fields: Sequence[str],
) -> bool:
    if control.empty:
        return False
    for _, row in control.iterrows():
        nested = row.get("replay_metadata")
        if isinstance(nested, Mapping):
            return True
        if any(not _is_missing_value(row.get(field)) for field in metadata_fields):
            return True
    return False


def _validate_cluster1_raw_control_identity(control: pd.DataFrame) -> None:
    missing: set[str] = set()
    for _, row in control.iterrows():
        for column in ("kernel_class", "kernel_name", "dtype"):
            if _is_missing_value(row.get(column)):
                missing.add(column)
        if _is_missing_value(row.get("base_seed")) and _is_missing_value(
            row.get("generation_seed")
        ):
            missing.add("generation_seed_or_base_seed")
        if not _is_missing_value(
            _metadata_value(row, row.get("generated_metadata"), "replay_pair_id")
        ):
            raise ValueError("Cluster 1 raw controls must not contain replay_pair_id")
    if missing:
        raise ValueError(
            "missing required Cluster 1 raw paired identity fields: "
            + ", ".join(sorted(missing))
        )


def _pair_metadata_frame(
    df: pd.DataFrame,
    *,
    metadata_column: str,
    required_metadata_fields: tuple[str, ...],
    optional_metadata_fields: tuple[str, ...] = (),
) -> pd.DataFrame:
    rows = []
    metadata_fields = (*required_metadata_fields, *optional_metadata_fields)
    for _, row in df.iterrows():
        record = {column: row[column] for column in PAIR_KEY_COLUMNS}
        nested = row.get(metadata_column)
        for field in required_metadata_fields:
            value = _metadata_value(row, nested, field)
            if _is_missing_value(value):
                raise ValueError(f"missing paired replay metadata: {field}")
            record[field] = value
        for field in optional_metadata_fields:
            value = _metadata_value(row, nested, field)
            record[field] = None if _is_missing_value(value) else value
        rows.append(record)

    metadata = pd.DataFrame(rows)
    if metadata.duplicated(list(PAIR_KEY_COLUMNS) + list(metadata_fields)).any():
        metadata = metadata.drop_duplicates(list(PAIR_KEY_COLUMNS) + list(metadata_fields))
    if metadata.duplicated(list(PAIR_KEY_COLUMNS)).any():
        raise ValueError("metadata mismatch within paired replay dataframe")
    return metadata.set_index(list(PAIR_KEY_COLUMNS)).sort_index()


def _validate_seed_metadata_matches_pair_key(metadata: pd.DataFrame) -> None:
    base_seed_position = list(PAIR_KEY_COLUMNS).index("base_seed")
    for key, row in metadata.iterrows():
        base_seed = key[base_seed_position] if isinstance(key, tuple) else key
        if row["replay_base_seed"] != base_seed:
            raise ValueError("metadata mismatch in paired replay dataframe")
        if row["replay_generation_seed"] != base_seed:
            raise ValueError("metadata mismatch in paired replay dataframe")


def _validate_generated_seed_metadata(
    treatment: pd.DataFrame,
    *,
    expected_control_condition: str,
) -> None:
    for _, row in treatment.iterrows():
        nested = row.get("generated_metadata")
        replay_control_condition = _metadata_value(
            row,
            nested,
            "replay_control_condition",
        )
        if _is_missing_value(replay_control_condition):
            raise ValueError(
                "missing paired replay metadata: replay_control_condition"
            )
        if replay_control_condition != expected_control_condition:
            raise ValueError("metadata mismatch in paired replay dataframe")

        if row["attempt_index"] != 0:
            continue
        generation_seed = _metadata_value(row, nested, "generation_seed")
        if _is_missing_value(generation_seed):
            raise ValueError("missing paired replay metadata: generation_seed")
        replay_generation_seed = _metadata_value(row, nested, "replay_generation_seed")
        if generation_seed != replay_generation_seed:
            raise ValueError("metadata mismatch in paired replay dataframe")


def _validate_known_revision_metadata(
    treatment: pd.DataFrame,
    control: pd.DataFrame,
) -> None:
    for field in ("model_revision", "tokenizer_revision"):
        known_control = control[field].map(_known_frozen_revision)
        if known_control.any():
            if not treatment.loc[known_control, field].equals(control.loc[known_control, field]):
                raise ValueError("metadata mismatch in paired replay dataframe")


def _known_frozen_revision(value: object) -> bool:
    return (
        value is not None
        and not _is_missing_value(value)
        and value != UNAVAILABLE_FROZEN_REVISION
    )


def _validate_prompt_parity(df: pd.DataFrame) -> None:
    if df.empty:
        return
    _require_columns(df, ("condition", "kernel_class", "dtype"))
    for (kernel_class, dtype), group in df.groupby(
        ["kernel_class", "dtype"],
        sort=True,
        dropna=False,
    ):
        condition_hashes: dict[str, str] = {}
        for condition, condition_group in group.groupby("condition", sort=True):
            hashes = {
                _prompt_sha256_for_row(row)
                for _, row in condition_group.iterrows()
            }
            if len(hashes) != 1:
                raise ValueError(
                    "prompt parity mismatch within condition "
                    f"{condition!r} for kernel_class={kernel_class!r}, dtype={dtype!r}: "
                    f"{sorted(hashes)}"
                )
            condition_hashes[str(condition)] = next(iter(hashes))
        unique_hashes = set(condition_hashes.values())
        if len(unique_hashes) > 1:
            raise ValueError(
                "prompt parity mismatch across conditions for "
                f"kernel_class={kernel_class!r}, dtype={dtype!r}: {condition_hashes}"
            )


def _prompt_sha256_for_row(row: pd.Series) -> str:
    for metadata_column in ("generated_metadata", "replay_metadata"):
        nested = row.get(metadata_column)
        value = _metadata_value(row, nested, "prompt_sha256")
        if not _is_missing_value(value):
            return str(value)
    return _expected_prompt_sha256(str(row["kernel_class"]), str(row["dtype"]))


def _expected_prompt_sha256(kernel_class: str, dtype: str) -> str:
    from cluster1.data.kernels import KERNEL_SPECS
    from cluster1.data.prompts.prompt_contract import build_prompt

    try:
        spec = KERNEL_SPECS[kernel_class]
    except KeyError as exc:
        raise ValueError(f"unknown kernel_class for prompt parity: {kernel_class!r}") from exc
    prompt = build_prompt(spec, dtype)
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def _metadata_value(
    row: pd.Series,
    nested: object,
    field: str,
) -> object:
    aliases = {
        "prompt_sha256": ("prompt_sha256", "prompt_hash"),
        "prompt_hash": ("prompt_hash", "prompt_sha256"),
    }
    for candidate in aliases.get(field, (field,)):
        value = row.get(candidate)
        if not _is_missing_value(value):
            return value
        if isinstance(nested, Mapping):
            value = nested.get(candidate)
            if not _is_missing_value(value):
                return value
    return None


def _metadata_first_present(
    payload: Mapping[str, Any],
    generated_metadata: Mapping[str, Any] | None,
    replay_metadata: Mapping[str, Any] | None,
    *fields: str,
    default: Any = None,
) -> Any:
    for field in fields:
        value = payload.get(field)
        if not _is_missing_value(value):
            return value
        for nested in (generated_metadata, replay_metadata):
            if nested is None:
                continue
            value = nested.get(field)
            if not _is_missing_value(value):
                return value
    return default


def _first_present(
    payload: Mapping[str, Any],
    *fields: str,
    nested: Mapping[str, Any] | None = None,
    default: Any = None,
) -> Any:
    for field in fields:
        value = payload.get(field)
        if not _is_missing_value(value):
            return value
        if nested is not None:
            value = nested.get(field)
            if not _is_missing_value(value):
                return value
    return default


def _bool_or_none(value: object) -> bool | None:
    if _is_missing_value(value):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, np.integer)) and value in {0, 1}:
        return bool(value)
    raise ValueError(f"expected boolean metric value, got {value!r}")


def _int_or_none(value: object) -> int | None:
    if _is_missing_value(value):
        return None
    return int(value)


def _float_or_none(value: object) -> float | None:
    if _is_missing_value(value):
        return None
    return float(value)


def _is_missing_value(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, (dict, list, tuple, set)):
        return False
    return bool(pd.isna(value))


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    return value


if __name__ == "__main__":
    raise SystemExit(main())
