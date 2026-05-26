"""Deterministic Cluster 3 compile-error feedback prompts."""

from __future__ import annotations

import hashlib
from typing import Final

from cluster3.constants import P_ELIGIBLE_FAILURE_CODES
from cluster3.feedback.sanitizer import (
    sanitize_p_feedback_text,
    validate_no_forbidden_p_terms,
)


P_SECTION_ORDER: Final[tuple[str, ...]] = (
    "Base task",
    "Previous source",
    "Failure code",
    "Feedback",
    "Compile error",
    "Instruction",
)
P_COMPILE_ERROR_EXCERPT_CHARS: Final[int] = 2000

_DIAGNOSTIC_NOTE_BY_CLASS: Final[dict[tuple[str, str], str]] = {
    (
        "F1_COMPILE",
        "CompilationError",
    ): "Compilation stopped before downstream validation. Failure code: F1_COMPILE. Compile error class: CompilationError.",
    (
        "F1_COMPILE",
        "TritonCompilationError",
    ): "Compilation stopped before downstream validation. Failure code: F1_COMPILE. Compile error class: TritonCompilationError.",
    (
        "F1_COMPILE",
        "LLVMError",
    ): "Compilation stopped before downstream validation. Failure code: F1_COMPILE. Compile error class: LLVMError.",
    (
        "F1_COMPILE",
        "PTXAssemblyError",
    ): "Compilation stopped before downstream validation. Failure code: F1_COMPILE. Compile error class: PTXAssemblyError.",
}


def excerpt_compile_error(
    compile_error: str | None,
    *,
    limit: int = P_COMPILE_ERROR_EXCERPT_CHARS,
) -> tuple[str, str]:
    """Return a sanitized head excerpt and the SHA256 of the full raw error."""

    if compile_error is None:
        return "", ""
    if not isinstance(compile_error, str):
        raise TypeError("compile_error must be a string or None")
    if not isinstance(limit, int) or isinstance(limit, bool):
        raise TypeError("limit must be an int")
    if limit < 0:
        raise ValueError("limit must be non-negative")

    full_sha256 = hashlib.sha256(compile_error.encode("utf-8")).hexdigest()
    excerpt = sanitize_p_feedback_text(compile_error, limit=limit)
    return excerpt, full_sha256


def build_compile_diagnostic_note(
    failure_code: str,
    compile_error_type: str | None,
    compile_error: str | None,
) -> str:
    """Build a deterministic diagnostic note without proposing source edits."""

    error_class = _normalize_error_class(compile_error_type)
    note = _DIAGNOSTIC_NOTE_BY_CLASS.get(
        (failure_code, error_class),
        (
            "Compilation stopped before downstream validation. "
            f"Failure code: {failure_code}. Compile error class: {error_class}."
        ),
    )
    if compile_error:
        _, full_sha256 = excerpt_compile_error(compile_error)
        note = f"{note} Full compile error sha256: {full_sha256}."
    else:
        note = f"{note} No compile error text was available."
    validate_no_forbidden_p_terms(note)
    return note


def build_p_feedback_prompt(
    base_prompt: str,
    candidate_source: str | None,
    failure_code: str | None,
    compile_error: str | None,
    compile_error_type: str | None,
) -> str | None:
    """Build a six-section P repair prompt for Level 1 compile failures."""

    if failure_code not in P_ELIGIBLE_FAILURE_CODES:
        return None
    _require_non_empty_string(base_prompt, "base_prompt")

    previous_source = sanitize_p_feedback_text(candidate_source, limit=None)
    compile_error_excerpt, full_sha256 = excerpt_compile_error(compile_error)
    diagnostic_note = build_compile_diagnostic_note(
        failure_code,
        compile_error_type,
        compile_error,
    )
    compile_error_section = _compile_error_section(
        excerpt=compile_error_excerpt,
        full_sha256=full_sha256,
    )
    sections = {
        "Base task": base_prompt,
        "Previous source": previous_source,
        "Failure code": failure_code,
        "Feedback": diagnostic_note,
        "Compile error": compile_error_section,
        "Instruction": "Produce a corrected complete Triton Python module.",
    }

    lines: list[str] = []
    for section_name in P_SECTION_ORDER:
        lines.append(f"{section_name}:")
        lines.append(sections[section_name])
        lines.append("")
    prompt = "\n".join(lines).strip()

    feedback_without_base_prompt = prompt.replace(base_prompt, "", 1)
    validate_no_forbidden_p_terms(feedback_without_base_prompt)
    return prompt


def _compile_error_section(*, excerpt: str, full_sha256: str) -> str:
    if not excerpt:
        return "No compile error text provided."
    return f"Full compile error sha256: {full_sha256}\n{excerpt}"


def _normalize_error_class(value: str | None) -> str:
    if value is None or not value.strip():
        return "UnknownError"
    return sanitize_p_feedback_text(value, limit=120) or "UnknownError"


def _require_non_empty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
