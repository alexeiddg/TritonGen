"""Local Cluster 3 P repair-loop skeleton for compile-error feedback."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from typing import Any, Final

from cluster3.constants import (
    DEFAULT_P_REPAIR_BUDGET,
    P_ELIGIBLE_FAILURE_CODES,
    P_REPAIR_STOP_REASONS,
)
from cluster3.feedback.prompts import build_p_feedback_prompt
from cluster3.feedback.sanitizer import sanitize_p_feedback_text
from cluster3.feedback.trace import PRepairAttemptSummary, build_p_attempt_summary
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


P_COMPILE_REPAIRED_THEN_SUCCESS = "compile_repaired_then_success"
P_COMPILE_REPAIRED_F2_OBSERVED = "compile_repaired_f2_observed"
P_POST_P_F3_OBSERVED = "post_p_f3_observed"
P_COMPILE_UNCHANGED_EXHAUSTED = "compile_unchanged_exhausted"
P_TERMINATED_UNRECOVERABLE = "terminated_unrecoverable"

P_REPAIR_STATUSES: Final[frozenset[str]] = frozenset(
    {
        P_COMPILE_REPAIRED_THEN_SUCCESS,
        P_COMPILE_REPAIRED_F2_OBSERVED,
        P_POST_P_F3_OBSERVED,
        P_COMPILE_UNCHANGED_EXHAUSTED,
        P_TERMINATED_UNRECOVERABLE,
    }
)
P_REPAIR_STATUS_TO_STOP_REASON: Final[dict[str, str]] = {
    P_COMPILE_REPAIRED_THEN_SUCCESS: "p_compile_repaired_then_success",
    P_COMPILE_REPAIRED_F2_OBSERVED: "p_compile_repaired_f2_observed",
    P_COMPILE_UNCHANGED_EXHAUSTED: "p_budget_exhausted",
    P_TERMINATED_UNRECOVERABLE: "p_terminal_non_repairable",
}
P_F2_FAILURE_CODES: Final[frozenset[str]] = frozenset(
    {"F2_NUMERIC_LARGE", "F2_NUMERIC_NAN", "F2_SHAPE_MISMATCH"}
)


@dataclass(frozen=True)
class PRepairGenerationInput:
    """Generation request for one P repair attempt after the cached seed."""

    attempt_index: int
    base_seed: int
    generation_seed: int
    prompt: str
    previous_feedback: str | None = None


@dataclass(frozen=True)
class PRepairEvaluationInput:
    """Evaluation request for one P repair candidate source."""

    attempt_index: int
    base_seed: int
    generation_seed: int
    source: str


@dataclass(frozen=True)
class PRepairPromptMetadata:
    """Nullable/defaultable P repair-history prompt metadata."""

    p_history_policy: str
    p_repair_prompt_template_version: str | None
    p_repair_prompt_renderer_version: str | None
    p_repair_anchor_attempt_index: int | None
    p_repair_latest_attempt_index: int | None
    p_repair_history_attempt_count: int | None
    p_repair_prompt_sha256: str | None
    p_repair_prompt_char_count: int | None
    p_repair_max_prompt_chars: int | None
    p_repair_include_latest_source: bool | None
    p_repair_anchor_source_hash: str | None
    p_repair_latest_source_hash: str | None
    p_repair_history_summary_sha256: str | None
    p_repair_history_error_code: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PSeedAttempt:
    """Cached attempt-0 candidate and Level 1 compile-failure evidence."""

    source: str
    generation_seed: int
    base_seed: int
    sample_index: int
    kernel_class: str
    kernel_name: str
    dtype: str
    source_hash: str
    prompt_hash: str
    prompt: str | None
    evaluation_result: object
    failure_code: str
    compile_error: str | None
    compile_error_type: str | None

    def __post_init__(self) -> None:
        _require_non_empty_string(self.source, "source")
        _require_non_negative_int(self.generation_seed, "generation_seed")
        _require_non_negative_int(self.base_seed, "base_seed")
        _require_non_negative_int(self.sample_index, "sample_index")
        _require_non_empty_string(self.kernel_class, "kernel_class")
        _require_non_empty_string(self.kernel_name, "kernel_name")
        _require_non_empty_string(self.dtype, "dtype")
        _validate_sha256(self.source_hash, "source_hash")
        if self.source_hash != _sha256(self.source):
            raise ValueError("source_hash must equal sha256(source)")
        _validate_sha256(self.prompt_hash, "prompt_hash")
        if self.prompt is not None:
            _require_non_empty_string(self.prompt, "prompt")
            if self.prompt_hash != _sha256(self.prompt):
                raise ValueError("prompt_hash must equal sha256(prompt)")
        if self.failure_code not in P_ELIGIBLE_FAILURE_CODES:
            raise ValueError("P seed attempt requires F1_COMPILE failure_code")

        result_view = _evaluation_view(self.evaluation_result)
        if result_view.failure_code != self.failure_code:
            raise ValueError(
                "declared failure_code must match evaluation_result classification"
            )
        if not _has_level1_compile_failure_evidence(
            result_view=result_view,
            compile_error=self.compile_error,
            compile_error_type=self.compile_error_type,
        ):
            raise ValueError("P seed attempt requires Level 1 compile-failure evidence")
        _validate_identity_binding(self)
        _require_prompt_hash_metadata_when_prompt_absent(self)


@dataclass(frozen=True)
class PRepairLoopResult:
    """Terminal P repair-loop result with source-free attempt summaries."""

    status: str
    attempts: tuple[PRepairAttemptSummary, ...]
    attempts_executed: int
    successful_attempt_index: int | None
    repair_budget: int
    initial_failure_code: str
    final_failure_code: str | None
    stop_reason: str
    terminal_source: str
    terminal_attempt_index: int
    terminal_generation_seed: int
    terminal_source_hash: str
    terminal_compile_success: bool | None
    terminal_level_reached: int | None
    terminal_prompt_metadata: PRepairPromptMetadata | None = None

    def __post_init__(self) -> None:
        if self.status not in P_REPAIR_STATUSES:
            raise ValueError(f"unsupported P repair status {self.status!r}")
        if not isinstance(self.attempts, tuple) or not self.attempts:
            raise ValueError("attempts must be a non-empty tuple")
        _require_non_negative_int(self.attempts_executed, "attempts_executed")
        if self.attempts_executed != len(self.attempts):
            raise ValueError("attempts_executed must equal len(attempts)")
        _validate_optional_non_negative_int(
            self.successful_attempt_index,
            "successful_attempt_index",
        )
        _require_non_negative_int(self.repair_budget, "repair_budget")
        _validate_failure_code(self.initial_failure_code, "initial_failure_code")
        _validate_optional_failure_code(self.final_failure_code, "final_failure_code")
        if self.stop_reason != stop_reason_for_status(
            self.status,
            failure_code=self.final_failure_code,
            terminal_compile_success=self.terminal_compile_success,
            terminal_level_reached=self.terminal_level_reached,
        ):
            raise ValueError("stop_reason does not match P repair status/evidence")
        if self.stop_reason not in P_REPAIR_STOP_REASONS:
            raise ValueError(f"unsupported P repair stop_reason {self.stop_reason!r}")
        _require_non_empty_string(self.terminal_source, "terminal_source")
        _require_non_negative_int(self.terminal_attempt_index, "terminal_attempt_index")
        _require_non_negative_int(
            self.terminal_generation_seed,
            "terminal_generation_seed",
        )
        _validate_sha256(self.terminal_source_hash, "terminal_source_hash")
        if self.terminal_source_hash != _sha256(self.terminal_source):
            raise ValueError("terminal_source_hash must equal sha256(terminal_source)")
        _validate_optional_bool(self.terminal_compile_success, "terminal_compile_success")
        _validate_optional_non_negative_int(
            self.terminal_level_reached,
            "terminal_level_reached",
        )
        if self.terminal_prompt_metadata is not None and not isinstance(
            self.terminal_prompt_metadata,
            PRepairPromptMetadata,
        ):
            raise TypeError(
                "terminal_prompt_metadata must be PRepairPromptMetadata or None"
            )


GenerationCallable = Callable[[PRepairGenerationInput], object]
EvaluationCallable = Callable[[PRepairEvaluationInput], object]


def seed_for_p_attempt(base_seed: int, attempt_index: int) -> int:
    """Return the deterministic Cluster 3 repair generation seed."""

    _require_non_negative_int(base_seed, "base_seed")
    _require_non_negative_int(attempt_index, "attempt_index")
    return base_seed * 10 + attempt_index


def stop_reason_for_status(
    status: str,
    *,
    failure_code: str | None,
    terminal_compile_success: bool | None,
    terminal_level_reached: int | None,
) -> str:
    """Return the required P stop reason for a terminal status and evidence."""

    if status == P_POST_P_F3_OBSERVED:
        if _has_compile_repair_evidence(
            compile_success=terminal_compile_success,
            level_reached=terminal_level_reached,
        ):
            return "p_post_compile_f3_observed"
        return "p_f3_without_compile_evidence"
    try:
        reason = P_REPAIR_STATUS_TO_STOP_REASON[status]
    except KeyError as exc:
        raise ValueError(f"unsupported P repair status {status!r}") from exc
    if status == P_TERMINATED_UNRECOVERABLE and not _is_non_repairable(failure_code):
        raise ValueError("terminated_unrecoverable requires F0_* or F1_RUNTIME")
    return reason


def p_compile_repair_succeeded_from_result(result: PRepairLoopResult) -> bool:
    """Return whether P produced compile-repair evidence before any C loop."""

    if result.status in {
        P_COMPILE_REPAIRED_THEN_SUCCESS,
        P_COMPILE_REPAIRED_F2_OBSERVED,
    }:
        return True
    if result.status == P_POST_P_F3_OBSERVED:
        return _has_compile_repair_evidence(
            compile_success=result.terminal_compile_success,
            level_reached=result.terminal_level_reached,
        )
    return False


def run_p_repair_loop(
    *,
    base_prompt: str,
    base_seed: int,
    generation: GenerationCallable,
    evaluation: EvaluationCallable,
    seed_attempt: PSeedAttempt,
    repair_budget: int = DEFAULT_P_REPAIR_BUDGET,
    repair_history_config: RepairHistoryConfig | None = None,
) -> PRepairLoopResult:
    """Run the local P compile-error repair loop.

    Attempt 0 is the already-generated seed attempt and is never regenerated or
    re-evaluated by this loop.
    """

    _require_non_empty_string(base_prompt, "base_prompt")
    _require_non_negative_int(base_seed, "base_seed")
    _require_non_negative_int(repair_budget, "repair_budget")
    if repair_budget > DEFAULT_P_REPAIR_BUDGET:
        raise ValueError(f"repair_budget must be <= {DEFAULT_P_REPAIR_BUDGET}")
    _require_callable(generation, "generation")
    _require_callable(evaluation, "evaluation")
    if not isinstance(seed_attempt, PSeedAttempt):
        raise TypeError("seed_attempt must be a PSeedAttempt")
    if seed_attempt.failure_code not in P_ELIGIBLE_FAILURE_CODES:
        raise ValueError("P repair loop seed_attempt must be F1_COMPILE")
    if seed_attempt.base_seed != base_seed:
        raise ValueError("base_seed must match seed_attempt.base_seed")
    resolved_repair_history_config = _coerce_repair_history_config(
        repair_history_config
    )

    attempts: list[PRepairAttemptSummary] = []
    source_records: list[RepairSourceRecord] = [
        RepairSourceRecord(
            attempt_index=0,
            source_text=seed_attempt.source,
            source_hash=seed_attempt.source_hash,
        )
    ]
    prompt_metadata_by_attempt: dict[int, PRepairPromptMetadata] = {
        0: _initial_p_prompt_metadata(resolved_repair_history_config),
    }
    seed_view = _evaluation_view(seed_attempt.evaluation_result)
    attempts.append(
        build_p_attempt_summary(
            attempt_index=0,
            generation_seed=seed_attempt.generation_seed,
            compile_success=seed_view.compile_success,
            failure_code=seed_attempt.failure_code,
            compile_error_class=seed_attempt.compile_error_type
            or seed_view.compile_error_type,
            compile_error=seed_attempt.compile_error or seed_view.compile_error,
            source_hash=seed_attempt.source_hash,
        )
    )

    previous_source = seed_attempt.source
    previous_failure_code: str | None = seed_attempt.failure_code
    previous_compile_error = seed_attempt.compile_error or seed_view.compile_error
    previous_compile_error_type = (
        seed_attempt.compile_error_type or seed_view.compile_error_type
    )
    previous_feedback: str | None = None
    terminal_source = seed_attempt.source
    terminal_view = seed_view
    terminal_attempt_index = 0
    terminal_generation_seed = seed_attempt.generation_seed

    if repair_budget == 0:
        return _result(
            status=P_COMPILE_UNCHANGED_EXHAUSTED,
            attempts=attempts,
            repair_budget=repair_budget,
            initial_failure_code=seed_attempt.failure_code,
            final_failure_code="F1_COMPILE",
            terminal_source=terminal_source,
            terminal_attempt_index=terminal_attempt_index,
            terminal_generation_seed=terminal_generation_seed,
            terminal_view=terminal_view,
            terminal_prompt_metadata=prompt_metadata_by_attempt[terminal_attempt_index],
        )

    for attempt_index in range(1, repair_budget + 1):
        if should_render_agentic_transcript(resolved_repair_history_config):
            feedback_prompt, prompt_metadata = _build_agentic_p_feedback_prompt(
                base_prompt=base_prompt,
                seed_prompt_hash=seed_attempt.prompt_hash,
                attempts=attempts,
                source_records=source_records,
                latest_compile_error=previous_compile_error,
                latest_compile_error_type=previous_compile_error_type,
                config=resolved_repair_history_config,
            )
        else:
            feedback_prompt = build_p_feedback_prompt(
                base_prompt,
                previous_source,
                previous_failure_code,
                previous_compile_error,
                previous_compile_error_type,
            )
            if feedback_prompt is None:
                raise ValueError("P feedback prompt builder returned None for F1_COMPILE")
            prompt_metadata = _legacy_p_prompt_metadata(
                policy=resolved_repair_history_config.repair_history_policy,
            )
        previous_feedback = feedback_prompt
        prompt_metadata_by_attempt[attempt_index] = prompt_metadata
        generation_seed = seed_for_p_attempt(base_seed, attempt_index)
        generated_source = _coerce_generated_source(
            generation(
                PRepairGenerationInput(
                    attempt_index=attempt_index,
                    base_seed=base_seed,
                    generation_seed=generation_seed,
                    prompt=feedback_prompt,
                    previous_feedback=previous_feedback,
                )
            )
        )
        evaluation_result = evaluation(
            PRepairEvaluationInput(
                attempt_index=attempt_index,
                base_seed=base_seed,
                generation_seed=generation_seed,
                source=generated_source,
            )
        )
        public_result = _evaluation_view(evaluation_result)
        source_records.append(
            RepairSourceRecord(
                attempt_index=attempt_index,
                source_text=generated_source,
            )
        )
        attempts.append(
            build_p_attempt_summary(
                attempt_index=attempt_index,
                generation_seed=generation_seed,
                compile_success=public_result.compile_success,
                failure_code=public_result.failure_code,
                compile_error_class=public_result.compile_error_type,
                compile_error=public_result.compile_error,
                compile_error_changed_from_previous=_compile_error_changed(
                    previous_compile_error_type,
                    public_result.compile_error_type,
                    previous_compile_error,
                    public_result.compile_error,
                ),
                source=generated_source,
                feedback=feedback_prompt,
            )
        )
        terminal_source = generated_source
        terminal_view = public_result
        terminal_attempt_index = attempt_index
        terminal_generation_seed = generation_seed

        if _is_full_success(public_result):
            return _result(
                status=P_COMPILE_REPAIRED_THEN_SUCCESS,
                attempts=attempts,
                repair_budget=repair_budget,
                initial_failure_code=seed_attempt.failure_code,
                final_failure_code=None,
                terminal_source=terminal_source,
                terminal_attempt_index=terminal_attempt_index,
                terminal_generation_seed=terminal_generation_seed,
                terminal_view=terminal_view,
                successful_attempt_index=attempt_index,
                terminal_prompt_metadata=prompt_metadata_by_attempt[attempt_index],
            )

        failure_code = public_result.failure_code
        if failure_code in P_F2_FAILURE_CODES:
            return _result(
                status=P_COMPILE_REPAIRED_F2_OBSERVED,
                attempts=attempts,
                repair_budget=repair_budget,
                initial_failure_code=seed_attempt.failure_code,
                final_failure_code=failure_code,
                terminal_source=terminal_source,
                terminal_attempt_index=terminal_attempt_index,
                terminal_generation_seed=terminal_generation_seed,
                terminal_view=terminal_view,
                terminal_prompt_metadata=prompt_metadata_by_attempt[attempt_index],
            )
        if failure_code is not None and failure_code.startswith("F3_"):
            return _result(
                status=P_POST_P_F3_OBSERVED,
                attempts=attempts,
                repair_budget=repair_budget,
                initial_failure_code=seed_attempt.failure_code,
                final_failure_code=failure_code,
                terminal_source=terminal_source,
                terminal_attempt_index=terminal_attempt_index,
                terminal_generation_seed=terminal_generation_seed,
                terminal_view=terminal_view,
                terminal_prompt_metadata=prompt_metadata_by_attempt[attempt_index],
            )
        if _is_non_repairable(failure_code):
            return _result(
                status=P_TERMINATED_UNRECOVERABLE,
                attempts=attempts,
                repair_budget=repair_budget,
                initial_failure_code=seed_attempt.failure_code,
                final_failure_code=failure_code,
                terminal_source=terminal_source,
                terminal_attempt_index=terminal_attempt_index,
                terminal_generation_seed=terminal_generation_seed,
                terminal_view=terminal_view,
                terminal_prompt_metadata=prompt_metadata_by_attempt[attempt_index],
            )
        if failure_code == "F1_COMPILE":
            previous_source = generated_source
            previous_failure_code = failure_code
            previous_compile_error = public_result.compile_error
            previous_compile_error_type = public_result.compile_error_type
            if attempt_index < repair_budget:
                continue
            return _result(
                status=P_COMPILE_UNCHANGED_EXHAUSTED,
                attempts=attempts,
                repair_budget=repair_budget,
                initial_failure_code=seed_attempt.failure_code,
                final_failure_code="F1_COMPILE",
                terminal_source=terminal_source,
                terminal_attempt_index=terminal_attempt_index,
                terminal_generation_seed=terminal_generation_seed,
                terminal_view=terminal_view,
                terminal_prompt_metadata=prompt_metadata_by_attempt[attempt_index],
            )
        raise ValueError(f"unsupported P repair terminal failure_code {failure_code!r}")

    return _result(
        status=P_COMPILE_UNCHANGED_EXHAUSTED,
        attempts=attempts,
        repair_budget=repair_budget,
        initial_failure_code=seed_attempt.failure_code,
        final_failure_code="F1_COMPILE",
        terminal_source=terminal_source,
        terminal_attempt_index=terminal_attempt_index,
        terminal_generation_seed=terminal_generation_seed,
        terminal_view=terminal_view,
        terminal_prompt_metadata=prompt_metadata_by_attempt[terminal_attempt_index],
    )


@dataclass(frozen=True)
class _PublicPEvaluationResult:
    failure_code: str | None
    level_reached: int | None
    compile_success: bool | None
    functional_success: bool | None
    repair_set_success: bool | None
    eval_set_success: bool | None
    compile_error: str | None
    compile_error_type: str | None


def _result(
    *,
    status: str,
    attempts: list[PRepairAttemptSummary],
    repair_budget: int,
    initial_failure_code: str,
    final_failure_code: str | None,
    terminal_source: str,
    terminal_attempt_index: int,
    terminal_generation_seed: int,
    terminal_view: _PublicPEvaluationResult,
    successful_attempt_index: int | None = None,
    terminal_prompt_metadata: PRepairPromptMetadata | None = None,
) -> PRepairLoopResult:
    stop_reason = stop_reason_for_status(
        status,
        failure_code=final_failure_code,
        terminal_compile_success=terminal_view.compile_success,
        terminal_level_reached=terminal_view.level_reached,
    )
    return PRepairLoopResult(
        status=status,
        attempts=tuple(attempts),
        attempts_executed=len(attempts),
        successful_attempt_index=successful_attempt_index,
        repair_budget=repair_budget,
        initial_failure_code=initial_failure_code,
        final_failure_code=final_failure_code,
        stop_reason=stop_reason,
        terminal_source=terminal_source,
        terminal_attempt_index=terminal_attempt_index,
        terminal_generation_seed=terminal_generation_seed,
        terminal_source_hash=_sha256(terminal_source),
        terminal_compile_success=terminal_view.compile_success,
        terminal_level_reached=terminal_view.level_reached,
        terminal_prompt_metadata=terminal_prompt_metadata,
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


def _build_agentic_p_feedback_prompt(
    *,
    base_prompt: str,
    seed_prompt_hash: str,
    attempts: Sequence[PRepairAttemptSummary],
    source_records: Sequence[RepairSourceRecord],
    latest_compile_error: str | None,
    latest_compile_error_type: str | None,
    config: RepairHistoryConfig,
) -> tuple[str, PRepairPromptMetadata]:
    rendered = render_repair_history_prompt(
        base_task=base_prompt,
        repair_objective=(
            "Repair the latest Cluster 3 compile failure using only public "
            "compile-error evidence."
        ),
        attempts=tuple(
            _p_attempt_evidence(attempt, seed_prompt_hash=seed_prompt_hash)
            for attempt in attempts
        ),
        source_records=source_records,
        latest_failure_details=_latest_compile_failure_details(
            latest_compile_error=latest_compile_error,
            latest_compile_error_type=latest_compile_error_type,
        ),
        loop_kind="P",
        config=config,
    )
    if rendered is None:
        raise InvalidRepairHistoryConfigError(
            "agentic_transcript_v1 did not render a P repair prompt"
        )
    sources_by_attempt = {record.attempt_index: record for record in source_records}
    anchor_source_hash = sources_by_attempt[
        rendered.anchor_attempt_index
    ].source_hash
    latest_source_hash = sources_by_attempt[
        rendered.latest_attempt_index
    ].source_hash
    return rendered.text, PRepairPromptMetadata(
        p_history_policy=rendered.repair_history_policy,
        p_repair_prompt_template_version="agentic_transcript_v1",
        p_repair_prompt_renderer_version="agentic_transcript_v1",
        p_repair_anchor_attempt_index=rendered.anchor_attempt_index,
        p_repair_latest_attempt_index=rendered.latest_attempt_index,
        p_repair_history_attempt_count=len(attempts),
        p_repair_prompt_sha256=rendered.repair_prompt_sha256,
        p_repair_prompt_char_count=len(rendered.text),
        p_repair_max_prompt_chars=rendered.max_prompt_chars,
        p_repair_include_latest_source=rendered.include_latest_source,
        p_repair_anchor_source_hash=anchor_source_hash,
        p_repair_latest_source_hash=latest_source_hash,
        p_repair_history_summary_sha256=rendered.repair_history_summary_sha256,
    )


def _p_attempt_evidence(
    attempt: PRepairAttemptSummary,
    *,
    seed_prompt_hash: str,
) -> RepairAttemptEvidence:
    if attempt.source_hash is None:
        raise InvalidRepairHistoryConfigError(
            f"P attempt {attempt.attempt_index} is missing source_hash"
        )
    prompt_hash = seed_prompt_hash if attempt.attempt_index == 0 else attempt.feedback_sha256
    return RepairAttemptEvidence(
        attempt_index=attempt.attempt_index,
        generation_seed=attempt.generation_seed,
        failure_code=attempt.failure_code,
        level_reached=_p_level_reached(attempt),
        compile_success=attempt.compile_success,
        functional_success=True if attempt.failure_code is None else False,
        repair_set_success=None,
        eval_set_success=None,
        public_failure_summary=_p_public_failure_summary(attempt),
        source_hash=attempt.source_hash,
        prompt_hash=prompt_hash,
        compile_error_type=attempt.compile_error_class,
        compile_error_excerpt_sha256=attempt.compile_error_excerpt_sha256,
        compile_error_changed_from_previous=(
            attempt.compile_error_changed_from_previous
        ),
    )


def _p_level_reached(attempt: PRepairAttemptSummary) -> int | None:
    if attempt.failure_code == "F1_COMPILE":
        return 1
    if attempt.failure_code is None and attempt.compile_success is True:
        return 2
    if attempt.failure_code and attempt.failure_code.startswith("F0_"):
        return 0
    if attempt.failure_code and attempt.failure_code.startswith("F2_"):
        return 2
    return None


def _p_public_failure_summary(attempt: PRepairAttemptSummary) -> str | None:
    if attempt.failure_code is None:
        return "Compilation and public validation succeeded."
    if attempt.failure_code == "F1_COMPILE":
        error_class = (
            sanitize_p_feedback_text(attempt.compile_error_class, limit=120)
            or "UnknownError"
        )
        summary = f"Compilation failed with {error_class}."
        if attempt.compile_error_excerpt_sha256:
            summary = (
                f"{summary} Compile error excerpt sha256: "
                f"{attempt.compile_error_excerpt_sha256}."
            )
        return summary
    if attempt.failure_code.startswith("F0_"):
        return f"Terminal non-repairable failure: {attempt.failure_code}."
    return f"Terminal failure: {attempt.failure_code}."


def _latest_compile_failure_details(
    *,
    latest_compile_error: str | None,
    latest_compile_error_type: str | None,
) -> str:
    error_class = (
        sanitize_p_feedback_text(latest_compile_error_type, limit=120)
        or "UnknownError"
    )
    parts = [f"Failure code: F1_COMPILE.", f"Compile error class: {error_class}."]
    excerpt = sanitize_p_feedback_text(latest_compile_error, limit=2000)
    if excerpt:
        parts.append(f"Compile error excerpt sha256: {sha256_text(excerpt)}.")
        parts.append(f"Compile error excerpt: {excerpt}")
    else:
        parts.append("No compile error text was available.")
    return " ".join(parts)


def _initial_p_prompt_metadata(config: RepairHistoryConfig) -> PRepairPromptMetadata:
    return PRepairPromptMetadata(
        p_history_policy=config.repair_history_policy,
        p_repair_prompt_template_version=None,
        p_repair_prompt_renderer_version=None,
        p_repair_anchor_attempt_index=None,
        p_repair_latest_attempt_index=None,
        p_repair_history_attempt_count=None,
        p_repair_prompt_sha256=None,
        p_repair_prompt_char_count=None,
        p_repair_max_prompt_chars=None,
        p_repair_include_latest_source=None,
        p_repair_anchor_source_hash=None,
        p_repair_latest_source_hash=None,
        p_repair_history_summary_sha256=None,
    )


def _legacy_p_prompt_metadata(*, policy: str) -> PRepairPromptMetadata:
    return PRepairPromptMetadata(
        p_history_policy=policy,
        p_repair_prompt_template_version=None,
        p_repair_prompt_renderer_version=None,
        p_repair_anchor_attempt_index=None,
        p_repair_latest_attempt_index=None,
        p_repair_history_attempt_count=None,
        p_repair_prompt_sha256=None,
        p_repair_prompt_char_count=None,
        p_repair_max_prompt_chars=None,
        p_repair_include_latest_source=None,
        p_repair_anchor_source_hash=None,
        p_repair_latest_source_hash=None,
        p_repair_history_summary_sha256=None,
    )


def _compile_error_changed(
    previous_type: str | None,
    current_type: str | None,
    previous_error: str | None,
    current_error: str | None,
) -> bool | None:
    previous = (previous_type, previous_error)
    current = (current_type, current_error)
    if previous == (None, None) or current == (None, None):
        return None
    return previous != current


def _evaluation_view(result: object) -> _PublicPEvaluationResult:
    compile_error = _optional_string(
        _first_present_field(result, ("compile_error", "compile_error_excerpt"))
    )
    compile_error_type = _optional_string(
        _first_present_field(result, ("compile_error_type", "error_type"))
    )
    failure_code = _normalize_failure_code(_field(result, "failure_code"))
    if failure_code is None:
        failure_code = _classify_from_fields(result)
    return _PublicPEvaluationResult(
        failure_code=failure_code,
        level_reached=_optional_non_negative_int(_field(result, "level_reached")),
        compile_success=_optional_bool(_field(result, "compile_success")),
        functional_success=_optional_bool(_field(result, "functional_success")),
        repair_set_success=_optional_bool(_level2_field(result, "repair_set_success")),
        eval_set_success=_optional_bool(_level2_field(result, "eval_set_success")),
        compile_error=compile_error,
        compile_error_type=compile_error_type,
    )


def _classify_from_fields(result: object) -> str | None:
    parse_success = _field(result, "parse_success")
    if parse_success is False:
        return "F0_PARSE"
    compile_success = _field(result, "compile_success")
    if compile_success is False:
        return "F1_COMPILE"
    functional_success = _field(result, "functional_success")
    if functional_success is False:
        correctness_error = str(_field(result, "correctness_error") or "").lower()
        if "shape" in correctness_error:
            return "F2_SHAPE_MISMATCH"
        if "nan" in correctness_error or "inf" in correctness_error:
            return "F2_NUMERIC_NAN"
        return "F2_NUMERIC_LARGE"
    safe_success = _field(result, "safe_success")
    if safe_success is False:
        errors = " ".join(_string_sequence(_field(result, "sanitizer_errors"))).lower()
        if "timeout" in errors:
            return "F3_TIMEOUT"
        if "race" in errors:
            return "F3_RACE"
        return "F3_OOB"
    return None


def _has_level1_compile_failure_evidence(
    *,
    result_view: _PublicPEvaluationResult,
    compile_error: str | None,
    compile_error_type: str | None,
) -> bool:
    if result_view.failure_code != "F1_COMPILE":
        return False
    if result_view.compile_success is not False:
        return False
    if result_view.level_reached not in (None, 1):
        return False
    return any(
        _non_empty_optional_string(value)
        for value in (
            compile_error_type,
            compile_error,
            result_view.compile_error_type,
            result_view.compile_error,
        )
    )


def _validate_identity_binding(seed: PSeedAttempt) -> None:
    binding_fields = {
        "generation_seed": seed.generation_seed,
        "base_seed": seed.base_seed,
        "sample_index": seed.sample_index,
        "kernel_class": seed.kernel_class,
        "kernel_name": seed.kernel_name,
        "dtype": seed.dtype,
        "source_hash": seed.source_hash,
        "prompt_hash": seed.prompt_hash,
    }
    aliases = {
        "dtype": ("dtype", "dtype_tested"),
        "source_hash": ("source_hash", "source_sha256"),
        "prompt_hash": ("prompt_hash", "prompt_sha256", "base_prompt_sha256"),
    }
    for logical_name, expected in binding_fields.items():
        present_values = _present_identity_values(
            seed.evaluation_result,
            aliases.get(logical_name, (logical_name,)),
        )
        for value in present_values:
            if value != expected:
                raise ValueError(f"{logical_name} does not match evaluation_result")


def _require_prompt_hash_metadata_when_prompt_absent(seed: PSeedAttempt) -> None:
    if seed.prompt is not None:
        return
    present_values = _present_identity_values(
        seed.evaluation_result,
        ("prompt_hash", "prompt_sha256", "base_prompt_sha256"),
    )
    if not present_values:
        raise ValueError("prompt_hash metadata is required when prompt is not stored")


def _present_identity_values(result: object, field_names: tuple[str, ...]) -> list[Any]:
    containers: list[object] = [result]
    for nested_name in (
        "identity",
        "source_identity",
        "eval_identity",
        "generated_metadata",
        "metadata",
        "parent_row",
    ):
        nested = _field(result, nested_name)
        if nested is not None:
            containers.append(nested)
    values: list[Any] = []
    for container in containers:
        for field_name in field_names:
            value = _field(container, field_name)
            if value is not None:
                values.append(value)
    return values


def _is_full_success(result: _PublicPEvaluationResult) -> bool:
    if result.failure_code is not None:
        return False
    if result.compile_success is not True:
        return False
    return result.functional_success is True or (
        result.repair_set_success is True and result.eval_set_success is True
    )


def _has_compile_repair_evidence(
    *,
    compile_success: bool | None,
    level_reached: int | None,
) -> bool:
    if compile_success is True:
        return True
    return (
        isinstance(level_reached, int)
        and not isinstance(level_reached, bool)
        and level_reached >= 2
    )


def _is_non_repairable(failure_code: str | None) -> bool:
    return bool(
        failure_code is not None
        and (failure_code.startswith("F0_") or failure_code == "F1_RUNTIME")
    )


def _coerce_generated_source(result: object) -> str:
    if isinstance(result, str):
        source = result
    else:
        source = _field(result, "source")
    _require_non_empty_string(source, "generation source")
    return source


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


def _level2_field(result: object, field_name: str) -> object:
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


def _field(result: object, field_name: str) -> object:
    if isinstance(result, dict):
        return result.get(field_name)
    return getattr(result, field_name, None)


def _string_sequence(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if not isinstance(value, tuple | list):
        raise TypeError("string sequence fields must be sequences of strings")
    values: list[str] = []
    for entry in value:
        if not isinstance(entry, str):
            raise TypeError("string sequence fields must contain strings")
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
    _require_non_negative_int(value, "level_reached")
    return value


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("compile details must be strings when present")
    return value or None


def _non_empty_optional_string(value: str | None) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_failure_code(value: str, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if value not in FAILURE_CODES:
        raise ValueError(f"unsupported {field_name} {value!r}")


def _validate_optional_failure_code(value: str | None, field_name: str) -> None:
    if value is None:
        return
    _validate_failure_code(value, field_name)


def _require_non_empty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_non_negative_int(value: object, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field_name} must be an int")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")


def _validate_optional_non_negative_int(value: int | None, field_name: str) -> None:
    if value is None:
        return
    _require_non_negative_int(value, field_name)


def _validate_optional_bool(value: bool | None, field_name: str) -> None:
    if value is None:
        return
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be a bool when present")


def _validate_sha256(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} is required")
    if len(value) != 64:
        raise ValueError(f"{field_name} must be a 64-character SHA256 hex digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a SHA256 hex digest") from exc


def _require_callable(value: object, field_name: str) -> None:
    if not callable(value):
        raise TypeError(f"{field_name} must be callable")


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
