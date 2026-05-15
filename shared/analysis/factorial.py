"""
2^3 Factorial analysis across all three clusters.

The experiment is a 2³ full-factorial design:
  G (Grammar constraint)   - Cluster 1
  C (Test-driven feedback) - Cluster 2
  P (Compiler/profiler)    - Cluster 3

This module combines per-cluster JSONL result files and computes:
  - Main effects: G, C, P on pass@k
  - Two-way interactions: G*C, G*P, C*P
  - Three-way interaction: G*C*P (additive vs interference)

Results feed directly into the thesis's interaction-effect hypothesis.
Callers should filter to a single scale_tier, normally paper, before computing
reportable summaries. Mixed-scale summaries are diagnostics only.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


FACTORS = ("grammar_active", "compiler_feedback_active", "perf_feedback_active")
PAIRED_REPLAY_COMPARISONS = {"C": "none", "G+C": "G"}
PAIR_KEY_COLUMNS = ("kernel_class", "dtype", "base_seed")
UNAVAILABLE_FROZEN_REVISION = "unavailable_in_frozen_cluster1_artifact"


def load_results(jsonl_path: Path) -> pd.DataFrame:
    rows = [json.loads(line) for line in jsonl_path.read_text().splitlines() if line.strip()]
    return pd.DataFrame(rows)


def merge_cluster_results(
    cluster1_path: Path | None = None,
    cluster2_path: Path | None = None,
    cluster3_path: Path | None = None,
) -> pd.DataFrame:
    """Merge JSONL result files from all clusters into one DataFrame.

    Missing cluster paths produce columns filled with False/NaN so partial
    analyses work before all clusters are complete.
    """
    frames = []
    for path, has_c, has_p in [
        (cluster1_path, False, False),
        (cluster2_path, True, False),
        (cluster3_path, True, True),
    ]:
        if path is not None and path.exists():
            df = load_results(path)
            if "compiler_feedback_active" not in df.columns:
                df["compiler_feedback_active"] = has_c
            if "perf_feedback_active" not in df.columns:
                df["perf_feedback_active"] = has_p
            frames.append(df)
    if not frames:
        raise ValueError("No result files provided.")
    return pd.concat(frames, ignore_index=True)


def factorial_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Return compile-only pass@1 diagnostics by factor combination.

    This legacy summary is not the Cluster 2 paper-primary path. Cluster 2
    primary claims use paired replay summaries over ``functional_success``.
    """
    group_cols = [f for f in FACTORS if f in df.columns] + ["kernel_class", "dtype"]
    return (
        df.groupby(group_cols)["compile_success"]
        .agg(["sum", "count"])
        .rename(columns={"sum": "n_correct", "count": "n_total"})
        .assign(pass_at_1=lambda x: x["n_correct"] / x["n_total"])
        .reset_index()
    )


def validate_paired_replay_dataframe(
    df: pd.DataFrame,
    *,
    treatment_condition: str,
    control_condition: str | None = None,
) -> None:
    """Reject primary Cluster 2 comparisons that are not paired by seed."""

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
        ("condition", "functional_success", "attempt_index", *PAIR_KEY_COLUMNS),
    )
    treatment = df[df["condition"] == treatment_condition]
    control = df[df["condition"] == resolved_control]
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
) -> pd.DataFrame:
    """Return paired binary outcomes for a generated-vs-replay comparison."""

    expected_control = PAIRED_REPLAY_COMPARISONS[treatment_condition]
    resolved_control = expected_control if control_condition is None else control_condition
    validate_paired_replay_dataframe(
        df,
        treatment_condition=treatment_condition,
        control_condition=resolved_control,
    )
    treatment = (
        df[df["condition"] == treatment_condition]
        .groupby(list(PAIR_KEY_COLUMNS))["functional_success"]
        .any()
        .rename("treatment_success")
    )
    control = (
        df[df["condition"] == resolved_control]
        .groupby(list(PAIR_KEY_COLUMNS))["functional_success"]
        .any()
        .rename("control_success")
    )
    paired = pd.concat([treatment, control], axis=1).reset_index()
    paired["paired_lift"] = paired["treatment_success"].astype(int) - paired[
        "control_success"
    ].astype(int)
    paired["treatment_condition"] = treatment_condition
    paired["control_condition"] = resolved_control
    return paired


def _require_columns(df: pd.DataFrame, columns: tuple[str, ...]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")


def _unique_pair_keys(
    df: pd.DataFrame,
    *,
    allow_repeated_attempts: bool,
) -> set[tuple[object, ...]]:
    key_cols = list(PAIR_KEY_COLUMNS)
    if not allow_repeated_attempts and df.duplicated(key_cols).any():
        raise ValueError("duplicate replay pair in dataframe")
    if allow_repeated_attempts and "attempt_index" in df.columns:
        if df.duplicated([*key_cols, "attempt_index"]).any():
            raise ValueError("duplicate generated pair attempt in dataframe")
    return set(df[key_cols].itertuples(index=False, name=None))


def _require_replay_attempt_zero(control: pd.DataFrame) -> None:
    nonzero = control[control["attempt_index"] != 0]
    if not nonzero.empty:
        raise ValueError("paired replay control rows must use attempt_index 0")


def _require_generated_attempt_zero(treatment: pd.DataFrame) -> None:
    missing = []
    for key, group in treatment.groupby(list(PAIR_KEY_COLUMNS), sort=True):
        if 0 not in set(group["attempt_index"]):
            missing.append(key)
    if missing:
        raise ValueError(
            "paired replay treatment rows must include attempt_index 0: "
            f"{missing}"
        )


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
    revision_columns = ("model_revision", "tokenizer_revision")
    treatment_meta = _pair_metadata_frame(
        treatment,
        metadata_column="generated_metadata",
        required_metadata_fields=required_metadata_columns,
        optional_metadata_fields=revision_columns,
    )
    control_meta = _pair_metadata_frame(
        control,
        metadata_column="replay_metadata",
        required_metadata_fields=required_metadata_columns,
        optional_metadata_fields=revision_columns,
    )
    if not treatment_meta[list(required_metadata_columns)].equals(
        control_meta[list(required_metadata_columns)]
    ):
        raise ValueError("metadata mismatch in paired replay dataframe")
    _validate_seed_metadata_matches_pair_key(treatment_meta)
    _validate_seed_metadata_matches_pair_key(control_meta)
    _validate_generated_seed_metadata(
        treatment,
        expected_control_condition=expected_control_condition,
    )
    _validate_known_revision_metadata(treatment_meta, control_meta)


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
    for key, row in metadata.iterrows():
        base_seed = key[2] if isinstance(key, tuple) else key
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


def _metadata_value(
    row: pd.Series,
    nested: object,
    field: str,
) -> object:
    value = row.get(field)
    if _is_missing_value(value) and isinstance(nested, dict):
        value = nested.get(field)
    return value


def _is_missing_value(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, (dict, list, tuple, set)):
        return False
    return bool(pd.isna(value))
