import pytest

from cluster2.feedback.prompts import FORBIDDEN_FEEDBACK_TERMS
from cluster3.feedback.sanitizer import (
    LLVM_PTX_ALLOWED,
    P_FORBIDDEN_FEEDBACK_TERMS,
    sanitize_p_feedback_text,
    validate_no_forbidden_p_terms,
)


def test_cluster3_sanitizer_terms_match_cluster2_current_terms() -> None:
    assert set(P_FORBIDDEN_FEEDBACK_TERMS) == set(FORBIDDEN_FEEDBACK_TERMS) - {
        "LLVM",
        "PTX",
    }
    assert LLVM_PTX_ALLOWED is True


def test_validate_no_forbidden_p_terms_rejects_speedup() -> None:
    with pytest.raises(ValueError, match="speedup"):
        validate_no_forbidden_p_terms("reported speedup was large")


def test_validate_no_forbidden_p_terms_rejects_profil_token_benchmark() -> None:
    for term in ("profiling", "tokens", "benchmarks"):
        with pytest.raises(ValueError):
            validate_no_forbidden_p_terms(f"contains {term}")


def test_validate_no_forbidden_p_terms_allows_llvm() -> None:
    validate_no_forbidden_p_terms("LLVM ERROR: verifier rejected a module")


def test_validate_no_forbidden_p_terms_allows_ptx() -> None:
    validate_no_forbidden_p_terms("PTX assembler failed at line 12")


def test_sanitize_p_feedback_text_redacts_eval_set_details() -> None:
    assert sanitize_p_feedback_text("eval_shape_set leaks") == "[redacted]"


def test_sanitize_p_feedback_text_truncates_to_limit() -> None:
    assert sanitize_p_feedback_text("a" * 5000, limit=2000) == "a" * 2000

