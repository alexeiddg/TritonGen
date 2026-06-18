"""Public evidence and in-memory source records for repair history."""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, TypeAlias

from shared.repair_history.errors import (
    ForbiddenFeedbackContentError,
    InvalidAttemptEvidenceError,
)


LoopKind: TypeAlias = Literal["C", "P"]

SUCCESS_MARKERS: frozenset[str] = frozenset({"SUCCESS", "success"})
F2_FAILURE_CODES: frozenset[str] = frozenset(
    {"F2_NUMERIC_LARGE", "F2_NUMERIC_NAN", "F2_SHAPE_MISMATCH"}
)
F1_FAILURE_CODES: frozenset[str] = frozenset({"F1_COMPILE", "F1_RUNTIME"})
F0_FAILURE_CODES: frozenset[str] = frozenset(
    {
        "F0_PARSE",
        "F0_GBNF_PARSE",
        "F0_SEMANTIC_INVALID",
        "F0_GRAMMAR_INVALID",
        "F0_NO_DECORATOR",
        "F0_BAD_SIGNATURE",
        "F0_SURFACE_VIOLATION",
    }
)
F3_FAILURE_CODES: frozenset[str] = frozenset(
    {"F3_EVAL_PIPELINE", "F3_OOB", "F3_RACE", "F3_TIMEOUT"}
)
KNOWN_FAILURE_CODES: frozenset[str] = (
    F0_FAILURE_CODES | F1_FAILURE_CODES | F2_FAILURE_CODES | F3_FAILURE_CODES
)

_HEX_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_PUBLIC_EVIDENCE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("eval_shape_set", re.compile(r"(?<![A-Za-z0-9_])eval_shape_set(?![A-Za-z0-9_])", re.IGNORECASE)),
    ("hidden", re.compile(r"(?<![A-Za-z0-9_])hidden(?![A-Za-z0-9_])", re.IGNORECASE)),
    ("private", re.compile(r"(?<![A-Za-z0-9_])private(?![A-Za-z0-9_])", re.IGNORECASE)),
    ("held-out", re.compile(r"(?<![A-Za-z0-9_])held[- ]out(?![A-Za-z0-9_])", re.IGNORECASE)),
    ("token", re.compile(r"(?<![A-Za-z0-9_])token[A-Za-z0-9_]*(?![A-Za-z0-9_])", re.IGNORECASE)),
    ("billing", re.compile(r"(?<![A-Za-z0-9_])billing(?![A-Za-z0-9_])", re.IGNORECASE)),
    ("profiler", re.compile(r"(?<![A-Za-z0-9_])profil[A-Za-z0-9_]*(?![A-Za-z0-9_])", re.IGNORECASE)),
    ("timing", re.compile(r"(?<![A-Za-z0-9_])timing[A-Za-z0-9_]*(?![A-Za-z0-9_])", re.IGNORECASE)),
    ("performance", re.compile(r"(?<![A-Za-z0-9_])performance(?![A-Za-z0-9_])", re.IGNORECASE)),
    ("speedup", re.compile(r"(?<![A-Za-z0-9_])speedup[A-Za-z0-9_]*(?![A-Za-z0-9_])", re.IGNORECASE)),
    ("benchmark", re.compile(r"(?<![A-Za-z0-9_])benchmark[A-Za-z0-9_]*(?![A-Za-z0-9_])", re.IGNORECASE)),
    ("nsight", re.compile(r"(?<![A-Za-z0-9_])nsight(?![A-Za-z0-9_])", re.IGNORECASE)),
    ("ncu", re.compile(r"(?<![A-Za-z0-9_])ncu(?![A-Za-z0-9_])", re.IGNORECASE)),
    ("nvml", re.compile(r"(?<![A-Za-z0-9_])nvml(?![A-Za-z0-9_])", re.IGNORECASE)),
    ("raw correctness tensor", re.compile(r"raw[^.\n]*correctness[^.\n]*tensor", re.IGNORECASE)),
)


@dataclass(frozen=True)
class RepairSourceRecord:
    """In-memory source text for an attempt."""

    attempt_index: int
    source_text: str
    source_hash: str | None = None

    def __post_init__(self) -> None:
        _require_non_negative_int(self.attempt_index, "attempt_index")
        if not isinstance(self.source_text, str):
            raise InvalidAttemptEvidenceError("source_text must be a string")
        computed = sha256_text(self.source_text)
        if self.source_hash is None:
            object.__setattr__(self, "source_hash", computed)
        elif self.source_hash != computed:
            raise InvalidAttemptEvidenceError(
                "source_hash must match source_text sha256"
            )
        _require_sha256(str(self.source_hash), "source_hash")


@dataclass(frozen=True)
class RepairAttemptEvidence:
    """Prompt-visible public evidence for one repair attempt."""

    attempt_index: int
    generation_seed: int
    failure_code: str | None
    level_reached: int | None
    compile_success: bool | None
    functional_success: bool | None
    repair_set_success: bool | None
    eval_set_success: bool | None
    public_failure_summary: str | None
    source_hash: str
    prompt_hash: str | None
    repair_shapes_passed: int | None = None
    num_repair_shapes: int | None = None
    public_eval_shapes_passed: int | None = None
    num_public_eval_shapes: int | None = None
    max_abs_diff: float | None = None
    max_rel_diff: float | None = None
    nan_or_inf_observed: bool | None = None
    shape_mismatch_observed: bool | None = None
    compile_error_type: str | None = None
    compile_error_excerpt_sha256: str | None = None
    compile_error_changed_from_previous: bool | None = None
    post_compile_level_reached: int | None = None

    def __post_init__(self) -> None:
        _require_non_negative_int(self.attempt_index, "attempt_index")
        _require_non_negative_int(self.generation_seed, "generation_seed")
        _require_sha256(self.source_hash, "source_hash")
        if self.prompt_hash is not None:
            _require_sha256(self.prompt_hash, "prompt_hash")
        if self.failure_code is not None:
            if not isinstance(self.failure_code, str):
                raise InvalidAttemptEvidenceError(
                    "failure_code must be a string when present"
                )
            if self.failure_code not in KNOWN_FAILURE_CODES:
                raise InvalidAttemptEvidenceError(
                    f"unsupported failure_code {self.failure_code!r}"
                )
        _require_optional_level(self.level_reached, "level_reached")
        _require_optional_level(
            self.post_compile_level_reached,
            "post_compile_level_reached",
        )
        for field_name in (
            "compile_success",
            "functional_success",
            "repair_set_success",
            "eval_set_success",
            "nan_or_inf_observed",
            "shape_mismatch_observed",
            "compile_error_changed_from_previous",
        ):
            _require_optional_bool(getattr(self, field_name), field_name)
        _validate_count_pair(
            self.repair_shapes_passed,
            self.num_repair_shapes,
            "repair_shapes_passed",
            "num_repair_shapes",
        )
        _validate_count_pair(
            self.public_eval_shapes_passed,
            self.num_public_eval_shapes,
            "public_eval_shapes_passed",
            "num_public_eval_shapes",
        )
        _require_optional_non_negative_float(self.max_abs_diff, "max_abs_diff")
        _require_optional_non_negative_float(self.max_rel_diff, "max_rel_diff")
        if self.compile_error_excerpt_sha256 is not None:
            _require_sha256(
                self.compile_error_excerpt_sha256,
                "compile_error_excerpt_sha256",
            )
        validate_prompt_visible_text(
            self.public_failure_summary,
            field_name="public_failure_summary",
        )
        validate_prompt_visible_text(
            self.compile_error_type,
            field_name="compile_error_type",
        )
        if self.failure_code in F2_FAILURE_CODES:
            if self.level_reached != 2:
                raise InvalidAttemptEvidenceError(
                    "F2 history requires level_reached=2"
                )
            if not self.public_failure_summary:
                raise InvalidAttemptEvidenceError(
                    "F2 history requires public_failure_summary"
                )


def sha256_text(value: str) -> str:
    """Return the SHA256 hex digest for exact UTF-8 text."""

    if not isinstance(value, str):
        raise InvalidAttemptEvidenceError("hash input must be a string")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def validate_prompt_visible_text(value: str | None, *, field_name: str) -> None:
    """Reject prompt-visible evidence that carries forbidden private signals."""

    if value is None:
        return
    if not isinstance(value, str):
        raise InvalidAttemptEvidenceError(f"{field_name} must be a string")
    for term, pattern in _FORBIDDEN_PUBLIC_EVIDENCE_PATTERNS:
        if pattern.search(value):
            raise ForbiddenFeedbackContentError(
                f"{field_name} contains forbidden prompt-visible term: {term}"
            )


def validate_attempt_history(
    attempts: Sequence[RepairAttemptEvidence],
    *,
    loop_kind: LoopKind,
) -> tuple[RepairAttemptEvidence, ...]:
    """Validate rendered-history minimums and return attempts in index order."""

    if loop_kind not in {"C", "P"}:
        raise InvalidAttemptEvidenceError("loop_kind must be C or P")
    ordered = tuple(sorted(attempts, key=lambda attempt: attempt.attempt_index))
    if not ordered:
        raise InvalidAttemptEvidenceError("attempt history must not be empty")
    expected = tuple(range(len(ordered)))
    actual = tuple(attempt.attempt_index for attempt in ordered)
    if actual != expected:
        raise InvalidAttemptEvidenceError(
            "attempt indexes must be contiguous and zero-based"
        )
    latest_attempt_index = ordered[-1].attempt_index
    for attempt in ordered:
        if attempt.functional_success is True and attempt.failure_code is not None:
            raise InvalidAttemptEvidenceError(
                "success history requires failure_code=None"
            )
        if attempt.failure_code is None and attempt.functional_success is not True:
            raise InvalidAttemptEvidenceError(
                "missing failure_code requires a success marker"
            )
        if attempt.failure_code in F0_FAILURE_CODES:
            _validate_f0_evidence(attempt)
        if (
            attempt.failure_code in F3_FAILURE_CODES
            and attempt.attempt_index != latest_attempt_index
        ):
            raise InvalidAttemptEvidenceError("F3 history must end the active loop")
        if loop_kind == "P" and attempt.failure_code == "F1_COMPILE":
            _validate_p_compile_evidence(attempt)
    return ordered


def validate_source_records(
    records: Iterable[RepairSourceRecord],
) -> dict[int, RepairSourceRecord]:
    """Return source records by attempt index without deduplicating hashes."""

    by_attempt: dict[int, RepairSourceRecord] = {}
    for record in records:
        if record.attempt_index in by_attempt:
            raise InvalidAttemptEvidenceError(
                f"duplicate source record for attempt {record.attempt_index}"
            )
        by_attempt[record.attempt_index] = record
    return by_attempt


def latest_attempt_is_repairable(
    latest: RepairAttemptEvidence,
    *,
    loop_kind: LoopKind,
) -> bool:
    """Return whether the latest attempt is eligible for active repair."""

    if latest.functional_success is True:
        return False
    if loop_kind == "C":
        return latest.failure_code in F2_FAILURE_CODES
    if loop_kind == "P":
        return latest.failure_code == "F1_COMPILE" and latest.compile_success is False
    raise InvalidAttemptEvidenceError("loop_kind must be C or P")


def source_hash_counts(
    attempts: Sequence[RepairAttemptEvidence],
) -> Mapping[str, int]:
    counts: dict[str, int] = {}
    for attempt in attempts:
        counts[attempt.source_hash] = counts.get(attempt.source_hash, 0) + 1
    return counts


def _validate_p_compile_evidence(attempt: RepairAttemptEvidence) -> None:
    if attempt.compile_success is not False:
        raise InvalidAttemptEvidenceError(
            "P F1_COMPILE history requires compile_success=False"
        )
    if not (attempt.compile_error_type or attempt.compile_error_excerpt_sha256):
        raise InvalidAttemptEvidenceError(
            "P F1_COMPILE history requires public compile evidence"
        )


def _validate_f0_evidence(attempt: RepairAttemptEvidence) -> None:
    if attempt.level_reached not in {0, None}:
        raise InvalidAttemptEvidenceError(
            "F0 history requires level_reached=0 or unavailable"
        )
    if not attempt.public_failure_summary:
        raise InvalidAttemptEvidenceError(
            "F0 history requires public_failure_summary"
        )


def _require_sha256(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not _HEX_SHA256_RE.fullmatch(value):
        raise InvalidAttemptEvidenceError(f"{field_name} must be a sha256 hex digest")


def _require_non_negative_int(value: object, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise InvalidAttemptEvidenceError(f"{field_name} must be a non-negative int")


def _require_optional_level(value: object, field_name: str) -> None:
    if value is None:
        return
    if not isinstance(value, int) or isinstance(value, bool) or value < 0 or value > 3:
        raise InvalidAttemptEvidenceError(f"{field_name} must be an int from 0 to 3")


def _require_optional_bool(value: object, field_name: str) -> None:
    if value is not None and not isinstance(value, bool):
        raise InvalidAttemptEvidenceError(f"{field_name} must be a bool when present")


def _require_optional_non_negative_float(value: object, field_name: str) -> None:
    if value is None:
        return
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise InvalidAttemptEvidenceError(
            f"{field_name} must be a non-negative number when present"
        )


def _validate_count_pair(
    passed: int | None,
    total: int | None,
    passed_name: str,
    total_name: str,
) -> None:
    if passed is None and total is None:
        return
    if passed is None or total is None:
        raise InvalidAttemptEvidenceError(
            f"{passed_name} and {total_name} must be provided together"
        )
    _require_non_negative_int(passed, passed_name)
    _require_non_negative_int(total, total_name)
    if total <= 0:
        raise InvalidAttemptEvidenceError(f"{total_name} must be positive")
    if passed > total:
        raise InvalidAttemptEvidenceError(f"{passed_name} must not exceed {total_name}")
