"""Local 12-cell grammar-mode x C x P planning matrix.

This module is intentionally planning-only. It defines labels and expected
metadata for future launch packets but does not invoke generation, Modal,
correctness evaluation, output writing, tracking, or artifact refreshes.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from cluster3.constants import P_HISTORY_POLICY_V1
from shared.factors.cells import FactorCell, require_valid_factor_cell
from shared.factors.grammar_modes import (
    GRAMMAR_MODE_VALUES,
    GrammarMode,
    grammar_mode_config,
)


@dataclass(frozen=True)
class GrammarModeCellSpec:
    """One planned L1a grammar-mode/C/P cell."""

    condition_name: str
    factor_cell: FactorCell
    grammar_mode: GrammarMode
    grammar_active: bool
    grammar_variant: str | None
    grammar_path: str | None
    grammar_claim_scope: str | None
    correctness_feedback_active: bool
    compile_feedback_active: bool
    repair_history_policy: str
    output_namespace_suffix: str
    expected_eligibility_notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_l1a_grammar_mode_cp_matrix(
    *,
    repair_history_policy: str = P_HISTORY_POLICY_V1,
) -> tuple[GrammarModeCellSpec, ...]:
    """Return the 12 local specs for ``grammar_mode x C x P`` L1a planning."""

    cells: list[GrammarModeCellSpec] = []
    for grammar_mode in GRAMMAR_MODE_VALUES:
        for correctness_feedback_active, compile_feedback_active in (
            (False, False),
            (True, False),
            (False, True),
            (True, True),
        ):
            config = grammar_mode_config(grammar_mode)
            factor_parts: list[str] = []
            if config.grammar_active:
                factor_parts.append("G")
            if correctness_feedback_active:
                factor_parts.append("C")
            if compile_feedback_active:
                factor_parts.append("P")
            factor_cell = require_valid_factor_cell(
                "+".join(factor_parts) if factor_parts else "none"
            )
            cells.append(
                GrammarModeCellSpec(
                    condition_name=_condition_name(
                        grammar_mode=grammar_mode,
                        correctness_feedback_active=correctness_feedback_active,
                        compile_feedback_active=compile_feedback_active,
                    ),
                    factor_cell=factor_cell,
                    grammar_mode=config.grammar_mode,
                    grammar_active=config.grammar_active,
                    grammar_variant=config.grammar_variant,
                    grammar_path=config.grammar_path,
                    grammar_claim_scope=config.grammar_claim_scope,
                    correctness_feedback_active=correctness_feedback_active,
                    compile_feedback_active=compile_feedback_active,
                    repair_history_policy=repair_history_policy,
                    output_namespace_suffix=_output_namespace_suffix(
                        grammar_mode=grammar_mode,
                        correctness_feedback_active=correctness_feedback_active,
                        compile_feedback_active=compile_feedback_active,
                    ),
                    expected_eligibility_notes=_eligibility_notes(
                        grammar_active=config.grammar_active,
                        correctness_feedback_active=correctness_feedback_active,
                        compile_feedback_active=compile_feedback_active,
                    ),
                )
            )
    _validate_unique_specs(cells)
    return tuple(cells)


def _condition_name(
    *,
    grammar_mode: str,
    correctness_feedback_active: bool,
    compile_feedback_active: bool,
) -> str:
    parts = [grammar_mode]
    if correctness_feedback_active:
        parts.append("C")
    if compile_feedback_active:
        parts.append("P")
    return "+".join(parts)


def _output_namespace_suffix(
    *,
    grammar_mode: str,
    correctness_feedback_active: bool,
    compile_feedback_active: bool,
) -> str:
    return (
        f"{grammar_mode}__c_{_on_off(correctness_feedback_active)}"
        f"__p_{_on_off(compile_feedback_active)}"
    )


def _on_off(value: bool) -> str:
    return "on" if value else "off"


def _eligibility_notes(
    *,
    grammar_active: bool,
    correctness_feedback_active: bool,
    compile_feedback_active: bool,
) -> tuple[str, ...]:
    notes = [
        (
            "grammar metadata required for active grammar rows"
            if grammar_active
            else "grammar metadata must be absent for grammar_off rows"
        )
    ]
    notes.append(
        "C loop eligible only for F2 failures"
        if correctness_feedback_active
        else "C loop must not fire"
    )
    notes.append(
        "P loop eligible only for F1_COMPILE failures"
        if compile_feedback_active
        else "P loop must not fire"
    )
    return tuple(notes)


def _validate_unique_specs(cells: list[GrammarModeCellSpec]) -> None:
    condition_names = [cell.condition_name for cell in cells]
    if len(condition_names) != len(set(condition_names)):
        raise ValueError("duplicate grammar-mode condition_name values")
    suffixes = [cell.output_namespace_suffix for cell in cells]
    if len(suffixes) != len(set(suffixes)):
        raise ValueError("duplicate grammar-mode output namespace suffixes")
