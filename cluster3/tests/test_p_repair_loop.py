import hashlib

import pytest

from cluster3.constants import DEFAULT_P_REPAIR_BUDGET
from cluster3.feedback import compile_error_repair as repair
from cluster3.feedback.compile_error_repair import (
    PRepairLoopResult,
    PSeedAttempt,
    p_compile_repair_succeeded_from_result,
    run_p_repair_loop,
    stop_reason_for_status,
)
from cluster3.feedback.trace import build_p_attempt_summary


BASE_PROMPT = "Implement the relu kernel as a complete Triton Python module."
SEED_SOURCE = "def relu_kernel(x):\n    return x\n"


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _eval(
    failure_code: str | None,
    *,
    level_reached: int = 1,
    compile_success: bool | None = False,
    functional_success: bool | None = None,
    compile_error: str | None = "compiler failed",
    compile_error_type: str | None = "CompilationError",
    **extra: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "failure_code": failure_code,
        "level_reached": level_reached,
        "compile_success": compile_success,
        "functional_success": functional_success,
        "compile_error": compile_error,
        "compile_error_type": compile_error_type,
    }
    payload.update(extra)
    return payload


def _seed(**overrides: object) -> PSeedAttempt:
    prompt_value = overrides.pop("prompt", BASE_PROMPT)
    prompt = None if prompt_value is None else str(prompt_value)
    source = str(overrides.pop("source", SEED_SOURCE))
    prompt_hash_for_default_eval = _sha256(prompt or BASE_PROMPT)
    eval_result = overrides.pop(
        "evaluation_result",
        _eval(
            "F1_COMPILE",
            generation_seed=7,
            base_seed=7,
            sample_index=0,
            kernel_class="elementwise",
            kernel_name="relu",
            dtype="fp32",
            source_hash=_sha256(source),
            prompt_hash=prompt_hash_for_default_eval,
        ),
    )
    values = {
        "source": source,
        "generation_seed": 7,
        "base_seed": 7,
        "sample_index": 0,
        "kernel_class": "elementwise",
        "kernel_name": "relu",
        "dtype": "fp32",
        "source_hash": _sha256(source),
        "prompt_hash": prompt_hash_for_default_eval,
        "prompt": prompt,
        "evaluation_result": eval_result,
        "failure_code": "F1_COMPILE",
        "compile_error": "compiler failed",
        "compile_error_type": "CompilationError",
    }
    values.update(overrides)
    return PSeedAttempt(**values)  # type: ignore[arg-type]


class _GenerationRecorder:
    def __init__(self) -> None:
        self.inputs: list[object] = []

    @property
    def call_count(self) -> int:
        return len(self.inputs)

    def __call__(self, generation_input: object) -> str:
        self.inputs.append(generation_input)
        attempt_index = getattr(generation_input, "attempt_index")
        return f"def relu_kernel_{attempt_index}(x):\n    return x\n"


class _EvaluationRecorder:
    def __init__(self, *results: dict[str, object]) -> None:
        self.results = list(results)
        self.inputs: list[object] = []

    @property
    def call_count(self) -> int:
        return len(self.inputs)

    def __call__(self, evaluation_input: object) -> dict[str, object]:
        self.inputs.append(evaluation_input)
        if not self.results:
            raise AssertionError("unexpected evaluation call")
        return self.results.pop(0)


def _run_once(result: dict[str, object]) -> PRepairLoopResult:
    return run_p_repair_loop(
        base_prompt=BASE_PROMPT,
        base_seed=7,
        generation=_GenerationRecorder(),
        evaluation=_EvaluationRecorder(result),
        seed_attempt=_seed(),
        repair_budget=1,
    )


def test_p_loop_seed_attempt_does_not_call_generation_for_attempt_0() -> None:
    generation = _GenerationRecorder()
    run_p_repair_loop(
        base_prompt=BASE_PROMPT,
        base_seed=7,
        generation=generation,
        evaluation=_EvaluationRecorder(),
        seed_attempt=_seed(),
        repair_budget=0,
    )

    assert generation.call_count == 0


def test_p_loop_seed_attempt_does_not_call_evaluation_for_attempt_0() -> None:
    evaluation = _EvaluationRecorder()
    run_p_repair_loop(
        base_prompt=BASE_PROMPT,
        base_seed=7,
        generation=_GenerationRecorder(),
        evaluation=evaluation,
        seed_attempt=_seed(),
        repair_budget=0,
    )

    assert evaluation.call_count == 0


def test_p_loop_seed_attempt_records_attempt_0_in_trace() -> None:
    seed = _seed()
    result = run_p_repair_loop(
        base_prompt=BASE_PROMPT,
        base_seed=7,
        generation=_GenerationRecorder(),
        evaluation=_EvaluationRecorder(),
        seed_attempt=seed,
        repair_budget=0,
    )

    assert result.attempts[0].source_hash == _sha256(seed.source)
    assert result.attempts[0].failure_code == seed.failure_code


def test_p_loop_first_feedback_built_from_seed_attempt(monkeypatch) -> None:
    calls: list[tuple[object, ...]] = []

    def fake_builder(*args: object) -> str:
        calls.append(args)
        return f"{BASE_PROMPT}\nfeedback"

    monkeypatch.setattr(repair, "build_p_feedback_prompt", fake_builder)

    run_p_repair_loop(
        base_prompt=BASE_PROMPT,
        base_seed=7,
        generation=_GenerationRecorder(),
        evaluation=_EvaluationRecorder(
            _eval(None, level_reached=2, compile_success=True, functional_success=True)
        ),
        seed_attempt=_seed(),
        repair_budget=1,
    )

    assert calls[0][3] == "compiler failed"


def test_p_loop_status_compile_repaired_then_success() -> None:
    result = _run_once(
        _eval(None, level_reached=2, compile_success=True, functional_success=True)
    )

    assert result.status == "compile_repaired_then_success"
    assert result.successful_attempt_index == 1
    assert result.final_failure_code is None


def test_p_loop_status_compile_repaired_f2_observed() -> None:
    result = _run_once(
        _eval(
            "F2_NUMERIC_LARGE",
            level_reached=2,
            compile_success=True,
            functional_success=False,
            compile_error=None,
        )
    )

    assert result.status == "compile_repaired_f2_observed"
    assert result.final_failure_code == "F2_NUMERIC_LARGE"


def test_p_loop_status_post_p_f3_observed() -> None:
    result = _run_once(
        _eval(
            "F3_EVAL_PIPELINE",
            level_reached=2,
            compile_success=True,
            functional_success=False,
        )
    )

    assert result.status == "post_p_f3_observed"
    assert result.terminal_compile_success is True
    assert result.terminal_level_reached == 2


def test_p_loop_compile_repaired_then_success_sets_stop_reason() -> None:
    result = _run_once(
        _eval(None, level_reached=2, compile_success=True, functional_success=True)
    )

    assert result.stop_reason == "p_compile_repaired_then_success"


def test_p_loop_compile_repaired_f2_observed_sets_stop_reason() -> None:
    result = _run_once(
        _eval("F2_NUMERIC_LARGE", level_reached=2, compile_success=True)
    )

    assert result.stop_reason == "p_compile_repaired_f2_observed"


def test_p_loop_post_p_f3_with_compile_evidence_sets_post_compile_stop_reason() -> None:
    result = _run_once(
        _eval("F3_TIMEOUT", level_reached=2, compile_success=False)
    )

    assert result.stop_reason == "p_post_compile_f3_observed"


def test_p_loop_post_p_f3_without_compile_evidence_sets_no_compile_evidence_stop_reason() -> None:
    result = _run_once(
        _eval("F3_TIMEOUT", level_reached=0, compile_success=False)
    )

    assert result.stop_reason == "p_f3_without_compile_evidence"


def test_post_p_f3_without_compile_evidence_not_compile_repaired() -> None:
    result = _run_once(
        _eval("F3_TIMEOUT", level_reached=0, compile_success=False)
    )

    assert p_compile_repair_succeeded_from_result(result) is False


def test_post_p_f3_with_compile_evidence_can_mark_compile_repaired() -> None:
    result = _run_once(
        _eval("F3_TIMEOUT", level_reached=2, compile_success=False)
    )

    assert p_compile_repair_succeeded_from_result(result) is True


def test_f3_eval_pipeline_level0_does_not_set_p_compile_repair_succeeded() -> None:
    result = _run_once(
        _eval("F3_EVAL_PIPELINE", level_reached=0, compile_success=False)
    )

    assert p_compile_repair_succeeded_from_result(result) is False


def test_p_loop_status_compile_unchanged_exhausted() -> None:
    result = run_p_repair_loop(
        base_prompt=BASE_PROMPT,
        base_seed=7,
        generation=_GenerationRecorder(),
        evaluation=_EvaluationRecorder(
            _eval("F1_COMPILE"),
            _eval("F1_COMPILE"),
        ),
        seed_attempt=_seed(),
        repair_budget=2,
    )

    assert result.status == "compile_unchanged_exhausted"
    assert result.stop_reason == "p_budget_exhausted"
    assert result.attempts_executed == 3


def test_p_loop_status_terminated_unrecoverable_f0() -> None:
    result = _run_once(
        _eval("F0_PARSE", level_reached=0, compile_success=None)
    )

    assert result.status == "terminated_unrecoverable"
    assert result.stop_reason == "p_terminal_non_repairable"


def test_p_loop_status_terminated_unrecoverable_f1_runtime() -> None:
    result = _run_once(
        _eval("F1_RUNTIME", level_reached=1, compile_success=False)
    )

    assert result.status == "terminated_unrecoverable"
    assert result.stop_reason == "p_terminal_non_repairable"


def test_p_stop_reason_compile_repaired_f2_observed() -> None:
    assert (
        stop_reason_for_status(
            "compile_repaired_f2_observed",
            failure_code="F2_NUMERIC_LARGE",
            terminal_compile_success=True,
            terminal_level_reached=2,
        )
        == "p_compile_repaired_f2_observed"
    )


def test_p_stop_reason_f3_without_compile_evidence() -> None:
    assert (
        stop_reason_for_status(
            "post_p_f3_observed",
            failure_code="F3_TIMEOUT",
            terminal_compile_success=False,
            terminal_level_reached=0,
        )
        == "p_f3_without_compile_evidence"
    )


def test_p_terminal_non_repairable_uses_prefix_for_f0() -> None:
    assert (
        stop_reason_for_status(
            "terminated_unrecoverable",
            failure_code="F0_BAD_SIGNATURE",
            terminal_compile_success=None,
            terminal_level_reached=0,
        )
        == "p_terminal_non_repairable"
    )


def test_p_loop_unknown_status_rejected_before_row_construction() -> None:
    with pytest.raises(ValueError, match="unsupported P repair status"):
        PRepairLoopResult(
            status="unknown",
            attempts=(
                build_p_attempt_summary(
                    attempt_index=0,
                    generation_seed=7,
                    compile_success=False,
                    failure_code="F1_COMPILE",
                    source=SEED_SOURCE,
                ),
            ),
            attempts_executed=1,
            successful_attempt_index=None,
            repair_budget=0,
            initial_failure_code="F1_COMPILE",
            final_failure_code="F1_COMPILE",
            stop_reason="p_budget_exhausted",
            terminal_source=SEED_SOURCE,
            terminal_attempt_index=0,
            terminal_generation_seed=7,
            terminal_source_hash=_sha256(SEED_SOURCE),
            terminal_compile_success=False,
            terminal_level_reached=1,
        )


def test_p_loop_terminal_source_hash_matches_last_attempt() -> None:
    result = _run_once(
        _eval(None, level_reached=2, compile_success=True, functional_success=True)
    )

    assert result.attempts[-1].source_hash == _sha256(result.terminal_source)


def test_p_loop_rejects_budget_above_default() -> None:
    with pytest.raises(ValueError, match="repair_budget"):
        run_p_repair_loop(
            base_prompt=BASE_PROMPT,
            base_seed=7,
            generation=_GenerationRecorder(),
            evaluation=_EvaluationRecorder(),
            seed_attempt=_seed(),
            repair_budget=DEFAULT_P_REPAIR_BUDGET + 1,
        )


def test_p_loop_rejects_base_seed_mismatch() -> None:
    with pytest.raises(ValueError, match="base_seed"):
        run_p_repair_loop(
            base_prompt=BASE_PROMPT,
            base_seed=8,
            generation=_GenerationRecorder(),
            evaluation=_EvaluationRecorder(),
            seed_attempt=_seed(),
            repair_budget=0,
        )


def test_p_loop_rejects_seed_attempt_with_non_eligible_failure_code() -> None:
    with pytest.raises(ValueError, match="F1_COMPILE"):
        _seed(
            failure_code="F2_NUMERIC_LARGE",
            evaluation_result=_eval(
                "F2_NUMERIC_LARGE",
                level_reached=2,
                compile_success=True,
            ),
        )


def test_p_seed_attempt_requires_generation_seed() -> None:
    with pytest.raises(TypeError, match="generation_seed"):
        _seed(generation_seed=None)


def test_p_seed_attempt_requires_kernel_name() -> None:
    with pytest.raises(TypeError, match="kernel_name"):
        _seed(kernel_name=None)


def test_p_seed_attempt_source_hash_matches_source() -> None:
    with pytest.raises(ValueError, match="source_hash"):
        _seed(source_hash="0" * 64)


def test_p_seed_attempt_requires_prompt_hash() -> None:
    with pytest.raises(ValueError, match="prompt_hash"):
        _seed(prompt_hash="0" * 63)


def test_p_seed_attempt_rejects_missing_prompt_hash() -> None:
    with pytest.raises(ValueError, match="prompt_hash"):
        _seed(prompt_hash="")


def test_p_seed_attempt_prompt_hash_matches_prompt_when_prompt_stored() -> None:
    with pytest.raises(ValueError, match="prompt_hash"):
        _seed(prompt_hash="0" * 64)


def test_p_seed_attempt_prompt_hash_matches_prompt_metadata_when_prompt_not_stored() -> None:
    prompt_hash = _sha256(BASE_PROMPT)
    seed = _seed(
        prompt=None,
        prompt_hash=prompt_hash,
        evaluation_result=_eval(
            "F1_COMPILE",
            generation_seed=7,
            base_seed=7,
            sample_index=0,
            kernel_class="elementwise",
            kernel_name="relu",
            dtype="fp32",
            source_hash=_sha256(SEED_SOURCE),
            prompt_hash=prompt_hash,
        ),
    )

    assert seed.prompt_hash == prompt_hash


def test_p_seed_attempt_requires_prompt_hash_metadata_when_prompt_not_stored() -> None:
    with pytest.raises(ValueError, match="prompt_hash metadata"):
        _seed(
            prompt=None,
            prompt_hash=_sha256(BASE_PROMPT),
            evaluation_result=_eval("F1_COMPILE"),
        )


def test_p_seed_attempt_identity_matches_parent_row() -> None:
    _seed(
        evaluation_result=_eval(
            "F1_COMPILE",
            identity={
                "generation_seed": 7,
                "base_seed": 7,
                "sample_index": 0,
                "kernel_class": "elementwise",
                "kernel_name": "relu",
                "dtype": "fp32",
            },
        )
    )
    with pytest.raises(ValueError, match="kernel_name"):
        _seed(
            evaluation_result=_eval(
                "F1_COMPILE",
                identity={
                    "generation_seed": 7,
                    "base_seed": 7,
                    "sample_index": 0,
                    "kernel_class": "elementwise",
                    "kernel_name": "softmax",
                    "dtype": "fp32",
                },
            )
        )


def test_p_seed_attempt_rejects_f1_without_compile_error_evidence() -> None:
    with pytest.raises(ValueError, match="compile-failure evidence"):
        _seed(
            compile_error=None,
            compile_error_type=None,
            evaluation_result=_eval(
                "F1_COMPILE",
                compile_error=None,
                compile_error_type=None,
            ),
        )


def test_p_seed_attempt_rejects_failure_code_eval_result_mismatch() -> None:
    with pytest.raises(ValueError, match="failure_code"):
        _seed(evaluation_result=_eval("F0_PARSE", level_reached=0, compile_success=None))


def test_p_loop_passes_previous_feedback_to_generation(monkeypatch) -> None:
    feedbacks: list[str] = []

    def fake_builder(
        base_prompt: str,
        candidate_source: str | None,
        failure_code: str | None,
        compile_error: str | None,
        compile_error_type: str | None,
    ) -> str:
        del candidate_source, failure_code, compile_error_type
        feedback = f"{base_prompt}\nfeedback from {compile_error}"
        feedbacks.append(feedback)
        return feedback

    monkeypatch.setattr(repair, "build_p_feedback_prompt", fake_builder)
    generation = _GenerationRecorder()
    run_p_repair_loop(
        base_prompt=BASE_PROMPT,
        base_seed=7,
        generation=generation,
        evaluation=_EvaluationRecorder(
            _eval("F1_COMPILE", compile_error="attempt one failed"),
            _eval(None, level_reached=2, compile_success=True, functional_success=True),
        ),
        seed_attempt=_seed(),
        repair_budget=2,
    )

    assert getattr(generation.inputs[0], "previous_feedback") == feedbacks[0]
    assert getattr(generation.inputs[1], "previous_feedback") == feedbacks[1]
