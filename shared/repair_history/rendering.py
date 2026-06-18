"""Byte-stable Agentic Transcript v1 prompt rendering."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import hashlib

from cluster2.constants import AGENTIC_TRANSCRIPT_REPAIR_HISTORY_POLICY_V1

from shared.repair_history.errors import (
    MissingAnchorSourceError,
    PromptBudgetExceededError,
)
from shared.repair_history.evidence import (
    LoopKind,
    RepairAttemptEvidence,
    RepairSourceRecord,
    latest_attempt_is_repairable,
    source_hash_counts,
    validate_attempt_history,
    validate_prompt_visible_text,
    validate_source_records,
)
from shared.repair_history.policies import (
    RepairHistoryConfig,
    should_render_agentic_transcript,
)
from shared.repair_history.ranking import select_best_anchor


DEFAULT_AGENTIC_TRANSCRIPT_INSTRUCTION = (
    "Produce a corrected complete Triton Python module. Do not explain. "
    "Do not concatenate prior attempts. Use the history only to avoid repeated mistakes."
)
SECTION_ORDER: tuple[str, ...] = (
    "Base task",
    "Repair objective",
    "Attempt history",
    "Best previous source to repair from",
    "Latest failed source",
    "Latest failure details",
    "Instruction",
)


@dataclass(frozen=True)
class RenderedRepairPrompt:
    """Rendered prompt plus stable metadata hashes."""

    text: str
    repair_prompt_sha256: str
    repair_history_summary_sha256: str
    anchor_attempt_index: int
    latest_attempt_index: int
    include_latest_source: bool
    repair_history_policy: str
    max_prompt_chars: int


def render_repair_history_prompt(
    *,
    base_task: str,
    repair_objective: str,
    attempts: Sequence[RepairAttemptEvidence],
    source_records: Sequence[RepairSourceRecord],
    latest_failure_details: str | None,
    loop_kind: LoopKind,
    config: RepairHistoryConfig,
    instruction: str = DEFAULT_AGENTIC_TRANSCRIPT_INSTRUCTION,
) -> RenderedRepairPrompt | None:
    """Render an opt-in agentic transcript prompt or return None for legacy paths."""

    if not should_render_agentic_transcript(config):
        return None
    if config.repair_history_policy != AGENTIC_TRANSCRIPT_REPAIR_HISTORY_POLICY_V1:
        return None

    _require_text(base_task, "base_task")
    _require_text(repair_objective, "repair_objective")
    _require_text(instruction, "instruction")
    validate_prompt_visible_text(
        latest_failure_details,
        field_name="latest_failure_details",
    )

    ordered = validate_attempt_history(attempts, loop_kind=loop_kind)
    latest = ordered[-1]
    if not latest_attempt_is_repairable(latest, loop_kind=loop_kind):
        return None

    sources_by_attempt = validate_source_records(source_records)
    anchor = select_best_anchor(ordered, loop_kind=loop_kind)
    try:
        anchor_source = sources_by_attempt[anchor.attempt_index]
    except KeyError as exc:
        raise MissingAnchorSourceError(
            f"missing source for anchor attempt {anchor.attempt_index}"
        ) from exc
    if anchor_source.source_hash != anchor.source_hash:
        raise MissingAnchorSourceError(
            f"source hash mismatch for anchor attempt {anchor.attempt_index}"
        )

    latest_source = sources_by_attempt.get(latest.attempt_index)
    if config.include_latest_source and latest_source is None:
        raise MissingAnchorSourceError(
            f"missing source for latest attempt {latest.attempt_index}"
        )
    if latest_source is not None and latest_source.source_hash != latest.source_hash:
        raise MissingAnchorSourceError(
            f"source hash mismatch for latest attempt {latest.attempt_index}"
        )

    history_body = render_attempt_history_body(
        ordered,
        anchor_attempt_index=anchor.attempt_index,
        latest_attempt_index=latest.attempt_index,
    )
    failure_details = _compact_text(latest_failure_details) or (
        _compact_text(latest.public_failure_summary) or "unavailable"
    )
    include_latest = config.include_latest_source
    text = _assemble_prompt(
        base_task=base_task,
        repair_objective=repair_objective,
        history_body=history_body,
        anchor_source=anchor_source.source_text,
        latest_source=latest_source.source_text if include_latest and latest_source else None,
        latest_failure_details=failure_details,
        instruction=instruction,
    )
    if len(text) > config.max_prompt_chars and include_latest:
        include_latest = False
        text = _assemble_prompt(
            base_task=base_task,
            repair_objective=repair_objective,
            history_body=history_body,
            anchor_source=anchor_source.source_text,
            latest_source=None,
            latest_failure_details=failure_details,
            instruction=instruction,
        )
    if len(text) > config.max_prompt_chars:
        raise PromptBudgetExceededError(
            "agentic transcript prompt exceeds max_prompt_chars"
        )
    return RenderedRepairPrompt(
        text=text,
        repair_prompt_sha256=_sha256(text),
        repair_history_summary_sha256=_sha256(history_body),
        anchor_attempt_index=anchor.attempt_index,
        latest_attempt_index=latest.attempt_index,
        include_latest_source=include_latest,
        repair_history_policy=config.repair_history_policy,
        max_prompt_chars=config.max_prompt_chars,
    )


def render_attempt_history_body(
    attempts: Sequence[RepairAttemptEvidence],
    *,
    anchor_attempt_index: int,
    latest_attempt_index: int,
) -> str:
    """Render the compact Attempt history section body."""

    counts = source_hash_counts(attempts)
    lines: list[str] = []
    for attempt in sorted(attempts, key=lambda item: item.attempt_index):
        summary = _compact_text(attempt.public_failure_summary) or "unavailable"
        outcome = "success" if attempt.functional_success is True else (
            attempt.failure_code or "UNKNOWN"
        )
        level = (
            str(attempt.level_reached)
            if attempt.level_reached is not None
            else "unknown"
        )
        parts = [
            f"Attempt {attempt.attempt_index}: seed={attempt.generation_seed}",
            f"source_sha256={attempt.source_hash}",
            f"prompt_sha256={attempt.prompt_hash or 'unavailable'}",
            f"outcome={outcome}",
            f"level={level}",
            f"anchor={_yes_no(attempt.attempt_index == anchor_attempt_index)}",
            f"latest={_yes_no(attempt.attempt_index == latest_attempt_index)}",
            f"summary={summary}",
        ]
        if attempt.repair_shapes_passed is not None and attempt.num_repair_shapes is not None:
            parts.append(
                f"c_repair_shapes={attempt.repair_shapes_passed}/{attempt.num_repair_shapes}"
            )
        if (
            attempt.public_eval_shapes_passed is not None
            and attempt.num_public_eval_shapes is not None
        ):
            parts.append(
                "c_public_eval_shapes="
                f"{attempt.public_eval_shapes_passed}/{attempt.num_public_eval_shapes}"
            )
        if attempt.compile_error_type:
            parts.append(f"p_compile_error_type={_compact_text(attempt.compile_error_type)}")
        if attempt.compile_error_changed_from_previous is not None:
            parts.append(
                "p_compile_error_changed="
                f"{_yes_no(attempt.compile_error_changed_from_previous)}"
            )
        if counts[attempt.source_hash] > 1:
            parts.append("repeated_source_sha256=yes")
        lines.append("; ".join(parts))
    return "\n".join(lines)


def _assemble_prompt(
    *,
    base_task: str,
    repair_objective: str,
    history_body: str,
    anchor_source: str,
    latest_source: str | None,
    latest_failure_details: str,
    instruction: str,
) -> str:
    sections: list[tuple[str, str]] = [
        ("Base task", base_task),
        ("Repair objective", repair_objective),
        ("Attempt history", history_body),
        (
            "Best previous source to repair from",
            f"BEGIN BEST PREVIOUS SOURCE\n{anchor_source}\nEND BEST PREVIOUS SOURCE",
        ),
    ]
    if latest_source is not None:
        sections.append(
            (
                "Latest failed source",
                f"BEGIN LATEST FAILED SOURCE\n{latest_source}\nEND LATEST FAILED SOURCE",
            )
        )
    sections.extend(
        [
            (
                "Latest failure details",
                "BEGIN LATEST FAILURE DETAILS\n"
                f"{latest_failure_details}\n"
                "END LATEST FAILURE DETAILS",
            ),
            ("Instruction", instruction),
        ]
    )
    return "\n\n".join(f"{name}:\n{body}" for name, body in sections)


def _compact_text(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.split()).strip()


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _require_text(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
