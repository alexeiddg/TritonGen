import json

import pytest

from cluster3.feedback.trace import (
    Cluster3TraceSummary,
    build_cluster3_trace_summary,
)


HASH_A = "a" * 64
HASH_B = "b" * 64
PROMPT_HASH = "c" * 64


def _summary(**overrides: object) -> Cluster3TraceSummary:
    values = {
        "condition": "P",
        "initial_failure_code": "F1_COMPILE",
        "final_failure_code": None,
        "p_loop_fired": True,
        "p_attempt_count": 1,
        "p_terminal_failure_code": None,
        "p_compile_repair_succeeded": True,
        "c_loop_fired": False,
        "c_loop_source": "none",
        "c_attempt_count": 0,
        "c_terminal_failure_code": None,
        "terminal_source_stage": "p_attempt",
        "terminal_attempt_index": 1,
        "terminal_source_hash": HASH_A,
        "terminal_generation_seed": 71,
        "terminal_prompt_hash": PROMPT_HASH,
        "terminal_prompt_hash_source": "p_repair_prompt",
        "compile_success": True,
        "functional_success": True,
        "repair_set_success": True,
        "eval_set_success": True,
        "row_source_hash": HASH_A,
        "failure_path": ["initial:F1_COMPILE", "p_attempt:1:success"],
        "private_eval_data_included": False,
    }
    values.update(overrides)
    return Cluster3TraceSummary(**values)  # type: ignore[arg-type]


def test_cluster3_trace_summary_json_serializable() -> None:
    summary = _summary()

    assert json.loads(summary.to_json()) == summary.to_dict()


def test_cluster3_trace_summary_distinguishes_initial_f2_from_post_p_f2() -> None:
    direct = build_cluster3_trace_summary(
        condition="C+P",
        initial_failure_code="F2_NUMERIC_LARGE",
        final_failure_code=None,
        p_loop_fired=False,
        p_attempt_count=0,
        p_compile_repair_succeeded=False,
        c_loop_fired=True,
        c_loop_source="initial_f2",
        c_attempt_count=1,
        terminal_source_hash=HASH_A,
        terminal_generation_seed=72,
        terminal_prompt_hash=PROMPT_HASH,
        terminal_prompt_hash_source="c_repair_prompt",
        compile_success=True,
        functional_success=True,
        row_source_hash=HASH_A,
        failure_path=[
            "initial:F2_NUMERIC_LARGE",
            "c_seed:F2_NUMERIC_LARGE",
            "c_attempt:1:success",
        ],
    )
    post_p = build_cluster3_trace_summary(
        condition="C+P",
        initial_failure_code="F1_COMPILE",
        final_failure_code=None,
        p_loop_fired=True,
        p_attempt_count=1,
        p_terminal_failure_code="F2_NUMERIC_LARGE",
        p_compile_repair_succeeded=True,
        c_loop_fired=True,
        c_loop_source="post_p_f2",
        c_attempt_count=1,
        terminal_source_hash=HASH_B,
        terminal_generation_seed=73,
        terminal_prompt_hash=PROMPT_HASH,
        terminal_prompt_hash_source="c_repair_prompt",
        compile_success=True,
        functional_success=True,
        row_source_hash=HASH_B,
        failure_path=[
            "initial:F1_COMPILE",
            "p_attempt:1:F2_NUMERIC_LARGE",
            "c_seed:F2_NUMERIC_LARGE",
            "c_attempt:1:success",
        ],
    )

    assert direct.c_loop_source == "initial_f2"
    assert post_p.c_loop_source == "post_p_f2"
    assert direct.final_failure_code is None
    assert post_p.final_failure_code is None
    assert direct.failure_path != post_p.failure_path


def test_cluster3_trace_summary_preserves_success_final_failure_none() -> None:
    summary = build_cluster3_trace_summary(
        condition="P",
        initial_failure_code="F1_COMPILE",
        p_loop_fired=True,
        p_attempt_count=1,
        p_terminal_failure_code=None,
        p_compile_repair_succeeded=True,
        c_loop_fired=False,
        c_loop_source="none",
        c_attempt_count=0,
        terminal_source_stage="p_attempt",
        terminal_attempt_index=1,
        terminal_source_hash=HASH_A,
        terminal_generation_seed=72,
        terminal_prompt_hash=PROMPT_HASH,
        terminal_prompt_hash_source="p_repair_prompt",
        compile_success=True,
        functional_success=True,
        row_source_hash=HASH_A,
        failure_path=["initial:F1_COMPILE", "p_attempt:1:success"],
    )

    assert summary.final_failure_code is None


def test_cluster3_trace_summary_derives_p_only_success_flags() -> None:
    summary = build_cluster3_trace_summary(
        condition="P",
        initial_failure_code="F1_COMPILE",
        p_loop_result={
            "status": "compile_repaired_then_success",
            "attempts_executed": 2,
            "attempts": [
                {"attempt_index": 0, "failure_code": "F1_COMPILE"},
                {"attempt_index": 1, "failure_code": None},
            ],
            "final_failure_code": None,
            "terminal_compile_success": True,
            "terminal_level_reached": 2,
        },
        c_loop_fired=False,
        c_loop_source="none",
        c_attempt_count=0,
        terminal_source_stage="p_attempt",
        terminal_attempt_index=1,
        terminal_source_hash=HASH_A,
        terminal_generation_seed=72,
        terminal_prompt_hash=PROMPT_HASH,
        terminal_prompt_hash_source="p_repair_prompt",
        row_source_hash=HASH_A,
    )

    assert summary.compile_success is True
    assert summary.functional_success is True
    assert summary.final_failure_code is None


def test_cluster3_trace_summary_derives_initial_success_flags() -> None:
    summary = build_cluster3_trace_summary(
        condition="P",
        initial_result={
            "failure_code": None,
            "compile_success": True,
            "functional_success": True,
        },
        c_loop_fired=False,
        c_loop_source="none",
        c_attempt_count=0,
        terminal_source_stage="initial",
        terminal_attempt_index=0,
        terminal_source_hash=HASH_A,
        terminal_generation_seed=72,
        terminal_prompt_hash=PROMPT_HASH,
        terminal_prompt_hash_source="initial_prompt",
        row_source_hash=HASH_A,
    )

    assert summary.compile_success is True
    assert summary.functional_success is True
    assert summary.failure_path == ["initial:success"]


def test_cluster3_trace_summary_preserves_initial_f2_seed_failure_code() -> None:
    summary = build_cluster3_trace_summary(
        condition="C+P",
        initial_failure_code="F2_NUMERIC_NAN",
        p_loop_fired=False,
        p_attempt_count=0,
        p_compile_repair_succeeded=False,
        c_loop_fired=True,
        c_loop_source="initial_f2",
        c_attempt_count=1,
        terminal_source_hash=HASH_A,
        terminal_generation_seed=72,
        terminal_prompt_hash=PROMPT_HASH,
        terminal_prompt_hash_source="c_repair_prompt",
        compile_success=True,
        functional_success=True,
        row_source_hash=HASH_A,
    )

    assert summary.failure_path == [
        "initial:F2_NUMERIC_NAN",
        "c_seed:F2_NUMERIC_NAN",
        "c_attempt:1:success",
    ]
    assert summary.final_failure_code is None


def test_cluster3_trace_summary_marks_private_eval_data_false() -> None:
    assert _summary().private_eval_data_included is False
    with pytest.raises(ValueError, match="private_eval_data_included"):
        _summary(private_eval_data_included=True)


def test_cluster3_trace_summary_self_contained_invariants() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        _summary(condition="C")
    with pytest.raises(ValueError, match="terminal_source_hash"):
        _summary(terminal_source_hash="bad")
    with pytest.raises(ValueError, match="terminal_prompt_hash"):
        _summary(
            terminal_prompt_hash=None,
            terminal_prompt_hash_source="p_repair_prompt",
        )
    with pytest.raises(ValueError, match="failure_path"):
        _summary(failure_path=["initial:F1_COMPILE", "def source(): pass"])


def test_cluster3_trace_summary_failure_path_consistent_with_loop_flags() -> None:
    _summary(c_loop_fired=False, c_loop_source="none", c_attempt_count=0)
    _summary(
        condition="C+P",
        c_loop_fired=True,
        c_loop_source="post_p_f2",
        c_attempt_count=0,
        c_terminal_failure_code="F2_NUMERIC_LARGE",
        failure_path=[
            "initial:F1_COMPILE",
            "p_attempt:1:F2_NUMERIC_LARGE",
            "c_seed:F2_NUMERIC_LARGE",
        ],
    )
    with pytest.raises(ValueError, match="C labels"):
        _summary(
            p_loop_fired=False,
            p_attempt_count=0,
            p_terminal_failure_code=None,
            p_compile_repair_succeeded=False,
            c_loop_fired=False,
            c_loop_source="none",
            c_attempt_count=0,
            failure_path=["initial:F1_COMPILE", "c_seed:F2_NUMERIC_LARGE"],
        )


def test_cluster3_trace_summary_rejects_p_state_when_p_does_not_fire() -> None:
    with pytest.raises(ValueError, match="p_attempt_count"):
        _summary(
            p_loop_fired=False,
            p_attempt_count=1,
            p_terminal_failure_code=None,
            p_compile_repair_succeeded=False,
            failure_path=["initial:F1_COMPILE"],
        )
    with pytest.raises(ValueError, match="p_terminal_failure_code"):
        _summary(
            p_loop_fired=False,
            p_attempt_count=0,
            p_terminal_failure_code="F2_NUMERIC_LARGE",
            p_compile_repair_succeeded=False,
            failure_path=["initial:F1_COMPILE"],
        )
    with pytest.raises(ValueError, match="P labels"):
        _summary(
            p_loop_fired=False,
            p_attempt_count=0,
            p_terminal_failure_code=None,
            p_compile_repair_succeeded=False,
            failure_path=["initial:F1_COMPILE", "p_attempt:1:success"],
        )


def test_c_attempt_count_excludes_seed_candidate() -> None:
    summary = _summary(
        condition="C+P",
        c_loop_fired=True,
        c_loop_source="post_p_f2",
        c_attempt_count=2,
        c_terminal_failure_code=None,
        failure_path=[
            "initial:F1_COMPILE",
            "p_attempt:1:F2_NUMERIC_LARGE",
            "c_seed:F2_NUMERIC_LARGE",
            "c_attempt:1:F2_NUMERIC_LARGE",
            "c_attempt:2:success",
        ],
    )

    assert summary.c_attempt_count == 2


def test_c_attempt_count_zero_when_budget_zero() -> None:
    summary = _summary(
        condition="C+P",
        c_loop_fired=True,
        c_loop_source="post_p_f2",
        c_attempt_count=0,
        c_terminal_failure_code="F2_NUMERIC_LARGE",
        failure_path=[
            "initial:F1_COMPILE",
            "p_attempt:1:F2_NUMERIC_LARGE",
            "c_seed:F2_NUMERIC_LARGE",
        ],
    )

    assert summary.c_attempt_count == 0


def test_c_trace_path_length_is_attempt_count_plus_one_when_c_fires() -> None:
    summary = _summary(
        condition="C+P",
        p_loop_fired=False,
        p_attempt_count=0,
        p_terminal_failure_code=None,
        p_compile_repair_succeeded=False,
        c_loop_fired=True,
        c_loop_source="initial_f2",
        c_attempt_count=1,
        c_terminal_failure_code=None,
        failure_path=[
            "initial:F2_NUMERIC_LARGE",
            "c_seed:F2_NUMERIC_LARGE",
            "c_attempt:1:success",
        ],
    )
    c_labels = [
        label
        for label in summary.failure_path
        if label.startswith("c_seed:") or label.startswith("c_attempt:")
    ]

    assert len(c_labels) == summary.c_attempt_count + 1


def test_c_attempt_count_zero_when_c_does_not_fire() -> None:
    assert _summary(c_loop_fired=False, c_loop_source="none").c_attempt_count == 0
    with pytest.raises(ValueError, match="c_attempt_count"):
        _summary(c_loop_fired=False, c_loop_source="none", c_attempt_count=1)


def test_trace_summary_no_private_eval_data() -> None:
    serialized = _summary().to_json().lower()

    assert "eval_shape_set" not in serialized
    assert "hidden" not in serialized
    assert "private" not in serialized.replace('"private_eval_data_included"', "")
    assert "def " not in serialized
    assert "traceback" not in serialized
