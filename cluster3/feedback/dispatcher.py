"""Deterministic Cluster 3 failure-code dispatcher."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from cluster3 import constants
from shared.eval.failure_taxonomy import FAILURE_CODES


DispatchRoute: TypeAlias = Literal["terminate", "p_loop", "c_loop"]
CLoopSource: TypeAlias = Literal["none", "initial_f2"]


@dataclass(frozen=True)
class DispatchDecision:
    route: DispatchRoute
    reason: str
    failure_code: str | None
    c_loop_source: CLoopSource = "none"


def dispatch(
    condition: str,
    failure_code: str | None,
    level_reached: int | None,
    *,
    functional_success: bool | None = None,
) -> DispatchDecision:
    """Route an initial Cluster 3 evaluation result to terminal, P, or C."""

    normalized_condition = constants.normalize_cluster3_condition(condition)
    p_active, c_active = _active_factors(normalized_condition)
    if not p_active:
        raise ValueError(f"Cluster 3 condition {condition!r} must activate P")

    _validate_failure_code(failure_code)
    _validate_level_reached(level_reached)
    if level_reached is not None and failure_code is not None:
        _validate_failure_code_level_compatibility(failure_code, level_reached)

    if functional_success is True or failure_code is None:
        return DispatchDecision(
            route="terminate",
            reason="success",
            failure_code=None,
        )

    if level_reached is None:
        return DispatchDecision(
            route="terminate",
            reason="level_reached_missing",
            failure_code=failure_code,
        )

    if failure_code.startswith("F0_"):
        return DispatchDecision(
            route="terminate",
            reason="f0_terminal",
            failure_code=failure_code,
        )

    if failure_code == "F1_COMPILE":
        return DispatchDecision(
            route="p_loop",
            reason="p_eligible",
            failure_code=failure_code,
        )

    if failure_code == "F1_RUNTIME":
        return DispatchDecision(
            route="terminate",
            reason="unrecoverable_runtime",
            failure_code=failure_code,
        )

    if failure_code.startswith("F2_"):
        if c_active:
            return DispatchDecision(
                route="c_loop",
                reason="c_eligible_initial_f2",
                failure_code=failure_code,
                c_loop_source="initial_f2",
            )
        return DispatchDecision(
            route="terminate",
            reason="f2_terminal_no_c",
            failure_code=failure_code,
        )

    if failure_code.startswith("F3_"):
        return DispatchDecision(
            route="terminate",
            reason="f3_terminal",
            failure_code=failure_code,
        )

    raise ValueError(f"unsupported failure code family for {failure_code!r}")


def is_p_eligible(failure_code: str | None) -> bool:
    """Return whether a failure code is eligible for the P loop by code alone."""

    return failure_code in constants.P_ELIGIBLE_FAILURE_CODES


def _active_factors(condition: str) -> tuple[bool, bool]:
    c_active = condition in {"C+P", "G+C+P"}
    return True, c_active


def _validate_failure_code(failure_code: str | None) -> None:
    if failure_code is None:
        return
    if failure_code not in FAILURE_CODES:
        raise ValueError(f"unknown failure_code {failure_code!r}")


def _validate_level_reached(level_reached: int | None) -> None:
    if level_reached is None:
        return
    if not isinstance(level_reached, int) or isinstance(level_reached, bool):
        raise ValueError("level_reached must be an integer or None")
    if level_reached < 0:
        raise ValueError("level_reached must be non-negative")


def _validate_failure_code_level_compatibility(
    failure_code: str,
    level_reached: int,
) -> None:
    if failure_code.startswith("F0_"):
        _require_level(failure_code, level_reached, expected=0)
        return
    if failure_code.startswith("F1_"):
        _require_level(failure_code, level_reached, expected=1)
        return
    if failure_code.startswith("F2_"):
        if level_reached < 2:
            raise ValueError(
                f"{failure_code} requires level_reached >= 2, got {level_reached}"
            )
        return
    if failure_code.startswith("F3_"):
        return
    raise ValueError(f"unsupported failure code family for {failure_code!r}")


def _require_level(failure_code: str, level_reached: int, *, expected: int) -> None:
    if level_reached != expected:
        raise ValueError(
            f"{failure_code} requires level_reached == {expected}, got {level_reached}"
        )


__all__ = [
    "CLoopSource",
    "DispatchDecision",
    "DispatchRoute",
    "dispatch",
    "is_p_eligible",
]
