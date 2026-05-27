from __future__ import annotations

import hashlib
import json
from dataclasses import fields

import pytest

from cluster2.constants import GENERATED_SOURCE_CLASS
from cluster2.feedback.trace import TraceSummary
from cluster3.constants import (
    DEFAULT_P_REPAIR_BUDGET,
    P_FEEDBACK_FORMAT_V1,
    P_HISTORY_POLICY_V1,
    generation_mode_for_cluster3_condition,
)
from cluster3.feedback.trace import Cluster3TraceSummary, PRepairAttemptSummary
from cluster3.results.dataclass import (
    CLUSTER3_RESULTS_SCHEMA_VERSION,
    Cluster3ContentHashSidecar,
    Cluster3EvalRow,
    Cluster3GeneratedRowMetadata,
    Cluster3ReplayRowMetadata,
    generated_row,
)


HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64
HASH_D = "d" * 64
HASH_E = "e" * 64
INITIAL_PROMPT_HASH = "1" * 64
P_PROMPT_HASH = "2" * 64
C_PROMPT = "repair prompt for C"
C_PROMPT_HASH = hashlib.sha256(C_PROMPT.encode("utf-8")).hexdigest()
GEN_HASHES = {"cluster3/results/dataclass.py": HASH_D}


def _generated_metadata(
    *,
    condition: str = "P",
    generation_seed: int = 110,
    terminal_source_stage: str = "initial",
    terminal_attempt_index: int | None = 0,
    terminal_source_hash: str = HASH_A,
    terminal_prompt_hash: str | None = INITIAL_PROMPT_HASH,
    terminal_prompt_hash_source: str = "initial_prompt",
    p_repair_attempted: bool = False,
    p_compile_repair_succeeded: bool = False,
    p_repair_attempt_count: int = 0,
    c_loop_fired: bool = False,
    c_loop_source: str = "none",
) -> Cluster3GeneratedRowMetadata:
    grammar_fields = {}
    if condition in {"G+P", "G+C+P"}:
        grammar_fields = {
            "grammar_variant": "task_agnostic",
            "grammar_path": "cluster1/grammar/triton_kernel_agnostic.gbnf",
            "grammar_claim_scope": "primary",
        }
    return Cluster3GeneratedRowMetadata(
        c3_generation_hashes=GEN_HASHES,
        generation_seed=generation_seed,
        terminal_source_stage=terminal_source_stage,  # type: ignore[arg-type]
        terminal_attempt_index=terminal_attempt_index,
        terminal_source_hash=terminal_source_hash,
        terminal_prompt_hash=terminal_prompt_hash,
        terminal_prompt_hash_source=terminal_prompt_hash_source,  # type: ignore[arg-type]
        p_repair_attempted=p_repair_attempted,
        p_compile_repair_succeeded=p_compile_repair_succeeded,
        p_repair_attempt_count=p_repair_attempt_count,
        c_loop_fired=c_loop_fired,
        c_loop_source=c_loop_source,  # type: ignore[arg-type]
        **grammar_fields,
    )


def _p_attempt(
    *,
    attempt_index: int,
    failure_code: str | None,
    generation_seed: int,
    source_hash: str = HASH_A,
) -> PRepairAttemptSummary:
    return PRepairAttemptSummary(
        attempt_index=attempt_index,
        generation_seed=generation_seed,
        compile_success=True
        if failure_code is None
        else not failure_code.startswith(("F0_", "F1_")),
        failure_code=failure_code,
        compile_error_class="CompilationError" if failure_code == "F1_COMPILE" else None,
        source_hash=source_hash,
        feedback_sha256=HASH_E if attempt_index > 0 else None,
    )


def _p_trace(
    *,
    attempt_count: int,
    terminal_failure_code: str | None,
    terminal_source_hash: str = HASH_B,
    terminal_generation_seed: int = 111,
) -> tuple[PRepairAttemptSummary, ...]:
    attempts = [
        _p_attempt(
            attempt_index=0,
            failure_code="F1_COMPILE",
            generation_seed=110,
            source_hash=HASH_A,
        )
    ]
    for index in range(1, attempt_count + 1):
        attempts.append(
            _p_attempt(
                attempt_index=index,
                failure_code=terminal_failure_code if index == attempt_count else "F1_COMPILE",
                generation_seed=terminal_generation_seed + index - attempt_count,
                source_hash=terminal_source_hash if index == attempt_count else HASH_A,
            )
        )
    return tuple(attempts)


def _c_trace(
    *,
    attempt_index: int = 1,
    failure_code: str | None = None,
    source_hash: str = HASH_C,
    functional_success: bool = True,
    repair_set_success: bool = True,
    eval_set_success: bool = True,
) -> TraceSummary:
    return TraceSummary(
        attempt_index=attempt_index,
        failure_code=failure_code,
        public_failure_summary="Candidate passed Level 2."
        if functional_success
        else "Validation failed.",
        functional_success=functional_success,
        repair_set_success=repair_set_success,
        eval_set_success=eval_set_success,
        source_hash=source_hash,
    )


def _failure_path(values: dict[str, object], c_attempt_count: int) -> list[str]:
    path = [f"initial:{values['initial_failure_code'] or 'success'}"]
    if values["p_repair_attempted"]:
        count = int(values["p_repair_attempt_count"])
        for index in range(1, count + 1):
            code = values["p_terminal_failure_code"] if index == count else "F1_COMPILE"
            path.append(f"p_attempt:{index}:{code or 'success'}")
    if values["c_loop_fired"]:
        seed_code = (
            values["p_terminal_failure_code"]
            if values["c_loop_source"] == "post_p_f2"
            else values["initial_failure_code"]
        )
        path.append(f"c_seed:{seed_code or 'success'}")
        for index in range(1, c_attempt_count + 1):
            code = values["c_terminal_failure_code"] if index == c_attempt_count else "F2_NUMERIC_LARGE"
            path.append(f"c_attempt:{index}:{code or 'success'}")
    return path


def _trace_summary(values: dict[str, object], c_attempt_count: int) -> Cluster3TraceSummary:
    return Cluster3TraceSummary(
        condition=str(values["condition"]),
        initial_failure_code=values["initial_failure_code"],  # type: ignore[arg-type]
        final_failure_code=values["failure_code"],  # type: ignore[arg-type]
        p_loop_fired=bool(values["p_repair_attempted"]),
        p_attempt_count=int(values["p_repair_attempt_count"]),
        p_terminal_failure_code=values["p_terminal_failure_code"],  # type: ignore[arg-type]
        p_compile_repair_succeeded=bool(values["p_compile_repair_succeeded"]),
        c_loop_fired=bool(values["c_loop_fired"]),
        c_loop_source=values["c_loop_source"],  # type: ignore[arg-type]
        c_attempt_count=c_attempt_count,
        c_terminal_failure_code=values["c_terminal_failure_code"],  # type: ignore[arg-type]
        terminal_source_stage=str(values["terminal_source_stage"]),
        terminal_attempt_index=values["terminal_attempt_index"],  # type: ignore[arg-type]
        terminal_source_hash=str(values["terminal_source_hash"]),
        terminal_generation_seed=int(values["terminal_generation_seed"]),
        terminal_prompt_hash=values["terminal_prompt_hash"],  # type: ignore[arg-type]
        terminal_prompt_hash_source=values["terminal_prompt_hash_source"],  # type: ignore[arg-type]
        compile_success=bool(values["compile_success"]),
        functional_success=bool(values["functional_success"]),
        repair_set_success=bool(values["repair_set_success"]),
        eval_set_success=bool(values["eval_set_success"]),
        row_source_hash=str(values["source_hash"]),
        failure_path=_failure_path(values, c_attempt_count),
        private_eval_data_included=False,
    )


def _row(**overrides: object) -> Cluster3EvalRow:
    values: dict[str, object] = {
        "condition": "P",
        "attempt_index": 0,
        "kernel_class": "elementwise",
        "kernel_name": "relu",
        "dtype": "fp32",
        "base_seed": 11,
        "source_hash": HASH_A,
        "grammar_active": False,
        "compile_success": True,
        "functional_success": True,
        "repair_set_success": True,
        "eval_set_success": True,
        "failure_code": None,
        "repair_trace": None,
        "initial_failure_code": None,
        "p_repair_attempted": False,
        "p_compile_repair_succeeded": False,
        "p_repair_changed_terminal_class": False,
        "p_repair_budget": DEFAULT_P_REPAIR_BUDGET,
        "p_repair_attempt_count": 0,
        "p_initial_failure_code": None,
        "p_terminal_failure_code": None,
        "c_loop_fired": False,
        "c_loop_source": "none",
        "c_terminal_failure_code": None,
        "c_terminal_level_reached": None,
        "p_compile_error_class": None,
        "p_raw_error_excerpt_sha256": None,
        "p_repair_stop_reason": "p_not_applicable",
        "p_feedback_format": P_FEEDBACK_FORMAT_V1,
        "p_history_policy": P_HISTORY_POLICY_V1,
        "p_repair_trace": None,
        "terminal_source_stage": "initial",
        "terminal_generation_seed": 110,
        "terminal_attempt_index": 0,
        "terminal_source_hash": HASH_A,
        "terminal_prompt_hash": INITIAL_PROMPT_HASH,
        "terminal_prompt_hash_source": "initial_prompt",
        "terminal_source_matches_row_source": True,
    }
    trace_override_present = "trace_summary" in overrides
    metadata_override_present = "generated_metadata" in overrides
    c_attempt_count = int(overrides.pop("trace_c_attempt_count", 0))
    values.update(overrides)
    condition = str(values["condition"])
    values["source_class"] = overrides.get("source_class", GENERATED_SOURCE_CLASS)
    values["generation_mode"] = overrides.get(
        "generation_mode",
        generation_mode_for_cluster3_condition(condition)
        if condition in {"P", "G+P", "C+P", "G+C+P"}
        else "invalid",
    )
    if "grammar_active" not in overrides:
        values["grammar_active"] = condition in {"G+P", "G+C+P"}
    if values["c_loop_fired"] and c_attempt_count == 0:
        c_attempt_count = 1 if values["terminal_source_stage"] == "c_attempt" else 0
    if not trace_override_present:
        values["trace_summary"] = _trace_summary(values, c_attempt_count)
    if not metadata_override_present:
        values["generated_metadata"] = _generated_metadata(
            condition=condition,
            generation_seed=int(values["terminal_generation_seed"]),
            terminal_source_stage=str(values["terminal_source_stage"]),
            terminal_attempt_index=values["terminal_attempt_index"],  # type: ignore[arg-type]
            terminal_source_hash=str(values["terminal_source_hash"]),
            terminal_prompt_hash=values["terminal_prompt_hash"],  # type: ignore[arg-type]
            terminal_prompt_hash_source=str(values["terminal_prompt_hash_source"]),
            p_repair_attempted=bool(values["p_repair_attempted"]),
            p_compile_repair_succeeded=bool(values["p_compile_repair_succeeded"]),
            p_repair_attempt_count=int(values["p_repair_attempt_count"]),
            c_loop_fired=bool(values["c_loop_fired"]),
            c_loop_source=str(values["c_loop_source"]),
        )
    values.setdefault("replay_metadata", None)
    return Cluster3EvalRow(**values)  # type: ignore[arg-type]


def _p_row(
    *,
    terminal_failure_code: str | None = None,
    failure_code: str | None = None,
    functional_success: bool = True,
    compile_success: bool = True,
    attempt_count: int = 1,
    terminal_source_hash: str = HASH_B,
    terminal_generation_seed: int = 111,
    terminal_prompt_hash: str | None = P_PROMPT_HASH,
    terminal_prompt_hash_source: str = "p_repair_prompt",
    terminal_source_stage: str = "p_attempt",
    terminal_attempt_index: int | None = 1,
    p_compile_repair_succeeded: bool = True,
    stop_reason: str = "p_compile_repaired_then_success",
    **overrides: object,
) -> Cluster3EvalRow:
    resolved_failure = terminal_failure_code if failure_code is None else failure_code
    changed = "F1_COMPILE" != terminal_failure_code or terminal_failure_code is None
    values = {
        "source_hash": terminal_source_hash,
        "compile_success": compile_success,
        "functional_success": functional_success,
        "repair_set_success": functional_success,
        "eval_set_success": functional_success,
        "failure_code": resolved_failure,
        "initial_failure_code": "F1_COMPILE",
        "p_repair_attempted": True,
        "p_compile_repair_succeeded": p_compile_repair_succeeded,
        "p_repair_changed_terminal_class": changed,
        "p_repair_attempt_count": attempt_count,
        "p_initial_failure_code": "F1_COMPILE",
        "p_terminal_failure_code": terminal_failure_code,
        "p_repair_stop_reason": stop_reason,
        "p_compile_error_class": "CompilationError",
        "p_raw_error_excerpt_sha256": HASH_E,
        "p_repair_trace": _p_trace(
            attempt_count=attempt_count,
            terminal_failure_code=terminal_failure_code,
            terminal_source_hash=terminal_source_hash,
            terminal_generation_seed=terminal_generation_seed,
        ),
        "terminal_source_stage": terminal_source_stage,
        "terminal_generation_seed": terminal_generation_seed,
        "terminal_attempt_index": terminal_attempt_index,
        "terminal_source_hash": terminal_source_hash,
        "terminal_prompt_hash": terminal_prompt_hash,
        "terminal_prompt_hash_source": terminal_prompt_hash_source,
    }
    values.update(overrides)
    return _row(**values)


def _direct_c_row(
    *,
    c_terminal_failure_code: str | None = None,
    functional_success: bool = True,
    compile_success: bool = True,
    terminal_source_hash: str = HASH_C,
    terminal_source_stage: str = "c_attempt",
    terminal_attempt_index: int | None = 1,
    terminal_prompt_hash: str | None = C_PROMPT_HASH,
    terminal_prompt_hash_source: str = "c_repair_prompt",
    **overrides: object,
) -> Cluster3EvalRow:
    values = {
        "condition": "C+P",
        "source_hash": terminal_source_hash,
        "compile_success": compile_success,
        "functional_success": functional_success,
        "repair_set_success": functional_success,
        "eval_set_success": functional_success,
        "failure_code": c_terminal_failure_code,
        "repair_trace": (
            _c_trace(
                failure_code=c_terminal_failure_code,
                source_hash=terminal_source_hash,
                functional_success=functional_success,
                repair_set_success=functional_success,
                eval_set_success=functional_success,
            ),
        ),
        "initial_failure_code": "F2_NUMERIC_LARGE",
        "c_loop_fired": True,
        "c_loop_source": "initial_f2",
        "c_terminal_failure_code": c_terminal_failure_code,
        "c_terminal_level_reached": 2,
        "terminal_source_stage": terminal_source_stage,
        "terminal_generation_seed": 210,
        "terminal_attempt_index": terminal_attempt_index,
        "terminal_source_hash": terminal_source_hash,
        "terminal_prompt_hash": terminal_prompt_hash,
        "terminal_prompt_hash_source": terminal_prompt_hash_source,
    }
    values.update(overrides)
    return _row(**values)


def _p_then_c_row(
    *,
    c_terminal_failure_code: str | None = None,
    functional_success: bool = True,
    compile_success: bool = True,
    p_terminal_failure_code: str | None = "F2_NUMERIC_LARGE",
    terminal_source_hash: str = HASH_C,
    **overrides: object,
) -> Cluster3EvalRow:
    values = {
        "condition": "C+P",
        "source_hash": terminal_source_hash,
        "compile_success": compile_success,
        "functional_success": functional_success,
        "repair_set_success": functional_success,
        "eval_set_success": functional_success,
        "failure_code": c_terminal_failure_code,
        "repair_trace": (
            _c_trace(
                failure_code=c_terminal_failure_code,
                source_hash=terminal_source_hash,
                functional_success=functional_success,
                repair_set_success=functional_success,
                eval_set_success=functional_success,
            ),
        ),
        "initial_failure_code": "F1_COMPILE",
        "p_repair_attempted": True,
        "p_compile_repair_succeeded": True,
        "p_repair_changed_terminal_class": True,
        "p_repair_attempt_count": 1,
        "p_initial_failure_code": "F1_COMPILE",
        "p_terminal_failure_code": p_terminal_failure_code,
        "p_repair_stop_reason": "p_compile_repaired_f2_observed",
        "p_compile_error_class": "CompilationError",
        "p_raw_error_excerpt_sha256": HASH_E,
        "p_repair_trace": _p_trace(
            attempt_count=1,
            terminal_failure_code=p_terminal_failure_code,
            terminal_source_hash=HASH_B,
            terminal_generation_seed=111,
        ),
        "c_loop_fired": True,
        "c_loop_source": "post_p_f2",
        "c_terminal_failure_code": c_terminal_failure_code,
        "c_terminal_level_reached": 2,
        "terminal_source_stage": "c_attempt",
        "terminal_generation_seed": 210,
        "terminal_attempt_index": 1,
        "terminal_source_hash": terminal_source_hash,
        "terminal_prompt_hash": C_PROMPT_HASH,
        "terminal_prompt_hash_source": "c_repair_prompt",
    }
    values.update(overrides)
    return _row(**values)


def test_cluster3_row_accepts_p_condition() -> None:
    assert _row(condition="P").condition == "P"


@pytest.mark.parametrize("condition", ["none", "G", "C", "G+C"])
def test_cluster3_row_rejects_none_g_c_gc(condition: str) -> None:
    with pytest.raises(ValueError):
        _row(condition=condition)


def test_cluster3_row_rejects_unknown_failure_code() -> None:
    with pytest.raises(ValueError, match="failure_code"):
        _row(failure_code="F9_UNKNOWN", functional_success=False)


@pytest.mark.parametrize(
    "field_name,value",
    [
        ("p_repair_attempt_count", 1),
        ("p_initial_failure_code", "F1_COMPILE"),
        ("p_terminal_failure_code", "F1_COMPILE"),
        ("p_repair_trace", (_p_attempt(attempt_index=0, failure_code="F1_COMPILE", generation_seed=1),)),
        ("p_compile_error_class", "CompilationError"),
        ("p_raw_error_excerpt_sha256", HASH_E),
        ("p_compile_repair_succeeded", True),
        ("p_repair_changed_terminal_class", True),
    ],
)
def test_cluster3_row_p_attempted_false_requires_p_outcome_fields_inactive(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(ValueError):
        _row(**{field_name: value})


def test_inactive_p_rows_record_p_config_but_no_p_attempt() -> None:
    row = _row()
    assert row.p_repair_attempted is False
    assert row.p_feedback_format == P_FEEDBACK_FORMAT_V1
    assert row.p_history_policy == P_HISTORY_POLICY_V1


def test_inactive_p_rows_use_p_not_applicable_stop_reason() -> None:
    with pytest.raises(ValueError, match="p_not_applicable"):
        _row(p_repair_stop_reason="p_budget_exhausted")
    assert _row().p_repair_stop_reason == "p_not_applicable"


def test_direct_initial_f2_c_row_has_p_attempt_count_zero() -> None:
    assert _direct_c_row().p_repair_attempt_count == 0


def test_direct_initial_f2_c_row_uses_p_not_applicable_stop_reason() -> None:
    assert _direct_c_row().p_repair_stop_reason == "p_not_applicable"


def test_inactive_p_terminal_fields_are_null_or_false_except_stop_reason() -> None:
    row = _direct_c_row()
    assert row.p_initial_failure_code is None
    assert row.p_terminal_failure_code is None
    assert row.p_repair_trace is None
    assert row.p_compile_error_class is None
    assert row.p_raw_error_excerpt_sha256 is None
    assert row.p_compile_repair_succeeded is False
    assert row.p_repair_changed_terminal_class is False
    assert row.p_repair_stop_reason == "p_not_applicable"


def test_cluster3_row_p_compile_repair_succeeded_allows_f2_failure_code() -> None:
    row = _p_row(
        terminal_failure_code="F2_NUMERIC_LARGE",
        functional_success=False,
        compile_success=True,
        p_compile_repair_succeeded=True,
        stop_reason="p_compile_repaired_f2_observed",
    )
    assert row.failure_code == "F2_NUMERIC_LARGE"
    assert row.p_compile_repair_succeeded is True


def test_p_compile_repair_succeeded_survives_c_regression_to_f1() -> None:
    row = _p_then_c_row(
        c_terminal_failure_code="F1_COMPILE",
        functional_success=False,
        compile_success=False,
    )
    assert row.p_compile_repair_succeeded is True
    assert row.failure_code == "F1_COMPILE"


def test_final_row_compile_success_reflects_c_terminal_not_p_terminal() -> None:
    row = _p_then_c_row(
        c_terminal_failure_code="F1_COMPILE",
        functional_success=False,
        compile_success=False,
    )
    assert row.compile_success is False


def test_cluster3_row_p_attempted_failed_allows_terminal_class_change() -> None:
    row = _p_row(
        terminal_failure_code="F0_PARSE",
        functional_success=False,
        compile_success=False,
        p_compile_repair_succeeded=False,
        stop_reason="p_terminal_non_repairable",
    )
    assert row.p_repair_changed_terminal_class is True


def test_cluster3_row_p_attempted_failed_allows_f1_runtime_terminal() -> None:
    row = _p_row(
        terminal_failure_code="F1_RUNTIME",
        functional_success=False,
        compile_success=False,
        p_compile_repair_succeeded=False,
        stop_reason="p_terminal_non_repairable",
    )
    assert row.failure_code == "F1_RUNTIME"


def test_cluster3_row_p_attempted_failed_allows_f3_terminal() -> None:
    row = _p_row(
        terminal_failure_code="F3_EVAL_PIPELINE",
        functional_success=False,
        compile_success=True,
        p_compile_repair_succeeded=False,
        stop_reason="p_f3_without_compile_evidence",
    )
    assert row.failure_code == "F3_EVAL_PIPELINE"


def test_cluster3_row_p_only_after_p_compile_repair_failure_code_matches_p_terminal() -> None:
    with pytest.raises(ValueError, match="failure_code"):
        _p_row(
            terminal_failure_code="F2_NUMERIC_LARGE",
            failure_code="F2_NUMERIC_NAN",
            functional_success=False,
            stop_reason="p_compile_repaired_f2_observed",
        )


def test_cluster3_row_c_plus_p_after_c_success_failure_code_is_none() -> None:
    row = _p_then_c_row(c_terminal_failure_code=None, functional_success=True)
    assert row.failure_code is None


def test_cluster3_row_c_loop_fired_requires_c_in_condition() -> None:
    with pytest.raises(ValueError, match="c_loop_fired"):
        _direct_c_row(condition="P")


def test_cluster3_row_c_loop_fired_requires_repair_trace_non_none() -> None:
    with pytest.raises(ValueError, match="repair_trace"):
        _direct_c_row(repair_trace=None)


def test_schema_allows_c_loop_fired_without_p_repair_attempted_when_source_initial_f2() -> None:
    row = _direct_c_row()
    assert row.c_loop_source == "initial_f2"
    assert row.p_repair_attempted is False


def test_c_loop_source_none_when_c_not_fired() -> None:
    with pytest.raises(ValueError, match="c_loop_source"):
        _row(c_loop_source="initial_f2")


def test_c_loop_inactive_rejects_repair_trace() -> None:
    with pytest.raises(ValueError, match="repair_trace"):
        _row(repair_trace=(_c_trace(),))


@pytest.mark.parametrize(
    ("failure_code", "compile_success", "functional_success"),
    [
        (None, True, True),
        ("F0_PARSE", False, False),
        ("F1_COMPILE", False, False),
        ("F2_NUMERIC_LARGE", True, False),
        ("F3_EVAL_PIPELINE", True, False),
    ],
)
def test_c_loop_terminal_allows_f0_f1_f2_f3_none(
    failure_code: str | None,
    compile_success: bool,
    functional_success: bool,
) -> None:
    assert _direct_c_row(
        c_terminal_failure_code=failure_code,
        compile_success=compile_success,
        functional_success=functional_success,
    ).c_terminal_failure_code == failure_code


def test_p_to_f2_then_c_to_f1_row_validates() -> None:
    assert _p_then_c_row(
        c_terminal_failure_code="F1_COMPILE",
        functional_success=False,
        compile_success=False,
    ).failure_code == "F1_COMPILE"


def test_c_loop_source_post_p_requires_p_terminal_f2() -> None:
    with pytest.raises(ValueError, match="post_p_f2"):
        _p_then_c_row(
            p_terminal_failure_code="F3_EVAL_PIPELINE",
            p_repair_stop_reason="p_post_compile_f3_observed",
        )


def test_c_loop_source_initial_f2_rejects_p_fields() -> None:
    with pytest.raises(ValueError, match="initial_failure_code"):
        _direct_c_row(
            p_repair_attempted=True,
            p_initial_failure_code="F1_COMPILE",
            p_terminal_failure_code="F2_NUMERIC_LARGE",
            p_repair_attempt_count=1,
            p_repair_trace=_p_trace(
                attempt_count=1,
                terminal_failure_code="F2_NUMERIC_LARGE",
            ),
            p_compile_error_class="CompilationError",
            p_raw_error_excerpt_sha256=HASH_E,
            p_repair_stop_reason="p_compile_repaired_f2_observed",
            p_repair_changed_terminal_class=True,
            p_compile_repair_succeeded=True,
        )


def test_cluster3_row_p_repair_attempt_count_excludes_seed() -> None:
    row = _p_row(
        terminal_failure_code="F1_COMPILE",
        functional_success=False,
        compile_success=False,
        attempt_count=0,
        terminal_source_hash=HASH_A,
        terminal_generation_seed=110,
        terminal_source_stage="initial",
        terminal_attempt_index=0,
        terminal_prompt_hash=INITIAL_PROMPT_HASH,
        terminal_prompt_hash_source="initial_prompt",
        p_compile_repair_succeeded=False,
        stop_reason="p_budget_exhausted",
    )
    assert row.p_repair_attempt_count == 0
    assert len(row.p_repair_trace or ()) == 1


def test_cluster3_row_initial_terminal_rejects_generated_p_attempts() -> None:
    with pytest.raises(ValueError, match="generated P attempts"):
        _p_row(
            terminal_failure_code="F1_COMPILE",
            functional_success=False,
            compile_success=False,
            terminal_source_hash=HASH_A,
            terminal_generation_seed=110,
            terminal_source_stage="initial",
            terminal_attempt_index=0,
            terminal_prompt_hash=INITIAL_PROMPT_HASH,
            terminal_prompt_hash_source="initial_prompt",
            p_compile_repair_succeeded=False,
            stop_reason="p_budget_exhausted",
        )


def test_cluster3_row_p_repair_trace_length_matches_attempt_count_plus_seed() -> None:
    with pytest.raises(ValueError, match="p_repair_trace"):
        _p_row(
            terminal_failure_code=None,
            p_repair_trace=(_p_attempt(attempt_index=0, failure_code="F1_COMPILE", generation_seed=1),),
        )


def test_cluster3_row_p_terminal_failure_code_matches_p_trace_terminal() -> None:
    with pytest.raises(ValueError, match="p_terminal_failure_code"):
        _p_row(
            terminal_failure_code="F2_NUMERIC_LARGE",
            functional_success=False,
            compile_success=True,
            attempt_count=0,
            terminal_source_hash=HASH_A,
            terminal_generation_seed=110,
            terminal_source_stage="initial",
            terminal_attempt_index=0,
            terminal_prompt_hash=INITIAL_PROMPT_HASH,
            terminal_prompt_hash_source="initial_prompt",
            p_compile_repair_succeeded=True,
            stop_reason="p_compile_repaired_f2_observed",
        )


def test_cluster3_row_p_seed_trace_matches_initial_failure_code() -> None:
    valid = _p_row()
    assert valid.p_repair_trace is not None
    bad_seed_trace = (
        _p_attempt(
            attempt_index=0,
            failure_code=None,
            generation_seed=110,
            source_hash=HASH_A,
        ),
        valid.p_repair_trace[-1],
    )
    with pytest.raises(ValueError, match="p_initial_failure_code"):
        _p_row(p_repair_trace=bad_seed_trace)


@pytest.mark.parametrize("initial_failure_code", [None, "F2_NUMERIC_LARGE"])
def test_cluster3_row_active_p_initial_failure_code_matches_p_initial_failure_code(
    initial_failure_code: str | None,
) -> None:
    with pytest.raises(ValueError, match="initial_failure_code"):
        _p_row(initial_failure_code=initial_failure_code)


@pytest.mark.parametrize(
    "override",
    [
        {
            "p_repair_trace": (
                PRepairAttemptSummary(
                    attempt_index=0,
                    generation_seed=110,
                    compile_success=True,
                    failure_code="F1_COMPILE",
                    compile_error_class="CompilationError",
                    source_hash=HASH_A,
                    feedback_sha256=None,
                ),
                _p_trace(attempt_count=1, terminal_failure_code=None)[-1],
            )
        },
        {"p_compile_error_class": None},
        {
            "p_repair_trace": (
                _p_attempt(
                    attempt_index=0,
                    failure_code="F1_COMPILE",
                    generation_seed=110,
                    source_hash=HASH_A,
                ),
                _p_trace(attempt_count=1, terminal_failure_code=None)[-1],
            ),
            "p_compile_error_class": "DifferentError",
        },
        {"p_raw_error_excerpt_sha256": None},
    ],
)
def test_cluster3_row_p_seed_trace_requires_compile_error_metadata(
    override: dict[str, object],
) -> None:
    with pytest.raises(ValueError, match="P seed|p_compile_error_class|p_raw"):
        _p_row(**override)


def test_cluster3_row_p_compile_repair_succeeded_matches_p_trace_compile() -> None:
    with pytest.raises(ValueError, match="p_compile_repair_succeeded"):
        _p_row(
            terminal_failure_code="F2_NUMERIC_LARGE",
            functional_success=False,
            compile_success=True,
            p_repair_trace=(
                _p_attempt(
                    attempt_index=0,
                    failure_code="F1_COMPILE",
                    generation_seed=110,
                    source_hash=HASH_A,
                ),
                PRepairAttemptSummary(
                    attempt_index=1,
                    generation_seed=111,
                    compile_success=False,
                    failure_code="F2_NUMERIC_LARGE",
                    compile_error_class=None,
                    source_hash=HASH_B,
                    feedback_sha256=HASH_E,
                ),
            ),
            p_compile_repair_succeeded=True,
            stop_reason="p_compile_repaired_f2_observed",
        )


def test_cluster3_row_p_compile_repair_succeeded_allows_post_compile_f3_evidence() -> None:
    row = _p_row(
        terminal_failure_code="F3_EVAL_PIPELINE",
        functional_success=False,
        compile_success=False,
        p_repair_trace=(
            _p_attempt(
                attempt_index=0,
                failure_code="F1_COMPILE",
                generation_seed=110,
                source_hash=HASH_A,
            ),
            PRepairAttemptSummary(
                attempt_index=1,
                generation_seed=111,
                compile_success=False,
                failure_code="F3_EVAL_PIPELINE",
                compile_error_class=None,
                source_hash=HASH_B,
                feedback_sha256=HASH_E,
            ),
        ),
        p_compile_repair_succeeded=True,
        stop_reason="p_post_compile_f3_observed",
    )
    assert row.p_compile_repair_succeeded is True


@pytest.mark.parametrize(
    ("terminal_failure_code", "functional_success", "compile_success", "stop_reason"),
    [
        (None, True, True, "p_compile_repaired_then_success"),
        ("F2_NUMERIC_LARGE", False, True, "p_compile_repaired_f2_observed"),
        ("F3_EVAL_PIPELINE", False, False, "p_post_compile_f3_observed"),
    ],
)
def test_compile_repaired_stop_reasons_require_success_flag(
    terminal_failure_code: str | None,
    functional_success: bool,
    compile_success: bool,
    stop_reason: str,
) -> None:
    with pytest.raises(ValueError, match="p_compile_repair_succeeded"):
        _p_row(
            terminal_failure_code=terminal_failure_code,
            functional_success=functional_success,
            compile_success=compile_success,
            p_compile_repair_succeeded=False,
            stop_reason=stop_reason,
        )


@pytest.mark.parametrize(
    (
        "terminal_failure_code",
        "functional_success",
        "compile_success",
        "p_compile_repair_succeeded",
        "stop_reason",
    ),
    [
        (None, True, True, True, "p_compile_repaired_f2_observed"),
        ("F2_NUMERIC_LARGE", False, True, True, "p_compile_repaired_then_success"),
        ("F2_NUMERIC_LARGE", False, True, False, "p_f3_without_compile_evidence"),
        ("F3_EVAL_PIPELINE", False, True, True, "p_f3_without_compile_evidence"),
        ("F1_RUNTIME", False, False, True, "p_terminal_non_repairable"),
        (None, True, True, False, "p_budget_exhausted"),
    ],
)
def test_p_stop_reason_must_match_terminal_outcome(
    terminal_failure_code: str | None,
    functional_success: bool,
    compile_success: bool,
    p_compile_repair_succeeded: bool,
    stop_reason: str,
) -> None:
    with pytest.raises(ValueError, match="p_repair_stop_reason"):
        _p_row(
            terminal_failure_code=terminal_failure_code,
            functional_success=functional_success,
            compile_success=compile_success,
            p_compile_repair_succeeded=p_compile_repair_succeeded,
            stop_reason=stop_reason,
        )


@pytest.mark.parametrize(
    ("terminal_code", "expected"),
    [(None, True), ("F1_COMPILE", False), ("F1_RUNTIME", True), ("F2_NUMERIC_LARGE", True)],
)
def test_cluster3_row_p_repair_changed_terminal_class_consistency(
    terminal_code: str | None,
    expected: bool,
) -> None:
    kwargs = {
        "terminal_failure_code": terminal_code,
        "functional_success": terminal_code is None,
        "compile_success": terminal_code is None or terminal_code.startswith(("F2_", "F3_")),
        "p_compile_repair_succeeded": terminal_code is None or terminal_code.startswith("F2_"),
        "stop_reason": "p_compile_repaired_then_success"
        if terminal_code is None
        else "p_compile_repaired_f2_observed"
        if terminal_code.startswith("F2_")
        else "p_terminal_non_repairable",
    }
    if terminal_code == "F1_COMPILE":
        kwargs["stop_reason"] = "p_budget_exhausted"
    row = _p_row(**kwargs)
    assert row.p_repair_changed_terminal_class is expected
    with pytest.raises(ValueError, match="p_repair_changed_terminal_class"):
        _p_row(p_repair_changed_terminal_class=not expected, **kwargs)


def test_cluster3_row_p_attempted_false_requires_changed_class_false() -> None:
    with pytest.raises(ValueError, match="p_repair_changed_terminal_class"):
        _row(p_repair_changed_terminal_class=True)


def test_cluster3_row_p_attempted_false_allows_direct_c_loop_from_initial_f2() -> None:
    assert _direct_c_row().p_repair_attempted is False


def test_cluster3_row_has_no_p_helped_attribute() -> None:
    assert "p_helped" not in {field.name for field in fields(Cluster3EvalRow)}


def test_cluster3_row_uses_p_terminal_failure_code_attribute() -> None:
    assert "p_terminal_failure_code" in {field.name for field in fields(Cluster3EvalRow)}


def test_cluster3_row_requires_trace_summary() -> None:
    with pytest.raises(TypeError, match="trace_summary"):
        _row(trace_summary=None)


def test_trace_summary_mentions_p_and_c_loop_status_without_private_data() -> None:
    row = _p_then_c_row()
    payload = row.trace_summary.to_dict()
    rendered = json.dumps(payload, sort_keys=True)
    assert payload["p_loop_fired"] is True
    assert payload["c_loop_fired"] is True
    assert "hidden" not in rendered
    assert "traceback" not in rendered
    assert "def " not in rendered


def test_trace_summary_terminal_hash_matches_row() -> None:
    valid = _row()
    bad_trace = Cluster3TraceSummary.from_dict(
        {**valid.trace_summary.to_dict(), "terminal_source_hash": HASH_B}
    )
    with pytest.raises(ValueError, match="terminal_source_hash"):
        _row(trace_summary=bad_trace)


def test_trace_summary_terminal_stage_matches_row() -> None:
    valid = _p_then_c_row()
    bad_trace = Cluster3TraceSummary.from_dict(
        {
            **valid.trace_summary.to_dict(),
            "terminal_source_stage": "initial",
            "terminal_attempt_index": 0,
        }
    )
    with pytest.raises(ValueError, match="terminal_source_stage"):
        _p_then_c_row(trace_summary=bad_trace)


def test_trace_summary_terminal_attempt_index_matches_row() -> None:
    valid = _p_then_c_row()
    bad_trace = Cluster3TraceSummary.from_dict(
        {**valid.trace_summary.to_dict(), "terminal_attempt_index": 99}
    )
    with pytest.raises(ValueError, match="terminal_attempt_index"):
        _p_then_c_row(trace_summary=bad_trace)


def test_trace_summary_final_success_flags_match_row() -> None:
    valid = _row()
    bad_trace = Cluster3TraceSummary.from_dict(
        {**valid.trace_summary.to_dict(), "functional_success": False}
    )
    with pytest.raises(ValueError, match="functional_success"):
        _row(trace_summary=bad_trace)


def test_trace_summary_terminal_generation_seed_matches_row_metadata() -> None:
    valid = _row()
    bad_trace = Cluster3TraceSummary.from_dict(
        {**valid.trace_summary.to_dict(), "terminal_generation_seed": 999}
    )
    with pytest.raises(ValueError, match="terminal_generation_seed"):
        _row(trace_summary=bad_trace)


def test_trace_summary_no_private_eval_data() -> None:
    assert _row().trace_summary.private_eval_data_included is False


def test_cluster3_trace_summary_matches_row_terminal_provenance() -> None:
    row = _p_then_c_row()
    assert row.trace_summary.terminal_source_hash == row.terminal_source_hash
    assert row.trace_summary.row_source_hash == row.source_hash
    assert row.trace_summary.terminal_prompt_hash == row.terminal_prompt_hash


def test_cluster3_trace_summary_matches_row_final_success_flags() -> None:
    row = _p_then_c_row(
        c_terminal_failure_code="F1_COMPILE",
        functional_success=False,
        compile_success=False,
    )
    assert row.trace_summary.compile_success is row.compile_success
    assert row.trace_summary.functional_success is row.functional_success
    assert row.trace_summary.repair_set_success is row.repair_set_success
    assert row.trace_summary.eval_set_success is row.eval_set_success


def test_terminal_source_stage_initial_sets_generation_seed_from_initial() -> None:
    assert _row().terminal_generation_seed == 110


def test_terminal_source_stage_p_attempt_sets_generation_seed_from_p_attempt() -> None:
    assert _p_row().terminal_generation_seed == 111


def test_terminal_source_stage_c_attempt_sets_generation_seed_from_c_attempt() -> None:
    assert _p_then_c_row().terminal_generation_seed == 210


def test_row_source_hash_equals_terminal_source_hash() -> None:
    with pytest.raises(ValueError, match="source_hash"):
        _row(terminal_source_hash=HASH_B)


def test_generated_metadata_generation_seed_equals_terminal_generation_seed() -> None:
    with pytest.raises(ValueError, match="generation_seed"):
        _row(generated_metadata=_generated_metadata(generation_seed=999))


def test_p_terminal_source_preserved_when_c_regresses() -> None:
    row = _p_then_c_row(
        c_terminal_failure_code="F1_COMPILE",
        functional_success=False,
        compile_success=False,
    )
    assert row.terminal_source_hash == HASH_C
    assert row.p_repair_trace is not None
    assert row.p_repair_trace[-1].source_hash == HASH_B


def test_terminal_prompt_hash_initial_source_uses_initial_prompt_hash() -> None:
    row = _row()
    assert row.terminal_prompt_hash == INITIAL_PROMPT_HASH
    assert row.terminal_prompt_hash_source == "initial_prompt"


def test_terminal_prompt_hash_p_attempt_uses_p_prompt_hash() -> None:
    row = _p_row()
    assert row.terminal_prompt_hash == P_PROMPT_HASH
    assert row.terminal_prompt_hash_source == "p_repair_prompt"


def test_terminal_prompt_hash_generated_c_attempt_hashes_c_prompt() -> None:
    row = _p_then_c_row()
    assert row.terminal_prompt_hash == C_PROMPT_HASH
    assert row.terminal_prompt_hash_source == "c_repair_prompt"


@pytest.mark.parametrize(
    ("prompt_hash", "prompt_hash_source"),
    [
        (P_PROMPT_HASH, "seed_prompt_metadata"),
        (None, "seed_prompt_unavailable"),
    ],
)
def test_post_p_c_seed_terminal_allows_seed_prompt_hash_sources(
    prompt_hash: str | None,
    prompt_hash_source: str,
) -> None:
    row = _p_then_c_row(
        c_terminal_failure_code="F2_NUMERIC_LARGE",
        functional_success=False,
        compile_success=True,
        repair_trace=(),
        terminal_source_hash=HASH_B,
        terminal_source_stage="p_attempt",
        terminal_generation_seed=111,
        terminal_attempt_index=1,
        terminal_prompt_hash=prompt_hash,
        terminal_prompt_hash_source=prompt_hash_source,
        trace_c_attempt_count=0,
    )
    assert row.c_loop_fired is True
    assert row.c_loop_source == "post_p_f2"
    assert row.terminal_source_stage == "p_attempt"
    assert row.terminal_prompt_hash_source == prompt_hash_source


def test_terminal_source_stage_p_attempt_requires_p_loop() -> None:
    with pytest.raises(ValueError, match="p_attempt"):
        _row(
            source_hash=HASH_B,
            terminal_source_hash=HASH_B,
            terminal_source_stage="p_attempt",
            terminal_generation_seed=111,
            terminal_attempt_index=1,
            terminal_prompt_hash=P_PROMPT_HASH,
            terminal_prompt_hash_source="p_repair_prompt",
        )


def test_terminal_source_stage_p_attempt_requires_generated_p_attempt() -> None:
    with pytest.raises(ValueError, match="generated P attempt"):
        _p_row(
            terminal_failure_code="F1_COMPILE",
            functional_success=False,
            compile_success=False,
            attempt_count=0,
            terminal_source_hash=HASH_A,
            terminal_generation_seed=110,
            terminal_source_stage="p_attempt",
            terminal_attempt_index=0,
            terminal_prompt_hash=P_PROMPT_HASH,
            terminal_prompt_hash_source="p_repair_prompt",
            p_compile_repair_succeeded=False,
            stop_reason="p_budget_exhausted",
        )


def test_terminal_source_stage_p_attempt_binds_attempt_index_to_p_trace() -> None:
    with pytest.raises(ValueError, match="terminal_attempt_index"):
        _p_row(terminal_attempt_index=2)


def test_terminal_source_stage_p_attempt_binds_p_trace_to_attempt_count() -> None:
    with pytest.raises(ValueError, match="p_repair_attempt_count"):
        _p_row(
            p_repair_trace=(
                _p_attempt(
                    attempt_index=0,
                    failure_code="F1_COMPILE",
                    generation_seed=110,
                    source_hash=HASH_A,
                ),
                _p_attempt(
                    attempt_index=2,
                    failure_code=None,
                    generation_seed=111,
                    source_hash=HASH_B,
                ),
            )
        )


def test_p_then_c_row_validates_p_trace_attempt_index_sequence() -> None:
    with pytest.raises(ValueError, match="p_repair_attempt_count"):
        _p_then_c_row(
            p_repair_trace=(
                _p_attempt(
                    attempt_index=0,
                    failure_code="F1_COMPILE",
                    generation_seed=110,
                    source_hash=HASH_A,
                ),
                _p_attempt(
                    attempt_index=99,
                    failure_code="F2_NUMERIC_LARGE",
                    generation_seed=111,
                    source_hash=HASH_B,
                ),
            )
        )


def test_terminal_source_stage_p_attempt_binds_seed_to_p_trace() -> None:
    with pytest.raises(ValueError, match="terminal_generation_seed"):
        _p_row(
            p_repair_trace=_p_trace(
                attempt_count=1,
                terminal_failure_code=None,
                terminal_source_hash=HASH_B,
                terminal_generation_seed=111,
            ),
            terminal_generation_seed=999,
        )


def test_terminal_source_stage_p_attempt_binds_source_hash_to_p_trace() -> None:
    with pytest.raises(ValueError, match="terminal_source_hash"):
        _p_row(
            p_repair_trace=_p_trace(
                attempt_count=1,
                terminal_failure_code=None,
                terminal_source_hash=HASH_A,
                terminal_generation_seed=111,
            ),
            terminal_source_hash=HASH_B,
        )


def test_terminal_source_stage_c_attempt_requires_c_loop() -> None:
    with pytest.raises(ValueError, match="c_attempt"):
        _row(
            source_hash=HASH_C,
            terminal_source_hash=HASH_C,
            terminal_source_stage="c_attempt",
            terminal_generation_seed=210,
            terminal_attempt_index=1,
            terminal_prompt_hash=C_PROMPT_HASH,
            terminal_prompt_hash_source="c_repair_prompt",
        )


def test_terminal_source_stage_c_attempt_binds_attempt_index_to_repair_trace() -> None:
    with pytest.raises(ValueError, match="terminal_attempt_index"):
        _p_then_c_row(terminal_attempt_index=2)


def test_terminal_source_stage_c_attempt_binds_repair_trace_index_sequence() -> None:
    with pytest.raises(ValueError, match="repair_trace attempt_index"):
        _p_then_c_row(
            repair_trace=(_c_trace(attempt_index=99, source_hash=HASH_C),),
            terminal_attempt_index=99,
            trace_c_attempt_count=1,
        )


def test_terminal_source_stage_c_attempt_binds_source_hash_to_repair_trace() -> None:
    with pytest.raises(ValueError, match="terminal_source_hash"):
        _p_then_c_row(repair_trace=(_c_trace(source_hash=HASH_A),))


def test_terminal_source_stage_c_attempt_binds_failure_code_to_repair_trace() -> None:
    with pytest.raises(ValueError, match="c_terminal_failure_code"):
        _p_then_c_row(
            c_terminal_failure_code="F1_COMPILE",
            functional_success=False,
            compile_success=False,
            repair_trace=(_c_trace(failure_code=None, source_hash=HASH_C),),
        )


def test_terminal_source_stage_c_attempt_binds_success_flags_to_repair_trace() -> None:
    with pytest.raises(ValueError, match="functional_success"):
        _p_then_c_row(
            c_terminal_failure_code=None,
            functional_success=True,
            compile_success=True,
            repair_trace=(
                _c_trace(
                    failure_code=None,
                    source_hash=HASH_C,
                    functional_success=False,
                    repair_set_success=False,
                    eval_set_success=False,
                ),
            ),
        )


def test_initial_c_seed_terminal_rejects_generated_c_repair_trace() -> None:
    with pytest.raises(ValueError, match="C seed terminal"):
        _direct_c_row(
            terminal_source_stage="initial",
            terminal_attempt_index=0,
            terminal_source_hash=HASH_A,
            source_hash=HASH_A,
            terminal_prompt_hash=INITIAL_PROMPT_HASH,
            terminal_prompt_hash_source="initial_prompt",
            terminal_generation_seed=110,
            trace_c_attempt_count=0,
        )


def test_post_p_c_seed_terminal_rejects_generated_c_repair_trace() -> None:
    with pytest.raises(ValueError, match="C seed terminal"):
        _p_then_c_row(
            c_terminal_failure_code="F2_NUMERIC_LARGE",
            functional_success=False,
            compile_success=True,
            terminal_source_hash=HASH_B,
            source_hash=HASH_B,
            terminal_source_stage="p_attempt",
            terminal_generation_seed=111,
            terminal_attempt_index=1,
            terminal_prompt_hash=P_PROMPT_HASH,
            terminal_prompt_hash_source="seed_prompt_metadata",
            trace_c_attempt_count=0,
        )


def test_terminal_prompt_hash_seed_candidate_allows_none_only_with_unavailable_source() -> None:
    row = _direct_c_row(
        repair_trace=(),
        terminal_source_stage="initial",
        terminal_attempt_index=0,
        terminal_source_hash=HASH_A,
        source_hash=HASH_A,
        terminal_prompt_hash=None,
        terminal_prompt_hash_source="seed_prompt_unavailable",
        terminal_generation_seed=110,
        trace_c_attempt_count=0,
    )
    assert row.terminal_prompt_hash is None
    with pytest.raises(ValueError, match="terminal_prompt_hash"):
        _row(terminal_prompt_hash=None, terminal_prompt_hash_source="initial_prompt")


def test_terminal_prompt_hash_generated_c_attempt_cannot_be_none() -> None:
    with pytest.raises(ValueError, match="terminal_prompt_hash"):
        _p_then_c_row(terminal_prompt_hash=None)


def test_generated_row_requires_explicit_terminal_prompt_provenance() -> None:
    baseline = _row()
    with pytest.raises(TypeError, match="terminal_prompt_hash"):
        generated_row(
            condition="P",
            attempt_index=baseline.attempt_index,
            kernel_class=baseline.kernel_class,
            kernel_name=baseline.kernel_name,
            dtype=baseline.dtype,
            base_seed=baseline.base_seed,
            source_hash=baseline.source_hash,
            functional_success=baseline.functional_success,
            repair_set_success=baseline.repair_set_success,
            eval_set_success=baseline.eval_set_success,
            failure_code=baseline.failure_code,
            trace_summary=baseline.trace_summary,
            c3_generation_hashes=GEN_HASHES,
            generation_seed=baseline.terminal_generation_seed,
            initial_failure_code=baseline.initial_failure_code,
        )


def test_generated_row_accepts_explicit_initial_terminal_prompt_provenance() -> None:
    baseline = _row()
    row = generated_row(
        condition="P",
        attempt_index=baseline.attempt_index,
        kernel_class=baseline.kernel_class,
        kernel_name=baseline.kernel_name,
        dtype=baseline.dtype,
        base_seed=baseline.base_seed,
        source_hash=baseline.source_hash,
        functional_success=baseline.functional_success,
        repair_set_success=baseline.repair_set_success,
        eval_set_success=baseline.eval_set_success,
        failure_code=baseline.failure_code,
        trace_summary=baseline.trace_summary,
        c3_generation_hashes=GEN_HASHES,
        generation_seed=baseline.terminal_generation_seed,
        initial_failure_code=baseline.initial_failure_code,
        terminal_prompt_hash=baseline.terminal_prompt_hash,
        terminal_prompt_hash_source=baseline.terminal_prompt_hash_source,
    )
    assert row.terminal_prompt_hash == INITIAL_PROMPT_HASH
    assert row.terminal_prompt_hash_source == "initial_prompt"


def test_cluster3_generated_metadata_rejects_invalid_grammar_variant() -> None:
    with pytest.raises(ValueError, match="grammar_variant"):
        Cluster3GeneratedRowMetadata(
            c3_generation_hashes=GEN_HASHES,
            generation_seed=110,
            terminal_source_stage="initial",
            terminal_attempt_index=0,
            terminal_source_hash=HASH_A,
            terminal_prompt_hash=INITIAL_PROMPT_HASH,
            terminal_prompt_hash_source="initial_prompt",
            p_repair_attempted=False,
            p_compile_repair_succeeded=False,
            p_repair_attempt_count=0,
            c_loop_fired=False,
            c_loop_source="none",
            grammar_variant="not_a_variant",
            grammar_path="wrong.gbnf",
            grammar_claim_scope="wrong",
        )


def test_cluster3_generated_metadata_rejects_invalid_grammar_path() -> None:
    with pytest.raises(ValueError, match="grammar_path"):
        Cluster3GeneratedRowMetadata(
            c3_generation_hashes=GEN_HASHES,
            generation_seed=110,
            terminal_source_stage="initial",
            terminal_attempt_index=0,
            terminal_source_hash=HASH_A,
            terminal_prompt_hash=INITIAL_PROMPT_HASH,
            terminal_prompt_hash_source="initial_prompt",
            p_repair_attempted=False,
            p_compile_repair_succeeded=False,
            p_repair_attempt_count=0,
            c_loop_fired=False,
            c_loop_source="none",
            grammar_variant="task_agnostic",
            grammar_path="cluster1/grammar/triton_kernel.gbnf",
            grammar_claim_scope="wrong",
        )


def test_cluster3_generated_metadata_rejects_invalid_grammar_claim_scope() -> None:
    with pytest.raises(ValueError, match="grammar_claim_scope"):
        Cluster3GeneratedRowMetadata(
            c3_generation_hashes=GEN_HASHES,
            generation_seed=110,
            terminal_source_stage="initial",
            terminal_attempt_index=0,
            terminal_source_hash=HASH_A,
            terminal_prompt_hash=INITIAL_PROMPT_HASH,
            terminal_prompt_hash_source="initial_prompt",
            p_repair_attempted=False,
            p_compile_repair_succeeded=False,
            p_repair_attempt_count=0,
            c_loop_fired=False,
            c_loop_source="none",
            grammar_variant="task_agnostic",
            grammar_path="cluster1/grammar/triton_kernel_agnostic.gbnf",
            grammar_claim_scope="wrong",
        )


@pytest.mark.parametrize(
    ("override", "match"),
    [
        ({"stop_reason": "bad"}, "stop_reason"),
        ({"rejection_layer": "bad"}, "rejection_layer"),
        ({"gbnf_parse_valid": True}, "grammar validation fields"),
    ],
)
def test_cluster3_generated_metadata_rejects_invalid_runtime_metadata(
    override: dict[str, object],
    match: str,
) -> None:
    kwargs = {
        "c3_generation_hashes": GEN_HASHES,
        "generation_seed": 110,
        "terminal_source_stage": "initial",
        "terminal_attempt_index": 0,
        "terminal_source_hash": HASH_A,
        "terminal_prompt_hash": INITIAL_PROMPT_HASH,
        "terminal_prompt_hash_source": "initial_prompt",
        "p_repair_attempted": False,
        "p_compile_repair_succeeded": False,
        "p_repair_attempt_count": 0,
        "c_loop_fired": False,
        "c_loop_source": "none",
        **override,
    }
    with pytest.raises((TypeError, ValueError), match=match):
        Cluster3GeneratedRowMetadata(**kwargs)


@pytest.mark.parametrize("field_name", ["cluster1_artifact_id", "replay_source"])
def test_cluster3_generated_metadata_rejects_empty_replay_pairing_strings(
    field_name: str,
) -> None:
    kwargs = {
        "c3_generation_hashes": GEN_HASHES,
        "generation_seed": 110,
        "terminal_source_stage": "initial",
        "terminal_attempt_index": 0,
        "terminal_source_hash": HASH_A,
        "terminal_prompt_hash": INITIAL_PROMPT_HASH,
        "terminal_prompt_hash_source": "initial_prompt",
        "p_repair_attempted": False,
        "p_compile_repair_succeeded": False,
        "p_repair_attempt_count": 0,
        "c_loop_fired": False,
        "c_loop_source": "none",
        field_name: "",
    }
    with pytest.raises(ValueError, match=field_name):
        Cluster3GeneratedRowMetadata(**kwargs)


def test_cluster3_generated_metadata_rejects_non_replay_control_condition() -> None:
    with pytest.raises(ValueError, match="replay_control_condition"):
        Cluster3GeneratedRowMetadata(
            c3_generation_hashes=GEN_HASHES,
            generation_seed=110,
            terminal_source_stage="initial",
            terminal_attempt_index=0,
            terminal_source_hash=HASH_A,
            terminal_prompt_hash=INITIAL_PROMPT_HASH,
            terminal_prompt_hash_source="initial_prompt",
            p_repair_attempted=False,
            p_compile_repair_succeeded=False,
            p_repair_attempt_count=0,
            c_loop_fired=False,
            c_loop_source="none",
            replay_control_condition="C",
        )


def test_cluster3_sidecar_rejects_non_replay_control_hash_condition() -> None:
    with pytest.raises(ValueError, match="replay_control_hashes"):
        Cluster3ContentHashSidecar(
            schema_version=CLUSTER3_RESULTS_SCHEMA_VERSION,
            eval_pipeline_hashes={"shared/eval/pipeline.py": HASH_A},
            generated_condition_hashes={"P": GEN_HASHES},
            replay_control_hashes={"C": {"outputs/cluster1/baseline.jsonl": HASH_B}},
            external_pins={"python": "3.14.2"},
        )


def test_cluster3_replay_row_metadata_mirrors_cluster2_replay_metadata_contract() -> None:
    metadata = Cluster3ReplayRowMetadata(
        frozen_cluster1_artifact_id="cluster1-none",
        frozen_cluster1_source_hash=HASH_A,
        frozen_cluster1_generation_hashes={"cluster1/result.jsonl": HASH_B},
        frozen_cluster1_failure_code="F1_COMPILE",
        frozen_cluster1_compile_success=False,
        replay_pair_id="pair-1",
        replay_base_seed=11,
        replay_generation_seed=110,
        prompt_sha256=INITIAL_PROMPT_HASH,
    )
    assert metadata.frozen_cluster1_source_hash == HASH_A
    assert "frozen_cluster1_source_hash" in {field.name for field in fields(metadata)}


def test_cluster3_replay_row_metadata_not_used_as_generated_row_metadata() -> None:
    metadata = Cluster3ReplayRowMetadata(
        frozen_cluster1_artifact_id="cluster1-none",
        frozen_cluster1_source_hash=HASH_A,
        frozen_cluster1_generation_hashes={"cluster1/result.jsonl": HASH_B},
    )
    with pytest.raises(TypeError, match="generated_metadata"):
        _row(generated_metadata=metadata)


def test_cluster3_row_budget_bounds() -> None:
    for budget in range(DEFAULT_P_REPAIR_BUDGET + 1):
        assert _row(p_repair_budget=budget).p_repair_budget == budget
    with pytest.raises(ValueError, match="p_repair_budget"):
        _row(p_repair_budget=DEFAULT_P_REPAIR_BUDGET + 1)


def test_cluster3_row_attempt_count_bounds() -> None:
    with pytest.raises(ValueError, match="p_repair_attempt_count"):
        _p_row(p_repair_attempt_count=DEFAULT_P_REPAIR_BUDGET + 1)


def test_cluster3_row_feedback_format_constant() -> None:
    with pytest.raises(ValueError, match="p_feedback_format"):
        _row(p_feedback_format="old")


def test_cluster3_row_serializes_round_trips() -> None:
    row = _p_then_c_row()
    assert Cluster3EvalRow.from_json(row.to_json()) == row


def test_cluster3_schema_version_constant() -> None:
    assert CLUSTER3_RESULTS_SCHEMA_VERSION == 1
