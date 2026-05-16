"""Guard against KernelBench problem-ID drift across Cluster 1 contracts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from cluster1.data.kernels import KERNEL_SPECS
from cluster1.experiments.kernelbench_adapter import _resolve_problem_id


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / ".contracts" / "agentic" / "cluster1_contract.md"
MANIFEST_PATH = (
    REPO_ROOT / "cluster2" / "contracts" / "frozen_cluster1_artifacts_manifest.json"
)

DATASET_ID = "ScalingIntelligence/KernelBench"
CANONICAL_IDS = {
    "elementwise": 19,
    "reduction": 23,
    "matmul": 1,
}

CONTRACT_TABLE_PATTERNS = {
    "elementwise": re.compile(
        r"^\|\s*ReLU\s*\|.*?\|\s*KernelBench level 1,\s*problem\s+(\d+)\s*\|",
        re.MULTILINE,
    ),
    "reduction": re.compile(
        r"^\|\s*Softmax\s*\|.*?\|\s*KernelBench level 1,\s*problem\s+(\d+)\s*\|",
        re.MULTILINE,
    ),
    "matmul": re.compile(
        r"^\|\s*Tiled GEMM\s*\|.*?\|\s*KernelBench level 1,\s*problem\s+(\d+)\s*\|",
        re.MULTILINE,
    ),
}

CONTRACT_PINNED_IDS_PATTERN = re.compile(
    r"The locked Cluster 1 KernelBench Level 1 problem IDs are "
    r"ReLU=(\d+), Softmax=(\d+), and GEMM/Matmul=(\d+)\."
)


def _extract_contract_ids(markdown: str) -> dict[str, int]:
    table_ids: dict[str, int] = {}
    for kernel_class, pattern in CONTRACT_TABLE_PATTERNS.items():
        match = pattern.search(markdown)
        assert match is not None, (
            f"Cluster 1 contract is missing an explicit KernelBench Level 1 "
            f"problem ID table entry for {kernel_class}"
        )
        table_ids[kernel_class] = int(match.group(1))

    pinned_match = CONTRACT_PINNED_IDS_PATTERN.search(markdown)
    assert pinned_match is not None, (
        "Cluster 1 contract is missing the locked-ID pinning sentence for "
        "ReLU, Softmax, and GEMM/Matmul"
    )
    pinned_ids = {
        "elementwise": int(pinned_match.group(1)),
        "reduction": int(pinned_match.group(2)),
        "matmul": int(pinned_match.group(3)),
    }

    assert table_ids == pinned_ids, (
        f"Cluster 1 contract table IDs {table_ids} disagree with pinned "
        f"sentence IDs {pinned_ids}"
    )
    return table_ids


def _extract_manifest_ids(manifest_json: str) -> dict[str, int]:
    manifest = json.loads(manifest_json)
    entries = manifest.get("scale_requirements", {}).get("locked_kernel_classes")
    assert isinstance(entries, list), (
        "frozen Cluster 1 manifest is missing scale_requirements.locked_kernel_classes"
    )

    ids: dict[str, int] = {}
    for entry in entries:
        kernel_class = entry.get("kernel_class")
        if kernel_class not in CANONICAL_IDS:
            continue

        assert entry.get("dataset_id") == DATASET_ID, (
            f"frozen Cluster 1 manifest dataset_id mismatch for {kernel_class}: "
            f"expected {DATASET_ID}, got {entry.get('dataset_id')!r}"
        )
        problem_id = entry.get("dataset_problem_id")
        assert isinstance(problem_id, int), (
            f"frozen Cluster 1 manifest dataset_problem_id for {kernel_class} "
            f"must be an int, got {problem_id!r}"
        )
        ids[kernel_class] = problem_id

    return ids


def _extract_kernel_spec_ids() -> dict[str, int]:
    ids: dict[str, int] = {}
    for kernel_class, spec in KERNEL_SPECS.items():
        assert spec.dataset_id == DATASET_ID, (
            f"KernelSpec dataset_id mismatch for {kernel_class}: expected "
            f"{DATASET_ID}, got {spec.dataset_id!r}"
        )
        ids[kernel_class] = spec.dataset_problem_id
    return ids


def _extract_kernelbench_export_ids() -> dict[str, int]:
    return {
        kernel_class: _resolve_problem_id(SimpleNamespace(kernel_class=kernel_class))
        for kernel_class in CANONICAL_IDS
    }


def _assert_source_ids(source_name: str, observed: dict[str, int]) -> None:
    assert set(observed) == set(CANONICAL_IDS), (
        f"{source_name} must define exactly the locked kernel classes "
        f"{sorted(CANONICAL_IDS)}; got {sorted(observed)}"
    )
    for kernel_class, expected_problem_id in CANONICAL_IDS.items():
        observed_problem_id = observed[kernel_class]
        assert observed_problem_id == expected_problem_id, (
            f"{source_name} mismatch for {kernel_class}: expected KernelBench "
            f"Level 1 problem {expected_problem_id}, got {observed_problem_id}"
        )


def test_contract_parser_extracts_table_and_pinned_ids() -> None:
    markdown = """
| Kernel | Class | KernelBench Source | Reference Signature (locked) |
|---|---|---|---|
| ReLU | Elementwise / memory-bound | KernelBench level 1, problem 19 | `relu(...)` |
| Softmax | Reduction / memory-bound | KernelBench level 1, problem 23 | `softmax(...)` |
| Tiled GEMM | Matmul-class / compute-bound | KernelBench level 1, problem 1 | `matmul(...)` |

The locked Cluster 1 KernelBench Level 1 problem IDs are ReLU=19, Softmax=23, and GEMM/Matmul=1.
"""

    assert _extract_contract_ids(markdown) == CANONICAL_IDS


def test_contract_parser_rejects_internal_contract_drift() -> None:
    markdown = """
| Kernel | Class | KernelBench Source | Reference Signature (locked) |
|---|---|---|---|
| ReLU | Elementwise / memory-bound | KernelBench level 1, problem 1 | `relu(...)` |
| Softmax | Reduction / memory-bound | KernelBench level 1, problem 23 | `softmax(...)` |
| Tiled GEMM | Matmul-class / compute-bound | KernelBench level 1, problem 1 | `matmul(...)` |

The locked Cluster 1 KernelBench Level 1 problem IDs are ReLU=19, Softmax=23, and GEMM/Matmul=1.
"""

    with pytest.raises(AssertionError, match="contract table IDs"):
        _extract_contract_ids(markdown)


def test_manifest_parser_extracts_locked_kernel_classes() -> None:
    manifest_json = json.dumps(
        {
            "scale_requirements": {
                "locked_kernel_classes": [
                    {
                        "kernel_class": "elementwise",
                        "dataset_id": DATASET_ID,
                        "dataset_problem_id": 19,
                    },
                    {
                        "kernel_class": "reduction",
                        "dataset_id": DATASET_ID,
                        "dataset_problem_id": 23,
                    },
                    {
                        "kernel_class": "matmul",
                        "dataset_id": DATASET_ID,
                        "dataset_problem_id": 1,
                    },
                ]
            }
        }
    )

    assert _extract_manifest_ids(manifest_json) == CANONICAL_IDS


def test_source_id_assertion_reports_mismatch() -> None:
    with pytest.raises(AssertionError, match="sample source mismatch for elementwise"):
        _assert_source_ids(
            "sample source",
            {
                "elementwise": 1,
                "reduction": 23,
                "matmul": 1,
            },
        )


def test_contract_manifest_kernel_specs_and_export_adapter_agree() -> None:
    sources = {
        "Cluster 1 contract": _extract_contract_ids(CONTRACT_PATH.read_text()),
        "frozen Cluster 1 manifest": _extract_manifest_ids(MANIFEST_PATH.read_text()),
        "Cluster 1 KernelSpec definitions": _extract_kernel_spec_ids(),
        "KernelBench export adapter": _extract_kernelbench_export_ids(),
    }

    for source_name, ids in sources.items():
        _assert_source_ids(source_name, ids)

    contract_ids = sources["Cluster 1 contract"]
    for source_name, ids in sources.items():
        assert ids == contract_ids, (
            f"{source_name} IDs {ids} disagree with Cluster 1 contract IDs "
            f"{contract_ids}"
        )
