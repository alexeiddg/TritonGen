"""Coverage feasibility metrics for Phase 13 Cluster 2 reporting."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from typing import Any

from cluster2.results.dataclass import Cluster2EvalRow


COVERAGE_OK_STATUS = "ok"
COVERAGE_FAILURE_PREFIX = "coverage_failure_"


@dataclass(frozen=True)
class CoverageSummary:
    """Coverage as a gating/feasibility summary, separate from outcomes."""

    total_records: int
    covered_records: int
    coverage_failures: int
    candidate_failures: int
    coverage_rate: float
    passed: bool
    failure_reasons: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_coverage(
    coverage_status_records: Iterable[Cluster2EvalRow | Mapping[str, Any] | object],
) -> CoverageSummary:
    """Compute coverage without treating candidate failures as coverage failures."""

    total = 0
    covered = 0
    coverage_failures = 0
    candidate_failures = 0
    reasons: Counter[str] = Counter()

    for record in coverage_status_records:
        total += 1
        if isinstance(record, Cluster2EvalRow):
            covered += 1
            if not record.functional_success:
                candidate_failures += 1
            continue

        status = _status(record)
        if status.startswith(COVERAGE_FAILURE_PREFIX):
            coverage_failures += 1
            reasons[status] += 1
            continue

        covered += 1
        if status != COVERAGE_OK_STATUS:
            candidate_failures += 1
            reasons[status] += 1

    coverage_rate = 0.0 if total == 0 else covered / total
    return CoverageSummary(
        total_records=total,
        covered_records=covered,
        coverage_failures=coverage_failures,
        candidate_failures=candidate_failures,
        coverage_rate=coverage_rate,
        passed=coverage_failures == 0,
        failure_reasons=dict(sorted(reasons.items())),
    )


def _status(record: Mapping[str, Any] | object) -> str:
    if isinstance(record, Mapping):
        value = record.get("status")
    else:
        value = getattr(record, "status", None)
    if not isinstance(value, str) or not value:
        raise ValueError("coverage status records must expose a non-empty status")
    return value
