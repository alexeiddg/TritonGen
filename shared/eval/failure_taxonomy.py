"""Failure classification for shared evaluation results."""

from __future__ import annotations

from shared.eval.schema import EvalResult


FAILURE_CODES = {
    "F0_PARSE",
    "F0_NO_DECORATOR",
    "F0_BAD_SIGNATURE",
    "F1_COMPILE",
    "F1_RUNTIME",
    "F2_NUMERIC_LARGE",
    "F2_NUMERIC_NAN",
    "F2_SHAPE_MISMATCH",
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


def classify_failure(result: EvalResult) -> str | None:
    """Return one contract failure code, or ``None`` for a successful record.

    This is pure dispatch over populated ``EvalResult`` fields. It does not run
    parse, compile, correctness, sanitizer, or performance checks.
    """

    if result.failure_code in FAILURE_CODES:
        return result.failure_code
    if result.failure_code in LEGACY_FAILURE_CODE_MAP:
        return LEGACY_FAILURE_CODE_MAP[result.failure_code]

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
