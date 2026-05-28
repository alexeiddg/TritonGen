from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
METHODOLOGY_DOC = REPO_ROOT / "docs" / "04_methodology_cluster3.md"
DECISION_LOG = REPO_ROOT / "docs" / "08_decision_log.md"
REGISTRY = REPO_ROOT / "docs" / "05_artifacts_and_results_registry.md"
README = REPO_ROOT / "cluster3" / "README.md"
FAILURE_TAXONOMY = REPO_ROOT / "docs" / "06_failure_taxonomy_and_eval_ladder.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _section(text: str, start_marker: str, end_marker: str) -> str:
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    return text[start:end]


def test_methodology_doc_exists() -> None:
    assert METHODOLOGY_DOC.is_file()


def test_methodology_doc_mentions_compile_error_repair_scope() -> None:
    text = _read(METHODOLOGY_DOC).lower()

    assert "p = compile-error feedback repair" in text
    assert "p observes only `f1_compile`" in text
    assert "f1_runtime is deferred to v2" in text
    assert "no new failure codes" in text
    assert "cluster3_results_schema_version = 1" in text
    assert "compile-error excerpt cap is 2000 chars" in text
    assert "llvm/ptx are allowed" in text


def test_methodology_doc_does_not_claim_paper_scale_results() -> None:
    text = _read(METHODOLOGY_DOC).lower()

    assert "paper-scale cluster 3 results are deferred" in text
    assert "paper-scale deferred" in text
    assert "paper-scale complete" not in text
    assert "cluster 3 results show" not in text
    assert "does not support full 2^3 result claims" in text


def test_methodology_doc_mentions_phase11_requires_user_approval() -> None:
    text = _read(METHODOLOGY_DOC).lower()

    assert "phase 11 n=1 modal smoke requires explicit user approval" in text
    assert "development/pre-modal-smoke" in text


def test_decision_log_mentions_cluster3() -> None:
    text = _read(DECISION_LOG).lower()

    assert "cluster 3" in text
    assert "compile-error-only" in text


def test_decision_log_mentions_f1_runtime_deferred() -> None:
    text = _read(DECISION_LOG).lower()

    assert "f1_runtime is deferred to v2" in text
    assert "`f1_runtime` terminates in v1" in text


def test_decision_log_mentions_no_new_failure_codes() -> None:
    text = _read(DECISION_LOG).lower()

    assert "p does not add new failure codes" in text
    assert "adds no new failure-code names" in text


def test_registry_mentions_cluster3_schema_version() -> None:
    text = _read(REGISTRY)

    assert "Cluster 3 v1 row schema" in text
    assert "`CLUSTER3_RESULTS_SCHEMA_VERSION = 1`" in text
    assert "`cluster3/results/dataclass.py`" in text


def test_registry_mentions_no_p_pair_manifest() -> None:
    text = _read(REGISTRY)

    assert "`cluster3/contracts/no_p_pair_manifest.json`" in text


def test_registry_tracks_cluster3_smoke_without_claiming_scale_outputs() -> None:
    text = _read(REGISTRY)
    cluster3_section = _section(
        text,
        "## 2A. Cluster 3 Planned Artifacts And Schema",
        "## 3. Current Authoritative Artifacts",
    ).lower()

    assert "outputs/cluster3/p_smoke_l4_n1.jsonl" in cluster3_section
    assert "n=1 smoke" in cluster3_section
    assert "row count | schema | status" in cluster3_section
    assert "generated / validated / smoke only / not paper-scale" in cluster3_section
    assert "no p-lift claim" in cluster3_section
    assert "outputs/cluster3/blocked/p_smoke_l4_n1.blocked_attempt_001.jsonl" in cluster3_section
    assert "row count | hash / sidecar | caveats" in cluster3_section
    assert "not valid smoke evidence" in cluster3_section

    planned_paths = (
        "outputs/cluster3/p_dev_l4_n5.jsonl",
        "outputs/cluster3/g_plus_p_dev_l4_n5.jsonl",
        "outputs/cluster3/c_plus_p_dev_l4_n5.jsonl",
        "outputs/cluster3/g_plus_c_plus_p_dev_l4_n5.jsonl",
    )
    for path in planned_paths:
        assert path in cluster3_section
    assert cluster3_section.count("planned / not generated yet") == len(planned_paths)
    assert "no phase 12 cluster 3 rows are registered" in cluster3_section
    assert "no paper-scale p artifacts exist" in cluster3_section
    assert "no performance/speedup/profiler artifacts exist" in cluster3_section


def test_cluster3_readme_status_updated() -> None:
    text = _read(README).lower()

    assert "status: v1 implemented locally through phase 10" in text
    assert "compile-error feedback repair only" in text
    assert "what p observes" in text
    assert "p observes `f1_compile` only" in text


def test_cluster3_readme_defers_profiler_speedup() -> None:
    text = _read(README).lower()

    assert "out of scope" in text
    assert "profiler" in text
    assert "speedup" in text
    assert "timing" in text
    assert "performance feedback" in text
    assert "phase 11 n=1 modal smoke requires explicit user approval" in text


def test_failure_taxonomy_mentions_p_fires_on_f1_compile() -> None:
    text = _read(FAILURE_TAXONOMY).lower()

    assert "cluster 3 p repair fires on f1_compile" in text
    assert "cluster 3 p observes `f1_compile` only" in text
    assert "`f1_runtime` terminates in v1" in text
    assert "no new failure codes are added for p" in text
    assert "f2 remains the c-loop boundary" in text
    assert "f3 remains infrastructure/eval-pipeline" in text


def test_failure_taxonomy_does_not_modify_canonical_code_table_marker_if_present() -> None:
    text = _read(FAILURE_TAXONOMY)

    if "The canonical code registry is `shared/eval/failure_taxonomy.py`" not in text:
        return

    canonical_table = _section(text, "| Family | Meaning | Verified canonical codes |", "Current report-scale artifacts")
    assert "`F1_COMPILE`, `F1_RUNTIME`" in canonical_table
    assert "`F2_NUMERIC_LARGE`, `F2_NUMERIC_NAN`, `F2_SHAPE_MISMATCH`" in canonical_table
    assert "`F3_EVAL_PIPELINE`, `F3_OOB`, `F3_RACE`, `F3_TIMEOUT`" in canonical_table
    assert "P_" not in canonical_table
