"""Fireworks API + Modal runner for the L2b n=2 smoke.

The default execution path calls a Modal remote function that invokes the
Fireworks REST API. Unit tests inject a fake generation adapter so no network,
Modal, GPU, or output mutation is required to validate the local contract.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cluster2.feedback.repair_loop import (
    RepairEvaluationInput,
    RepairGenerationInput,
    run_repair_loop,
)
from cluster_fw.planning.l2b_smoke import (
    DTYPE_NAMES,
    FIREWORKS_L2B_RUN_TIER,
    FIREWORKS_GBNF_N20_RUN_TIER,
    FIREWORKS_AUTHORIZATION_TOKENS,
    FIREWORKS_MODEL_SLOTS,
    FIREWORKS_OUTPUT_ROOTS,
    KERNEL_CLASS_NAMES,
    FireworksRunTier,
    ProviderApi,
    build_l2b_smoke_plan,
)
from cluster_fw.providers.fireworks import FireworksGenerationRequest

GenerationAdapter = Any
CompileAdapter = Any
CorrectnessAdapter = Any
FireworksGrammarMode = str


@dataclass(frozen=True)
class FireworksRunResult:
    rows_planned: int
    rows_written: int
    output: str
    run_id: str


def run_fireworks_l2b(
    *,
    output: Path,
    model_slots: tuple[str, ...] = FIREWORKS_MODEL_SLOTS,
    condition_selector: str = "all",
    kernel_classes: tuple[str, ...] = KERNEL_CLASS_NAMES,
    dtypes: tuple[str, ...] = DTYPE_NAMES,
    n: int = 2,
    provider_api: ProviderApi = "responses",
    run_tier: FireworksRunTier = FIREWORKS_L2B_RUN_TIER,
    fireworks_grammar_mode: FireworksGrammarMode = "disabled",
    temperature: float = 0.2,
    max_output_tokens: int = 1536,
    generation_adapter: GenerationAdapter | None = None,
    compile_adapter: CompileAdapter | None = None,
    correctness_adapter: CorrectnessAdapter | None = None,
    model_id_overrides: Mapping[str, str] | None = None,
    resume: bool = False,
    repair_budget: int = 5,
) -> FireworksRunResult:
    """Generate L2b rows and append/write JSONL output."""

    plan = build_l2b_smoke_plan(
        model_slots=model_slots,
        condition_selector=condition_selector,
        kernel_classes=kernel_classes,
        dtypes=dtypes,
        n=n,
        provider_api=provider_api,
        run_tier=run_tier,
        model_id_overrides=model_id_overrides,
    )
    _validate_fireworks_grammar_mode(
        fireworks_grammar_mode,
        provider_api=provider_api,
    )
    adapter = generation_adapter or _modal_fireworks_generation_adapter
    correctness = correctness_adapter
    run_id = str(uuid.uuid4())
    existing = _existing_keys(output) if resume else set()
    mode = "a" if resume else "w"
    output.parent.mkdir(parents=True, exist_ok=True)

    rows_written = 0
    with output.open(mode, encoding="utf-8") as handle:
        for item in plan:
            key = (
                item.model_slot,
                item.condition_id,
                item.kernel_class,
                item.dtype,
                item.seed,
            )
            if key in existing:
                continue
            request = FireworksGenerationRequest(
                model_slot=item.model_slot,
                model_id=item.model_id,
                prompt=item.prompt,
                provider_api=provider_api,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                response_format_grammar=_response_format_grammar_for_item(
                    item,
                    fireworks_grammar_mode=fireworks_grammar_mode,
                ),
            )
            provider = _call_generation_adapter(adapter, request)
            compile_result = None
            correctness_result = None
            repair_result = None
            if provider.get("provider_error_type"):
                compile_result = _provider_error_compile_result(provider)
            elif correctness is not None:
                (
                    provider,
                    correctness_result,
                    repair_result,
                ) = _evaluate_or_repair_functional_correctness(
                    item,
                    provider=provider,
                    base_prompt=item.prompt,
                    generation_adapter=adapter,
                    correctness_adapter=correctness,
                    run_id=run_id,
                    provider_api=provider_api,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                    fireworks_grammar_mode=fireworks_grammar_mode,
                    repair_budget=repair_budget,
                )
            elif compile_adapter is not None:
                compile_result = compile_adapter(
                    source=provider.get("source", ""),
                    kernel_class=item.kernel_class,
                    kernel_name=item.kernel_name,
                    factor_cell=_compile_harness_factor_cell(item),
                    run_id=run_id,
                )
            row = _build_output_row(
                item,
                provider=provider,
                compile_result=compile_result,
                correctness_result=correctness_result,
                repair_result=repair_result,
                run_id=run_id,
            )
            handle.write(json.dumps(row, sort_keys=True) + "\n")
            rows_written += 1

    return FireworksRunResult(
        rows_planned=len(plan),
        rows_written=rows_written,
        output=str(output),
        run_id=run_id,
    )


def build_dry_plan_payload(
    *,
    model_slots: tuple[str, ...],
    condition_selector: str,
    kernel_classes: tuple[str, ...],
    dtypes: tuple[str, ...],
    n: int,
    provider_api: ProviderApi,
    run_tier: FireworksRunTier = FIREWORKS_L2B_RUN_TIER,
    fireworks_grammar_mode: FireworksGrammarMode = "disabled",
    model_id_overrides: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    plan = build_l2b_smoke_plan(
        model_slots=model_slots,
        condition_selector=condition_selector,
        kernel_classes=kernel_classes,
        dtypes=dtypes,
        n=n,
        provider_api=provider_api,
        run_tier=run_tier,
        model_id_overrides=model_id_overrides,
    )
    return {
        "selector": "grammar_mode_cp_12cell",
        "provider": "fireworks",
        "provider_api": provider_api,
        "run_tier": run_tier,
        "fireworks_grammar_mode": fireworks_grammar_mode,
        "model_slots": list(model_slots),
        "model_id_overrides": dict(model_id_overrides or {}),
        "condition_count": len({row.condition_id for row in plan}),
        "kernel_classes": list(kernel_classes),
        "dtypes": list(dtypes),
        "n": n,
        "rows_planned": len(plan),
        "rows_per_model": {
            slot: sum(1 for row in plan if row.model_slot == slot)
            for slot in model_slots
        },
        "first_rows": [row.to_dict() for row in plan[: min(5, len(plan))]],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run or plan the Fireworks API + Modal L2b n=2 smoke."
    )
    parser.add_argument(
        "--condition",
        default="grammar_mode_cp_12cell",
        choices=("grammar_mode_cp_12cell",),
    )
    parser.add_argument("--condition-cell", default="all")
    parser.add_argument(
        "--kernel-class",
        default="all",
        choices=(*KERNEL_CLASS_NAMES, "all"),
    )
    parser.add_argument("--dtypes", nargs="+", default=["all"])
    parser.add_argument("--n", type=int, default=2)
    parser.add_argument(
        "--run-tier",
        choices=(FIREWORKS_L2B_RUN_TIER, FIREWORKS_GBNF_N20_RUN_TIER),
        default=FIREWORKS_L2B_RUN_TIER,
    )
    parser.add_argument("--models", nargs="+", default=list(FIREWORKS_MODEL_SLOTS))
    parser.add_argument(
        "--model-id-overrides",
        nargs="*",
        default=[],
        metavar="SLOT=MODEL_ID",
        help=(
            "Override default Fireworks model IDs, e.g. "
            "FW-A=accounts/<acct>/models/<deployment-or-model-id>"
        ),
    )
    parser.add_argument(
        "--provider-api",
        choices=("responses", "chat_completions"),
        default="responses",
    )
    parser.add_argument(
        "--fireworks-grammar-mode",
        choices=("disabled", "gbnf"),
        default="disabled",
    )
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-output-tokens", type=int, default=1536)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--dry-plan", action="store_true")
    parser.add_argument("--execution-plan", action="store_true")
    parser.add_argument("--list-serverless-models", action="store_true")
    parser.add_argument("--compile-modal", action="store_true")
    parser.add_argument("--correctness-modal", action="store_true")
    parser.add_argument("--repair-budget", type=int, default=5)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--signed-fireworks-authorization", default=None)
    parser.add_argument("--signed-fireworks-l2b-authorization", default=None)
    args = parser.parse_args(argv)

    if args.list_serverless_models:
        print(json.dumps(_list_serverless_models(), indent=2, sort_keys=True))
        return 0
    if args.dry_plan and args.execution_plan:
        raise SystemExit("--dry-plan and --execution-plan are mutually exclusive")
    model_slots = tuple(args.models)
    kernel_classes = (
        KERNEL_CLASS_NAMES if args.kernel_class == "all" else (args.kernel_class,)
    )
    dtypes = DTYPE_NAMES if args.dtypes == ["all"] else tuple(args.dtypes)
    provider_api = args.provider_api
    model_id_overrides = _parse_model_id_overrides(args.model_id_overrides)
    payload = build_dry_plan_payload(
        model_slots=model_slots,
        condition_selector=args.condition_cell,
        kernel_classes=kernel_classes,
        dtypes=dtypes,
        n=args.n,
        provider_api=provider_api,
        run_tier=args.run_tier,
        fireworks_grammar_mode=args.fireworks_grammar_mode,
        model_id_overrides=model_id_overrides,
    )
    if args.dry_plan or args.execution_plan:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    _validate_execution_authorization(args)
    if args.resume and args.overwrite:
        raise SystemExit("--resume and --overwrite are mutually exclusive")

    output = args.output or _default_output(model_slots, run_tier=args.run_tier)
    result = run_fireworks_l2b(
        output=output,
        model_slots=model_slots,
        condition_selector=args.condition_cell,
        kernel_classes=kernel_classes,
        dtypes=dtypes,
        n=args.n,
        provider_api=provider_api,
        run_tier=args.run_tier,
        fireworks_grammar_mode=args.fireworks_grammar_mode,
        temperature=args.temperature,
        max_output_tokens=args.max_output_tokens,
        compile_adapter=_modal_compile_adapter if args.compile_modal else None,
        correctness_adapter=(
            _modal_correctness_adapter if args.correctness_modal else None
        ),
        model_id_overrides=model_id_overrides,
        resume=args.resume and not args.overwrite,
        repair_budget=args.repair_budget,
    )
    print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    return 0


def modal_entrypoint(
    condition_cell: str = "all",
    kernel_class: str = "all",
    dtypes: str = "all",
    n: int = 2,
    run_tier: str = FIREWORKS_L2B_RUN_TIER,
    models: str = "FW-A,FW-B",
    model_id_overrides: str = "",
    provider_api: str = "responses",
    fireworks_grammar_mode: str = "disabled",
    temperature: float = 0.2,
    max_output_tokens: int = 1536,
    output: str = "",
    dry_plan: bool = False,
    execution_plan: bool = False,
    list_serverless_models: bool = False,
    compile_modal: bool = False,
    correctness_modal: bool = False,
    repair_budget: int = 5,
    resume: bool = False,
    overwrite: bool = False,
    signed_fireworks_authorization: str = "",
    signed_fireworks_l2b_authorization: str = "",
) -> None:
    """Modal local entrypoint matching ``modal run -m`` usage."""

    argv = [
        "--condition-cell",
        condition_cell,
        "--kernel-class",
        kernel_class,
        "--n",
        str(n),
        "--run-tier",
        run_tier,
        "--provider-api",
        provider_api,
        "--fireworks-grammar-mode",
        fireworks_grammar_mode,
        "--temperature",
        str(temperature),
        "--max-output-tokens",
        str(max_output_tokens),
        "--repair-budget",
        str(repair_budget),
        "--models",
        *_split_csv(models),
        "--model-id-overrides",
        *_split_csv(model_id_overrides),
        "--dtypes",
        *_split_csv(dtypes),
    ]
    if output:
        argv.extend(["--output", output])
    if dry_plan:
        argv.append("--dry-plan")
    if execution_plan:
        argv.append("--execution-plan")
    if list_serverless_models:
        argv.append("--list-serverless-models")
    if compile_modal:
        argv.append("--compile-modal")
    if correctness_modal:
        argv.append("--correctness-modal")
    if resume:
        argv.append("--resume")
    if overwrite:
        argv.append("--overwrite")
    if signed_fireworks_l2b_authorization:
        argv.extend(
            [
                "--signed-fireworks-l2b-authorization",
                signed_fireworks_l2b_authorization,
            ]
        )
    if signed_fireworks_authorization:
        argv.extend(
            [
                "--signed-fireworks-authorization",
                signed_fireworks_authorization,
            ]
        )
    main(argv)


def _register_modal_local_entrypoint_if_needed() -> None:
    """Expose ``modal run -m`` while preserving cheap normal imports."""

    if "modal" not in sys.modules:
        return

    from shared.modal_harness.app import app as _modal_app
    if _argv_requests_compile_modal(sys.argv):
        import shared.modal_harness.compile  # noqa: F401
    if _argv_requests_correctness_modal(sys.argv):
        import cluster2.modal.correctness  # noqa: F401
    import shared.modal_harness.fireworks_generation  # noqa: F401

    globals()["fireworks_l2b_modal_entrypoint"] = _modal_app.local_entrypoint(
        name="fireworks_l2b_modal_entrypoint"
    )(modal_entrypoint)


def _argv_requests_compile_modal(argv: list[str]) -> bool:
    return "--compile-modal" in argv or any(
        value.startswith("--compile-modal=") for value in argv
    )


def _argv_requests_correctness_modal(argv: list[str]) -> bool:
    return "--correctness-modal" in argv or any(
        value.startswith("--correctness-modal=") for value in argv
    )


_register_modal_local_entrypoint_if_needed()


def _modal_fireworks_generation_adapter(
    request: FireworksGenerationRequest,
) -> dict[str, Any]:
    from shared.modal_harness.fireworks_generation import generate_fireworks_remote

    return generate_fireworks_remote.remote(request.__dict__)


def _call_generation_adapter(
    adapter: GenerationAdapter,
    request: FireworksGenerationRequest,
) -> dict[str, Any]:
    try:
        return adapter(request)
    except Exception as exc:
        return _provider_exception_payload(request, exc)


def _provider_exception_payload(
    request: FireworksGenerationRequest,
    exc: Exception,
) -> dict[str, Any]:
    message = str(exc)
    source = ""
    return {
        "provider": "fireworks",
        "provider_api": request.provider_api,
        "provider_model_id": request.model_id,
        "provider_model_snapshot": request.model_id,
        "model_slot": request.model_slot,
        "source": source,
        "finish_reason": "provider_error",
        "provider_response_id": None,
        "provider_request_id": None,
        "input_tokens": None,
        "output_tokens": None,
        "reasoning_tokens": None,
        "cached_input_tokens": None,
        "prompt_sha256": request.prompt_sha256,
        "response_sha256": None,
        "source_sha256": _sha256(source),
        "raw_source_sha256": _sha256(source),
        "source_extraction_method": "empty",
        "source_extraction_warning": "provider_error_no_source",
        "response_format_type": "grammar" if request.response_format_grammar else None,
        "response_format_grammar_sha256": request.response_format_grammar_sha256,
        "provider_error_type": type(exc).__name__,
        "provider_error_msg": message[:500],
        "raw_response_shape_version": "fireworks_provider_exception_v1",
    }


def _provider_error_compile_result(provider: dict[str, Any]) -> dict[str, Any]:
    return {
        "compile_success": False,
        "compile_error_type": "ProviderError",
        "compile_error_msg": provider.get("provider_error_msg"),
        "failure_code": "F3_EVAL_PIPELINE",
        "compile_results_by_dtype": {"fp32": False, "fp16": False, "bf16": False},
        "n_shapes_tested": 0,
    }


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _list_serverless_models() -> dict[str, Any]:
    from shared.modal_harness.fireworks_generation import (
        list_fireworks_serverless_models_remote,
    )

    return list_fireworks_serverless_models_remote.remote()


def _modal_compile_adapter(**kwargs: Any) -> dict[str, Any]:
    from shared.modal_harness.compile import remote_compile_only

    result = remote_compile_only.remote(
        {
            "factor_cell": kwargs["factor_cell"],
            "kernel_class": kwargs["kernel_class"],
            "kernel_name": kwargs["kernel_name"],
            "source": kwargs["source"],
            "run_id": kwargs["run_id"],
            "timeout_s": 180,
        }
    )
    return {
        "compile_success": result.get("compile_success"),
        "compile_error_type": result.get("compile_error_type"),
        "compile_error_msg": result.get("compile_error_msg"),
        "failure_code": result.get("failure_code"),
        "compile_results_by_dtype": result.get("compile_results_by_dtype"),
        "n_shapes_tested": result.get("n_shapes_tested"),
    }


def _modal_correctness_adapter(**kwargs: Any) -> dict[str, Any]:
    from cluster2.constants import (
        generation_mode_for_condition,
        source_class_for_condition,
    )
    from cluster2.modal.correctness import remote_c2_correctness
    from cluster2.modal.schemas import EvalIdentity, RemoteCorrectnessRequest

    item = kwargs["item"]
    condition = _c2_correctness_condition(item)
    identity = EvalIdentity(
        run_id=str(kwargs["run_id"]),
        condition=condition,
        source_class=source_class_for_condition(condition),
        generation_mode=generation_mode_for_condition(condition),
        kernel_class=item.kernel_class,
        kernel_name=item.kernel_name,
        dtype=item.dtype,
        sample_index=int(item.seed),
        base_seed=int(item.seed),
        attempt_index=int(kwargs.get("attempt_index", 0)),
    )
    request = RemoteCorrectnessRequest(
        identity=identity,
        source=str(kwargs["source"]),
    )
    return remote_c2_correctness.remote(request.model_dump())


def _evaluate_or_repair_functional_correctness(
    item: Any,
    *,
    provider: dict[str, Any],
    base_prompt: str,
    generation_adapter: GenerationAdapter,
    correctness_adapter: CorrectnessAdapter,
    run_id: str,
    provider_api: ProviderApi,
    temperature: float,
    max_output_tokens: int,
    fireworks_grammar_mode: FireworksGrammarMode,
    repair_budget: int,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    initial_source = str(provider.get("source", ""))
    if not item.correctness_feedback_active:
        initial_result = _call_correctness_adapter(
            correctness_adapter,
            item=item,
            source=initial_source,
            run_id=run_id,
            attempt_index=0,
        )
        return provider, initial_result, None

    attempt_providers: dict[int, dict[str, Any]] = {0: provider}
    attempt_sources: dict[int, str] = {0: initial_source}
    attempt_results: dict[int, dict[str, Any]] = {}

    def repair_generation(input_: RepairGenerationInput) -> str:
        request = FireworksGenerationRequest(
            model_slot=item.model_slot,
            model_id=item.model_id,
            prompt=input_.prompt,
            provider_api=provider_api,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            response_format_grammar=_response_format_grammar_for_item(
                item,
                fireworks_grammar_mode=fireworks_grammar_mode,
            ),
        )
        generated = _call_generation_adapter(generation_adapter, request)
        attempt_providers[input_.attempt_index] = generated
        source = str(generated.get("source", ""))
        attempt_sources[input_.attempt_index] = source
        return source

    def repair_evaluation(input_: RepairEvaluationInput) -> dict[str, Any]:
        result = _call_correctness_adapter(
            correctness_adapter,
            item=item,
            source=input_.source,
            run_id=run_id,
            attempt_index=input_.attempt_index,
        )
        attempt_results[input_.attempt_index] = result
        return result

    repair_loop = run_repair_loop(
        condition=_c_repair_condition(item),
        base_prompt=base_prompt,
        base_seed=int(item.seed),
        generation=repair_generation,
        evaluation=repair_evaluation,
        repair_budget=repair_budget,
        seed_candidate_source=initial_source,
    )
    terminal_attempt = (
        repair_loop.successful_attempt_index
        if repair_loop.successful_attempt_index is not None
        else repair_loop.attempts[-1].attempt_index
    )
    terminal_provider = attempt_providers.get(terminal_attempt, provider)
    terminal_source = attempt_sources.get(terminal_attempt, initial_source)
    if terminal_provider is not provider:
        provider = terminal_provider
    provider = dict(provider)
    provider["source"] = terminal_source
    provider["source_sha256"] = _sha256(terminal_source)
    provider["raw_source_sha256"] = _sha256(terminal_source)

    terminal_result = attempt_results[terminal_attempt]
    return provider, terminal_result, repair_loop.to_dict()


def _call_correctness_adapter(
    adapter: CorrectnessAdapter,
    *,
    item: Any,
    source: str,
    run_id: str,
    attempt_index: int,
) -> dict[str, Any]:
    payload = adapter(
        item=item,
        source=source,
        run_id=run_id,
        attempt_index=attempt_index,
    )
    return _extract_correctness_result(payload)


def _extract_correctness_result(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TypeError("correctness adapter must return a dict")
    result = payload.get("correctness_result")
    if isinstance(result, dict):
        return dict(result)
    infrastructure_failure = payload.get("infrastructure_failure")
    if isinstance(infrastructure_failure, dict):
        return {
            "functional_success": False,
            "repair_set_success": False,
            "eval_set_success": False,
            "failure_code": "F3_EVAL_PIPELINE",
            "correctness_error": infrastructure_failure.get("error_msg"),
            "feedback": None,
            "max_abs_diff": None,
            "max_rel_diff": None,
            "level_reached": None,
            "compile_success": False,
            "compile_error": infrastructure_failure.get("error_msg"),
            "compile_error_type": infrastructure_failure.get("error_type"),
        }
    return dict(payload)


def _c_repair_condition(item: Any) -> str:
    return "G+C" if item.grammar_active else "C"


def _c2_correctness_condition(item: Any) -> str:
    return "G+C" if item.grammar_active else "C"


def _compile_harness_factor_cell(item: Any) -> str:
    """Map Fireworks factorial cells to Cluster 1 compile-only labels."""

    return "G" if item.grammar_active else "none"


def _validate_fireworks_grammar_mode(
    fireworks_grammar_mode: FireworksGrammarMode,
    *,
    provider_api: ProviderApi,
) -> None:
    if fireworks_grammar_mode not in {"disabled", "gbnf"}:
        raise ValueError(
            f"unsupported fireworks_grammar_mode: {fireworks_grammar_mode!r}"
        )
    if fireworks_grammar_mode == "gbnf" and provider_api != "chat_completions":
        raise ValueError("Fireworks GBNF mode requires provider_api=chat_completions")


def _validate_execution_authorization(args: argparse.Namespace) -> None:
    run_tier = args.run_tier
    required = FIREWORKS_AUTHORIZATION_TOKENS[run_tier]
    supplied = args.signed_fireworks_authorization or args.signed_fireworks_l2b_authorization
    if supplied != required:
        raise SystemExit(
            f"Fireworks execution for run_tier={run_tier!r} requires "
            f"--signed-fireworks-authorization {required}"
        )
    if run_tier == FIREWORKS_L2B_RUN_TIER:
        if args.n > 2:
            raise SystemExit(
                f"{FIREWORKS_L2B_RUN_TIER} is capped at n<=2; use "
                f"--run-tier {FIREWORKS_GBNF_N20_RUN_TIER} for n=20"
            )
        _require_output_under_run_tier_root(args.output, run_tier=run_tier)
        return
    if run_tier == FIREWORKS_GBNF_N20_RUN_TIER:
        if args.n != 20:
            raise SystemExit(f"{FIREWORKS_GBNF_N20_RUN_TIER} requires --n 20")
        if args.provider_api != "chat_completions":
            raise SystemExit(
                f"{FIREWORKS_GBNF_N20_RUN_TIER} requires "
                "--provider-api chat_completions"
            )
        if args.fireworks_grammar_mode != "gbnf":
            raise SystemExit(
                f"{FIREWORKS_GBNF_N20_RUN_TIER} requires "
                "--fireworks-grammar-mode gbnf"
            )
        if not args.compile_modal and not args.correctness_modal:
            raise SystemExit(
                f"{FIREWORKS_GBNF_N20_RUN_TIER} requires "
                "--compile-modal or --correctness-modal"
            )
        _require_output_under_run_tier_root(args.output, run_tier=run_tier)
        return
    raise SystemExit(f"unsupported run_tier: {run_tier!r}")


def _require_output_under_run_tier_root(
    output: Path | None,
    *,
    run_tier: FireworksRunTier,
) -> None:
    if output is None:
        return
    root = Path(FIREWORKS_OUTPUT_ROOTS[run_tier])
    try:
        output.relative_to(root)
    except ValueError as exc:
        raise SystemExit(
            f"output for run_tier={run_tier!r} must be under {root}"
        ) from exc


def _response_format_grammar_for_item(
    item: Any,
    *,
    fireworks_grammar_mode: FireworksGrammarMode,
) -> str | None:
    if fireworks_grammar_mode == "disabled" or not item.grammar_active:
        return None
    if item.grammar_path is None:
        raise ValueError(
            f"grammar-active condition {item.condition_id!r} is missing grammar_path"
        )
    return _normalize_gbnf_for_fireworks(Path(item.grammar_path).read_text(encoding="utf-8"))


def _normalize_gbnf_for_fireworks(grammar: str) -> str:
    """Convert local multiline GBNF into Fireworks' stricter line format."""

    rules: list[str] = []
    current: str | None = None
    for raw_line in grammar.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "::=" in line:
            if current is not None:
                rules.append(current)
            current = line
            continue
        if current is None:
            rules.append(line)
        else:
            current = f"{current} {line}"
    if current is not None:
        rules.append(current)
    return "\n".join(rules) + "\n"


def _build_output_row(
    item: Any,
    *,
    provider: dict[str, Any],
    compile_result: dict[str, Any] | None,
    correctness_result: dict[str, Any] | None,
    repair_result: dict[str, Any] | None,
    run_id: str,
) -> dict[str, Any]:
    compile_result = compile_result or {}
    correctness_result = correctness_result or {}
    repair_result = repair_result or {}
    compile_success = _first_not_none(
        correctness_result.get("compile_success"),
        compile_result.get("compile_success"),
    )
    failure_code = _first_not_none(
        correctness_result.get("failure_code"),
        compile_result.get("failure_code"),
    )
    compile_error_type = _first_not_none(
        correctness_result.get("compile_error_type"),
        compile_result.get("compile_error_type"),
    )
    compile_error_msg = _first_not_none(
        correctness_result.get("compile_error"),
        compile_result.get("compile_error_msg"),
    )
    return {
        "experiment_id": item.experiment_id,
        "run_tier": item.run_tier,
        "selector": item.selector,
        "condition_id": item.condition_id,
        "condition": item.factor_cell,
        "grammar_mode": item.grammar_mode,
        "grammar_active": item.grammar_active,
        "grammar_variant": item.grammar_variant,
        "grammar_path": item.grammar_path,
        "grammar_sha256": item.grammar_sha256,
        "correctness_feedback_active": item.correctness_feedback_active,
        "compile_feedback_active": item.compile_feedback_active,
        "kernel_class": item.kernel_class,
        "kernel_name": item.kernel_name,
        "dtype": item.dtype,
        "generation_seed": item.seed,
        "source": provider.get("source", ""),
        "compile_success": compile_success,
        "failure_code": failure_code,
        "compile_error_type": compile_error_type,
        "compile_error_msg": compile_error_msg,
        "compile_results_by_dtype": compile_result.get("compile_results_by_dtype"),
        "n_shapes_tested": compile_result.get("n_shapes_tested"),
        "functional_success": correctness_result.get("functional_success"),
        "correctness_error": correctness_result.get("correctness_error"),
        "repair_set_success": correctness_result.get("repair_set_success"),
        "eval_set_success": correctness_result.get("eval_set_success"),
        "max_abs_diff": correctness_result.get("max_abs_diff"),
        "max_rel_diff": correctness_result.get("max_rel_diff"),
        "level_reached": correctness_result.get("level_reached"),
        "num_repair_shapes": correctness_result.get("num_repair_shapes"),
        "num_eval_shapes": correctness_result.get("num_eval_shapes"),
        "num_test_shapes": correctness_result.get("num_test_shapes"),
        "shapes_passed": correctness_result.get("shapes_passed"),
        "repair_shapes_passed": correctness_result.get("repair_shapes_passed"),
        "eval_shapes_passed": correctness_result.get("eval_shapes_passed"),
        "c_repair_status": repair_result.get("status"),
        "c_repair_attempts_executed": repair_result.get("attempts_executed"),
        "c_repair_successful_attempt_index": repair_result.get(
            "successful_attempt_index"
        ),
        "c_repair_final_failure_code": repair_result.get("final_failure_code"),
        "c_repair_final_public_failure_summary": repair_result.get(
            "final_public_failure_summary"
        ),
        "c_repair_attempts": repair_result.get("attempts"),
        "c_repair_terminal_prompt_metadata": repair_result.get(
            "terminal_prompt_metadata"
        ),
        "model_slot": item.model_slot,
        "model_name": item.model_id,
        "provider": provider.get("provider"),
        "provider_api": provider.get("provider_api"),
        "provider_model_id": provider.get("provider_model_id"),
        "provider_model_snapshot": provider.get("provider_model_snapshot"),
        "finish_reason": provider.get("finish_reason"),
        "provider_response_id": provider.get("provider_response_id"),
        "provider_request_id": provider.get("provider_request_id"),
        "input_tokens": provider.get("input_tokens"),
        "output_tokens": provider.get("output_tokens"),
        "reasoning_tokens": provider.get("reasoning_tokens"),
        "cached_input_tokens": provider.get("cached_input_tokens"),
        "prompt_sha256": provider.get("prompt_sha256") or item.prompt_sha256,
        "response_sha256": provider.get("response_sha256"),
        "source_sha256": provider.get("source_sha256"),
        "raw_source_sha256": provider.get("raw_source_sha256"),
        "source_extraction_method": provider.get("source_extraction_method"),
        "source_extraction_warning": provider.get("source_extraction_warning"),
        "response_format_type": provider.get("response_format_type"),
        "response_format_grammar_sha256": provider.get(
            "response_format_grammar_sha256"
        ),
        "provider_error_type": provider.get("provider_error_type"),
        "provider_error_msg": provider.get("provider_error_msg"),
        "raw_response_shape_version": provider.get("raw_response_shape_version"),
        "run_id": run_id,
        "timestamp_utc": datetime.now(UTC).isoformat(),
    }


def _first_not_none(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _existing_keys(output: Path) -> set[tuple[str, str, str, str, int]]:
    if not output.exists():
        return set()
    keys: set[tuple[str, str, str, str, int]] = set()
    with output.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            keys.add(
                (
                    row["model_slot"],
                    row["condition_id"],
                    row["kernel_class"],
                    row["dtype"],
                    int(row["generation_seed"]),
                )
            )
    return keys


def _default_output(
    model_slots: tuple[str, ...],
    *,
    run_tier: FireworksRunTier,
) -> Path:
    suffix = "all_models" if len(model_slots) > 1 else model_slots[0].lower()
    return Path(FIREWORKS_OUTPUT_ROOTS[run_tier]) / f"{suffix}.jsonl"


def _split_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _parse_model_id_overrides(values: list[str]) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise SystemExit(
                "--model-id-overrides entries must use SLOT=MODEL_ID format; "
                f"got {value!r}"
            )
        slot, model_id = value.split("=", 1)
        slot = slot.strip()
        model_id = model_id.strip()
        if not slot or not model_id:
            raise SystemExit(
                "--model-id-overrides entries must use non-empty SLOT=MODEL_ID "
                f"format; got {value!r}"
            )
        overrides[slot] = model_id
    return overrides


if __name__ == "__main__":
    sys.exit(main())
