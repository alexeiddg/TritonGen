"""Cluster 3 adapter for invoking the Cluster 2 C repair loop.

The adapter is local and dependency-injected. It does not import Modal at module
load time and it records the terminal source/provenance that Cluster 2's compact
repair result intentionally omits.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

from cluster2.constants import (
    DEFAULT_C2_MODAL_GENERATION_GPU,
    DEFAULT_MAX_NEW_TOKENS,
)
from cluster2.feedback.repair_loop import (
    RepairEvaluationInput,
    RepairFeedbackInput,
    RepairGenerationInput,
    run_repair_loop,
)
from cluster2.feedback.trace import TraceSummary
from cluster3.constants import (
    generation_mode_for_cluster3_condition,
    normalize_cluster3_condition,
    source_class_for_cluster3_condition,
)
from cluster3.feedback.condition_adapters import (
    cluster3_to_cluster2_repair_condition,
)
from cluster3.modal.correctness_runner import Cluster3CorrectnessRequest
from cluster3.modal.result_extraction import (
    extract_or_synthesize_cluster3_correctness_result_dict,
)
from shared.eval.failure_taxonomy import FAILURE_CODES
from shared.generation_metadata import UNKNOWN


FeedbackCallable = Callable[[RepairFeedbackInput], str | None]
PromptHashSource = Literal[
    "initial_prompt",
    "p_repair_prompt",
    "c_repair_prompt",
    "seed_prompt_metadata",
    "seed_prompt_unavailable",
]
SeedPromptHashSource = Literal[
    "initial_prompt",
    "p_repair_prompt",
    "seed_prompt_metadata",
    "seed_prompt_unavailable",
]
CLoopSource = Literal["initial_f2", "post_p_f2"]

_C_LOOP_SOURCES = frozenset({"initial_f2", "post_p_f2"})
_PROMPT_HASH_SOURCES = frozenset(
    {
        "initial_prompt",
        "p_repair_prompt",
        "c_repair_prompt",
        "seed_prompt_metadata",
        "seed_prompt_unavailable",
    }
)
_SEED_PROMPT_HASH_SOURCES = frozenset(
    {
        "initial_prompt",
        "p_repair_prompt",
        "seed_prompt_metadata",
        "seed_prompt_unavailable",
    }
)
_PRIVATE_OR_P_FEEDBACK_MARKERS = (
    "CompilationError",
    "compile error",
    "compiler failed",
    "p compile",
    "traceback",
    "eval_shape_set",
    "eval shapes",
    "eval_set",
    "hidden",
    "private",
    "extra shapes",
    "edge cases",
)
_MODEL_ID_DEFAULT = "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"


@dataclass(frozen=True)
class Cluster3CLoopResult:
    """Source/provenance-complete wrapper around a Cluster 2 C repair result."""

    c_loop_fired: bool
    c_loop_source: CLoopSource
    c_attempt_count: int
    c_repair_budget: int
    c_terminal_failure_code: str | None
    c_terminal_level_reached: int | None
    c_terminal_compile_success: bool
    c_terminal_functional_success: bool
    terminal_source: str
    terminal_source_hash: str
    terminal_generation_seed: int
    terminal_prompt_hash: str | None
    terminal_prompt_hash_source: PromptHashSource
    terminal_attempt_index: int | None
    terminal_correctness_result: Mapping[str, Any]
    cluster2_repair_result: Mapping[str, Any] | object
    trace_summary_fragment: Mapping[str, Any]
    infrastructure_failure: bool
    f3_reason: str | None

    def __post_init__(self) -> None:
        _require_bool(self.c_loop_fired, "c_loop_fired")
        if self.c_loop_source not in _C_LOOP_SOURCES:
            raise ValueError(f"unsupported c_loop_source {self.c_loop_source!r}")
        _require_non_negative_int(self.c_attempt_count, "c_attempt_count")
        _require_non_negative_int(self.c_repair_budget, "c_repair_budget")
        if self.c_attempt_count > self.c_repair_budget:
            raise ValueError("c_attempt_count must be <= c_repair_budget")
        _validate_optional_failure_code(
            self.c_terminal_failure_code,
            "c_terminal_failure_code",
        )
        _validate_optional_non_negative_int(
            self.c_terminal_level_reached,
            "c_terminal_level_reached",
        )
        _require_bool(self.c_terminal_compile_success, "c_terminal_compile_success")
        _require_bool(
            self.c_terminal_functional_success,
            "c_terminal_functional_success",
        )
        _require_non_empty_string(self.terminal_source, "terminal_source")
        _validate_sha256(self.terminal_source_hash, "terminal_source_hash")
        if self.terminal_source_hash != _sha256(self.terminal_source):
            raise ValueError("terminal_source_hash must equal sha256(terminal_source)")
        _require_non_negative_int(
            self.terminal_generation_seed,
            "terminal_generation_seed",
        )
        _validate_optional_sha256(self.terminal_prompt_hash, "terminal_prompt_hash")
        _validate_prompt_hash_source(
            self.terminal_prompt_hash,
            self.terminal_prompt_hash_source,
        )
        _validate_optional_non_negative_int(
            self.terminal_attempt_index,
            "terminal_attempt_index",
        )
        if not isinstance(self.terminal_correctness_result, Mapping):
            raise TypeError("terminal_correctness_result must be a mapping")
        if self.c_attempt_count > 0:
            if self.terminal_prompt_hash_source != "c_repair_prompt":
                raise ValueError("generated C terminal requires c_repair_prompt")
            if self.terminal_prompt_hash is None:
                raise ValueError("generated C terminal requires terminal_prompt_hash")
        elif self.terminal_prompt_hash_source == "c_repair_prompt":
            raise ValueError("seed C terminal cannot use c_repair_prompt")
        if self.c_terminal_failure_code != self.terminal_correctness_result.get(
            "failure_code"
        ):
            raise ValueError(
                "c_terminal_failure_code must match terminal_correctness_result"
            )
        _require_bool(self.infrastructure_failure, "infrastructure_failure")
        if self.f3_reason is not None:
            _require_non_empty_string(self.f3_reason, "f3_reason")


@dataclass
class _CAttemptRecord:
    attempt_index: int
    source: str
    generation_seed: int
    prompt: str | None
    prompt_hash: str | None
    correctness_result: Mapping[str, Any] | None = None


def run_cluster3_c_loop_from_f2(
    *,
    outer_c3_condition: str,
    c_loop_source: CLoopSource,
    base_prompt: str,
    base_seed: int,
    sample_index: int,
    kernel_class: str,
    kernel_name: str,
    dtype: str,
    seed_candidate_source: str,
    seed_candidate_generation_seed: int,
    seed_candidate_prompt_hash: str | None,
    seed_candidate_prompt_hash_source: SeedPromptHashSource,
    seed_candidate_evaluation: Mapping[str, Any],
    feedback_builder: FeedbackCallable | None,
    repair_budget: int,
    model_config: Mapping[str, Any],
    provenance_base: Mapping[str, Any],
) -> Cluster3CLoopResult:
    """Run Cluster 2 C repair from an already-evaluated Cluster 3 F2 candidate."""

    c3_condition = normalize_cluster3_condition(outer_c3_condition)
    c2_repair_condition = cluster3_to_cluster2_repair_condition(c3_condition)
    if c_loop_source not in _C_LOOP_SOURCES:
        raise ValueError("c_loop_source must be initial_f2 or post_p_f2")
    _require_non_empty_string(base_prompt, "base_prompt")
    _require_non_negative_int(base_seed, "base_seed")
    _require_non_negative_int(sample_index, "sample_index")
    _require_non_empty_string(kernel_class, "kernel_class")
    _require_non_empty_string(kernel_name, "kernel_name")
    _require_non_empty_string(dtype, "dtype")
    _require_non_empty_string(seed_candidate_source, "seed_candidate_source")
    _require_non_negative_int(
        seed_candidate_generation_seed,
        "seed_candidate_generation_seed",
    )
    _validate_seed_prompt_hash(
        seed_candidate_prompt_hash,
        seed_candidate_prompt_hash_source,
    )
    if not isinstance(seed_candidate_evaluation, Mapping):
        raise TypeError("seed_candidate_evaluation must be a mapping")
    if not isinstance(model_config, Mapping):
        raise TypeError("model_config must be a mapping")
    if not isinstance(provenance_base, Mapping):
        raise TypeError("provenance_base must be a mapping")
    _require_non_negative_int(repair_budget, "repair_budget")
    if feedback_builder is not None and not callable(feedback_builder):
        raise TypeError("feedback_builder must be callable or None")

    generation = _resolve_generation_callable(model_config)
    correctness = _resolve_correctness_callable(model_config)
    run_id = str(provenance_base.get("run_id") or "cluster3-c-loop")
    records: dict[int, _CAttemptRecord] = {
        0: _CAttemptRecord(
            attempt_index=0,
            source=seed_candidate_source,
            generation_seed=seed_candidate_generation_seed,
            prompt=None,
            prompt_hash=seed_candidate_prompt_hash,
            correctness_result=dict(seed_candidate_evaluation),
        )
    }

    def generation_call(inputs: RepairGenerationInput) -> str:
        _assert_inner_condition(
            outer_c3_condition=c3_condition,
            expected_c2_condition=c2_repair_condition,
            observed_condition=inputs.condition,
        )
        if inputs.attempt_index == 0:
            raise AssertionError("attempt 0 must use the cached seed candidate")
        payload = generation(
            identity=_c2_generation_identity(
                run_id=run_id,
                condition=c2_repair_condition,
                kernel_class=kernel_class,
                kernel_name=kernel_name,
                dtype=dtype,
                sample_index=sample_index,
                base_seed=base_seed,
                attempt_index=inputs.attempt_index,
            ),
            prompt=inputs.prompt,
            model_id=str(model_config.get("model_id") or _MODEL_ID_DEFAULT),
            model_revision=str(model_config.get("model_revision") or UNKNOWN),
            tokenizer_revision=str(
                model_config.get("tokenizer_revision") or UNKNOWN
            ),
            generation_seed=inputs.generation_seed,
            temperature=float(model_config.get("temperature", 0.2)),
            max_new_tokens=int(
                model_config.get("max_new_tokens", DEFAULT_MAX_NEW_TOKENS)
            ),
            grammar_variant=(
                model_config.get("grammar_variant")
                if c2_repair_condition == "G+C"
                else None
            ),
            modal_generation_gpu=str(
                model_config.get(
                    "modal_generation_gpu",
                    DEFAULT_C2_MODAL_GENERATION_GPU,
                )
            ),
        )
        source = _extract_generated_source(payload)
        records[inputs.attempt_index] = _CAttemptRecord(
            attempt_index=inputs.attempt_index,
            source=source,
            generation_seed=inputs.generation_seed,
            prompt=inputs.prompt,
            prompt_hash=_sha256(inputs.prompt),
        )
        return source

    def evaluation_call(inputs: RepairEvaluationInput) -> Mapping[str, Any]:
        _assert_inner_condition(
            outer_c3_condition=c3_condition,
            expected_c2_condition=c2_repair_condition,
            observed_condition=inputs.condition,
        )
        if not kernel_name:
            raise ValueError("kernel_name is required for C evaluation identity")
        if inputs.attempt_index == 0:
            if inputs.source != seed_candidate_source:
                raise ValueError("attempt 0 source must be the cached seed candidate")
            return dict(seed_candidate_evaluation)

        identity = _cluster3_identity(
            run_id=run_id,
            condition=c3_condition,
            kernel_class=kernel_class,
            kernel_name=kernel_name,
            dtype=dtype,
            sample_index=sample_index,
            base_seed=base_seed,
            attempt_index=inputs.attempt_index,
        )
        request = Cluster3CorrectnessRequest(identity=identity, source=inputs.source)
        payload = correctness(request)
        result = _canonical_correctness_result(payload, identity)
        records.setdefault(
            inputs.attempt_index,
            _CAttemptRecord(
                attempt_index=inputs.attempt_index,
                source=inputs.source,
                generation_seed=inputs.generation_seed,
                prompt=None,
                prompt_hash=None,
            ),
        ).correctness_result = result
        return result

    wrapped_feedback_builder = _wrap_feedback_builder(feedback_builder)
    repair_result = run_repair_loop(
        condition=c2_repair_condition,
        base_prompt=base_prompt,
        base_seed=base_seed,
        generation=generation_call,
        evaluation=evaluation_call,
        feedback_builder=wrapped_feedback_builder,
        repair_budget=repair_budget,
        seed_candidate_source=seed_candidate_source,
    )

    terminal_index = _terminal_attempt_index(repair_result)
    terminal_record = records.get(terminal_index)
    if terminal_record is None:
        raise RuntimeError("C repair loop terminal attempt was not captured")
    if terminal_record.correctness_result is None:
        raise RuntimeError("C repair loop terminal correctness was not captured")
    terminal_result = terminal_record.correctness_result
    c_attempt_count = _generated_c_attempt_count(records)
    terminal_prompt_hash_source: PromptHashSource = (
        "c_repair_prompt"
        if terminal_index > 0
        else seed_candidate_prompt_hash_source
    )
    terminal_prompt_hash = (
        terminal_record.prompt_hash
        if terminal_index > 0
        else seed_candidate_prompt_hash
    )
    c_terminal_compile_success = _compile_success_from_result(terminal_result)
    c_terminal_functional_success = bool(terminal_result.get("functional_success"))
    f3_reason = _optional_string(terminal_result.get("f3_reason"))

    return Cluster3CLoopResult(
        c_loop_fired=True,
        c_loop_source=c_loop_source,
        c_attempt_count=c_attempt_count,
        c_repair_budget=repair_budget,
        c_terminal_failure_code=_optional_failure_code(
            terminal_result.get("failure_code")
        ),
        c_terminal_level_reached=_optional_non_negative_int(
            terminal_result.get("level_reached")
        ),
        c_terminal_compile_success=c_terminal_compile_success,
        c_terminal_functional_success=c_terminal_functional_success,
        terminal_source=terminal_record.source,
        terminal_source_hash=_sha256(terminal_record.source),
        terminal_generation_seed=terminal_record.generation_seed,
        terminal_prompt_hash=terminal_prompt_hash,
        terminal_prompt_hash_source=terminal_prompt_hash_source,
        terminal_attempt_index=terminal_index,
        terminal_correctness_result=terminal_result,
        cluster2_repair_result=repair_result,
        trace_summary_fragment=_trace_summary_fragment(
            outer_c3_condition=c3_condition,
            repair_condition=c2_repair_condition,
            c_loop_source=c_loop_source,
            c_attempt_count=c_attempt_count,
            seed_source=seed_candidate_source,
            terminal_record=terminal_record,
            terminal_result=terminal_result,
            repair_result=repair_result,
        ),
        infrastructure_failure=(
            terminal_result.get("failure_code") == "F3_EVAL_PIPELINE"
            and f3_reason is not None
        ),
        f3_reason=f3_reason,
    )


def generated_c_repair_traces(
    result: Cluster3CLoopResult,
) -> tuple[TraceSummary, ...]:
    """Return row-ready C repair traces, excluding the cached seed attempt."""

    traces = _field(result.cluster2_repair_result, "trace_summaries")
    if traces is None and isinstance(result.cluster2_repair_result, Mapping):
        traces = result.cluster2_repair_result.get("trace_summaries")
    if traces is None:
        return ()
    generated: list[TraceSummary] = []
    for trace in traces:
        trace_obj = trace if isinstance(trace, TraceSummary) else TraceSummary.from_dict(trace)
        if trace_obj.attempt_index > 0:
            generated.append(trace_obj)
    return tuple(generated)


def _resolve_generation_callable(model_config: Mapping[str, Any]) -> Callable[..., Any]:
    generation = model_config.get("generation")
    if generation is None:
        return _default_generation_call
    if not callable(generation):
        raise TypeError("model_config['generation'] must be callable")
    return generation


def _resolve_correctness_callable(
    model_config: Mapping[str, Any],
) -> Callable[[Cluster3CorrectnessRequest], Any]:
    correctness = model_config.get("correctness")
    if correctness is None:
        return _default_correctness_call
    if not callable(correctness):
        raise TypeError("model_config['correctness'] must be callable")
    return correctness


def _default_generation_call(**kwargs: Any) -> dict[str, Any]:
    from cluster2.generation.modal_generate_c2 import generate_source_c2_modal

    return generate_source_c2_modal(**kwargs)


def _default_correctness_call(request: Cluster3CorrectnessRequest) -> dict[str, Any]:
    from cluster3.modal.correctness_runner import run_cluster3_correctness

    return run_cluster3_correctness(request)


def _wrap_feedback_builder(
    feedback_builder: FeedbackCallable | None,
) -> FeedbackCallable | None:
    if feedback_builder is None:
        return None

    def wrapped(inputs: RepairFeedbackInput) -> str | None:
        feedback = feedback_builder(inputs)
        if feedback is not None:
            _validate_c_feedback_text(feedback)
        return feedback

    return wrapped


def _validate_c_feedback_text(feedback: str) -> None:
    if not isinstance(feedback, str):
        raise TypeError("feedback_builder must return str or None")
    lowered = feedback.lower()
    for marker in _PRIVATE_OR_P_FEEDBACK_MARKERS:
        if marker.lower() in lowered:
            raise ValueError(
                "C repair feedback must not include P compile-error text or "
                "private eval shapes"
            )


def _assert_inner_condition(
    *,
    outer_c3_condition: str,
    expected_c2_condition: str,
    observed_condition: str,
) -> None:
    translated = cluster3_to_cluster2_repair_condition(outer_c3_condition)
    if translated != expected_c2_condition:
        raise AssertionError("outer Cluster 3 condition translated inconsistently")
    if observed_condition != expected_c2_condition:
        raise AssertionError(
            "Cluster 2 C repair loop supplied unexpected inner condition "
            f"{observed_condition!r}; expected {expected_c2_condition!r}"
        )


def _c2_generation_identity(
    *,
    run_id: str,
    condition: str,
    kernel_class: str,
    kernel_name: str,
    dtype: str,
    sample_index: int,
    base_seed: int,
    attempt_index: int,
) -> Any:
    from cluster2.constants import generation_mode_for_condition, source_class_for_condition
    from cluster2.modal.schemas import EvalIdentity

    return EvalIdentity(
        run_id=run_id,
        condition=condition,
        source_class=source_class_for_condition(condition),
        generation_mode=generation_mode_for_condition(condition),
        kernel_class=kernel_class,
        kernel_name=kernel_name,
        dtype=dtype,
        sample_index=sample_index,
        base_seed=base_seed,
        attempt_index=attempt_index,
    )


def _cluster3_identity(
    *,
    run_id: str,
    condition: str,
    kernel_class: str,
    kernel_name: str,
    dtype: str,
    sample_index: int,
    base_seed: int,
    attempt_index: int,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "condition": condition,
        "source_class": source_class_for_cluster3_condition(condition),
        "generation_mode": generation_mode_for_cluster3_condition(condition),
        "kernel_class": kernel_class,
        "kernel_name": kernel_name,
        "dtype": dtype,
        "sample_index": sample_index,
        "base_seed": base_seed,
        "attempt_index": attempt_index,
    }


def _canonical_correctness_result(payload: Any, identity: Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(payload, Mapping) and "correctness_result" not in payload:
        if "failure_code" in payload or "functional_success" in payload:
            result = dict(payload)
            result.setdefault("identity", dict(identity))
            result.setdefault("level_reached", 0)
            result.setdefault("compile_success", _compile_success_from_result(result))
            result.setdefault("functional_success", False)
            result.setdefault("repair_set_success", False)
            result.setdefault("eval_set_success", False)
            return result
    return extract_or_synthesize_cluster3_correctness_result_dict(payload, identity)


def _extract_generated_source(payload: Any) -> str:
    if isinstance(payload, str):
        source = payload
    elif isinstance(payload, Mapping):
        source = payload.get("source")
    else:
        source = getattr(payload, "source", None)
    if not isinstance(source, str) or not source:
        raise ValueError("generation must return a non-empty source")
    return source


def _terminal_attempt_index(repair_result: Any) -> int:
    successful = _field(repair_result, "successful_attempt_index")
    if isinstance(successful, int) and not isinstance(successful, bool):
        return successful
    attempts = _field(repair_result, "attempts")
    if attempts:
        return int(_field(attempts[-1], "attempt_index"))
    raise RuntimeError("C repair loop produced no attempts")


def _generated_c_attempt_count(records: Mapping[int, _CAttemptRecord]) -> int:
    return len([attempt_index for attempt_index in records if attempt_index > 0])


def _trace_summary_fragment(
    *,
    outer_c3_condition: str,
    repair_condition: str,
    c_loop_source: str,
    c_attempt_count: int,
    seed_source: str,
    terminal_record: _CAttemptRecord,
    terminal_result: Mapping[str, Any],
    repair_result: Any,
) -> dict[str, Any]:
    return {
        "outer_c3_condition": outer_c3_condition,
        "repair_condition": repair_condition,
        "c_loop_source": c_loop_source,
        "c_attempt_count": c_attempt_count,
        "seed_source_hash": _sha256(seed_source),
        "terminal_attempt_index": terminal_record.attempt_index,
        "terminal_source_hash": _sha256(terminal_record.source),
        "terminal_generation_seed": terminal_record.generation_seed,
        "terminal_failure_code": terminal_result.get("failure_code"),
        "cluster2_status": _field(repair_result, "status"),
        "private_eval_data_included": False,
    }


def _compile_success_from_result(result: Mapping[str, Any]) -> bool:
    value = result.get("compile_success")
    if isinstance(value, bool):
        return value
    if result.get("functional_success") is True:
        return True
    failure_code = result.get("failure_code")
    if isinstance(failure_code, str):
        if failure_code.startswith(("F0_", "F1_")):
            return False
        if failure_code.startswith("F2_"):
            return True
    level_reached = result.get("level_reached")
    if isinstance(level_reached, int) and not isinstance(level_reached, bool):
        return level_reached >= 2
    return False


def _validate_seed_prompt_hash(value: str | None, source: str) -> None:
    if source not in _SEED_PROMPT_HASH_SOURCES:
        raise ValueError("unsupported seed_candidate_prompt_hash_source")
    _validate_optional_sha256(value, "seed_candidate_prompt_hash")
    if value is None and source != "seed_prompt_unavailable":
        raise ValueError(
            "seed_candidate_prompt_hash may be None only with "
            "seed_prompt_unavailable"
        )
    if value is not None and source == "seed_prompt_unavailable":
        raise ValueError(
            "seed_prompt_unavailable requires seed_candidate_prompt_hash None"
        )


def _validate_prompt_hash_source(value: str | None, source: str) -> None:
    if source not in _PROMPT_HASH_SOURCES:
        raise ValueError("unsupported terminal_prompt_hash_source")
    if value is None and source != "seed_prompt_unavailable":
        raise ValueError(
            "terminal_prompt_hash may be None only with seed_prompt_unavailable"
        )
    if value is not None and source == "seed_prompt_unavailable":
        raise ValueError("seed_prompt_unavailable requires terminal_prompt_hash None")


def _validate_optional_failure_code(value: str | None, field_name: str) -> None:
    if value is None:
        return
    if value not in FAILURE_CODES:
        raise ValueError(f"{field_name} must be canonical; got {value!r}")


def _optional_failure_code(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("failure_code must be a string when present")
    _validate_optional_failure_code(value, "failure_code")
    return value


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("value must be a string when present")
    return value or None


def _validate_optional_non_negative_int(value: int | None, field_name: str) -> None:
    if value is None:
        return
    _require_non_negative_int(value, field_name)


def _optional_non_negative_int(value: Any) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("value must be an int when present")
    if value < 0:
        raise ValueError("value must be non-negative")
    return value


def _require_non_negative_int(value: int, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field_name} must be an int")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")


def _require_bool(value: bool, field_name: str) -> None:
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be a bool")


def _require_non_empty_string(value: str, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value:
        raise ValueError(f"{field_name} must not be empty")


def _validate_sha256(value: str, field_name: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{field_name} must be a 64-character SHA256 hex digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a SHA256 hex digest") from exc


def _validate_optional_sha256(value: str | None, field_name: str) -> None:
    if value is None:
        return
    _validate_sha256(value, field_name)


def _field(container: Any, field_name: str) -> Any:
    if isinstance(container, Mapping):
        return container.get(field_name)
    return getattr(container, field_name, None)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


__all__ = [
    "Cluster3CLoopResult",
    "FeedbackCallable",
    "generated_c_repair_traces",
    "run_cluster3_c_loop_from_f2",
]
