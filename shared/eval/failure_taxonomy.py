"""Failure classification for shared evaluation results."""

from __future__ import annotations

from shared.eval.schema import EvalResult


FAILURE_CODES = {
    "F0_PARSE",
    "F0_GBNF_PARSE",
    "F0_SEMANTIC_INVALID",
    "F0_GRAMMAR_INVALID",
    "F0_NO_DECORATOR",
    "F0_BAD_SIGNATURE",
    "F0_SURFACE_VIOLATION",
    "F1_COMPILE",
    "F1_RUNTIME",
    "F2_NUMERIC_LARGE",
    "F2_NUMERIC_NAN",
    "F2_SHAPE_MISMATCH",
    "F3_EVAL_PIPELINE",
    "F3_OOB",
    "F3_RACE",
    "F3_TIMEOUT",
}

LEGACY_FAILURE_CODE_MAP = {
    "SyntaxError": "F0_PARSE",
    "NoDecoratorError": "F0_NO_DECORATOR",
    "SignatureError": "F0_BAD_SIGNATURE",
    "CompilationError": "F1_COMPILE",
    "RuntimeError": "F1_RUNTIME",
}

_PARSE_ERROR_MARKERS = (
    "syntax error in generated source",
    "syntaxerror",
    "invalid syntax",
)


def canonical_failure_code_from_compile_error(
    compile_error_type: str | None,
    compile_error_msg: str | None = None,
) -> str | None:
    """Map a legacy C1 compile label and message to a canonical failure code."""

    if compile_error_type is None:
        return None
    if compile_error_type == "SyntaxError":
        return "F0_PARSE"
    if compile_error_type == "SignatureError" and _is_parse_error_text(
        compile_error_msg
    ):
        return "F0_PARSE"
    return LEGACY_FAILURE_CODE_MAP.get(compile_error_type)


def classify_failure(result: EvalResult) -> str | None:
    """Return one contract failure code, or ``None`` for a successful record.

    This is pure dispatch over populated ``EvalResult`` fields. It does not run
    parse, compile, correctness, sanitizer, or performance checks.
    """

    if result.failure_code in FAILURE_CODES:
        return result.failure_code

    grammar_failure = _classify_grammar_failure(result)
    if grammar_failure is not None:
        return grammar_failure

    if result.failure_code in LEGACY_FAILURE_CODE_MAP:
        return canonical_failure_code_from_compile_error(
            result.failure_code,
            result.compile_error,
        )

    sanitizer_failure = _classify_sanitizer_failure(result)
    if sanitizer_failure is not None:
        return sanitizer_failure

    if result.parse_success is False:
        return "F0_PARSE"
    if result.has_triton_decorator is False:
        return "F0_NO_DECORATOR"
    if result.signature_valid is False:
        return "F0_BAD_SIGNATURE"

    if result.compile_success is False:
        error_text = (result.compile_error or "").lower()
        if "runtime" in error_text:
            return "F1_RUNTIME"
        return "F1_COMPILE"

    if result.functional_success is False:
        error_text = (result.correctness_error or "").lower()
        if "shape" in error_text:
            return "F2_SHAPE_MISMATCH"
        if "nan" in error_text or "inf" in error_text:
            return "F2_NUMERIC_NAN"
        return "F2_NUMERIC_LARGE"

    if result.safe_success is False:
        error_text = " ".join(result.sanitizer_errors or ()).lower()
        if "timeout" in error_text:
            return "F3_TIMEOUT"
        if "race" in error_text:
            return "F3_RACE"
        return "F3_OOB"

    return None


def _classify_grammar_failure(result: EvalResult) -> str | None:
    if result.grammar_active is not True or result.grammar_valid is not False:
        return None
    if result.gbnf_parse_valid is False:
        return "F0_GBNF_PARSE"
    if result.gbnf_parse_valid is True and result.semantic_valid is False:
        return "F0_SEMANTIC_INVALID"
    return "F0_GRAMMAR_INVALID"


def _classify_sanitizer_failure(result: EvalResult) -> str | None:
    if result.safe_success is not False:
        return None
    error_text = " ".join(result.sanitizer_errors or ()).lower()
    if "f0_parse" in error_text or "syntaxerror" in error_text:
        return "F0_PARSE"
    if "f0_surface_violation" in error_text or "surface violation" in error_text:
        return "F0_SURFACE_VIOLATION"
    return None


def _is_parse_error_text(error_msg: str | None) -> bool:
    error_text = (error_msg or "").lower()
    return any(marker in error_text for marker in _PARSE_ERROR_MARKERS)
