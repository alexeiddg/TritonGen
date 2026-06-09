"""L2b n=2 Fireworks smoke matrix."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from cluster1.data.kernels import KERNEL_SPECS
from cluster1.data.prompts.prompt_contract import build_prompt
from cluster2.constants import DTYPE_NAMES
from cluster3.planning.grammar_mode_matrix import (
    L1A_GRAMMAR_MODE_CP_SELECTOR,
    build_l1a_grammar_mode_cp_matrix,
)

ProviderApi = Literal["responses", "chat_completions"]
FireworksRunTier = Literal["l2b_n2_smoke", "fireworks_gbnf_n20"]

FIREWORKS_EXPERIMENT_ID = "fireworks_api_modal_v1"
FIREWORKS_L2B_SCALE_NAMESPACE = "l2b_n2"
FIREWORKS_L2B_RUN_TIER = "l2b_n2_smoke"
FIREWORKS_L2B_RUN_ID_PREFIX = f"{FIREWORKS_EXPERIMENT_ID}_{FIREWORKS_L2B_SCALE_NAMESPACE}"
FIREWORKS_L2B_OUTPUT_ROOT = (
    f"outputs/cluster_fw/{FIREWORKS_EXPERIMENT_ID}/{FIREWORKS_L2B_SCALE_NAMESPACE}"
)
FIREWORKS_L2B_AUTHORIZATION_TOKEN = "FIREWORKS_API_MODAL_L2B_N2_AUTHORIZATION_PACKET_V1"
FIREWORKS_GBNF_N20_SCALE_NAMESPACE = "l2_n20_gbnf"
FIREWORKS_GBNF_N20_RUN_TIER = "fireworks_gbnf_n20"
FIREWORKS_GBNF_N20_OUTPUT_ROOT = (
    f"outputs/cluster_fw/{FIREWORKS_EXPERIMENT_ID}/{FIREWORKS_GBNF_N20_SCALE_NAMESPACE}"
)
FIREWORKS_GBNF_N20_AUTHORIZATION_TOKEN = (
    "FIREWORKS_API_MODAL_GBNF_N20_AUTHORIZATION_PACKET_V1"
)

KERNEL_CLASS_NAMES: tuple[str, ...] = ("elementwise", "reduction", "matmul")
FIREWORKS_MODEL_IDS: dict[str, str] = {
    "FW-A": "accounts/fireworks/models/deepseek-r1",
    "FW-B": "accounts/fireworks/models/llama-v3p1-405b-instruct",
}
FIREWORKS_MODEL_SLOTS: tuple[str, ...] = tuple(FIREWORKS_MODEL_IDS)
FIREWORKS_L2B_EXPECTED_ROWS_PER_MODEL = 12 * len(KERNEL_CLASS_NAMES) * len(DTYPE_NAMES) * 2
FIREWORKS_GBNF_N20_EXPECTED_ROWS_PER_MODEL = (
    12 * len(KERNEL_CLASS_NAMES) * len(DTYPE_NAMES) * 20
)
FIREWORKS_OUTPUT_ROOTS: dict[FireworksRunTier, str] = {
    FIREWORKS_L2B_RUN_TIER: FIREWORKS_L2B_OUTPUT_ROOT,
    FIREWORKS_GBNF_N20_RUN_TIER: FIREWORKS_GBNF_N20_OUTPUT_ROOT,
}
FIREWORKS_AUTHORIZATION_TOKENS: dict[FireworksRunTier, str] = {
    FIREWORKS_L2B_RUN_TIER: FIREWORKS_L2B_AUTHORIZATION_TOKEN,
    FIREWORKS_GBNF_N20_RUN_TIER: FIREWORKS_GBNF_N20_AUTHORIZATION_TOKEN,
}
FIREWORKS_WAVE_CONDITIONS: dict[str, tuple[str, ...]] = {
    "wave_1": (
        "grammar_off__c_off__p_off",
        "task_agnostic__c_off__p_off",
        "template_upper_bound__c_off__p_off",
    ),
    "wave_2": (
        "grammar_off__c_on__p_off",
        "task_agnostic__c_on__p_off",
        "template_upper_bound__c_on__p_off",
    ),
    "wave_3": (
        "grammar_off__c_off__p_on",
        "task_agnostic__c_off__p_on",
        "template_upper_bound__c_off__p_on",
    ),
    "wave_4": (
        "grammar_off__c_on__p_on",
        "task_agnostic__c_on__p_on",
        "template_upper_bound__c_on__p_on",
    ),
}


@dataclass(frozen=True)
class FireworksL2bPlanRow:
    """One planned model/cell/kernel/dtype/seed generation row."""

    experiment_id: str
    run_tier: str
    model_slot: str
    model_id: str
    provider_api: ProviderApi
    selector: str
    condition_id: str
    factor_cell: str
    grammar_mode: str
    grammar_active: bool
    grammar_variant: str | None
    grammar_path: str | None
    grammar_sha256: str | None
    correctness_feedback_active: bool
    compile_feedback_active: bool
    kernel_class: str
    kernel_name: str
    dtype: str
    seed: int
    prompt: str
    prompt_sha256: str

    def to_dict(self, *, include_prompt: bool = False) -> dict[str, object]:
        payload = asdict(self)
        if not include_prompt:
            payload.pop("prompt", None)
        return payload


def build_l2b_smoke_plan(
    *,
    model_slots: tuple[str, ...] = FIREWORKS_MODEL_SLOTS,
    condition_selector: str = "all",
    kernel_classes: tuple[str, ...] = KERNEL_CLASS_NAMES,
    dtypes: tuple[str, ...] = DTYPE_NAMES,
    n: int = 2,
    provider_api: ProviderApi = "responses",
    run_tier: FireworksRunTier = FIREWORKS_L2B_RUN_TIER,
    model_id_overrides: Mapping[str, str] | None = None,
) -> tuple[FireworksL2bPlanRow, ...]:
    """Return the full L2b matrix for Fireworks smoke execution."""

    if n <= 0:
        raise ValueError("n must be positive")
    _require_members(model_slots, tuple(FIREWORKS_MODEL_IDS), "model_slots")
    _require_members(kernel_classes, KERNEL_CLASS_NAMES, "kernel_classes")
    _require_members(dtypes, DTYPE_NAMES, "dtypes")
    if provider_api not in ("responses", "chat_completions"):
        raise ValueError(f"unsupported provider_api: {provider_api!r}")
    if run_tier not in FIREWORKS_OUTPUT_ROOTS:
        raise ValueError(f"unsupported run_tier: {run_tier!r}")
    overrides = dict(model_id_overrides or {})
    _require_override_keys(overrides, tuple(FIREWORKS_MODEL_IDS))

    cells = build_l1a_grammar_mode_cp_matrix()
    selected_condition_ids = FIREWORKS_WAVE_CONDITIONS.get(condition_selector)
    if selected_condition_ids is not None:
        cells = tuple(
            cell for cell in cells if cell.output_namespace_suffix in selected_condition_ids
        )
    elif condition_selector != "all":
        cells = tuple(
            cell
            for cell in cells
            if cell.output_namespace_suffix == condition_selector
        )
        if not cells:
            raise ValueError(f"unknown condition_selector: {condition_selector!r}")

    rows: list[FireworksL2bPlanRow] = []
    for model_slot in model_slots:
        model_id = overrides.get(model_slot, FIREWORKS_MODEL_IDS[model_slot])
        for cell in cells:
            for kernel_class in kernel_classes:
                spec = KERNEL_SPECS[kernel_class]
                for dtype in dtypes:
                    prompt = build_prompt(spec, dtype)
                    for seed in range(n):
                        rows.append(
                            FireworksL2bPlanRow(
                                experiment_id=FIREWORKS_EXPERIMENT_ID,
                                run_tier=run_tier,
                                model_slot=model_slot,
                                model_id=model_id,
                                provider_api=provider_api,
                                selector=L1A_GRAMMAR_MODE_CP_SELECTOR,
                                condition_id=cell.output_namespace_suffix,
                                factor_cell=str(cell.factor_cell),
                                grammar_mode=str(cell.grammar_mode),
                                grammar_active=cell.grammar_active,
                                grammar_variant=cell.grammar_variant,
                                grammar_path=cell.grammar_path,
                                grammar_sha256=_file_sha256(cell.grammar_path),
                                correctness_feedback_active=(
                                    cell.correctness_feedback_active
                                ),
                                compile_feedback_active=cell.compile_feedback_active,
                                kernel_class=kernel_class,
                                kernel_name=spec.name,
                                dtype=dtype,
                                seed=seed,
                                prompt=prompt,
                                prompt_sha256=_sha256(prompt),
                            )
                        )
    return tuple(rows)


def _require_members(values: tuple[str, ...], allowed: tuple[str, ...], name: str) -> None:
    if not values:
        raise ValueError(f"{name} must not be empty")
    bad = [value for value in values if value not in allowed]
    if bad:
        raise ValueError(
            f"{name} must contain only {', '.join(allowed)}; got {', '.join(bad)}"
        )


def _require_override_keys(overrides: dict[str, str], allowed: tuple[str, ...]) -> None:
    bad = [key for key in overrides if key not in allowed]
    if bad:
        raise ValueError(
            "model_id_overrides keys must be valid model slots "
            f"{', '.join(allowed)}; got {', '.join(bad)}"
        )
    empty = [key for key, value in overrides.items() if not value.strip()]
    if empty:
        raise ValueError(
            "model_id_overrides values must be non-empty for slots "
            f"{', '.join(empty)}"
        )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _file_sha256(path: str | None) -> str | None:
    if path is None:
        return None
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
