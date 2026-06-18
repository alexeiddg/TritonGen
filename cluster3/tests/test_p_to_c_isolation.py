from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest

from cluster2.feedback.repair_loop import RepairFeedbackInput
from cluster3.experiments.run_cluster3_modal import (
    Cluster3RunnerConfig,
    RunnerDependencies,
    run_cluster3,
)
from cluster3.feedback.c_loop_adapter import run_cluster3_c_loop_from_f2


REV_A = "a" * 40
REV_B = "b" * 40
BASE_PROMPT = "Implement relu."
INITIAL_SOURCE = "def a4_seed_source(x):\n    return x\n"
P_TERMINAL_SOURCE = "def a4_post_p_seed_source(x):\n    return x\n"
C_TERMINAL_SOURCE = "def a4_c_terminal_source(x):\n    return x\n"
P_TERMINAL_SOURCE_IN_C_PROMPT = "def a4_post_p_seed_source(x): return x"
P_COMPILE_ERROR_TEXT = "A4 compiler failed sentinel wrong_launch_grid_17"
P_COMPILE_ERROR_TYPE = "A4CompileSentinelError"
C_PUBLIC_FAILURE_SUMMARY = "A4 C public numeric mismatch on repair shapes"
INITIAL_C_PUBLIC_FAILURE_SUMMARY = "A4 initial F2 public numeric mismatch"


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _config(
    tmp_path: Path,
    *,
    condition: str = "C+P",
    repair_history_policy: str = "last_attempt_only_v1",
    p_repair_budget: int = 1,
    c_repair_budget: int = 1,
) -> Cluster3RunnerConfig:
    return Cluster3RunnerConfig(
        condition=condition,
        output=str(tmp_path / f"{condition.replace('+', '_')}.jsonl"),
        model_revision=REV_A,
        tokenizer_revision=REV_B,
        n=1,
        kernel_class="elementwise",
        dtypes=("fp32",),
        repair_history_policy=repair_history_policy,
        p_repair_budget=p_repair_budget,
        c_repair_budget=c_repair_budget,
    )


def _result(
    failure_code: str | None,
    *,
    level_reached: int = 2,
    compile_success: bool | None = None,
    functional_success: bool | None = None,
    repair_set_success: bool | None = None,
    eval_set_success: bool | None = None,
    compile_error: str | None = None,
    compile_error_type: str | None = None,
    correctness_error: str | None = None,
) -> dict[str, Any]:
    if failure_code is None:
        compile_success = True if compile_success is None else compile_success
        functional_success = True if functional_success is None else functional_success
        repair_set_success = True if repair_set_success is None else repair_set_success
        eval_set_success = True if eval_set_success is None else eval_set_success
    else:
        if compile_success is None:
            compile_success = failure_code.startswith(("F2_", "F3_"))
        functional_success = False if functional_success is None else functional_success
        repair_set_success = False if repair_set_success is None else repair_set_success
        eval_set_success = False if eval_set_success is None else eval_set_success
    return {
        "failure_code": failure_code,
        "level_reached": level_reached,
        "compile_success": compile_success,
        "functional_success": functional_success,
        "repair_set_success": repair_set_success,
        "eval_set_success": eval_set_success,
        "compile_error": compile_error,
        "compile_error_type": compile_error_type,
        "correctness_error": correctness_error,
    }


def _f1_compile_result(
    *,
    compile_error: str = P_COMPILE_ERROR_TEXT,
    compile_error_type: str = P_COMPILE_ERROR_TYPE,
) -> dict[str, Any]:
    return _result(
        "F1_COMPILE",
        level_reached=1,
        compile_success=False,
        compile_error=compile_error,
        compile_error_type=compile_error_type,
    )


def _f1_runtime_result() -> dict[str, Any]:
    return _result("F1_RUNTIME", level_reached=1, compile_success=False)


def _f2_result(*, summary: str = C_PUBLIC_FAILURE_SUMMARY) -> dict[str, Any]:
    return _result(
        "F2_NUMERIC_LARGE",
        level_reached=2,
        compile_success=True,
        functional_success=False,
        repair_set_success=False,
        eval_set_success=False,
        correctness_error=summary,
    )


def _success_result() -> dict[str, Any]:
    return _result(None)


class SequencedGeneration:
    def __init__(self, sources: tuple[str, ...]) -> None:
        self.sources = list(sources)
        self.calls: list[dict[str, Any]] = []

    def __call__(self, **kwargs: Any) -> dict[str, str]:
        self.calls.append(kwargs)
        if not self.sources:
            raise AssertionError("unexpected generation call")
        return {"source": self.sources.pop(0)}


class SequencedCorrectness:
    def __init__(self, results: tuple[dict[str, Any], ...]) -> None:
        self.results = list(results)
        self.calls: list[Any] = []

    def __call__(self, request: Any) -> dict[str, Any]:
        self.calls.append(request)
        if not self.results:
            raise AssertionError("unexpected correctness call")
        return dict(self.results.pop(0))


def _run_cluster3_with_sequences(
    tmp_path: Path,
    *,
    condition: str = "C+P",
    repair_history_policy: str = "last_attempt_only_v1",
    generation_sources: tuple[str, ...],
    correctness_results: tuple[dict[str, Any], ...],
    p_repair_budget: int = 1,
    c_repair_budget: int = 1,
) -> tuple[Any, SequencedGeneration, SequencedCorrectness]:
    generation = SequencedGeneration(generation_sources)
    correctness = SequencedCorrectness(correctness_results)
    run = run_cluster3(
        _config(
            tmp_path,
            condition=condition,
            repair_history_policy=repair_history_policy,
            p_repair_budget=p_repair_budget,
            c_repair_budget=c_repair_budget,
        ),
        dependencies=RunnerDependencies(
            generation=generation,
            correctness=correctness,
        ),
    )
    return run, generation, correctness


def _adapter_call(
    *,
    c_loop_source: str = "post_p_f2",
    seed_candidate_evaluation: dict[str, Any] | None = None,
    feedback_builder: Any = None,
    generation: Any | None = None,
    correctness: Any | None = None,
) -> Any:
    seed_prompt_hash_source = (
        "p_repair_prompt" if c_loop_source == "post_p_f2" else "initial_prompt"
    )
    seed_prompt_text = "p repair prompt" if c_loop_source == "post_p_f2" else BASE_PROMPT
    return run_cluster3_c_loop_from_f2(
        outer_c3_condition="C+P",
        c_loop_source=c_loop_source,  # type: ignore[arg-type]
        base_prompt=BASE_PROMPT,
        base_seed=0,
        sample_index=0,
        kernel_class="elementwise",
        kernel_name="relu",
        dtype="fp32",
        seed_candidate_source=P_TERMINAL_SOURCE,
        seed_candidate_generation_seed=1,
        seed_candidate_prompt_hash=_sha(seed_prompt_text),
        seed_candidate_prompt_hash_source=seed_prompt_hash_source,  # type: ignore[arg-type]
        seed_candidate_evaluation=seed_candidate_evaluation or _f2_result(),
        feedback_builder=feedback_builder,
        repair_budget=1,
        model_config={
            "generation": generation
            or (lambda **_: {"source": C_TERMINAL_SOURCE}),
            "correctness": correctness or (lambda request: _success_result()),
            "model_id": "model",
            "model_revision": REV_A,
            "tokenizer_revision": REV_B,
            "temperature": 0.2,
            "max_new_tokens": 1536,
        },
        provenance_base={"run_id": "a4-isolation"},
    )


def test_post_p_f2_c_prompt_excludes_p_compile_history_text_and_hashes(
    tmp_path: Path,
) -> None:
    run, generation, correctness = _run_cluster3_with_sequences(
        tmp_path,
        repair_history_policy="agentic_transcript_v1",
        generation_sources=(
            INITIAL_SOURCE,
            P_TERMINAL_SOURCE,
            C_TERMINAL_SOURCE,
        ),
        correctness_results=(
            _f1_compile_result(),
            _f2_result(),
            _success_result(),
        ),
    )
    row = run.rows[0]

    assert row.p_repair_attempted is True
    assert row.p_history_policy == "agentic_transcript_v1"
    assert row.c_loop_fired is True
    assert row.c_loop_source == "post_p_f2"
    assert len(generation.calls) == 3
    assert len(correctness.calls) == 3

    p_prompt = generation.calls[1]["prompt"]
    c_prompt = generation.calls[2]["prompt"]
    assert P_COMPILE_ERROR_TEXT in p_prompt
    assert P_COMPILE_ERROR_TYPE in p_prompt
    assert "Attempt history:\nAttempt 0:" in p_prompt
    assert "p_compile_error_type=" in p_prompt

    assert (
        "Repair the latest Cluster 2 correctness attempt using only public "
        "failure evidence."
    ) in c_prompt
    assert "Attempt history:\nAttempt 0:" in c_prompt
    assert f"source_sha256={_sha(P_TERMINAL_SOURCE)}" in c_prompt
    assert "outcome=F2_NUMERIC_LARGE" in c_prompt
    assert "Best previous source to repair from:" in c_prompt
    assert "BEGIN BEST PREVIOUS SOURCE" in c_prompt
    assert P_TERMINAL_SOURCE in c_prompt
    assert "END BEST PREVIOUS SOURCE" in c_prompt
    assert "Latest failure details:\nBEGIN LATEST FAILURE DETAILS" in c_prompt
    assert C_PUBLIC_FAILURE_SUMMARY in c_prompt
    assert P_COMPILE_ERROR_TEXT not in c_prompt
    assert P_COMPILE_ERROR_TYPE not in c_prompt
    assert "p_compile_error_type=" not in c_prompt
    assert "p_compile_error_changed=" not in c_prompt
    assert "Compile error excerpt" not in c_prompt
    assert "Repair the latest Cluster 3 compile failure" not in c_prompt

    assert row.p_repair_trace is not None
    c_seed_source_hash = _sha(P_TERMINAL_SOURCE)
    p_forbidden_hashes = {
        value
        for attempt in row.p_repair_trace
        for value in (
            (
                attempt.source_hash
                if attempt.source_hash != c_seed_source_hash
                else None
            ),
            attempt.feedback_sha256,
            attempt.compile_error_excerpt_sha256,
        )
        if value
    }
    metadata = row.generated_metadata
    assert metadata is not None
    p_forbidden_hashes.update(
        value
        for value in (
            row.p_raw_error_excerpt_sha256,
            metadata.p_repair_prompt_sha256,
            metadata.p_repair_history_summary_sha256,
            metadata.p_repair_anchor_source_hash,
            (
                metadata.p_repair_latest_source_hash
                if metadata.p_repair_latest_source_hash != c_seed_source_hash
                else None
            ),
        )
        if value
    )
    for digest in p_forbidden_hashes:
        assert digest not in c_prompt

    assert row.repair_trace is not None
    c_trace_source_hashes = {trace.source_hash for trace in row.repair_trace}
    p_trace_source_hashes = {
        attempt.source_hash for attempt in row.p_repair_trace if attempt.source_hash
    }
    assert c_trace_source_hashes.isdisjoint(p_trace_source_hashes)


def test_initial_f2_c_prompt_uses_public_c_evidence_without_p_transcript(
    tmp_path: Path,
) -> None:
    run, generation, correctness = _run_cluster3_with_sequences(
        tmp_path,
        repair_history_policy="agentic_transcript_v1",
        generation_sources=(INITIAL_SOURCE, C_TERMINAL_SOURCE),
        correctness_results=(
            _f2_result(summary=INITIAL_C_PUBLIC_FAILURE_SUMMARY),
            _success_result(),
        ),
    )
    row = run.rows[0]

    assert row.p_repair_attempted is False
    assert row.c_loop_fired is True
    assert row.c_loop_source == "initial_f2"
    assert len(generation.calls) == 2
    assert len(correctness.calls) == 2
    c_prompt = generation.calls[1]["prompt"]
    assert (
        "Repair the latest Cluster 2 correctness attempt using only public "
        "failure evidence."
    ) in c_prompt
    assert "Attempt history:\nAttempt 0:" in c_prompt
    assert f"source_sha256={_sha(INITIAL_SOURCE)}" in c_prompt
    assert "outcome=F2_NUMERIC_LARGE" in c_prompt
    assert "Best previous source to repair from:" in c_prompt
    assert "BEGIN BEST PREVIOUS SOURCE" in c_prompt
    assert INITIAL_SOURCE in c_prompt
    assert "END BEST PREVIOUS SOURCE" in c_prompt
    assert "Latest failure details:\nBEGIN LATEST FAILURE DETAILS" in c_prompt
    assert INITIAL_C_PUBLIC_FAILURE_SUMMARY in c_prompt
    assert P_COMPILE_ERROR_TEXT not in c_prompt
    assert P_COMPILE_ERROR_TYPE not in c_prompt
    assert "p_compile_error_type=" not in c_prompt
    assert "p_compile_error_changed=" not in c_prompt
    assert "Repair the latest Cluster 3 compile failure" not in c_prompt


def test_f1_runtime_remains_terminal_and_never_reaches_p_or_c(
    tmp_path: Path,
) -> None:
    run, generation, correctness = _run_cluster3_with_sequences(
        tmp_path,
        repair_history_policy="agentic_transcript_v1",
        generation_sources=(INITIAL_SOURCE,),
        correctness_results=(_f1_runtime_result(),),
    )
    row = run.rows[0]

    assert row.failure_code == "F1_RUNTIME"
    assert row.p_repair_attempted is False
    assert row.c_loop_fired is False
    assert row.c_loop_source == "none"
    assert len(generation.calls) == 1
    assert len(correctness.calls) == 1


def test_f1_compile_stays_p_only_until_p_terminal_becomes_f2(
    tmp_path: Path,
) -> None:
    run, generation, correctness = _run_cluster3_with_sequences(
        tmp_path,
        generation_sources=(INITIAL_SOURCE, P_TERMINAL_SOURCE),
        correctness_results=(
            _f1_compile_result(),
            _f1_compile_result(
                compile_error="A4 second compiler failed sentinel",
                compile_error_type="A4SecondCompileError",
            ),
        ),
    )
    row = run.rows[0]

    assert row.p_repair_attempted is True
    assert row.p_terminal_failure_code == "F1_COMPILE"
    assert row.p_repair_stop_reason == "p_budget_exhausted"
    assert row.c_loop_fired is False
    assert row.c_loop_source == "none"
    assert len(generation.calls) == 2
    assert len(correctness.calls) == 2


def test_legacy_post_p_c_prompts_match_default_and_explicit_legacy(
    tmp_path: Path,
) -> None:
    _, default_generation, _ = _run_cluster3_with_sequences(
        tmp_path / "default",
        generation_sources=(
            INITIAL_SOURCE,
            P_TERMINAL_SOURCE,
            C_TERMINAL_SOURCE,
        ),
        correctness_results=(
            _f1_compile_result(),
            _f2_result(),
            _success_result(),
        ),
    )
    _, explicit_generation, _ = _run_cluster3_with_sequences(
        tmp_path / "explicit",
        repair_history_policy="last_attempt_only_v1",
        generation_sources=(
            INITIAL_SOURCE,
            P_TERMINAL_SOURCE,
            C_TERMINAL_SOURCE,
        ),
        correctness_results=(
            _f1_compile_result(),
            _f2_result(),
            _success_result(),
        ),
    )

    assert default_generation.calls[1]["prompt"] == explicit_generation.calls[1][
        "prompt"
    ]
    assert default_generation.calls[2]["prompt"] == explicit_generation.calls[2][
        "prompt"
    ]


def test_adapter_records_post_p_source_without_rendering_p_logs_to_c_prompt() -> None:
    generation_calls: list[dict[str, Any]] = []

    def generation(**kwargs: Any) -> dict[str, str]:
        generation_calls.append(kwargs)
        return {"source": C_TERMINAL_SOURCE}

    result = _adapter_call(generation=generation)

    assert result.c_loop_source == "post_p_f2"
    assert result.trace_summary_fragment["c_loop_source"] == "post_p_f2"
    assert result.trace_summary_fragment["seed_source_hash"] == _sha(
        P_TERMINAL_SOURCE
    )
    assert generation_calls
    c_prompt = generation_calls[0]["prompt"]
    assert "Previous source:\n" + P_TERMINAL_SOURCE_IN_C_PROMPT in c_prompt
    assert C_PUBLIC_FAILURE_SUMMARY in c_prompt
    assert P_COMPILE_ERROR_TEXT not in c_prompt
    assert P_COMPILE_ERROR_TYPE not in c_prompt
    assert "p_compile_error_type=" not in c_prompt


def test_adapter_rejects_p_compile_markers_from_custom_c_feedback_before_generation() -> None:
    generation_calls: list[dict[str, Any]] = []

    def generation(**kwargs: Any) -> dict[str, str]:
        generation_calls.append(kwargs)
        return {"source": C_TERMINAL_SOURCE}

    def feedback_builder(inputs: RepairFeedbackInput) -> str:
        return f"{inputs.base_prompt}\n{P_COMPILE_ERROR_TEXT}"

    with pytest.raises(ValueError, match="P compile-error"):
        _adapter_call(feedback_builder=feedback_builder, generation=generation)

    assert generation_calls == []
