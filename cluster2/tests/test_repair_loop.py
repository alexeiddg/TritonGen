"""Phase 9 tests for sequential Cluster 2 repair-loop orchestration."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from cluster2.constants import DEFAULT_REPAIR_BUDGET
from cluster2.feedback.prompts import FORBIDDEN_FEEDBACK_TERMS
from cluster2.feedback.repair_loop import (
    REPAIR_LOOP_EXHAUSTED_STATUS,
    REPAIR_LOOP_SUCCESS_STATUS,
    REPAIR_LOOP_TERMINATED_STATUS,
    RepairEvaluationInput,
    RepairFeedbackInput,
    RepairGenerationInput,
    run_repair_loop,
    seed_for_attempt,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
REPAIR_LOOP_PATH = REPO_ROOT / "cluster2" / "feedback" / "repair_loop.py"
BASE_PROMPT = "Implement the relu kernel as a complete Triton Python module."


def test_repair_loop_rejects_none() -> None:
    calls: list[RepairGenerationInput] = []

    with pytest.raises(ValueError, match="must not invoke C2 generation"):
        run_repair_loop(
            condition="none",
            base_prompt=BASE_PROMPT,
            base_seed=11,
            generation=lambda request: calls.append(request) or _source(0),
            evaluation=_successful_evaluation,
        )

    assert calls == []


def test_repair_loop_rejects_g() -> None:
    calls: list[RepairGenerationInput] = []

    with pytest.raises(ValueError, match="must not invoke C2 generation"):
        run_repair_loop(
            condition="G",
            base_prompt=BASE_PROMPT,
            base_seed=11,
            generation=lambda request: calls.append(request) or _source(0),
            evaluation=_successful_evaluation,
        )

    assert calls == []


@pytest.mark.parametrize("condition", ("C", "G+C"))
def test_repair_loop_accepts_generated_conditions(condition: str) -> None:
    result = run_repair_loop(
        condition=condition,
        base_prompt=BASE_PROMPT,
        base_seed=7,
        generation=lambda request: _source(request.attempt_index),
        evaluation=_successful_evaluation,
    )

    assert result.condition == condition
    assert result.status == REPAIR_LOOP_SUCCESS_STATUS
    assert result.successful_attempt_index == 0


def test_iteration_zero_success_generates_exactly_one_attempt() -> None:
    generation_calls: list[RepairGenerationInput] = []
    evaluation_calls: list[RepairEvaluationInput] = []

    def generation(request: RepairGenerationInput) -> str:
        generation_calls.append(request)
        return _source(request.attempt_index)

    def evaluation(request: RepairEvaluationInput) -> object:
        evaluation_calls.append(request)
        return _success()

    result = run_repair_loop(
        condition="C",
        base_prompt=BASE_PROMPT,
        base_seed=5,
        generation=generation,
        evaluation=evaluation,
        repair_budget=DEFAULT_REPAIR_BUDGET,
    )

    assert result.status == REPAIR_LOOP_SUCCESS_STATUS
    assert result.attempts_executed == 1
    assert [call.attempt_index for call in generation_calls] == [0]
    assert [call.attempt_index for call in evaluation_calls] == [0]


def test_seed_candidate_bypasses_only_initial_generation() -> None:
    generation_calls: list[RepairGenerationInput] = []
    evaluation_calls: list[RepairEvaluationInput] = []
    seed_source = "seed_candidate_source"

    def generation(request: RepairGenerationInput) -> str:
        generation_calls.append(request)
        return _source(request.attempt_index)

    def evaluation(request: RepairEvaluationInput) -> object:
        evaluation_calls.append(request)
        if request.attempt_index == 0:
            assert request.source == seed_source
            return _failure(request.attempt_index)
        assert request.source == _source(request.attempt_index)
        return _success()

    result = run_repair_loop(
        condition="C",
        base_prompt=BASE_PROMPT,
        base_seed=5,
        generation=generation,
        evaluation=evaluation,
        repair_budget=2,
        seed_candidate_source=seed_source,
    )

    assert result.status == REPAIR_LOOP_SUCCESS_STATUS
    assert result.successful_attempt_index == 1
    assert [call.attempt_index for call in generation_calls] == [1]
    assert generation_calls[0].previous_feedback is not None
    assert [call.attempt_index for call in evaluation_calls] == [0, 1]
    assert [attempt.attempt_index for attempt in result.attempts] == [0, 1]


def test_seed_candidate_f0_f1_failure_still_terminates_without_feedback() -> None:
    generation_calls: list[RepairGenerationInput] = []
    feedback_calls: list[RepairFeedbackInput] = []

    result = run_repair_loop(
        condition="C",
        base_prompt=BASE_PROMPT,
        base_seed=5,
        generation=lambda request: generation_calls.append(request) or _source(
            request.attempt_index
        ),
        evaluation=lambda request: _failure(
            request.attempt_index,
            failure_code="F1_COMPILE",
            summary="compile failed publicly",
            level_reached=1,
        ),
        feedback_builder=lambda inputs: feedback_calls.append(inputs)
        or _custom_feedback_prompt(inputs, "should-not-be-built"),
        repair_budget=2,
        seed_candidate_source="seed_candidate_source",
    )

    assert result.status == REPAIR_LOOP_TERMINATED_STATUS
    assert result.attempts_executed == 1
    assert result.final_failure_code == "F1_COMPILE"
    assert generation_calls == []
    assert feedback_calls == []


def test_stops_immediately_after_success() -> None:
    generation_calls: list[RepairGenerationInput] = []

    def generation(request: RepairGenerationInput) -> str:
        generation_calls.append(request)
        return _source(request.attempt_index)

    def evaluation(request: RepairEvaluationInput) -> object:
        return _success() if request.attempt_index == 2 else _failure(request.attempt_index)

    result = run_repair_loop(
        condition="G+C",
        base_prompt=BASE_PROMPT,
        base_seed=13,
        generation=generation,
        evaluation=evaluation,
        repair_budget=5,
    )

    assert result.status == REPAIR_LOOP_SUCCESS_STATUS
    assert result.successful_attempt_index == 2
    assert result.attempts_executed == 3
    assert [call.attempt_index for call in generation_calls] == [0, 1, 2]


def test_exhaustion_generates_repair_budget_plus_one_attempts() -> None:
    generation_calls: list[RepairGenerationInput] = []

    def generation(request: RepairGenerationInput) -> str:
        generation_calls.append(request)
        return _source(request.attempt_index)

    result = run_repair_loop(
        condition="C",
        base_prompt=BASE_PROMPT,
        base_seed=3,
        generation=generation,
        evaluation=lambda request: _failure(
            request.attempt_index,
            failure_code="F2_SHAPE_MISMATCH",
            summary=f"Repair shape failed at attempt {request.attempt_index}",
        ),
        repair_budget=2,
    )

    assert result.status == REPAIR_LOOP_EXHAUSTED_STATUS
    assert result.successful_attempt_index is None
    assert result.attempts_executed == 3
    assert len(generation_calls) == 3
    assert result.final_failure_code == "F2_SHAPE_MISMATCH"
    assert result.final_public_failure_summary == "Repair shape failed at attempt 2"


@pytest.mark.parametrize(
    ("failure_code", "level_reached"),
    (
        ("F0_PARSE", 0),
        ("F0_BAD_SIGNATURE", 0),
        ("F1_COMPILE", 1),
        ("F1_RUNTIME", 1),
        ("F3_OOB", 3),
    ),
)
def test_non_f2_failures_terminate_without_feedback_or_repair_generation(
    failure_code: str,
    level_reached: int,
) -> None:
    generation_calls: list[RepairGenerationInput] = []
    feedback_calls: list[RepairFeedbackInput] = []
    summary = f"public summary for {failure_code}"

    def generation(request: RepairGenerationInput) -> str:
        generation_calls.append(request)
        return _source(request.attempt_index)

    def feedback_builder(inputs: RepairFeedbackInput) -> str:
        feedback_calls.append(inputs)
        return _custom_feedback_prompt(inputs, "should-not-be-built")

    result = run_repair_loop(
        condition="C",
        base_prompt=BASE_PROMPT,
        base_seed=6,
        generation=generation,
        evaluation=lambda request: _failure(
            request.attempt_index,
            failure_code=failure_code,
            summary=summary,
            level_reached=level_reached,
        ),
        feedback_builder=feedback_builder,
        repair_budget=3,
    )

    assert result.status == REPAIR_LOOP_TERMINATED_STATUS
    assert result.attempts_executed == 1
    assert result.final_failure_code == failure_code
    assert result.final_public_failure_summary == summary
    assert [call.attempt_index for call in generation_calls] == [0]
    assert feedback_calls == []
    assert [trace.attempt_index for trace in result.trace_summaries] == [0]


@pytest.mark.parametrize(
    ("failure_code", "level_reached", "detail_field", "summary"),
    (
        ("F0_BAD_SIGNATURE", 0, "signature_error", "launcher signature mismatch"),
        ("F1_COMPILE", 1, "compile_error", "Triton compile failed publicly"),
        ("F0_SURFACE_VIOLATION", 0, "sanitizer_errors", "surface violation summary"),
    ),
)
def test_non_f2_termination_preserves_level0_level1_public_details(
    failure_code: str,
    level_reached: int,
    detail_field: str,
    summary: str,
) -> None:
    generation_calls: list[RepairGenerationInput] = []
    feedback_calls: list[RepairFeedbackInput] = []

    def generation(request: RepairGenerationInput) -> str:
        generation_calls.append(request)
        return _source(request.attempt_index)

    def feedback_builder(inputs: RepairFeedbackInput) -> str:
        feedback_calls.append(inputs)
        return _custom_feedback_prompt(inputs, "should-not-be-built")

    detail_payload = (
        {detail_field: (summary,)}
        if detail_field == "sanitizer_errors"
        else {detail_field: summary}
    )

    result = run_repair_loop(
        condition="C",
        base_prompt=BASE_PROMPT,
        base_seed=6,
        generation=generation,
        evaluation=lambda request: SimpleNamespace(
            functional_success=False,
            level_reached=level_reached,
            failure_code=failure_code,
            repair_set_success=False,
            eval_set_success=False,
            **detail_payload,
        ),
        feedback_builder=feedback_builder,
        repair_budget=3,
    )

    assert result.status == REPAIR_LOOP_TERMINATED_STATUS
    assert result.attempts_executed == 1
    assert result.final_failure_code == failure_code
    assert result.final_public_failure_summary == summary
    assert result.attempts[0].public_failure_summary == summary
    assert result.trace_summaries[0].public_failure_summary == summary
    assert [call.attempt_index for call in generation_calls] == [0]
    assert feedback_calls == []


def test_level_below_two_terminates_even_with_allowed_f2_failure_code() -> None:
    generation_calls: list[RepairGenerationInput] = []
    feedback_calls: list[RepairFeedbackInput] = []

    def generation(request: RepairGenerationInput) -> str:
        generation_calls.append(request)
        return _source(request.attempt_index)

    def feedback_builder(inputs: RepairFeedbackInput) -> str:
        feedback_calls.append(inputs)
        return _custom_feedback_prompt(inputs, "should-not-be-built")

    result = run_repair_loop(
        condition="C",
        base_prompt=BASE_PROMPT,
        base_seed=6,
        generation=generation,
        evaluation=lambda request: _failure(
            request.attempt_index,
            failure_code="F2_NUMERIC_LARGE",
            level_reached=1,
        ),
        feedback_builder=feedback_builder,
        repair_budget=3,
    )

    assert result.status == REPAIR_LOOP_TERMINATED_STATUS
    assert result.attempts_executed == 1
    assert result.final_failure_code == "F2_NUMERIC_LARGE"
    assert [call.attempt_index for call in generation_calls] == [0]
    assert feedback_calls == []


@pytest.mark.parametrize(
    "failure_code",
    ("F2_NUMERIC_LARGE", "F2_NUMERIC_NAN", "F2_SHAPE_MISMATCH"),
)
def test_allowed_f2_failures_trigger_correctness_feedback(
    failure_code: str,
) -> None:
    generation_calls: list[RepairGenerationInput] = []
    feedback_calls: list[RepairFeedbackInput] = []

    def generation(request: RepairGenerationInput) -> str:
        generation_calls.append(request)
        return _source(request.attempt_index)

    def evaluation(request: RepairEvaluationInput) -> object:
        if request.attempt_index == 1:
            return _success()
        return _failure(
            request.attempt_index,
            failure_code=failure_code,
            level_reached=2,
        )

    def feedback_builder(inputs: RepairFeedbackInput) -> str:
        feedback_calls.append(inputs)
        return _custom_feedback_prompt(
            inputs,
            f"correctness_error:{inputs.public_failure_summary}",
        )

    result = run_repair_loop(
        condition="C",
        base_prompt=BASE_PROMPT,
        base_seed=6,
        generation=generation,
        evaluation=evaluation,
        feedback_builder=feedback_builder,
        repair_budget=3,
    )

    assert result.status == REPAIR_LOOP_SUCCESS_STATUS
    assert [call.attempt_index for call in generation_calls] == [0, 1]
    assert [call.attempt_index for call in feedback_calls] == [0]
    assert feedback_calls[0].failure_code == failure_code
    assert feedback_calls[0].compile_error is None
    assert feedback_calls[0].signature_error is None
    assert feedback_calls[0].sanitizer_errors == ()
    assert "correctness_error:" in generation_calls[1].prompt


def test_repair_loop_rejects_repair_budget_above_phase9_maximum() -> None:
    calls: list[RepairGenerationInput] = []

    with pytest.raises(ValueError, match="repair_budget must be <= 5"):
        run_repair_loop(
            condition="C",
            base_prompt=BASE_PROMPT,
            base_seed=11,
            generation=lambda request: calls.append(request) or _source(0),
            evaluation=_successful_evaluation,
            repair_budget=DEFAULT_REPAIR_BUDGET + 1,
        )

    assert calls == []


def test_seed_schedule_uses_base_seed_times_ten_plus_attempt_index() -> None:
    generation_calls: list[RepairGenerationInput] = []

    def generation(request: RepairGenerationInput) -> str:
        generation_calls.append(request)
        return _source(request.attempt_index)

    run_repair_loop(
        condition="C",
        base_prompt=BASE_PROMPT,
        base_seed=17,
        generation=generation,
        evaluation=lambda request: _failure(request.attempt_index),
        repair_budget=3,
    )

    assert [call.generation_seed for call in generation_calls] == [170, 171, 172, 173]
    assert [seed_for_attempt(17, i) for i in range(4)] == [170, 171, 172, 173]


def test_feedback_from_attempt_i_is_passed_to_attempt_i_plus_one() -> None:
    generation_calls: list[RepairGenerationInput] = []
    feedback_calls: list[RepairFeedbackInput] = []

    def generation(request: RepairGenerationInput) -> str:
        generation_calls.append(request)
        return _source(request.attempt_index)

    def feedback_builder(inputs: RepairFeedbackInput) -> str:
        feedback_calls.append(inputs)
        return _custom_feedback_prompt(
            inputs,
            f"feedback-from-{inputs.attempt_index}:{inputs.public_failure_summary}",
        )

    result = run_repair_loop(
        condition="C",
        base_prompt=BASE_PROMPT,
        base_seed=2,
        generation=generation,
        evaluation=lambda request: (
            _success() if request.attempt_index == 2 else _failure(request.attempt_index)
        ),
        feedback_builder=feedback_builder,
        repair_budget=5,
    )

    assert result.status == REPAIR_LOOP_SUCCESS_STATUS
    prompt_1 = _custom_feedback_prompt(
        feedback_calls[0],
        "feedback-from-0:Repair shape failed at attempt 0",
    )
    prompt_2 = _custom_feedback_prompt(
        feedback_calls[1],
        "feedback-from-1:Repair shape failed at attempt 1",
    )
    assert [call.prompt for call in generation_calls] == [
        BASE_PROMPT,
        prompt_1,
        prompt_2,
    ]
    assert [call.previous_feedback for call in generation_calls] == [
        None,
        prompt_1,
        prompt_2,
    ]
    assert [call.attempt_index for call in feedback_calls] == [0, 1]


def test_feedback_builder_receives_public_sanitized_fields_only() -> None:
    feedback_inputs: list[RepairFeedbackInput] = []
    generation_calls: list[RepairGenerationInput] = []

    def generation(request: RepairGenerationInput) -> str:
        generation_calls.append(request)
        return _source(request.attempt_index)

    def evaluation(request: RepairEvaluationInput) -> object:
        if request.attempt_index == 0:
            return SimpleNamespace(
                functional_success=False,
                level_reached=2,
                failure_code="F2_NUMERIC_LARGE",
                correctness_error=(
                    "Repair shape failed; eval_shape_set shape (97,) hidden private "
                    "edge cases extra shapes token timing performance speedup"
                ),
                private_eval_details="shape (97,) max_abs_diff=99",
                repair_set_success=False,
                eval_set_success=False,
            )
        return _success()

    def feedback_builder(inputs: RepairFeedbackInput) -> str:
        feedback_inputs.append(inputs)
        return _custom_feedback_prompt(
            inputs,
            f"public-feedback:{inputs.public_failure_summary}",
        )

    run_repair_loop(
        condition="C",
        base_prompt=BASE_PROMPT,
        base_seed=4,
        generation=generation,
        evaluation=evaluation,
        feedback_builder=feedback_builder,
        repair_budget=3,
    )

    assert len(feedback_inputs) == 1
    feedback_input = feedback_inputs[0]
    assert not hasattr(feedback_input, "private_eval_details")
    assert "97" not in str(feedback_input.public_failure_summary)
    assert "eval_shape_set" not in str(feedback_input.public_failure_summary)
    _assert_no_forbidden_terms(str(feedback_input.public_failure_summary))
    assert BASE_PROMPT in generation_calls[1].prompt
    assert "97" not in generation_calls[1].prompt
    _assert_no_forbidden_terms(generation_calls[1].prompt)


def test_default_feedback_prompt_is_correctness_only() -> None:
    generation_calls: list[RepairGenerationInput] = []

    def generation(request: RepairGenerationInput) -> str:
        generation_calls.append(request)
        return _source(request.attempt_index)

    def evaluation(request: RepairEvaluationInput) -> object:
        if request.attempt_index == 0:
            return SimpleNamespace(
                functional_success=False,
                level_reached=2,
                failure_code="F2_NUMERIC_LARGE",
                correctness_error="Repair shape failed at attempt 0",
                compile_error="compile failure details must not be feedback",
                signature_error="signature failure details must not be feedback",
                sanitizer_errors=("sanitizer details must not be feedback",),
                repair_set_success=False,
                eval_set_success=True,
            )
        return _success()

    result = run_repair_loop(
        condition="C",
        base_prompt=BASE_PROMPT,
        base_seed=4,
        generation=generation,
        evaluation=evaluation,
        repair_budget=2,
    )

    assert result.status == REPAIR_LOOP_SUCCESS_STATUS
    repair_prompt = generation_calls[1].prompt
    assert "Repair shape failed at attempt 0" in repair_prompt
    assert "compile failure details" not in repair_prompt
    assert "signature failure details" not in repair_prompt
    assert "sanitizer details" not in repair_prompt
    assert "feedback_type" not in result.to_json()
    assert "compile_error" not in result.to_json()
    assert "signature_error" not in result.to_json()


def test_default_feedback_handoff_does_not_pass_private_eval_details() -> None:
    generation_calls: list[RepairGenerationInput] = []

    def generation(request: RepairGenerationInput) -> str:
        generation_calls.append(request)
        return _source(request.attempt_index)

    def evaluation(request: RepairEvaluationInput) -> object:
        if request.attempt_index == 0:
            return SimpleNamespace(
                functional_success=False,
                level_reached=2,
                failure_code="F2_NUMERIC_LARGE",
                correctness_error=(
                    "eval_shape_set shape (97,) max_abs_diff=99 hidden private "
                    "edge cases extra shapes"
                ),
                private_eval_details="secret eval shape (97,)",
                repair_set_success=True,
                eval_set_success=False,
            )
        return _success()

    run_repair_loop(
        condition="G+C",
        base_prompt=BASE_PROMPT,
        base_seed=9,
        generation=generation,
        evaluation=evaluation,
        repair_budget=2,
    )

    repair_prompt = generation_calls[1].prompt
    assert "97" not in repair_prompt
    assert "max_abs_diff=99" not in repair_prompt
    assert "secret eval shape" not in repair_prompt
    _assert_no_forbidden_terms(repair_prompt)


def test_feedback_handoff_rejects_injected_forbidden_terms() -> None:
    generation_calls: list[RepairGenerationInput] = []

    def generation(request: RepairGenerationInput) -> str:
        generation_calls.append(request)
        return _source(request.attempt_index)

    def unsafe_feedback_builder(_: RepairFeedbackInput) -> str:
        return "Feedback: private eval_shape_set shape (97,) leaked"

    with pytest.raises(ValueError, match="forbidden term"):
        run_repair_loop(
            condition="C",
            base_prompt=BASE_PROMPT,
            base_seed=9,
            generation=generation,
            evaluation=lambda request: _failure(request.attempt_index),
            feedback_builder=unsafe_feedback_builder,
            repair_budget=2,
        )

    assert [call.attempt_index for call in generation_calls] == [0]


def test_feedback_handoff_rejects_injected_prompt_without_base_prompt() -> None:
    generation_calls: list[RepairGenerationInput] = []

    def generation(request: RepairGenerationInput) -> str:
        generation_calls.append(request)
        return _source(request.attempt_index)

    def incomplete_feedback_builder(inputs: RepairFeedbackInput) -> str:
        return f"Feedback: {inputs.public_failure_summary}"

    with pytest.raises(ValueError, match="base_prompt verbatim"):
        run_repair_loop(
            condition="G+C",
            base_prompt=BASE_PROMPT,
            base_seed=9,
            generation=generation,
            evaluation=lambda request: _failure(request.attempt_index),
            feedback_builder=incomplete_feedback_builder,
            repair_budget=2,
        )

    assert [call.attempt_index for call in generation_calls] == [0]


def test_feedback_handoff_preserves_locked_base_prompt_wording() -> None:
    base_prompt = (
        "Base task requiring the canonical surface. "
        "Private Triton helper name is part of the locked prompt."
    )
    generation_calls: list[RepairGenerationInput] = []

    def generation(request: RepairGenerationInput) -> str:
        generation_calls.append(request)
        return _source(request.attempt_index)

    result = run_repair_loop(
        condition="G+C",
        base_prompt=base_prompt,
        base_seed=10,
        generation=generation,
        evaluation=lambda request: (
            _success() if request.attempt_index == 1 else _failure(request.attempt_index)
        ),
        repair_budget=2,
    )

    assert result.status == REPAIR_LOOP_SUCCESS_STATUS
    assert base_prompt in generation_calls[1].prompt


def test_trace_summaries_exclude_source_by_default() -> None:
    source = "candidate_source_attempt_0"
    result = run_repair_loop(
        condition="C",
        base_prompt=BASE_PROMPT,
        base_seed=1,
        generation=lambda request: source,
        evaluation=lambda request: _failure(request.attempt_index),
        repair_budget=0,
    )

    trace_payload = result.trace_summaries[0].to_dict()
    rendered = json.dumps(trace_payload, sort_keys=True)

    assert "source" not in trace_payload
    assert "source_hash" in trace_payload
    assert source not in rendered


def test_trace_summaries_exclude_timing_performance_and_token_fields() -> None:
    result = run_repair_loop(
        condition="C",
        base_prompt=BASE_PROMPT,
        base_seed=1,
        generation=lambda request: _source(request.attempt_index),
        evaluation=lambda request: _failure(
            request.attempt_index,
            summary=(
                "token timing performance speedup profile benchmark "
                "eval_shape_set hidden private edge cases extra shapes"
            ),
        ),
        repair_budget=1,
    )

    rendered = result.to_json().lower()
    for forbidden_key in (
        "tokens_input",
        "tokens_output",
        "timing",
        "performance",
        "speedup",
        "profile",
        "benchmark",
    ):
        assert forbidden_key not in rendered
    assert "source" not in _all_keys(result.trace_summaries[0].to_dict())
    _assert_no_forbidden_terms(rendered)


def test_repair_loop_module_requires_no_modal_or_generation_runtime_imports() -> None:
    imported_modules = _imported_modules(REPAIR_LOOP_PATH)
    forbidden_imports = (
        "cluster2.modal",
        "cluster2.generation",
        "cluster2.validation",
        "shared.modal_harness",
        "modal",
        "torch",
        "triton",
        "transformers",
        "xgrammar",
    )
    leaked = sorted(
        module
        for module in imported_modules
        if any(
            module == forbidden or module.startswith(f"{forbidden}.")
            for forbidden in forbidden_imports
        )
    )
    source = REPAIR_LOOP_PATH.read_text(encoding="utf-8")

    assert leaked == []
    assert "RemoteGenerator" not in source
    assert "RemoteC2Generator" not in source
    assert ".remote" not in source


def test_repair_loop_output_is_deterministic_for_same_callables_and_seed() -> None:
    def run_once() -> str:
        return run_repair_loop(
            condition="G+C",
            base_prompt=BASE_PROMPT,
            base_seed=8,
            generation=lambda request: _source(request.attempt_index),
            evaluation=lambda request: (
                _success() if request.attempt_index == 1 else _failure(0)
            ),
            repair_budget=4,
        ).to_json()

    assert run_once() == run_once()


def _source(attempt_index: int) -> str:
    return f"candidate_source_attempt_{attempt_index}"


def _success() -> SimpleNamespace:
    return SimpleNamespace(
        functional_success=True,
        level_reached=2,
        failure_code=None,
        correctness_error=None,
        repair_set_success=True,
        eval_set_success=True,
    )


def _failure(
    attempt_index: int,
    *,
    failure_code: str = "F2_NUMERIC_LARGE",
    summary: str | None = None,
    level_reached: int | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        functional_success=False,
        level_reached=level_reached,
        failure_code=failure_code,
        correctness_error=summary or f"Repair shape failed at attempt {attempt_index}",
        repair_set_success=False,
        eval_set_success=True,
    )


def _successful_evaluation(_: RepairEvaluationInput) -> object:
    return _success()


def _custom_feedback_prompt(inputs: RepairFeedbackInput, feedback: str) -> str:
    return (
        f"Base task:\n{inputs.base_prompt}\n\n"
        f"Feedback:\n{feedback}\n\n"
        "Instruction:\nProduce a corrected complete Triton Python module."
    )


def _assert_no_forbidden_terms(value: str) -> None:
    lowered = value.lower()
    for term in FORBIDDEN_FEEDBACK_TERMS:
        assert term.lower() not in lowered


def _all_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            keys.add(str(key))
            keys.update(_all_keys(nested))
    elif isinstance(value, list | tuple):
        for nested in value:
            keys.update(_all_keys(nested))
    return keys


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
    return modules
