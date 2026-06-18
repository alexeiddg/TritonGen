"""Deterministic best-anchor ranking for repair-history prompts."""

from __future__ import annotations

from collections.abc import Sequence

from shared.repair_history.evidence import (
    F0_FAILURE_CODES,
    F1_FAILURE_CODES,
    F2_FAILURE_CODES,
    LoopKind,
    RepairAttemptEvidence,
    validate_attempt_history,
)


def select_best_anchor(
    attempts: Sequence[RepairAttemptEvidence],
    *,
    loop_kind: LoopKind,
) -> RepairAttemptEvidence:
    """Select the deterministic best previous source anchor."""

    ordered = validate_attempt_history(attempts, loop_kind=loop_kind)
    return max(ordered, key=lambda attempt: _score_attempt(attempt, loop_kind))


def ranked_attempts(
    attempts: Sequence[RepairAttemptEvidence],
    *,
    loop_kind: LoopKind,
) -> tuple[RepairAttemptEvidence, ...]:
    """Return attempts from best to worst without deduplicating source hashes."""

    ordered = validate_attempt_history(attempts, loop_kind=loop_kind)
    return tuple(
        sorted(
            ordered,
            key=lambda attempt: _score_attempt(attempt, loop_kind),
            reverse=True,
        )
    )


def _score_attempt(attempt: RepairAttemptEvidence, loop_kind: LoopKind) -> tuple[object, ...]:
    if attempt.functional_success is True:
        category = 6
    elif attempt.failure_code in F2_FAILURE_CODES and _has_c_public_counts(attempt):
        category = 5
    elif attempt.failure_code in F2_FAILURE_CODES:
        category = 4
    elif attempt.failure_code == "F1_COMPILE":
        category = 3
    elif attempt.failure_code in F1_FAILURE_CODES:
        category = 2
    elif attempt.failure_code in F0_FAILURE_CODES:
        category = 1
    else:
        category = 0

    if loop_kind == "C":
        return (category, *_c_tie_breaks(attempt), attempt.attempt_index)
    return (category, *_p_tie_breaks(attempt), attempt.attempt_index)


def _c_tie_breaks(attempt: RepairAttemptEvidence) -> tuple[object, ...]:
    max_abs = float("inf") if attempt.max_abs_diff is None else attempt.max_abs_diff
    max_rel = float("inf") if attempt.max_rel_diff is None else attempt.max_rel_diff
    return (
        _count_or_missing(attempt.repair_shapes_passed),
        _count_or_missing(attempt.public_eval_shapes_passed),
        -max_abs,
        -max_rel,
        attempt.nan_or_inf_observed is False,
        attempt.shape_mismatch_observed is False,
    )


def _p_tie_breaks(attempt: RepairAttemptEvidence) -> tuple[object, ...]:
    return (
        attempt.compile_success is True,
        (attempt.level_reached or -1) >= 2
        or (attempt.post_compile_level_reached or -1) >= 2,
        attempt.compile_error_changed_from_previous is True,
        bool(attempt.compile_error_type or attempt.compile_error_excerpt_sha256),
    )


def _count_or_missing(value: int | None) -> int:
    return -1 if value is None else value


def _has_c_public_counts(attempt: RepairAttemptEvidence) -> bool:
    return attempt.repair_shapes_passed is not None or attempt.public_eval_shapes_passed is not None
