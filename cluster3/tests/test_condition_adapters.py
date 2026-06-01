import pytest

from cluster3 import constants
from cluster3.feedback.condition_adapters import (
    _CLUSTER3_TO_CLUSTER2_GENERATION,
    _CLUSTER3_TO_CLUSTER2_REPAIR,
    cluster3_to_cluster2_eval_condition,
    cluster3_to_cluster2_generation_condition,
    cluster3_to_cluster2_repair_condition,
    restamp_cluster3_condition,
)


def test_condition_adapter_tables_match_constants() -> None:
    assert _CLUSTER3_TO_CLUSTER2_GENERATION == constants._CLUSTER3_TO_CLUSTER2_GENERATION
    assert _CLUSTER3_TO_CLUSTER2_REPAIR == constants._CLUSTER3_TO_CLUSTER2_REPAIR


def test_generation_adapter_maps_p_to_c_and_gp_to_gc() -> None:
    assert {
        condition: cluster3_to_cluster2_generation_condition(condition)
        for condition in constants.CLUSTER3_CONDITIONS
    } == {"P": "C", "C+P": "C", "G+P": "G+C", "G+C+P": "G+C"}


def test_generation_adapter_rejects_unknown_condition() -> None:
    for condition in ("none", "C", "G", "G+C", "X"):
        with pytest.raises(ValueError):
            cluster3_to_cluster2_generation_condition(condition)


def test_eval_adapter_matches_generation_adapter() -> None:
    for condition in constants.CLUSTER3_CONDITIONS:
        assert cluster3_to_cluster2_eval_condition(
            condition
        ) == cluster3_to_cluster2_generation_condition(condition)


def test_repair_adapter_maps_cp_and_gcp() -> None:
    assert cluster3_to_cluster2_repair_condition("C+P") == "C"
    assert cluster3_to_cluster2_repair_condition("G+C+P") == "G+C"


def test_repair_adapter_rejects_p_and_gp() -> None:
    for condition in ("P", "G+P"):
        with pytest.raises(ValueError):
            cluster3_to_cluster2_repair_condition(condition)


def test_restamp_cluster3_condition_overwrites_returned_payload() -> None:
    payload = {
        "condition": "C",
        "surface": "c2_remote_correctness",
        "identity": {"condition": "C"},
        "source_identity": {"condition": "C"},
        "eval_identity": {"condition": "C"},
        "correctness_result": {"identity": {"condition": "C"}},
    }

    restamp_cluster3_condition(payload, "P")

    assert payload["condition"] == "P"
    assert payload["surface"] == "c3_remote_correctness"
    assert payload["identity"]["condition"] == "P"
    assert payload["source_identity"]["condition"] == "P"
    assert payload["eval_identity"]["condition"] == "P"
    assert payload["correctness_result"]["identity"]["condition"] == "P"

