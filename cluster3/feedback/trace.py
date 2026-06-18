"""Source-free Cluster 3 repair trace summaries."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from dataclasses import asdict, dataclass, fields
from typing import Any, Literal

from cluster3.constants import normalize_cluster3_condition
from shared.eval.failure_taxonomy import FAILURE_CODES


PromptHashSource = Literal[
    "initial_prompt",
    "p_repair_prompt",
    "c_repair_prompt",
    "seed_prompt_metadata",
    "seed_prompt_unavailable",
]
CTraceSource = Literal["none", "initial_f2", "post_p_f2"]

_TERMINAL_PROMPT_HASH_SOURCES: frozenset[str] = frozenset(
    {
        "initial_prompt",
        "p_repair_prompt",
        "c_repair_prompt",
        "seed_prompt_metadata",
        "seed_prompt_unavailable",
    }
)
_C_LOOP_SOURCES: frozenset[str] = frozenset({"none", "initial_f2", "post_p_f2"})
_FAILURE_PATH_LABEL = re.compile(
    r"^(?:initial|p_attempt|c_seed|c_attempt):(?:[0-9]+:)?(?:success|[A-Z0-9_]+)$"
)
_PRIVATE_MARKERS = (
    "eval_shape_set",
    "eval shapes",
    "eval_set",
    "hidden",
    "private",
    "extra shapes",
    "edge cases",
    "traceback",
    "def ",
    "import ",
    "@",
)


@dataclass(frozen=True)
class PRepairAttemptSummary:
    """One compact source-free P repair attempt summary."""

    attempt_index: int
    generation_seed: int
    compile_success: bool | None
    failure_code: str | None
    compile_error_class: str | None
    source_hash: str | None
    feedback_sha256: str | None
    compile_error_excerpt_sha256: str | None = None
    compile_error_changed_from_previous: bool | None = None

    def __post_init__(self) -> None:
        _require_non_negative_int(self.attempt_index, "attempt_index")
        _require_non_negative_int(self.generation_seed, "generation_seed")
        _validate_optional_bool(self.compile_success, "compile_success")
        _validate_optional_failure_code(self.failure_code, "failure_code")
        _validate_optional_string(self.compile_error_class, "compile_error_class")
        _validate_optional_sha256(
            self.compile_error_excerpt_sha256,
            "compile_error_excerpt_sha256",
        )
        _validate_optional_bool(
            self.compile_error_changed_from_previous,
            "compile_error_changed_from_previous",
        )
        _validate_optional_sha256(self.source_hash, "source_hash")
        _validate_optional_sha256(self.feedback_sha256, "feedback_sha256")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return _json_dumps(self.to_dict())

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PRepairAttemptSummary":
        if not isinstance(payload, dict):
            raise TypeError("PRepairAttemptSummary.from_dict requires a dict")
        _reject_unknown_fields(cls, payload)
        return cls(**payload)


@dataclass(frozen=True)
class Cluster3TraceSummary:
    """Whole-row Cluster 3 source-free trace summary."""

    condition: str
    initial_failure_code: str | None
    final_failure_code: str | None
    p_loop_fired: bool
    p_attempt_count: int
    p_terminal_failure_code: str | None
    p_compile_repair_succeeded: bool
    c_loop_fired: bool
    c_loop_source: CTraceSource
    c_attempt_count: int
    c_terminal_failure_code: str | None
    terminal_source_stage: str
    terminal_attempt_index: int | None
    terminal_source_hash: str
    terminal_generation_seed: int
    terminal_prompt_hash: str | None
    terminal_prompt_hash_source: PromptHashSource
    compile_success: bool
    functional_success: bool
    repair_set_success: bool | None
    eval_set_success: bool | None
    row_source_hash: str
    failure_path: list[str]
    private_eval_data_included: Literal[False] = False

    def __post_init__(self) -> None:
        normalize_cluster3_condition(self.condition)
        _validate_optional_failure_code(
            self.initial_failure_code,
            "initial_failure_code",
        )
        _validate_optional_failure_code(self.final_failure_code, "final_failure_code")
        _validate_bool(self.p_loop_fired, "p_loop_fired")
        _require_non_negative_int(self.p_attempt_count, "p_attempt_count")
        _validate_optional_failure_code(
            self.p_terminal_failure_code,
            "p_terminal_failure_code",
        )
        _validate_bool(
            self.p_compile_repair_succeeded,
            "p_compile_repair_succeeded",
        )
        _validate_bool(self.c_loop_fired, "c_loop_fired")
        if self.c_loop_source not in _C_LOOP_SOURCES:
            raise ValueError(f"unsupported c_loop_source {self.c_loop_source!r}")
        _require_non_negative_int(self.c_attempt_count, "c_attempt_count")
        _validate_optional_failure_code(
            self.c_terminal_failure_code,
            "c_terminal_failure_code",
        )
        _validate_loop_source_consistency(
            c_loop_fired=self.c_loop_fired,
            c_loop_source=self.c_loop_source,
            c_attempt_count=self.c_attempt_count,
        )
        _require_non_empty_string(
            self.terminal_source_stage,
            "terminal_source_stage",
        )
        _validate_optional_non_negative_int(
            self.terminal_attempt_index,
            "terminal_attempt_index",
        )
        _validate_sha256(self.terminal_source_hash, "terminal_source_hash")
        _require_non_negative_int(
            self.terminal_generation_seed,
            "terminal_generation_seed",
        )
        _validate_optional_sha256(self.terminal_prompt_hash, "terminal_prompt_hash")
        if self.terminal_prompt_hash_source not in _TERMINAL_PROMPT_HASH_SOURCES:
            raise ValueError(
                "terminal_prompt_hash_source must be one of: "
                f"{', '.join(sorted(_TERMINAL_PROMPT_HASH_SOURCES))}"
            )
        if (
            self.terminal_prompt_hash is None
            and self.terminal_prompt_hash_source != "seed_prompt_unavailable"
        ):
            raise ValueError(
                "terminal_prompt_hash is None only when "
                "terminal_prompt_hash_source is seed_prompt_unavailable"
            )
        _validate_bool(self.compile_success, "compile_success")
        _validate_bool(self.functional_success, "functional_success")
        _validate_optional_bool(self.repair_set_success, "repair_set_success")
        _validate_optional_bool(self.eval_set_success, "eval_set_success")
        _validate_sha256(self.row_source_hash, "row_source_hash")
        if self.private_eval_data_included is not False:
            raise ValueError("private_eval_data_included must be exactly False")
        _validate_failure_path(
            self.failure_path,
            p_loop_fired=self.p_loop_fired,
            p_attempt_count=self.p_attempt_count,
            c_loop_fired=self.c_loop_fired,
            c_attempt_count=self.c_attempt_count,
        )
        _validate_p_loop_consistency(
            p_loop_fired=self.p_loop_fired,
            p_attempt_count=self.p_attempt_count,
            p_terminal_failure_code=self.p_terminal_failure_code,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return _json_dumps(self.to_dict())

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Cluster3TraceSummary":
        if not isinstance(payload, dict):
            raise TypeError("Cluster3TraceSummary.from_dict requires a dict")
        _reject_unknown_fields(cls, payload)
        return cls(**payload)


def build_p_attempt_summary(
    *,
    attempt_index: int,
    generation_seed: int,
    compile_success: bool | None,
    failure_code: str | None,
    compile_error_class: str | None = None,
    compile_error: str | None = None,
    compile_error_excerpt_sha256: str | None = None,
    compile_error_changed_from_previous: bool | None = None,
    source_hash: str | None = None,
    source: str | None = None,
    feedback_sha256: str | None = None,
    feedback: str | None = None,
) -> PRepairAttemptSummary:
    """Build one P attempt summary without retaining source or feedback text."""

    resolved_source_hash = source_hash if source_hash is not None else _sha256_or_none(source)
    resolved_feedback_sha256 = (
        feedback_sha256 if feedback_sha256 is not None else _sha256_or_none(feedback)
    )
    resolved_compile_error_sha256 = (
        compile_error_excerpt_sha256
        if compile_error_excerpt_sha256 is not None
        else _sha256_or_none(compile_error)
    )
    return PRepairAttemptSummary(
        attempt_index=attempt_index,
        generation_seed=generation_seed,
        compile_success=compile_success,
        failure_code=failure_code,
        compile_error_class=compile_error_class,
        compile_error_excerpt_sha256=resolved_compile_error_sha256,
        compile_error_changed_from_previous=compile_error_changed_from_previous,
        source_hash=resolved_source_hash,
        feedback_sha256=resolved_feedback_sha256,
    )


def build_cluster3_trace_summary(
    *,
    condition: str,
    initial_failure_code: str | None = None,
    final_failure_code: str | None = None,
    initial_result: object | None = None,
    p_loop_result: object | None = None,
    c_loop_result: object | None = None,
    p_loop_fired: bool | None = None,
    p_attempt_count: int | None = None,
    p_terminal_failure_code: str | None = None,
    p_compile_repair_succeeded: bool | None = None,
    c_loop_fired: bool | None = None,
    c_loop_source: CTraceSource = "none",
    c_attempt_count: int | None = None,
    c_terminal_failure_code: str | None = None,
    terminal_source_stage: str = "initial",
    terminal_attempt_index: int | None = None,
    terminal_source_hash: str | None = None,
    terminal_source: str | None = None,
    terminal_generation_seed: int = 0,
    terminal_prompt_hash: str | None = None,
    terminal_prompt_hash_source: PromptHashSource = "seed_prompt_unavailable",
    compile_success: bool | None = None,
    functional_success: bool | None = None,
    repair_set_success: bool | None = None,
    eval_set_success: bool | None = None,
    row_source_hash: str | None = None,
    failure_path: Sequence[str] | None = None,
    private_eval_data_included: Literal[False] = False,
) -> Cluster3TraceSummary:
    """Build a source-free terminal trace summary from local orchestration state."""

    resolved_initial_failure = (
        initial_failure_code
        if initial_failure_code is not None
        else _failure_code_from(initial_result)
    )
    resolved_p_loop_fired = bool(p_loop_result is not None) if p_loop_fired is None else p_loop_fired
    resolved_c_loop_fired = (
        bool(c_loop_result is not None or c_loop_source != "none")
        if c_loop_fired is None
        else c_loop_fired
    )
    resolved_p_attempt_count = (
        _generated_p_attempt_count(p_loop_result)
        if p_attempt_count is None
        else p_attempt_count
    )
    resolved_p_terminal_failure_code = (
        p_terminal_failure_code
        if p_terminal_failure_code is not None
        else _failure_code_from(p_loop_result, field_name="final_failure_code")
    )
    resolved_p_compile_repaired = (
        _p_compile_repaired(p_loop_result)
        if p_compile_repair_succeeded is None
        else p_compile_repair_succeeded
    )
    resolved_c_attempt_count = (
        _generated_c_attempt_count(c_loop_result)
        if c_attempt_count is None
        else c_attempt_count
    )
    resolved_c_terminal_failure_code = (
        c_terminal_failure_code
        if c_terminal_failure_code is not None
        else _failure_code_from(c_loop_result, field_name="final_failure_code")
    )
    if final_failure_code is not None:
        resolved_final_failure_code = final_failure_code
    elif resolved_c_loop_fired:
        resolved_final_failure_code = resolved_c_terminal_failure_code
    elif resolved_p_loop_fired:
        resolved_final_failure_code = resolved_p_terminal_failure_code
    else:
        resolved_final_failure_code = resolved_initial_failure
    resolved_terminal_source_hash = (
        terminal_source_hash
        if terminal_source_hash is not None
        else _sha256_or_none(terminal_source)
    )
    if resolved_terminal_source_hash is None:
        raise ValueError("terminal_source_hash or terminal_source is required")
    resolved_row_source_hash = row_source_hash or resolved_terminal_source_hash
    resolved_compile_success = (
        bool(compile_success)
        if compile_success is not None
        else _inferred_compile_success(
            c_loop_result=c_loop_result,
            p_loop_result=p_loop_result,
            initial_result=initial_result,
        )
    )
    resolved_functional_success = (
        bool(functional_success)
        if functional_success is not None
        else _inferred_functional_success(
            c_loop_result=c_loop_result,
            p_loop_result=p_loop_result,
            initial_result=initial_result,
        )
    )
    resolved_failure_path = list(failure_path) if failure_path is not None else _build_failure_path(
        initial_failure_code=resolved_initial_failure,
        p_loop_result=p_loop_result,
        c_loop_fired=resolved_c_loop_fired,
        c_loop_source=c_loop_source,
        c_loop_result=c_loop_result,
        c_attempt_count=resolved_c_attempt_count,
    )

    return Cluster3TraceSummary(
        condition=condition,
        initial_failure_code=resolved_initial_failure,
        final_failure_code=resolved_final_failure_code,
        p_loop_fired=resolved_p_loop_fired,
        p_attempt_count=resolved_p_attempt_count,
        p_terminal_failure_code=resolved_p_terminal_failure_code,
        p_compile_repair_succeeded=resolved_p_compile_repaired,
        c_loop_fired=resolved_c_loop_fired,
        c_loop_source=c_loop_source,
        c_attempt_count=resolved_c_attempt_count,
        c_terminal_failure_code=resolved_c_terminal_failure_code,
        terminal_source_stage=terminal_source_stage,
        terminal_attempt_index=terminal_attempt_index,
        terminal_source_hash=resolved_terminal_source_hash,
        terminal_generation_seed=terminal_generation_seed,
        terminal_prompt_hash=terminal_prompt_hash,
        terminal_prompt_hash_source=terminal_prompt_hash_source,
        compile_success=resolved_compile_success,
        functional_success=resolved_functional_success,
        repair_set_success=repair_set_success,
        eval_set_success=eval_set_success,
        row_source_hash=resolved_row_source_hash,
        failure_path=resolved_failure_path,
        private_eval_data_included=private_eval_data_included,
    )


def _build_failure_path(
    *,
    initial_failure_code: str | None,
    p_loop_result: object | None,
    c_loop_fired: bool,
    c_loop_source: str,
    c_loop_result: object | None,
    c_attempt_count: int,
) -> list[str]:
    path = [f"initial:{_path_code(initial_failure_code)}"]
    p_attempts = _field(p_loop_result, "attempts")
    if isinstance(p_attempts, Sequence):
        for attempt in p_attempts:
            attempt_index = _field(attempt, "attempt_index")
            if attempt_index == 0:
                continue
            path.append(
                f"p_attempt:{attempt_index}:{_path_code(_failure_code_from(attempt))}"
            )
    if c_loop_fired:
        path.append(
            f"c_seed:{_path_code(_c_seed_failure(c_loop_source, p_loop_result, initial_failure_code))}"
        )
        c_attempts = _field(c_loop_result, "attempts")
        added = 0
        if isinstance(c_attempts, Sequence):
            for attempt in c_attempts:
                attempt_index = _field(attempt, "attempt_index")
                if attempt_index == 0:
                    continue
                path.append(
                    f"c_attempt:{attempt_index}:{_path_code(_failure_code_from(attempt))}"
                )
                added += 1
        while added < c_attempt_count:
            added += 1
            path.append(f"c_attempt:{added}:success")
    return path


def _c_seed_failure(
    c_loop_source: str,
    p_loop_result: object | None,
    initial_failure_code: str | None,
) -> str | None:
    if c_loop_source == "post_p_f2":
        return _failure_code_from(p_loop_result, field_name="final_failure_code")
    if c_loop_source == "initial_f2":
        return initial_failure_code
    return None


def _generated_p_attempt_count(p_loop_result: object | None) -> int:
    if p_loop_result is None:
        return 0
    attempts_executed = _field(p_loop_result, "attempts_executed")
    if isinstance(attempts_executed, int) and not isinstance(attempts_executed, bool):
        return max(0, attempts_executed - 1)
    attempts = _field(p_loop_result, "attempts")
    if isinstance(attempts, Sequence):
        return max(0, len(attempts) - 1)
    return 0


def _generated_c_attempt_count(c_loop_result: object | None) -> int:
    if c_loop_result is None:
        return 0
    for field_name in ("c_attempt_count", "generated_attempt_count", "repair_attempt_count"):
        value = _field(c_loop_result, field_name)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    attempts = _field(c_loop_result, "attempts")
    if isinstance(attempts, Sequence):
        return max(0, len(attempts) - 1)
    return 0


def _p_compile_repaired(p_loop_result: object | None) -> bool:
    if p_loop_result is None:
        return False
    status = _field(p_loop_result, "status")
    if status in {"compile_repaired_then_success", "compile_repaired_f2_observed"}:
        return True
    if status == "post_p_f3_observed":
        compile_success = _field(p_loop_result, "terminal_compile_success")
        level_reached = _field(p_loop_result, "terminal_level_reached")
        return compile_success is True or (
            isinstance(level_reached, int)
            and not isinstance(level_reached, bool)
            and level_reached >= 2
        )
    return False


def _failure_code_from(result: object | None, field_name: str = "failure_code") -> str | None:
    value = _field(result, field_name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string when present")
    return value


def _bool_from(result: object | None, field_name: str, default: bool) -> bool:
    value = _field(result, field_name)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise TypeError(f"{field_name} must be a bool when present")


def _optional_bool_from(result: object | None, field_name: str) -> bool | None:
    value = _field(result, field_name)
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    raise TypeError(f"{field_name} must be a bool when present")


def _inferred_compile_success(
    *,
    c_loop_result: object | None,
    p_loop_result: object | None,
    initial_result: object | None,
) -> bool:
    for result, field_name in (
        (c_loop_result, "compile_success"),
        (p_loop_result, "terminal_compile_success"),
        (initial_result, "compile_success"),
    ):
        value = _optional_bool_from(result, field_name)
        if value is not None:
            return value
    return False


def _inferred_functional_success(
    *,
    c_loop_result: object | None,
    p_loop_result: object | None,
    initial_result: object | None,
) -> bool:
    c_value = _optional_bool_from(c_loop_result, "functional_success")
    if c_value is not None:
        return c_value
    p_value = _optional_bool_from(p_loop_result, "functional_success")
    if p_value is not None:
        return p_value
    if _field(p_loop_result, "status") == "compile_repaired_then_success":
        return True
    initial_value = _optional_bool_from(initial_result, "functional_success")
    if initial_value is not None:
        return initial_value
    return False


def _field(result: object | None, field_name: str) -> Any:
    if result is None:
        return None
    if isinstance(result, dict):
        return result.get(field_name)
    return getattr(result, field_name, None)


def _path_code(failure_code: str | None) -> str:
    return failure_code or "success"


def _sha256_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("hash input must be a string when present")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _reject_unknown_fields(cls: type[Any], payload: dict[str, Any]) -> None:
    field_names = {field.name for field in fields(cls)}
    unknown = sorted(set(payload) - field_names)
    if unknown:
        raise ValueError(f"unknown {cls.__name__} fields: {', '.join(unknown)}")


def _validate_failure_path(
    failure_path: list[str],
    *,
    p_loop_fired: bool,
    p_attempt_count: int,
    c_loop_fired: bool,
    c_attempt_count: int,
) -> None:
    if not isinstance(failure_path, list):
        raise TypeError("failure_path must be a list")
    if not failure_path:
        raise ValueError("failure_path must not be empty")
    p_labels = 0
    c_labels = 0
    for label in failure_path:
        if not isinstance(label, str):
            raise TypeError("failure_path entries must be strings")
        if not label or len(label) > 160 or "\n" in label:
            raise ValueError("failure_path entries must be compact one-line labels")
        lower_label = label.lower()
        if any(marker in lower_label for marker in _PRIVATE_MARKERS):
            raise ValueError("failure_path must not include source or private data")
        if not _FAILURE_PATH_LABEL.fullmatch(label):
            raise ValueError(f"invalid failure_path label {label!r}")
        if label.startswith("p_attempt:"):
            p_labels += 1
        elif label.startswith("c_seed:") or label.startswith("c_attempt:"):
            c_labels += 1
    if p_loop_fired:
        if p_labels != p_attempt_count:
            raise ValueError("P failure path length must equal p_attempt_count")
    elif p_labels:
        raise ValueError("failure_path must not contain P labels when P does not fire")
    if c_loop_fired:
        if c_labels != c_attempt_count + 1:
            raise ValueError("C failure path length must equal c_attempt_count + 1")
    elif c_labels:
        raise ValueError("failure_path must not contain C labels when C does not fire")


def _validate_p_loop_consistency(
    *,
    p_loop_fired: bool,
    p_attempt_count: int,
    p_terminal_failure_code: str | None,
) -> None:
    if p_loop_fired:
        return
    if p_attempt_count != 0:
        raise ValueError("p_attempt_count must be 0 when P does not fire")
    if p_terminal_failure_code is not None:
        raise ValueError("p_terminal_failure_code must be None when P does not fire")


def _validate_loop_source_consistency(
    *,
    c_loop_fired: bool,
    c_loop_source: str,
    c_attempt_count: int,
) -> None:
    if c_loop_fired:
        if c_loop_source == "none":
            raise ValueError("c_loop_source cannot be none when C fires")
    else:
        if c_loop_source != "none":
            raise ValueError("c_loop_source must be none when C does not fire")
        if c_attempt_count != 0:
            raise ValueError("c_attempt_count must be 0 when C does not fire")


def _validate_optional_failure_code(value: str | None, field_name: str) -> None:
    if value is None:
        return
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string when present")
    if value not in FAILURE_CODES:
        raise ValueError(f"unsupported {field_name} {value!r}")


def _validate_bool(value: bool, field_name: str) -> None:
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be a bool")


def _validate_optional_bool(value: bool | None, field_name: str) -> None:
    if value is None:
        return
    _validate_bool(value, field_name)


def _require_non_negative_int(value: int, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field_name} must be an int")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")


def _validate_optional_non_negative_int(value: int | None, field_name: str) -> None:
    if value is None:
        return
    _require_non_negative_int(value, field_name)


def _require_non_empty_string(value: str, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _validate_optional_string(value: str | None, field_name: str) -> None:
    if value is None:
        return
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string when present")


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
