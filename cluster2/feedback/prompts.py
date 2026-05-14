"""Deterministic Cluster 2 feedback text construction."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Final

from cluster2.constants import NEW_GENERATION_CONDITIONS, normalize_cluster2_condition
from shared.eval.failure_taxonomy import FAILURE_CODES
from shared.eval.levels.level2_correctness import GENERIC_EVAL_FAILURE_FEEDBACK


MAX_PUBLIC_DETAIL_CHARS: Final = 200

FORBIDDEN_FEEDBACK_TERMS: Final[tuple[str, ...]] = (
    "speedup",
    "fast@",
    "nsight",
    "ncu",
    "nvml",
    "compute-sanitizer",
    "profil",
    "timing",
    "performance",
    "token",
    "benchmark",
    "RL",
    "GRPO",
    "TRL",
    "LLVM",
    "PTX",
    "C++ traceback",
    "eval_shape_set",
    "hidden",
    "private",
    "edge cases",
    "extra shapes",
)

_SECTION_ORDER: Final[tuple[str, ...]] = (
    "Base task",
    "Previous source",
    "Failure code",
    "Feedback",
    "Public details",
    "Instruction",
)

_FAILURE_FEEDBACK: Final[dict[str, str]] = {
    "F0_PARSE": (
        "The previous attempt did not parse as Python. Return a complete "
        "Triton Python module that satisfies the original task."
    ),
    "F0_NO_DECORATOR": (
        "The previous attempt did not define a @triton.jit kernel. Return a "
        "complete Triton Python module with the required decorated kernel."
    ),
    "F0_BAD_SIGNATURE": (
        "The previous attempt used an invalid kernel interface. Match the "
        "required signature and return a complete Triton Python module."
    ),
    "F0_SURFACE_VIOLATION": (
        "The previous attempt used a disallowed Python surface. Return a "
        "single compliant Triton Python module."
    ),
    "F1_COMPILE": (
        "The previous attempt failed to compile. Fix the Triton kernel and "
        "return a complete Triton Python module."
    ),
    "F1_RUNTIME": (
        "The previous attempt raised during execution. Fix the kernel logic "
        "and return a complete Triton Python module."
    ),
    "F2_NUMERIC_LARGE": (
        "The previous attempt produced incorrect numeric values on initial "
        "correctness shapes. Fix indexing, masks, strides, and arithmetic."
    ),
    "F2_NUMERIC_NAN": (
        "The previous attempt produced NaN or Inf values on initial "
        "correctness shapes. Fix initialization, masks, and arithmetic."
    ),
    "F2_SHAPE_MISMATCH": (
        "The previous attempt produced an output with the wrong shape. Fix "
        "the output layout and return a complete Triton Python module."
    ),
    "F3_OOB": (
        "The previous attempt failed memory-safety validation. Fix bounds "
        "checks, masks, and pointer offsets."
    ),
    "F3_RACE": (
        "The previous attempt has conflicting writes. Ensure each output "
        "element is written consistently."
    ),
    "F3_TIMEOUT": (
        "The previous attempt did not finish within the validation limit. "
        "Simplify the kernel while preserving correctness."
    ),
}


def _term_pattern(term: str) -> str:
    escaped = re.escape(term)
    if term in {"speedup", "profil", "timing", "performance", "token", "benchmark"}:
        return rf"(?<![A-Za-z0-9]){escaped}[A-Za-z0-9_]*"
    if re.fullmatch(r"[A-Za-z0-9_]+", term):
        return rf"(?<![A-Za-z0-9_]){escaped}(?![A-Za-z0-9_])"
    return escaped


_FORBIDDEN_PATTERNS: Final[tuple[re.Pattern[str], ...]] = tuple(
    re.compile(_term_pattern(term), re.IGNORECASE) for term in FORBIDDEN_FEEDBACK_TERMS
)
_SENSITIVE_DETAIL_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(
        r"(?<![A-Za-z0-9_])(?:eval_shape_set|eval[\s_-]+set|eval\s+shapes?)"
        r"(?![A-Za-z0-9_])[^|;]*",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?<![A-Za-z0-9_])(?:hidden|private|edge\s+cases|extra\s+shapes)"
        r"(?![A-Za-z0-9_])[^|;]*",
        re.IGNORECASE,
    ),
)


@dataclass(frozen=True)
class FeedbackPromptInputs:
    """Public inputs for one generated-condition repair feedback message."""

    condition: str
    failure_code: str | None
    base_prompt: str
    candidate_source: str | None = None
    public_failure_summary: str | None = None
    compile_error: str | None = None
    signature_error: str | None = None
    sanitizer_errors: tuple[str, ...] = ()
    functional_success: bool | None = None
    repair_set_success: bool | None = None
    eval_set_success: bool | None = None

    def __post_init__(self) -> None:
        normalize_cluster2_condition(self.condition)
        if self.failure_code is not None and self.failure_code not in FAILURE_CODES:
            raise ValueError(f"unsupported failure_code {self.failure_code!r}")
        if not isinstance(self.base_prompt, str) or not self.base_prompt.strip():
            raise ValueError("base_prompt must be a non-empty string")
        if self.candidate_source is not None and not isinstance(
            self.candidate_source,
            str,
        ):
            raise TypeError("candidate_source must be a string when provided")
        for value in self.sanitizer_errors:
            if not isinstance(value, str):
                raise TypeError("sanitizer_errors must contain strings")


def feedback_required_for_condition(condition: str) -> bool:
    """Return whether a Cluster 2 condition may receive repair feedback."""

    return normalize_cluster2_condition(condition) in NEW_GENERATION_CONDITIONS


def build_feedback_text(
    inputs: FeedbackPromptInputs | None = None,
    *,
    condition: str = "C",
    failure_code: str | None = None,
    public_failure_summary: str | None = None,
    compile_error: str | None = None,
    signature_error: str | None = None,
    sanitizer_errors: Sequence[str] | None = None,
    functional_success: bool | None = None,
    repair_set_success: bool | None = None,
    eval_set_success: bool | None = None,
) -> str | None:
    """Build the deterministic feedback sentence for one failed attempt."""

    if inputs is None and not feedback_required_for_condition(condition):
        return None

    resolved = _coerce_inputs(
        inputs,
        condition=condition,
        failure_code=failure_code,
        base_prompt="unused",
        public_failure_summary=public_failure_summary,
        compile_error=compile_error,
        signature_error=signature_error,
        sanitizer_errors=sanitizer_errors,
        functional_success=functional_success,
        repair_set_success=repair_set_success,
        eval_set_success=eval_set_success,
    )
    if not feedback_required_for_condition(resolved.condition):
        return None
    if resolved.functional_success is True:
        return None
    if _is_eval_only_failure(resolved):
        return GENERIC_EVAL_FAILURE_FEEDBACK
    if resolved.failure_code is None:
        return _validated_feedback_text(
            "The previous attempt failed validation. Produce a corrected "
            "complete Triton Python module."
        )

    message = _FAILURE_FEEDBACK[resolved.failure_code]
    detail = _public_detail(resolved)
    if detail:
        message = f"{message} Public details: {detail}"
    return _validated_feedback_text(message)


def build_feedback_prompt(
    inputs: FeedbackPromptInputs | None = None,
    *,
    condition: str = "C",
    failure_code: str | None = None,
    base_prompt: str = "",
    candidate_source: str | None = None,
    public_failure_summary: str | None = None,
    compile_error: str | None = None,
    signature_error: str | None = None,
    sanitizer_errors: Sequence[str] | None = None,
    functional_success: bool | None = None,
    repair_set_success: bool | None = None,
    eval_set_success: bool | None = None,
) -> str | None:
    """Build a deterministic repair prompt for generated conditions only."""

    if inputs is None and not feedback_required_for_condition(condition):
        return None

    resolved = _coerce_inputs(
        inputs,
        condition=condition,
        failure_code=failure_code,
        base_prompt=base_prompt,
        candidate_source=candidate_source,
        public_failure_summary=public_failure_summary,
        compile_error=compile_error,
        signature_error=signature_error,
        sanitizer_errors=sanitizer_errors,
        functional_success=functional_success,
        repair_set_success=repair_set_success,
        eval_set_success=eval_set_success,
    )
    if not feedback_required_for_condition(resolved.condition):
        return None

    feedback_text = build_feedback_text(resolved)
    if feedback_text is None:
        return None

    sections = {
        "Base task": resolved.base_prompt,
        "Previous source": _sanitize_detail(resolved.candidate_source, limit=None),
        "Failure code": resolved.failure_code or "UNKNOWN",
        "Feedback": feedback_text,
        "Public details": _public_detail(resolved),
        "Instruction": "Produce a corrected complete Triton Python module.",
    }
    lines: list[str] = []
    for name in _SECTION_ORDER:
        value = sections[name]
        if value:
            lines.append(f"{name}:")
            lines.append(value)
            lines.append("")
    prompt = "\n".join(lines).strip()
    validate_no_forbidden_feedback_terms(feedback_text)
    validate_no_forbidden_feedback_terms(sections["Public details"])
    validate_no_forbidden_feedback_terms(sections["Previous source"])
    return prompt


def build_feedback_prompt_from_result(
    result: object,
    *,
    base_prompt: str,
    candidate_source: str | None = None,
    condition: str | None = None,
) -> str | None:
    """Build feedback from any result object exposing the C2 correctness fields."""

    identity = getattr(result, "identity", None)
    resolved_condition = (
        condition
        or getattr(result, "condition", None)
        or getattr(identity, "condition", None)
        or "C"
    )
    if not feedback_required_for_condition(str(resolved_condition)):
        return None

    return build_feedback_prompt(
        condition=str(resolved_condition),
        failure_code=getattr(result, "failure_code", None),
        base_prompt=base_prompt,
        candidate_source=candidate_source,
        public_failure_summary=getattr(result, "correctness_error", None),
        compile_error=getattr(result, "compile_error", None),
        sanitizer_errors=getattr(result, "sanitizer_errors", None),
        functional_success=getattr(result, "functional_success", None),
        repair_set_success=_result_level2_success_flag(result, "repair_set_success"),
        eval_set_success=_result_level2_success_flag(result, "eval_set_success"),
    )


def sanitize_public_feedback_text(value: str | None, *, limit: int | None = MAX_PUBLIC_DETAIL_CHARS) -> str:
    """Return a compact public string with forbidden terms redacted."""

    return _sanitize_detail(value, limit=limit)


def validate_no_forbidden_feedback_terms(value: str) -> None:
    """Raise if text contains a term that Phase 8 feedback must not emit."""

    if not isinstance(value, str):
        raise TypeError("value must be a string")
    for term, pattern in zip(FORBIDDEN_FEEDBACK_TERMS, _FORBIDDEN_PATTERNS, strict=True):
        if pattern.search(value):
            raise ValueError(f"feedback contains forbidden term: {term}")


def _coerce_inputs(
    inputs: FeedbackPromptInputs | None,
    *,
    condition: str,
    failure_code: str | None,
    base_prompt: str,
    candidate_source: str | None = None,
    public_failure_summary: str | None = None,
    compile_error: str | None = None,
    signature_error: str | None = None,
    sanitizer_errors: Sequence[str] | None = None,
    functional_success: bool | None = None,
    repair_set_success: bool | None = None,
    eval_set_success: bool | None = None,
) -> FeedbackPromptInputs:
    if inputs is not None:
        return inputs
    return FeedbackPromptInputs(
        condition=condition,
        failure_code=failure_code,
        base_prompt=base_prompt,
        candidate_source=candidate_source,
        public_failure_summary=public_failure_summary,
        compile_error=compile_error,
        signature_error=signature_error,
        sanitizer_errors=tuple(sanitizer_errors or ()),
        functional_success=functional_success,
        repair_set_success=repair_set_success,
        eval_set_success=eval_set_success,
    )


def _is_eval_only_failure(inputs: FeedbackPromptInputs) -> bool:
    return inputs.repair_set_success is True and inputs.eval_set_success is False


def _public_detail(inputs: FeedbackPromptInputs) -> str:
    if _is_eval_only_failure(inputs):
        return ""
    details = [
        inputs.public_failure_summary,
        inputs.compile_error,
        inputs.signature_error,
        *_take_first(inputs.sanitizer_errors, limit=2),
    ]
    return " | ".join(
        detail for detail in (_sanitize_detail(value) for value in details) if detail
    )


def _sanitize_detail(value: str | None, *, limit: int | None = MAX_PUBLIC_DETAIL_CHARS) -> str:
    if value is None:
        return ""
    text = " ".join(value.split())
    for pattern in _SENSITIVE_DETAIL_PATTERNS:
        text = pattern.sub("[redacted]", text)
    for pattern in _FORBIDDEN_PATTERNS:
        text = pattern.sub("[redacted]", text)
    if limit is not None:
        text = text[:limit]
    return text.strip()


def _take_first(values: Iterable[str], *, limit: int) -> tuple[str, ...]:
    taken: list[str] = []
    for value in values:
        taken.append(value)
        if len(taken) == limit:
            break
    return tuple(taken)


def _validated_feedback_text(value: str) -> str:
    validate_no_forbidden_feedback_terms(value)
    return value


def _result_level2_success_flag(result: object, field_name: str) -> bool | None:
    value = getattr(result, field_name, None)
    if value is not None:
        return _optional_bool(value, field_name)

    dtype_payload = _result_dtype_payload(result)
    if dtype_payload is None:
        return None
    if isinstance(dtype_payload, dict):
        nested = dtype_payload.get(field_name)
    else:
        nested = getattr(dtype_payload, field_name, None)
    return _optional_bool(nested, field_name)


def _result_dtype_payload(result: object) -> object | None:
    dtype_results = getattr(result, "dtype_results", None)
    if not isinstance(dtype_results, dict) or not dtype_results:
        return None

    dtype_tested = getattr(result, "dtype_tested", None)
    if isinstance(dtype_tested, str) and dtype_tested in dtype_results:
        return dtype_results[dtype_tested]
    if len(dtype_results) == 1:
        return next(iter(dtype_results.values()))
    return None


def _optional_bool(value: object, field_name: str) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    raise TypeError(f"{field_name} must be a bool when present")
