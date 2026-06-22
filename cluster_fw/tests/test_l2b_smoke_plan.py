from __future__ import annotations

from collections import Counter, defaultdict

from cluster_fw.planning.l2b_smoke import (
    DTYPE_NAMES,
    FIREWORKS_GBNF_N20_EXPECTED_ROWS_PER_MODEL,
    FIREWORKS_GBNF_N20_RUN_TIER,
    FIREWORKS_L2B_EXPECTED_ROWS_PER_MODEL,
    KERNEL_CLASS_NAMES,
    build_l2b_smoke_plan,
)


def test_l2b_n2_plan_is_12_cells_all_kernel_classes_all_dtypes() -> None:
    plan = build_l2b_smoke_plan(model_slots=("FW-A",), n=2)

    assert len(plan) == FIREWORKS_L2B_EXPECTED_ROWS_PER_MODEL
    assert len({row.condition_id for row in plan}) == 12
    assert {row.kernel_class for row in plan} == set(KERNEL_CLASS_NAMES)
    assert {row.dtype for row in plan} == set(DTYPE_NAMES)

    grouped: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for row in plan:
        grouped[(row.condition_id, row.kernel_class, row.dtype)].append(row.seed)

    assert len(grouped) == 12 * len(KERNEL_CLASS_NAMES) * len(DTYPE_NAMES)
    assert all(sorted(seeds) == [0, 1] for seeds in grouped.values())


def test_l2b_default_plan_has_two_fireworks_models() -> None:
    plan = build_l2b_smoke_plan(n=2)
    per_model = Counter(row.model_slot for row in plan)

    assert per_model == {
        "FW-A": FIREWORKS_L2B_EXPECTED_ROWS_PER_MODEL,
        "FW-B": FIREWORKS_L2B_EXPECTED_ROWS_PER_MODEL,
    }
    assert len(plan) == FIREWORKS_L2B_EXPECTED_ROWS_PER_MODEL * 2


def test_l2b_plan_accepts_model_id_override_without_changing_matrix() -> None:
    plan = build_l2b_smoke_plan(
        model_slots=("FW-A",),
        n=1,
        model_id_overrides={"FW-A": "accounts/example/models/deployed-r1"},
    )

    assert {row.model_id for row in plan} == {"accounts/example/models/deployed-r1"}
    assert len(plan) == 12 * len(KERNEL_CLASS_NAMES) * len(DTYPE_NAMES)


def test_gbnf_n20_plan_has_paper_scale_row_count_and_tier() -> None:
    plan = build_l2b_smoke_plan(
        model_slots=("FW-B",),
        n=20,
        provider_api="chat_completions",
        run_tier=FIREWORKS_GBNF_N20_RUN_TIER,
    )

    assert len(plan) == FIREWORKS_GBNF_N20_EXPECTED_ROWS_PER_MODEL
    assert {row.run_tier for row in plan} == {FIREWORKS_GBNF_N20_RUN_TIER}
    assert len({row.condition_id for row in plan}) == 12


def test_gbnf_n20_wave_selectors_are_540_rows_each() -> None:
    for wave in ("wave_1", "wave_2", "wave_3", "wave_4"):
        plan = build_l2b_smoke_plan(
            model_slots=("FW-B",),
            condition_selector=wave,
            n=20,
            provider_api="chat_completions",
            run_tier=FIREWORKS_GBNF_N20_RUN_TIER,
        )

        assert len(plan) == 3 * len(KERNEL_CLASS_NAMES) * len(DTYPE_NAMES) * 20
        assert len({row.condition_id for row in plan}) == 3
