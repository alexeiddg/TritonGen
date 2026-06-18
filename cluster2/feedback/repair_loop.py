"""Sequential Cluster 2 repair-loop orchestration.

This module is intentionally local and dependency-injected. It does not import
Modal, generation runtimes, correctness runtimes, Torch, Triton, transformers,
or grammar/constrained decoding code.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from cluster2.constants import DEFAULT_REPAIR_BUDGET, require_generated_condition
from cluster2.feedback.prompts import (
    build_feedback_prompt,
    feedback_allowed_for_failure_code,
    sanitize_public_feedback_text,
    validate_no_forbidden_feedback_terms,
)
from cluster2.feedback.trace import TraceSummary, build_trace_summary
from shared.eval.failure_taxonomy import FAILURE_CODES, LEGACY_FAILURE_CODE_MAP
from shared.repair_history.errors import InvalidRepairHistoryConfigError
from shared.repair_history.evidence import (
    RepairAttemptEvidence,
    RepairSourceRecord,
    sha256_text,
)
from shared.repair_history.policies import (
    RepairHistoryConfig,
    should_render_agentic_transcript,
)
from shared.repair_history.rendering import render_repair_history_prompt


REPAIR_LOOP_SUCCESS_STATUS = "success"
REPAIR_LOOP_EXHAUSTED_STATUS = "exhausted"
REPAIR_LOOP_TERMINATED_STATUS = "terminated"


@dataclass(frozen=True)
class RepairGenerationInput:
    """Public generation request for one sequential repair-loop attempt."""

    condition: str
    attempt_index: int
    base_seed: int
    generation_seed: int
    prompt: str
    previous_feedback: str | None = None


@dataclass(frozen=True)
class RepairEvaluationInput:
    """Evaluation request for one generated candidate source."""

    condition: str
    attempt_index: int
    base_seed: int
    generation_seed: int
    source: str


@dataclass(frozen=True)
class RepairFeedbackInput:
    """Public-only fields available to feedback construction."""

    condition: str
    attempt_index: int
    base_prompt: str
    candidate_source: str
    failure_code: str | None
    public_failure_summary: str | None
    compile_error: str | None = None
    signature_error: str | None = None
    sanitizer_errors: tuple[str, ...] = ()
    functional_success: bool | None = None
    repair_set_success: bool | None = None
    eval_set_success: bool | None = None


@dataclass(frozen=True)
class RepairAttemptSummary:
    """Compact source-free summary for one attempted candidate."""

    attempt_index: int
    generation_seed: int
    functional_success: bool | None
    failure_code: str | None
    public_failure_summary: str | None
    source_hash: str | None
    prompt_hash: str | None = None
    level_reached: int | None = None
    repair_set_success: bool | None = None
    eval_set_success: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RepairPromptMetadata:
    """Nullable/defaultable repair-history prompt metadata for one attempt."""

    repair_history_policy: str
    repair_prompt_template_version: str | None
    repair_prompt_renderer_version: str | None
    repair_anchor_attempt_index: int | None
    repair_latest_attempt_index: int | None
    repair_history_attempt_count: int | None
    repair_prompt_sha256: str | None
    repair_prompt_char_count: int | None
    repair_max_prompt_chars: int | None
    repair_include_latest_source: bool | None
    repair_anchor_source_hash: str | None
    repair_latest_source_hash: str | None
    repair_history_summary_sha256: str | None
    repair_history_error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RepairLoopResult:
    """Source-free repair-loop result with compact trace summaries."""

    condition: str
    status: str
    base_seed: int
    repair_budget: int
    attempts_executed: int
    successful_attempt_index: int | None
    final_failure_code: str | None
    final_public_failure_summary: str | None
    attempts: tuple[RepairAttemptSummary, ...]
    trace_summaries: tuple[TraceSummary, ...]
    terminal_prompt_metadata: RepairPromptMetadata

    def to_dict(self) -> dict[str, Any]:
        return {
            "condition": self.condition,
            "status": self.status,
            "base_seed": self.base_seed,
            "repair_budget": self.repair_budget,
            "attempts_executed": self.attempts_executed,
            "successful_attempt_index": self.successful_attempt_index,
            "final_failure_code": self.final_failure_code,
            "final_public_failure_summary": self.final_public_failure_summary,
            "attempts": [attempt.to_dict() for attempt in self.attempts],
            "trace_summaries": [summary.to_dict() for summary in self.trace_summaries],
            "terminal_prompt_metadata": self.terminal_prompt_metadata.to_dict(),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


GenerationCallable = Callable[[RepairGenerationInput], object]
EvaluationCallable = Callable[[RepairEvaluationInput], object]
FeedbackCallable = Callable[[RepairFeedbackInput], str | None]


def run_repair_loop(
    *,
    condition: str,
    base_prompt: str,
    base_seed: int,
    generation: GenerationCallable,
    evaluation: EvaluationCallable,
    feedback_builder: FeedbackCallable | None = None,
    repair_budget: int = DEFAULT_REPAIR_BUDGET,
    seed_candidate_source: str | None = None,
    repair_history_config: RepairHistoryConfig | None = None,
) -> RepairLoopResult:
    """Run a deterministic sequential repair loop for ``C`` or ``G+C`` only."""

    normalized_condition = require_generated_condition(condition)
    _require_non_empty_string(base_prompt, "base_prompt")
    _require_non_negative_int(base_seed, "base_seed")
    _require_non_negative_int(repair_budget, "repair_budget")
    if repair_budget > DEFAULT_REPAIR_BUDGET:
        raise ValueError(f"repair_budget must be <= {DEFAULT_REPAIR_BUDGET}")
    _require_callable(generation, "generation")
    _require_callable(evaluation, "evaluation")
    resolved_seed_candidate_source = _coerce_optional_seed_candidate_source(
        seed_candidate_source
    )
    resolved_feedback_builder = feedback_builder or build_default_feedback_prompt
    _require_callable(resolved_feedback_builder, "feedback_builder")
    resolved_repair_history_config = _coerce_repair_history_config(
        repair_history_config
    )

    attempts: list[RepairAttemptSummary] = []
    traces: list[TraceSummary] = []
    source_records: list[RepairSourceRecord] = []
    prompt_metadata_by_attempt: dict[int, RepairPromptMetadata] = {
        0: _initial_prompt_metadata(resolved_repair_history_config),
    }
    next_prompt = base_prompt
    previous_feedback: str | None = None
    final_failure_code: str | None = None
    final_public_failure_summary: str | None = None

    for attempt_index in range(repair_budget + 1):
        generation_seed = seed_for_attempt(base_seed, attempt_index)
        prompt_hash = sha256_text(next_prompt)
        if attempt_index == 0 and resolved_seed_candidate_source is not None:
            source = resolved_seed_candidate_source
        else:
            generation_input = RepairGenerationInput(
                condition=normalized_condition,
                attempt_index=attempt_index,
                base_seed=base_seed,
                generation_seed=generation_seed,
                prompt=next_prompt,
                previous_feedback=previous_feedback,
            )
            source = _coerce_generated_source(generation(generation_input))
        evaluation_result = evaluation(
            RepairEvaluationInput(
                condition=normalized_condition,
                attempt_index=attempt_index,
                base_seed=base_seed,
                generation_seed=generation_seed,
                source=source,
            )
        )
        public_result = _public_result_view(evaluation_result)
        source_record = RepairSourceRecord(
            attempt_index=attempt_index,
            source_text=source,
        )
        source_records.append(source_record)
        terminate_without_feedback = (
            False
            if public_result.functional_success is True
            else _must_terminate_without_feedback(public_result)
        )
        trace_public_failure_summary = (
            public_result.termination_public_failure_summary
            if terminate_without_feedback
            else public_result.public_failure_summary
        )
        trace = build_trace_summary(
            condition=normalized_condition,
            attempt_index=attempt_index,
            failure_code=public_result.failure_code,
            public_failure_summary=trace_public_failure_summary,
            functional_success=public_result.functional_success,
            repair_set_success=public_result.repair_set_success,
            eval_set_success=public_result.eval_set_success,
            source=source,
        )
        if trace is None:
            raise RuntimeError("generated repair condition did not produce a trace")

        final_failure_code = public_result.failure_code
        final_public_failure_summary = trace.public_failure_summary
        attempts.append(
            RepairAttemptSummary(
                attempt_index=attempt_index,
                generation_seed=generation_seed,
                functional_success=public_result.functional_success,
                failure_code=public_result.failure_code,
                public_failure_summary=trace.public_failure_summary,
                source_hash=trace.source_hash,
                prompt_hash=prompt_hash,
                level_reached=public_result.level_reached,
                repair_set_success=public_result.repair_set_success,
                eval_set_success=public_result.eval_set_success,
            )
        )
        traces.append(trace)

        if public_result.functional_success is True:
            return RepairLoopResult(
                condition=normalized_condition,
                status=REPAIR_LOOP_SUCCESS_STATUS,
                base_seed=base_seed,
                repair_budget=repair_budget,
                attempts_executed=len(attempts),
                successful_attempt_index=attempt_index,
                final_failure_code=None,
                final_public_failure_summary=None,
                attempts=tuple(attempts),
                trace_summaries=tuple(traces),
                terminal_prompt_metadata=prompt_metadata_by_attempt[attempt_index],
            )

        if terminate_without_feedback:
            return RepairLoopResult(
                condition=normalized_condition,
                status=REPAIR_LOOP_TERMINATED_STATUS,
                base_seed=base_seed,
                repair_budget=repair_budget,
                attempts_executed=len(attempts),
                successful_attempt_index=None,
                final_failure_code=final_failure_code,
                final_public_failure_summary=final_public_failure_summary,
                attempts=tuple(attempts),
                trace_summaries=tuple(traces),
                terminal_prompt_metadata=prompt_metadata_by_attempt[attempt_index],
            )

        if attempt_index == repair_budget:
            break

        feedback_input = RepairFeedbackInput(
            condition=normalized_condition,
            attempt_index=attempt_index,
            base_prompt=base_prompt,
            candidate_source=source,
            failure_code=public_result.failure_code,
            public_failure_summary=public_result.public_failure_summary,
            compile_error=None,
            signature_error=None,
            sanitizer_errors=(),
            functional_success=public_result.functional_success,
            repair_set_success=public_result.repair_set_success,
            eval_set_success=public_result.eval_set_success,
        )
        if should_render_agentic_transcript(resolved_repair_history_config):
            previous_feedback, prompt_metadata = _build_agentic_feedback_prompt(
                base_prompt=base_prompt,
                attempts=attempts,
                source_records=source_records,
                latest_failure_details=trace.public_failure_summary,
                config=resolved_repair_history_config,
            )
        else:
            previous_feedback = _coerce_feedback(
                resolved_feedback_builder(feedback_input),
                attempt_index=attempt_index,
                base_prompt=base_prompt,
            )
            prompt_metadata = _legacy_prompt_metadata(
                policy=resolved_repair_history_config.repair_history_policy,
            )
        prompt_metadata_by_attempt[attempt_index + 1] = prompt_metadata
        next_prompt = previous_feedback

    return RepairLoopResult(
        condition=normalized_condition,
        status=REPAIR_LOOP_EXHAUSTED_STATUS,
        base_seed=base_seed,
        repair_budget=repair_budget,
        attempts_executed=len(attempts),
        successful_attempt_index=None,
        final_failure_code=final_failure_code,
        final_public_failure_summary=final_public_failure_summary,
        attempts=tuple(attempts),
        trace_summaries=tuple(traces),
        terminal_prompt_metadata=prompt_metadata_by_attempt[attempts[-1].attempt_index],
    )


def seed_for_attempt(base_seed: int, attempt_index: int) -> int:
    """Return the Phase 9 deterministic generation seed for one attempt."""

    _require_non_negative_int(base_seed, "base_seed")
    _require_non_negative_int(attempt_index, "attempt_index")
    return base_seed * 10 + attempt_index


def build_default_feedback_prompt(inputs: RepairFeedbackInput) -> str | None:
    """Build the standard deterministic feedback prompt from public fields."""

    return build_feedback_prompt(
        condition=inputs.condition,
        failure_code=inputs.failure_code,
        base_prompt=inputs.base_prompt,
        candidate_source=inputs.candidate_source,
        public_failure_summary=inputs.public_failure_summary,
        compile_error=inputs.compile_error,
        signature_error=inputs.signature_error,
        sanitizer_errors=inputs.sanitizer_errors,
        functional_success=inputs.functional_success,
        repair_set_success=inputs.repair_set_success,
        eval_set_success=inputs.eval_set_success,
    )


def _coerce_repair_history_config(
    config: RepairHistoryConfig | None,
) -> RepairHistoryConfig:
    if config is None:
        return RepairHistoryConfig()
    if not isinstance(config, RepairHistoryConfig):
        raise InvalidRepairHistoryConfigError(
            "repair_history_config must be a RepairHistoryConfig"
        )
    return config


def _build_agentic_feedback_prompt(
    *,
    base_prompt: str,
    attempts: Sequence[RepairAttemptSummary],
    source_records: Sequence[RepairSourceRecord],
    latest_failure_details: str | None,
    config: RepairHistoryConfig,
) -> tuple[str, RepairPromptMetadata]:
    rendered = render_repair_history_prompt(
        base_task=base_prompt,
        repair_objective=(
            "Repair the latest Cluster 2 correctness attempt using only public "
            "failure evidence."
        ),
        attempts=tuple(_attempt_evidence(attempt) for attempt in attempts),
        source_records=source_records,
        latest_failure_details=latest_failure_details,
        loop_kind="C",
        config=config,
    )
    if rendered is None:
        raise InvalidRepairHistoryConfigError(
            "agentic_transcript_v1 did not render a C repair prompt"
        )
    sources_by_attempt = {record.attempt_index: record for record in source_records}
    anchor_source_hash = sources_by_attempt[
        rendered.anchor_attempt_index
    ].source_hash
    latest_source_hash = sources_by_attempt[
        rendered.latest_attempt_index
    ].source_hash
    return rendered.text, RepairPromptMetadata(
        repair_history_policy=rendered.repair_history_policy,
        repair_prompt_template_version="agentic_transcript_v1",
        repair_prompt_renderer_version="agentic_transcript_v1",
        repair_anchor_attempt_index=rendered.anchor_attempt_index,
        repair_latest_attempt_index=rendered.latest_attempt_index,
        repair_history_attempt_count=len(attempts),
        repair_prompt_sha256=rendered.repair_prompt_sha256,
        repair_prompt_char_count=len(rendered.text),
        repair_max_prompt_chars=rendered.max_prompt_chars,
        repair_include_latest_source=rendered.include_latest_source,
        repair_anchor_source_hash=anchor_source_hash,
        repair_latest_source_hash=latest_source_hash,
        repair_history_summary_sha256=rendered.repair_history_summary_sha256,
    )


def _attempt_evidence(attempt: RepairAttemptSummary) -> RepairAttemptEvidence:
    if attempt.source_hash is None:
        raise ValueError(
            f"attempt {attempt.attempt_index} is missing source_hash"
        )
    return RepairAttemptEvidence(
        attempt_index=attempt.attempt_index,
        generation_seed=attempt.generation_seed,
        failure_code=attempt.failure_code,
        level_reached=attempt.level_reached,
        compile_success=None,
        functional_success=attempt.functional_success,
        repair_set_success=attempt.repair_set_success,
        eval_set_success=attempt.eval_set_success,
        public_failure_summary=attempt.public_failure_summary,
        source_hash=attempt.source_hash,
        prompt_hash=attempt.prompt_hash,
    )


def _initial_prompt_metadata(config: RepairHistoryConfig) -> RepairPromptMetadata:
    return RepairPromptMetadata(
        repair_history_policy=config.repair_history_policy,
        repair_prompt_template_version=None,
        repair_prompt_renderer_version=None,
        repair_anchor_attempt_index=None,
        repair_latest_attempt_index=None,
        repair_history_attempt_count=None,
        repair_prompt_sha256=None,
        repair_prompt_char_count=None,
        repair_max_prompt_chars=None,
        repair_include_latest_source=None,
        repair_anchor_source_hash=None,
        repair_latest_source_hash=None,
        repair_history_summary_sha256=None,
    )


def _legacy_prompt_metadata(*, policy: str) -> RepairPromptMetadata:
    return RepairPromptMetadata(
        repair_history_policy=policy,
        repair_prompt_template_version="last_attempt_only_v1",
        repair_prompt_renderer_version="cluster2_feedback_prompt_v1",
        repair_anchor_attempt_index=None,
        repair_latest_attempt_index=None,
        repair_history_attempt_count=1,
        repair_prompt_sha256=None,
        repair_prompt_char_count=None,
        repair_max_prompt_chars=None,
        repair_include_latest_source=None,
        repair_anchor_source_hash=None,
        repair_latest_source_hash=None,
        repair_history_summary_sha256=None,
    )


@dataclass(frozen=True)
class _PublicEvaluationResult:
    failure_code: str | None
    public_failure_summary: str | None
    termination_public_failure_summary: str | None
    level_reached: int | None
    functional_success: bool | None
    repair_set_success: bool | None
    eval_set_success: bool | None
    compile_error: str | None
    signature_error: str | None
    sanitizer_errors: tuple[str, ...]


def _public_result_view(result: object) -> _PublicEvaluationResult:
    failure_code = _normalize_failure_code(_field(result, "failure_code"))
    public_failure_summary = _public_text(
        _first_present_field(
            result,
            ("public_failure_summary", "correctness_error", "parse_error"),
        )
    )
    compile_error = _public_text(_field(result, "compile_error"))
    signature_error = _public_text(_field(result, "signature_error"))
    sanitizer_errors = tuple(
        _public_text(value) or ""
        for value in _string_sequence(_field(result, "sanitizer_errors"))
    )
    sanitized_sanitizer_errors = tuple(value for value in sanitizer_errors if value)
    termination_public_failure_summary = _first_non_empty_string(
        (
            public_failure_summary,
            signature_error,
            compile_error,
            *sanitized_sanitizer_errors,
        )
    )

    return _PublicEvaluationResult(
        failure_code=failure_code,
        public_failure_summary=public_failure_summary,
        termination_public_failure_summary=termination_public_failure_summary,
        level_reached=_optional_non_negative_int(_field(result, "level_reached")),
        functional_success=_optional_bool(_field(result, "functional_success")),
        repair_set_success=_optional_bool(
            _level2_flag(result, "repair_set_success")
        ),
        eval_set_success=_optional_bool(_level2_flag(result, "eval_set_success")),
        compile_error=compile_error,
        signature_error=signature_error,
        sanitizer_errors=sanitized_sanitizer_errors,
    )


def _must_terminate_without_feedback(result: _PublicEvaluationResult) -> bool:
    if result.level_reached is not None and result.level_reached < 2:
        return True
    return not feedback_allowed_for_failure_code(result.failure_code)


def _level2_flag(result: object, field_name: str) -> object:
    value = _field(result, field_name)
    if value is not None:
        return value

    dtype_payload = _dtype_payload(result)
    if dtype_payload is None:
        return None
    return _field(dtype_payload, field_name)


def _dtype_payload(result: object) -> object | None:
    dtype_results = _field(result, "dtype_results")
    if not isinstance(dtype_results, dict) or not dtype_results:
        return None

    dtype_tested = _field(result, "dtype_tested")
    if isinstance(dtype_tested, str) and dtype_tested in dtype_results:
        return dtype_results[dtype_tested]
    if len(dtype_results) == 1:
        return next(iter(dtype_results.values()))
    return None


def _coerce_generated_source(result: object) -> str:
    if isinstance(result, str):
        source = result
    else:
        source = _field(result, "source")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("generation must return a non-empty source string")
    return source


def _coerce_optional_seed_candidate_source(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError("seed_candidate_source must be a non-empty string")
    return value


def _normalize_failure_code(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("failure_code must be a string when present")
    normalized = LEGACY_FAILURE_CODE_MAP.get(value, value)
    if normalized not in FAILURE_CODES:
        raise ValueError(f"unsupported failure_code {value!r}")
    return normalized


def _first_present_field(result: object, field_names: tuple[str, ...]) -> object:
    for field_name in field_names:
        value = _field(result, field_name)
        if value is not None:
            return value
    return None


def _first_non_empty_string(values: tuple[str | None, ...]) -> str | None:
    for value in values:
        if value:
            return value
    return None


def _field(result: object, field_name: str) -> object:
    if isinstance(result, dict):
        return result.get(field_name)
    return getattr(result, field_name, None)


def _public_text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("public evaluation details must be strings when present")
    sanitized = sanitize_public_feedback_text(value)
    return sanitized or None


def _string_sequence(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if not isinstance(value, Sequence):
        raise TypeError("sanitizer_errors must be a sequence of strings")
    values: list[str] = []
    for entry in value:
        if not isinstance(entry, str):
            raise TypeError("sanitizer_errors must contain strings")
        values.append(entry)
    return tuple(values)


def _optional_bool(value: object) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    raise TypeError("success flags must be bool when present")


def _optional_non_negative_int(value: object) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("level_reached must be an int when present")
    if value < 0:
        raise ValueError("level_reached must be non-negative")
    return value


def _coerce_feedback(
    value: str | None,
    *,
    attempt_index: int,
    base_prompt: str,
) -> str:
    if value is None:
        raise ValueError(
            "feedback_builder returned None for failed attempt "
            f"{attempt_index}"
        )
    if not isinstance(value, str) or not value.strip():
        raise ValueError("feedback_builder must return a non-empty string")
    feedback_without_base_prompt = (
        value.replace(base_prompt, "", 1) if base_prompt in value else value
    )
    validate_no_forbidden_feedback_terms(feedback_without_base_prompt)
    if base_prompt not in value:
        raise ValueError("feedback_builder output must include base_prompt verbatim")
    return value


def _require_callable(value: object, field_name: str) -> None:
    if not callable(value):
        raise TypeError(f"{field_name} must be callable")


def _require_non_empty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value:
        raise ValueError(f"{field_name} must not be empty")


def _require_non_negative_int(value: object, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field_name} must be an int")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")
