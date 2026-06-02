"""Tests for deterministic best-anchor ranking."""

from __future__ import annotations

from shared.repair_history.evidence import RepairAttemptEvidence, sha256_text
from shared.repair_history.ranking import ranked_attempts, select_best_anchor


PROMPT_HASH = "b" * 64


def test_c_ranking_picks_earlier_better_f2_over_later_regression() -> None:
    attempts = (
        _c_attempt(0, repair_shapes_passed=4, max_abs_diff=0.01),
        _c_attempt(1, repair_shapes_passed=2, max_abs_diff=0.2),
        _c_attempt(2, repair_shapes_passed=0, max_abs_diff=3.0),
    )

    anchor = select_best_anchor(attempts, loop_kind="C")

    assert anchor.attempt_index == 0


def test_c_ranking_uses_later_attempt_only_after_evidence_ties() -> None:
    attempts = (
        _c_attempt(0, repair_shapes_passed=2, max_abs_diff=0.1),
        _c_attempt(1, repair_shapes_passed=2, max_abs_diff=0.1),
    )

    assert select_best_anchor(attempts, loop_kind="C").attempt_index == 1


def test_c_ranking_ignores_private_terminal_eval_signal() -> None:
    attempts = (
        _c_attempt(0, eval_set_success=True),
        _c_attempt(1, eval_set_success=False),
    )

    assert select_best_anchor(attempts, loop_kind="C").attempt_index == 1


def test_repeated_source_hashes_are_not_deduplicated_before_ranking() -> None:
    shared_hash = sha256_text("same source\n")
    attempts = (
        _c_attempt(0, source_hash=shared_hash, repair_shapes_passed=1),
        _c_attempt(1, source_hash=shared_hash, repair_shapes_passed=2),
        _c_attempt(2, repair_shapes_passed=0),
    )

    ranked = ranked_attempts(attempts, loop_kind="C")

    assert [attempt.attempt_index for attempt in ranked] == [1, 0, 2]
    assert ranked[0].source_hash == ranked[1].source_hash


def test_p_compile_success_evidence_beats_repeated_f1_compile() -> None:
    attempts = (
        _p_f1_attempt(0, "CompilationError", changed=False),
        _p_f1_attempt(1, "CompilationError", changed=False),
        _c_attempt(
            2,
            failure_code="F2_NUMERIC_LARGE",
            compile_success=True,
            level_reached=2,
            repair_shapes_passed=1,
        ),
    )

    assert select_best_anchor(attempts, loop_kind="P").attempt_index == 2


def test_p_ranking_prefers_changed_compile_error_type_after_evidence_ties() -> None:
    attempts = (
        _p_f1_attempt(0, "CompilationError", changed=False),
        _p_f1_attempt(1, "TritonCompilationError", changed=True),
    )

    assert select_best_anchor(attempts, loop_kind="P").attempt_index == 1


def _c_attempt(
    attempt_index: int,
    *,
    failure_code: str = "F2_NUMERIC_LARGE",
    source_hash: str | None = None,
    repair_shapes_passed: int = 2,
    max_abs_diff: float = 0.1,
    compile_success: bool | None = True,
    level_reached: int | None = 2,
    eval_set_success: bool | None = None,
) -> RepairAttemptEvidence:
    return RepairAttemptEvidence(
        attempt_index=attempt_index,
        generation_seed=100 + attempt_index,
        failure_code=failure_code,
        level_reached=level_reached,
        compile_success=compile_success,
        functional_success=False,
        repair_set_success=False,
        eval_set_success=eval_set_success,
        public_failure_summary=f"Attempt {attempt_index} public F2 failure.",
        source_hash=source_hash or sha256_text(f"source {attempt_index}\n"),
        prompt_hash=PROMPT_HASH,
        repair_shapes_passed=repair_shapes_passed,
        num_repair_shapes=4,
        max_abs_diff=max_abs_diff,
        max_rel_diff=max_abs_diff,
        nan_or_inf_observed=False,
        shape_mismatch_observed=False,
    )


def _p_f1_attempt(
    attempt_index: int,
    compile_error_type: str,
    *,
    changed: bool,
) -> RepairAttemptEvidence:
    return RepairAttemptEvidence(
        attempt_index=attempt_index,
        generation_seed=200 + attempt_index,
        failure_code="F1_COMPILE",
        level_reached=1,
        compile_success=False,
        functional_success=False,
        repair_set_success=None,
        eval_set_success=None,
        public_failure_summary="Compilation failed before validation.",
        source_hash=sha256_text(f"p source {attempt_index}\n"),
        prompt_hash=PROMPT_HASH,
        compile_error_type=compile_error_type,
        compile_error_excerpt_sha256=sha256_text(f"error {attempt_index}"),
        compile_error_changed_from_previous=changed,
    )
