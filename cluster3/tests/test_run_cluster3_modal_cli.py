from __future__ import annotations

import ast
import hashlib
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

import cluster3.experiments.run_cluster3_modal as runner_mod
from cluster2.constants import DEFAULT_REPAIR_BUDGET
from cluster2.feedback.repair_loop import RepairFeedbackInput, RepairGenerationInput
from cluster2.feedback.trace import TraceSummary
from cluster3.constants import DEFAULT_P_REPAIR_BUDGET
from cluster3.experiments.run_cluster3_modal import (
    Cluster3RunnerConfig,
    RunnerDependencies,
    parse_args,
    run_cluster3,
)
from cluster3.feedback import c_loop_adapter
from cluster3.feedback.c_loop_adapter import (
    Cluster3CLoopResult,
    run_cluster3_c_loop_from_f2,
)
from cluster3.replay.no_p_pairs import pair_for_condition, validate_pair_identity
from cluster3.results.logger import default_content_hash_sidecar_path


REPO_ROOT = Path(__file__).resolve().parents[2]
REV_A = "a" * 40
REV_B = "b" * 40
SEED_SOURCE = "def relu(x):\n    return x\n"
C_SOURCE = "def relu_c(x):\n    return x\n"
P_SOURCE = "def relu_p(x):\n    return x\n"
BASE_PROMPT = "Implement relu."
F1_DIAGNOSTIC_FIXTURE = "cluster3/tests/fixtures/f1_compile_kernels/bad_constexpr.py"
F2_DIAGNOSTIC_FIXTURE = "cluster2/tests/fixtures/f2_corrupted_relu.py"


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _config(tmp_path: Path, condition: str = "P", **overrides: object) -> Cluster3RunnerConfig:
    values: dict[str, object] = {
        "condition": condition,
        "output": str(tmp_path / f"{condition.replace('+', '_')}.jsonl"),
        "model_revision": REV_A,
        "tokenizer_revision": REV_B,
        "n": 1,
        "kernel_class": "elementwise",
        "dtypes": ("fp32",),
    }
    values.update(overrides)
    return Cluster3RunnerConfig(**values)  # type: ignore[arg-type]


def _result(
    failure_code: str | None,
    *,
    level_reached: int = 2,
    compile_success: bool | None = None,
    functional_success: bool | None = None,
    repair_set_success: bool | None = None,
    eval_set_success: bool | None = None,
    compile_error: str | None = None,
    compile_error_type: str | None = None,
    f3_reason: str | None = None,
) -> dict[str, Any]:
    if failure_code is None:
        compile_success = True if compile_success is None else compile_success
        functional_success = True if functional_success is None else functional_success
        repair_set_success = True if repair_set_success is None else repair_set_success
        eval_set_success = True if eval_set_success is None else eval_set_success
    else:
        functional_success = False if functional_success is None else functional_success
        repair_set_success = False if repair_set_success is None else repair_set_success
        eval_set_success = False if eval_set_success is None else eval_set_success
        if compile_success is None:
            compile_success = failure_code.startswith("F2_") or failure_code.startswith("F3_")
    payload: dict[str, Any] = {
        "failure_code": failure_code,
        "level_reached": level_reached,
        "compile_success": compile_success,
        "functional_success": functional_success,
        "repair_set_success": repair_set_success,
        "eval_set_success": eval_set_success,
        "compile_error": compile_error,
        "compile_error_type": compile_error_type,
        "correctness_error": "numeric mismatch" if failure_code else None,
    }
    if f3_reason is not None:
        payload["f3_reason"] = f3_reason
    return payload


def _f1_result() -> dict[str, Any]:
    return _result(
        "F1_COMPILE",
        level_reached=1,
        compile_success=False,
        compile_error="compiler failed",
        compile_error_type="CompilationError",
    )


def _f2_result() -> dict[str, Any]:
    return _result(
        "F2_NUMERIC_LARGE",
        level_reached=2,
        compile_success=True,
        functional_success=False,
    )


class GenerationRecorder:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        attempt_index = kwargs["identity"].attempt_index
        if attempt_index == 0:
            source = SEED_SOURCE
        elif attempt_index == 1:
            source = P_SOURCE
        else:
            source = f"def relu_attempt_{attempt_index}(x):\n    return x\n"
        return {"source": source}


class CorrectnessRecorder:
    def __init__(self, *results: dict[str, Any]) -> None:
        self.results = list(results)
        self.calls: list[Any] = []

    def __call__(self, request: Any) -> dict[str, Any]:
        self.calls.append(request)
        if not self.results:
            raise AssertionError("unexpected correctness call")
        result = dict(self.results.pop(0))
        result.setdefault("identity", _identity_dict(request.identity))
        return result


class CLoopRecorder:
    def __init__(
        self,
        *,
        terminal_failure_code: str | None = None,
        c_attempt_count: int = 1,
        terminal_source: str = C_SOURCE,
        terminal_generation_seed: int = 21,
        level_reached: int = 2,
        compile_success: bool = True,
        functional_success: bool = True,
    ) -> None:
        self.calls: list[dict[str, Any]] = []
        self.terminal_failure_code = terminal_failure_code
        self.c_attempt_count = c_attempt_count
        self.terminal_source = terminal_source
        self.terminal_generation_seed = terminal_generation_seed
        self.level_reached = level_reached
        self.compile_success = compile_success
        self.functional_success = functional_success

    def __call__(self, **kwargs: Any) -> Cluster3CLoopResult:
        self.calls.append(kwargs)
        if self.c_attempt_count == 0:
            source = kwargs["seed_candidate_source"]
            generation_seed = kwargs["seed_candidate_generation_seed"]
            prompt_hash = kwargs["seed_candidate_prompt_hash"]
            prompt_hash_source = kwargs["seed_candidate_prompt_hash_source"]
            terminal_index = 0
        else:
            source = self.terminal_source
            generation_seed = self.terminal_generation_seed
            prompt_hash = _sha("c repair prompt")
            prompt_hash_source = "c_repair_prompt"
            terminal_index = self.c_attempt_count
        result = {
            "failure_code": self.terminal_failure_code,
            "level_reached": self.level_reached,
            "compile_success": self.compile_success,
            "functional_success": self.functional_success,
            "repair_set_success": self.functional_success,
            "eval_set_success": self.functional_success,
        }
        traces = [
            TraceSummary(
                attempt_index=0,
                failure_code=kwargs["seed_candidate_evaluation"].get("failure_code"),
                public_failure_summary="seed failed",
                functional_success=False,
                repair_set_success=False,
                eval_set_success=False,
                source_hash=_sha(kwargs["seed_candidate_source"]),
            )
        ]
        if self.c_attempt_count:
            traces.append(
                TraceSummary(
                    attempt_index=self.c_attempt_count,
                    failure_code=self.terminal_failure_code,
                    public_failure_summary="terminal",
                    functional_success=self.functional_success,
                    repair_set_success=self.functional_success,
                    eval_set_success=self.functional_success,
                    source_hash=_sha(source),
                )
            )
        return Cluster3CLoopResult(
            c_loop_fired=True,
            c_loop_source=kwargs["c_loop_source"],
            c_attempt_count=self.c_attempt_count,
            c_repair_budget=kwargs["repair_budget"],
            c_terminal_failure_code=self.terminal_failure_code,
            c_terminal_level_reached=self.level_reached,
            c_terminal_compile_success=self.compile_success,
            c_terminal_functional_success=self.functional_success,
            terminal_source=source,
            terminal_source_hash=_sha(source),
            terminal_generation_seed=generation_seed,
            terminal_prompt_hash=prompt_hash,
            terminal_prompt_hash_source=prompt_hash_source,
            terminal_attempt_index=terminal_index,
            terminal_correctness_result=result,
            cluster2_repair_result={"trace_summaries": traces},
            trace_summary_fragment={"outer_c3_condition": kwargs["outer_c3_condition"]},
            infrastructure_failure=False,
            f3_reason=None,
        )


def _identity_dict(identity: Any) -> dict[str, Any]:
    if isinstance(identity, dict):
        return dict(identity)
    if hasattr(identity, "model_dump"):
        return identity.model_dump()
    return dict(identity)


def _run_with_results(
    tmp_path: Path,
    condition: str,
    *results: dict[str, Any],
    c_loop: CLoopRecorder | None = None,
    **config_overrides: object,
) -> tuple[Any, GenerationRecorder, CorrectnessRecorder, CLoopRecorder]:
    generation = GenerationRecorder()
    correctness = CorrectnessRecorder(*results)
    c_loop = c_loop or CLoopRecorder()
    run = run_cluster3(
        _config(tmp_path, condition, **config_overrides),
        dependencies=RunnerDependencies(
            generation=generation,
            correctness=correctness,
            c_loop_runner=c_loop,
        ),
    )
    return run, generation, correctness, c_loop


def _pair_rows(p_condition: str) -> tuple[dict[str, Any], dict[str, Any]]:
    control_condition = pair_for_condition(p_condition)
    common = {
        "kernel_class": "elementwise",
        "kernel_name": "relu",
        "dtype": "fp32",
        "base_seed": 0,
        "sample_index": 0,
        "replay_pair_id": "pair-0",
        "model_id": "model",
        "model_revision": REV_A,
        "tokenizer_revision": REV_B,
        "temperature": 0.2,
        "max_new_tokens": 1536,
        "prompt_sha256": "1" * 64,
    }
    p_row = {"condition": p_condition, **common}
    control_row = {"condition": control_condition, **common}
    if p_condition in {"G+P", "G+C+P"}:
        p_row["grammar_variant"] = "task_agnostic"
        control_row["grammar_variant"] = "task_agnostic"
    return p_row, control_row


def _c_loop_call(
    *,
    repair_budget: int = 1,
    outer_c3_condition: str = "C+P",
    feedback_builder: Any = None,
    generation: Any | None = None,
    correctness: Any | None = None,
    kernel_name: str = "relu",
) -> Cluster3CLoopResult:
    generation = generation or (lambda **_: {"source": C_SOURCE})
    correctness = correctness or (lambda request: {**_result(None), "identity": _identity_dict(request.identity)})
    return run_cluster3_c_loop_from_f2(
        outer_c3_condition=outer_c3_condition,
        c_loop_source="initial_f2",
        base_prompt=BASE_PROMPT,
        base_seed=2,
        sample_index=2,
        kernel_class="elementwise",
        kernel_name=kernel_name,
        dtype="fp32",
        seed_candidate_source=SEED_SOURCE,
        seed_candidate_generation_seed=2,
        seed_candidate_prompt_hash=_sha(BASE_PROMPT),
        seed_candidate_prompt_hash_source="initial_prompt",
        seed_candidate_evaluation=_f2_result(),
        feedback_builder=feedback_builder,
        repair_budget=repair_budget,
        model_config={
            "generation": generation,
            "correctness": correctness,
            "model_id": "model",
            "model_revision": REV_A,
            "tokenizer_revision": REV_B,
            "temperature": 0.2,
            "max_new_tokens": 1536,
        },
        provenance_base={"run_id": "test-run"},
    )


def test_runner_config_accepts_p_conditions(tmp_path: Path) -> None:
    for condition in ("P", "G+P", "C+P", "G+C+P", "all"):
        assert _config(tmp_path, condition).condition == condition


def test_runner_config_rejects_cluster2_conditions(tmp_path: Path) -> None:
    for condition in ("none", "G", "C", "G+C"):
        with pytest.raises(ValueError):
            _config(tmp_path, condition)


def test_runner_config_repair_budget_bounds(tmp_path: Path) -> None:
    assert _config(tmp_path, p_repair_budget=0, c_repair_budget=0)
    assert _config(tmp_path, p_repair_budget=DEFAULT_P_REPAIR_BUDGET)
    assert _config(tmp_path, c_repair_budget=DEFAULT_REPAIR_BUDGET)
    with pytest.raises(ValueError):
        _config(tmp_path, p_repair_budget=DEFAULT_P_REPAIR_BUDGET + 1)
    with pytest.raises(ValueError):
        _config(tmp_path, c_repair_budget=DEFAULT_REPAIR_BUDGET + 1)


def test_runner_config_modal_gpus_match_cluster2_defaults(tmp_path: Path) -> None:
    assert _config(tmp_path, modal_generation_gpu="L4", modal_eval_gpu="L4")
    with pytest.raises(ValueError):
        _config(tmp_path, modal_generation_gpu="A100")
    with pytest.raises(ValueError):
        _config(tmp_path, modal_eval_gpu="A100")


def test_runner_config_has_no_cluster3_timeout_or_retry_fields() -> None:
    fields = set(Cluster3RunnerConfig.__dataclass_fields__)
    assert not {
        "modal_timeout_s",
        "modal_retries",
        "max_containers",
        "min_containers",
        "scaledown_window",
    } & fields


def test_runner_config_requires_immutable_model_revision(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        _config(tmp_path, model_revision="main")
    with pytest.raises(ValueError):
        _config(tmp_path, tokenizer_revision="main")


def test_run_cluster3_source_defines_no_modal_app_function_or_image() -> None:
    source = Path(runner_mod.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_attrs = {
        ("modal", "App"),
        ("modal", "Image"),
        ("modal", "Volume"),
        ("modal", "Secret"),
        ("modal", "Queue"),
        ("app", "function"),
        ("app", "cls"),
        ("app", "local_entrypoint"),
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            assert (node.value.id, node.attr) not in forbidden_attrs
    assert "add_local_python_" + "source" not in source
    assert "web_endpoint" not in source
    assert "batched" not in source


def test_run_cluster3_uses_synchronous_c2_modal_calls_no_spawn_or_map() -> None:
    source = Path(runner_mod.__file__).read_text(encoding="utf-8")
    assert ".spawn(" not in source
    assert ".spawn_map(" not in source
    assert ".map(" not in source
    assert "FunctionCall" + ".get" not in source


def test_run_cluster3_modal_entrypoint_delegates_to_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    observed: list[str] = []

    def fake_main(argv: list[str]) -> None:
        observed.extend(argv)

    monkeypatch.setattr(runner_mod, "main", fake_main)

    runner_mod.modal_entrypoint(
        condition="P",
        kernel_class="elementwise",
        scale_tier="smoke",
        n=1,
        output="outputs/cluster3/p_smoke_l4_n1.jsonl",
        model_revision=REV_A,
        tokenizer_revision=REV_B,
        dtypes="fp32",
        p_repair_budget=5,
        c_repair_budget=0,
        overwrite=True,
    )

    assert observed == [
        "--condition",
        "P",
        "--kernel-class",
        "elementwise",
        "--scale-tier",
        "smoke",
        "--n",
        "1",
        "--model-id",
        runner_mod.MODEL_ID_DEFAULT,
        "--model-revision",
        REV_A,
        "--tokenizer-revision",
        REV_B,
        "--grammar-variant",
        runner_mod.GRAMMAR_VARIANT_TASK_AGNOSTIC,
        "--dtypes",
        "fp32",
        "--temperature",
        "0.2",
        "--max-new-tokens",
        str(runner_mod.DEFAULT_MAX_NEW_TOKENS),
        "--p-repair-budget",
        "5",
        "--c-repair-budget",
        "0",
        "--modal-generation-gpu",
        runner_mod.DEFAULT_C2_MODAL_GENERATION_GPU,
        "--modal-eval-gpu",
        runner_mod.DEFAULT_C2_MODAL_EVAL_GPU,
        "--output",
        "outputs/cluster3/p_smoke_l4_n1.jsonl",
        "--overwrite",
    ]


def test_run_cluster3_modal_entrypoint_rejects_two_write_modes() -> None:
    with pytest.raises(ValueError, match="mutually exclusive"):
        runner_mod.modal_entrypoint(
            condition="P",
            kernel_class="elementwise",
            scale_tier="smoke",
            n=1,
            output="outputs/cluster3/p_smoke_l4_n1.jsonl",
            overwrite=True,
            resume=True,
        )


def test_runner_accepts_diagnostic_seed_source_for_p_smoke(tmp_path: Path) -> None:
    config = _config(
        tmp_path,
        "G+P",
        diagnostic_seed_source=F1_DIAGNOSTIC_FIXTURE,
        diagnostic_expected_initial_failure="F1_COMPILE",
    )

    assert config.diagnostic_seed_source == F1_DIAGNOSTIC_FIXTURE
    assert config.diagnostic_expected_initial_failure == "F1_COMPILE"


def test_runner_rejects_diagnostic_seed_source_for_n_gt_2(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="n <= 2"):
        _config(
            tmp_path,
            "G+P",
            n=3,
            diagnostic_seed_source=F1_DIAGNOSTIC_FIXTURE,
            diagnostic_expected_initial_failure="F1_COMPILE",
        )


def test_runner_rejects_diagnostic_seed_source_for_non_p_conditions(tmp_path: Path) -> None:
    for condition in ("C+P", "G+C+P", "all"):
        with pytest.raises(ValueError, match="condition P or G\\+P"):
            _config(
                tmp_path,
                condition,
                diagnostic_seed_source=F1_DIAGNOSTIC_FIXTURE,
                diagnostic_expected_initial_failure="F1_COMPILE",
            )


def test_diagnostic_seed_accepts_expected_f2_for_gc_plus_p_smoke(tmp_path: Path) -> None:
    config = _config(
        tmp_path,
        "G+C+P",
        diagnostic_seed_source=F2_DIAGNOSTIC_FIXTURE,
        diagnostic_expected_initial_failure="F2_NUMERIC_LARGE",
    )

    assert config.diagnostic_seed_source == F2_DIAGNOSTIC_FIXTURE
    assert config.diagnostic_expected_initial_failure == "F2_NUMERIC_LARGE"


def test_diagnostic_seed_rejects_expected_f2_for_n_gt_1(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="n <= 1"):
        _config(
            tmp_path,
            "G+C+P",
            n=2,
            diagnostic_seed_source=F2_DIAGNOSTIC_FIXTURE,
            diagnostic_expected_initial_failure="F2_NUMERIC_LARGE",
        )


def test_diagnostic_seed_rejects_expected_f2_for_p_only(tmp_path: Path) -> None:
    for condition in ("P", "G+P", "all"):
        with pytest.raises(ValueError, match="condition C\\+P or G\\+C\\+P"):
            _config(
                tmp_path,
                condition,
                diagnostic_seed_source=F2_DIAGNOSTIC_FIXTURE,
                diagnostic_expected_initial_failure="F2_NUMERIC_LARGE",
            )


def test_runner_diagnostic_seed_still_uses_correctness_adapter(tmp_path: Path) -> None:
    fixture_source = (REPO_ROOT / F1_DIAGNOSTIC_FIXTURE).read_text(encoding="utf-8")
    run, generation, correctness, _ = _run_with_results(
        tmp_path,
        "G+P",
        _f1_result(),
        _result(None),
        diagnostic_seed_source=F1_DIAGNOSTIC_FIXTURE,
        diagnostic_expected_initial_failure="F1_COMPILE",
    )

    assert correctness.calls[0].source == fixture_source
    assert len(correctness.calls) == 2
    assert len(generation.calls) == 1
    assert generation.calls[0]["identity"].attempt_index == 1
    assert run.rows[0].p_repair_attempted is True
    assert run.rows[0].p_initial_failure_code == "F1_COMPILE"


def test_runner_diagnostic_seed_does_not_fabricate_f1(tmp_path: Path) -> None:
    fixture_source = (REPO_ROOT / F1_DIAGNOSTIC_FIXTURE).read_text(encoding="utf-8")
    generation = GenerationRecorder()
    correctness = CorrectnessRecorder(
        _result("F0_PARSE", level_reached=0, compile_success=False)
    )

    with pytest.raises(RuntimeError, match="expected initial failure F1_COMPILE"):
        run_cluster3(
            _config(
                tmp_path,
                "G+P",
                diagnostic_seed_source=F1_DIAGNOSTIC_FIXTURE,
                diagnostic_expected_initial_failure="F1_COMPILE",
            ),
            dependencies=RunnerDependencies(
                generation=generation,
                correctness=correctness,
            ),
        )

    assert correctness.calls[0].source == fixture_source
    assert generation.calls == []


def test_runner_diagnostic_seed_dispatches_f1_compile_to_p(tmp_path: Path) -> None:
    run, _, _, c_loop = _run_with_results(
        tmp_path,
        "G+P",
        _f1_result(),
        _result(None),
        diagnostic_seed_source=F1_DIAGNOSTIC_FIXTURE,
        diagnostic_expected_initial_failure="F1_COMPILE",
    )

    assert run.rows[0].p_repair_attempted is True
    assert run.rows[0].p_repair_stop_reason != "p_not_applicable"
    assert c_loop.calls == []


def test_diagnostic_seed_does_not_fabricate_f2(tmp_path: Path) -> None:
    fixture_source = (REPO_ROOT / F2_DIAGNOSTIC_FIXTURE).read_text(encoding="utf-8")
    generation = GenerationRecorder()
    correctness = CorrectnessRecorder(
        _result("F1_COMPILE", level_reached=1, compile_success=False)
    )

    with pytest.raises(RuntimeError, match="expected initial failure F2_NUMERIC_LARGE"):
        run_cluster3(
            _config(
                tmp_path,
                "G+C+P",
                diagnostic_seed_source=F2_DIAGNOSTIC_FIXTURE,
                diagnostic_expected_initial_failure="F2_NUMERIC_LARGE",
            ),
            dependencies=RunnerDependencies(
                generation=generation,
                correctness=correctness,
            ),
        )

    assert correctness.calls[0].source == fixture_source
    assert generation.calls == []


def test_initial_f2_diagnostic_routes_to_c_not_p_under_g_c_p(tmp_path: Path) -> None:
    fixture_source = (REPO_ROOT / F2_DIAGNOSTIC_FIXTURE).read_text(encoding="utf-8")
    run, generation, correctness, c_loop = _run_with_results(
        tmp_path,
        "G+C+P",
        _f2_result(),
        diagnostic_seed_source=F2_DIAGNOSTIC_FIXTURE,
        diagnostic_expected_initial_failure="F2_NUMERIC_LARGE",
    )
    row = run.rows[0]

    assert correctness.calls[0].source == fixture_source
    assert generation.calls == []
    assert row.p_repair_attempted is False
    assert row.p_repair_stop_reason == "p_not_applicable"
    assert row.c_loop_fired is True
    assert row.c_loop_source == "initial_f2"
    assert c_loop.calls[0]["seed_candidate_evaluation"]["failure_code"] == "F2_NUMERIC_LARGE"


def test_cluster3_validate_pair_identity_for_p_vs_none() -> None:
    validate_pair_identity(*_pair_rows("P"))


def test_cluster3_validate_pair_identity_for_cp_vs_c() -> None:
    validate_pair_identity(*_pair_rows("C+P"))


def test_cluster3_validate_pair_identity_requires_mandatory_fields() -> None:
    p_row, control_row = _pair_rows("P")
    del control_row["base_seed"]
    with pytest.raises(ValueError, match="missing required base_seed"):
        validate_pair_identity(p_row, control_row)


def test_cluster3_validate_pair_identity_requires_g_grammar_variant() -> None:
    p_row, control_row = _pair_rows("G+P")
    del control_row["grammar_variant"]
    with pytest.raises(ValueError, match="missing required grammar_variant"):
        validate_pair_identity(p_row, control_row)


def test_cluster3_runner_uses_public_validate_pair_identity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[Any, Any]] = []

    def validator(row: Any, control_row: Any) -> None:
        calls.append((row, control_row))

    monkeypatch.setattr("cluster3.replay.no_p_pairs.validate_pair_identity", validator)
    run_cluster3(
        _config(tmp_path, "P"),
        dependencies=RunnerDependencies(
            generation=GenerationRecorder(),
            correctness=CorrectnessRecorder(_result(None)),
            no_p_control_resolver=lambda row: {
                "condition": "none",
                "kernel_class": row.kernel_class,
                "kernel_name": row.kernel_name,
                "dtype": row.dtype,
                "base_seed": row.base_seed,
            },
        ),
    )
    assert len(calls) == 1


def test_run_cluster3_control_resolver_type_error_propagates(tmp_path: Path) -> None:
    calls = 0

    def resolver(row: Any) -> Any:
        nonlocal calls
        calls += 1
        raise TypeError("resolver bug")

    with pytest.raises(TypeError, match="resolver bug"):
        run_cluster3(
            _config(tmp_path, "P"),
            dependencies=RunnerDependencies(
                generation=GenerationRecorder(),
                correctness=CorrectnessRecorder(_result(None)),
                no_p_control_resolver=resolver,
            ),
        )

    assert calls == 1


def test_run_cluster3_control_resolver_accepts_keyword_identity(tmp_path: Path) -> None:
    calls: list[dict[str, Any]] = []

    def resolver(
        *,
        condition: str,
        control_condition: str,
        kernel_class: str,
        kernel_name: str,
        dtype: str,
        base_seed: int,
    ) -> dict[str, Any]:
        call = {
            "condition": condition,
            "control_condition": control_condition,
            "kernel_class": kernel_class,
            "kernel_name": kernel_name,
            "dtype": dtype,
            "base_seed": base_seed,
        }
        calls.append(call)
        return {
            "condition": control_condition,
            "kernel_class": kernel_class,
            "kernel_name": kernel_name,
            "dtype": dtype,
            "base_seed": base_seed,
        }

    run_cluster3(
        _config(tmp_path, "P"),
        dependencies=RunnerDependencies(
            generation=GenerationRecorder(),
            correctness=CorrectnessRecorder(_result(None)),
            no_p_control_resolver=resolver,
        ),
    )

    assert calls == [
        {
            "condition": "P",
            "control_condition": "none",
            "kernel_class": "elementwise",
            "kernel_name": "relu",
            "dtype": "fp32",
            "base_seed": 0,
        }
    ]


def test_run_cluster3_translates_p_to_c_for_generation(tmp_path: Path) -> None:
    _, generation, _, _ = _run_with_results(tmp_path, "P", _result(None))
    assert generation.calls[0]["identity"].condition == "C"


def test_run_cluster3_translates_gp_to_gc_for_generation(tmp_path: Path) -> None:
    _, generation, _, _ = _run_with_results(tmp_path, "G+P", _result(None))
    assert generation.calls[0]["identity"].condition == "G+C"


def test_run_cluster3_dispatches_f1_compile_to_p_loop_with_seed_attempt(tmp_path: Path) -> None:
    run, generation, correctness, _ = _run_with_results(tmp_path, "P", _f1_result(), _result(None))
    row = run.rows[0]
    assert row.p_repair_attempted is True
    assert row.p_initial_failure_code == "F1_COMPILE"
    assert len(generation.calls) == 2
    assert len(correctness.calls) == 2


def test_run_cluster3_terminates_on_f0_parse(tmp_path: Path) -> None:
    run, generation, _, c_loop = _run_with_results(
        tmp_path,
        "C+P",
        _result("F0_PARSE", level_reached=0, compile_success=False),
    )
    row = run.rows[0]
    assert row.failure_code == "F0_PARSE"
    assert row.p_repair_attempted is False
    assert c_loop.calls == []
    assert len(generation.calls) == 1


def test_run_cluster3_c_plus_p_initial_f2_invokes_c_loop_without_p(tmp_path: Path) -> None:
    run, _, _, c_loop = _run_with_results(tmp_path, "C+P", _f2_result())
    row = run.rows[0]
    assert len(c_loop.calls) == 1
    assert c_loop.calls[0]["c_loop_source"] == "initial_f2"
    assert row.p_repair_attempted is False
    assert row.c_loop_fired is True


def test_run_cluster3_gcp_initial_f2_invokes_c_loop_without_p(tmp_path: Path) -> None:
    run, _, _, c_loop = _run_with_results(tmp_path, "G+C+P", _f2_result())
    assert run.rows[0].c_loop_source == "initial_f2"
    assert c_loop.calls[0]["outer_c3_condition"] == "G+C+P"


def test_run_cluster3_p_repairs_compile_then_level2_fails_records_f2(tmp_path: Path) -> None:
    run, _, _, _ = _run_with_results(tmp_path, "P", _f1_result(), _f2_result())
    row = run.rows[0]
    assert row.p_compile_repair_succeeded is True
    assert row.failure_code == "F2_NUMERIC_LARGE"
    assert row.p_terminal_failure_code == "F2_NUMERIC_LARGE"


def test_run_cluster3_p_without_c_does_not_invoke_c_loop(tmp_path: Path) -> None:
    _, _, _, c_loop = _run_with_results(tmp_path, "P", _f1_result(), _f2_result())
    assert c_loop.calls == []


def test_run_cluster3_g_plus_p_without_c_does_not_invoke_c_loop(tmp_path: Path) -> None:
    _, _, _, c_loop = _run_with_results(tmp_path, "G+P", _f1_result(), _f2_result())
    assert c_loop.calls == []


def test_run_cluster3_c_plus_p_seeds_c_loop_with_p_terminal_source(tmp_path: Path) -> None:
    _, _, _, c_loop = _run_with_results(tmp_path, "C+P", _f1_result(), _f2_result())
    assert c_loop.calls[0]["c_loop_source"] == "post_p_f2"
    assert c_loop.calls[0]["seed_candidate_source"] == P_SOURCE


def test_run_cluster3_c_plus_p_passes_c_repair_budget_not_p_repair_budget(tmp_path: Path) -> None:
    _, _, _, c_loop = _run_with_results(
        tmp_path,
        "C+P",
        _f1_result(),
        _f2_result(),
        p_repair_budget=1,
        c_repair_budget=3,
    )
    assert c_loop.calls[0]["repair_budget"] == 3


def test_run_cluster3_p_repair_budget_independent_from_c_repair_budget(tmp_path: Path) -> None:
    run, _, _, c_loop = _run_with_results(
        tmp_path,
        "C+P",
        _f1_result(),
        _f2_result(),
        p_repair_budget=1,
        c_repair_budget=0,
        c_loop=CLoopRecorder(c_attempt_count=0),
    )
    assert run.rows[0].p_repair_attempt_count == 1
    assert c_loop.calls[0]["repair_budget"] == 0


def test_run_cluster3_c_plus_p_c_loop_first_eval_uses_cached_f2_result(tmp_path: Path) -> None:
    _, _, correctness, c_loop = _run_with_results(tmp_path, "C+P", _f1_result(), _f2_result())
    assert len(correctness.calls) == 2
    assert c_loop.calls[0]["seed_candidate_evaluation"]["failure_code"] == "F2_NUMERIC_LARGE"


def test_run_cluster3_c_plus_p_does_not_regenerate_after_p_repair(tmp_path: Path) -> None:
    _, generation, _, _ = _run_with_results(tmp_path, "C+P", _f1_result(), _f2_result())
    assert len(generation.calls) == 2


def test_run_cluster3_c_plus_p_translates_repair_condition(tmp_path: Path) -> None:
    _, _, _, c_loop = _run_with_results(tmp_path, "C+P", _f1_result(), _f2_result())
    result = _c_loop_call(outer_c3_condition=c_loop.calls[0]["outer_c3_condition"], repair_budget=0)
    assert result.trace_summary_fragment["repair_condition"] == "C"


def test_run_cluster3_g_plus_c_plus_p_translates_repair_condition() -> None:
    result = _c_loop_call(outer_c3_condition="G+C+P", repair_budget=0)
    assert result.trace_summary_fragment["repair_condition"] == "G+C"


def test_run_cluster3_c_plus_p_runs_c_loop_after_p_repair_and_succeeds(tmp_path: Path) -> None:
    run, _, _, _ = _run_with_results(tmp_path, "C+P", _f1_result(), _f2_result())
    row = run.rows[0]
    assert row.p_terminal_failure_code == "F2_NUMERIC_LARGE"
    assert row.c_loop_fired is True
    assert row.failure_code is None


def test_run_cluster3_c_wrapper_uses_outer_c3_condition_for_translation() -> None:
    assert _c_loop_call(outer_c3_condition="C+P", repair_budget=0).trace_summary_fragment["repair_condition"] == "C"


def test_run_cluster3_c_wrapper_translation_invariant_holds() -> None:
    assert _c_loop_call(outer_c3_condition="G+C+P", repair_budget=0).trace_summary_fragment["repair_condition"] == "G+C"


def test_run_cluster3_c_wrapper_rejects_unexpected_inner_condition(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_loop(**kwargs: Any) -> Any:
        generation = kwargs["generation"]
        generation(
            RepairGenerationInput(
                condition="G+C",
                attempt_index=1,
                base_seed=2,
                generation_seed=21,
                prompt=BASE_PROMPT,
            )
        )

    monkeypatch.setattr(c_loop_adapter, "run_repair_loop", fake_loop)
    with pytest.raises(AssertionError, match="unexpected inner condition"):
        _c_loop_call(outer_c3_condition="C+P")


def test_run_cluster3_c_loop_from_initial_f2_uses_same_budget_as_post_p_f2(tmp_path: Path) -> None:
    _, _, _, initial = _run_with_results(tmp_path, "C+P", _f2_result(), c_repair_budget=4)
    _, _, _, post = _run_with_results(tmp_path / "post", "C+P", _f1_result(), _f2_result(), c_repair_budget=4)
    assert initial.calls[0]["repair_budget"] == post.calls[0]["repair_budget"] == 4


def test_run_cluster3_c_loop_from_f2_preserves_outer_c3_condition() -> None:
    result = _c_loop_call(outer_c3_condition="G+C+P", repair_budget=0)
    assert result.trace_summary_fragment["outer_c3_condition"] == "G+C+P"


def test_run_cluster3_c_loop_from_f2_does_not_pass_p_compile_error_to_c_feedback() -> None:
    seen: list[RepairFeedbackInput] = []

    def builder(inputs: RepairFeedbackInput) -> str:
        seen.append(inputs)
        return inputs.base_prompt + "\nFix numeric values."

    _c_loop_call(feedback_builder=builder)
    assert seen[0].compile_error is None
    assert seen[0].signature_error is None


def test_run_cluster3_c_loop_from_f2_records_c_loop_source() -> None:
    assert _c_loop_call(repair_budget=0).c_loop_source == "initial_f2"


def test_c_loop_accepts_cluster2_feedback_callable_signature() -> None:
    def builder(inputs: RepairFeedbackInput) -> str:
        return inputs.base_prompt + "\nFix numeric values."

    assert _c_loop_call(feedback_builder=builder).terminal_source == C_SOURCE


def test_c_loop_allows_none_feedback_builder_for_default() -> None:
    assert _c_loop_call(feedback_builder=None).terminal_source == C_SOURCE


def test_c_loop_rejects_feedback_builder_that_includes_p_compile_error_text() -> None:
    def builder(inputs: RepairFeedbackInput) -> str:
        return inputs.base_prompt + "\nCompilationError: compiler failed"

    with pytest.raises(ValueError, match="P compile-error"):
        _c_loop_call(feedback_builder=builder)


def test_run_cluster3_c_loop_from_f2_requires_kernel_name() -> None:
    with pytest.raises(ValueError, match="kernel_name"):
        _c_loop_call(kernel_name="")


def test_run_cluster3_c_loop_from_f2_passes_kernel_name_to_eval_identity() -> None:
    kernel_names: list[str] = []

    def correctness(request: Any) -> dict[str, Any]:
        kernel_names.append(_identity_dict(request.identity)["kernel_name"])
        return {**_result(None), "identity": _identity_dict(request.identity)}

    _c_loop_call(correctness=correctness)
    assert kernel_names == ["relu"]


def test_cluster3_c_loop_result_contains_terminal_source_and_hash() -> None:
    result = _c_loop_call()
    assert result.terminal_source
    assert result.terminal_source_hash == _sha(result.terminal_source)


def test_cluster3_c_loop_result_budget_zero_preserves_seed_candidate_source() -> None:
    result = _c_loop_call(repair_budget=0)
    assert result.terminal_source == SEED_SOURCE
    assert result.c_attempt_count == 0


def test_cluster3_c_loop_result_terminal_correctness_result_drives_row_failure_code(tmp_path: Path) -> None:
    run, _, _, _ = _run_with_results(
        tmp_path,
        "C+P",
        _f2_result(),
        c_loop=CLoopRecorder(
            terminal_failure_code="F1_COMPILE",
            level_reached=1,
            compile_success=False,
            functional_success=False,
        ),
    )
    assert run.rows[0].failure_code == "F1_COMPILE"


def test_cluster3_c_loop_result_wraps_cluster2_result_without_losing_provenance() -> None:
    result = _c_loop_call()
    assert result.cluster2_repair_result is not None
    assert result.terminal_generation_seed == 21


def test_c_loop_budget_zero_terminal_seed_is_seed_candidate_generation_seed() -> None:
    assert _c_loop_call(repair_budget=0).terminal_generation_seed == 2


def test_c_loop_terminal_seed_tracks_final_c_attempt_seed() -> None:
    assert _c_loop_call().terminal_generation_seed == 21


def test_c_loop_seed_candidate_seed_not_overwritten_by_cluster2_internal_next_seed() -> None:
    result = _c_loop_call(repair_budget=0)
    assert result.terminal_generation_seed == 2
    assert result.terminal_generation_seed != 20


def test_phase5_row_construction_always_populates_p_repair_stop_reason(tmp_path: Path) -> None:
    run, _, _, _ = _run_with_results(tmp_path, "C+P", _f2_result())
    assert run.rows[0].p_repair_stop_reason == "p_not_applicable"


def test_phase5_copies_p_loop_stop_reason_to_row(tmp_path: Path) -> None:
    run, _, _, _ = _run_with_results(tmp_path, "P", _f1_result(), _result(None))
    assert run.rows[0].p_repair_stop_reason == "p_compile_repaired_then_success"


def test_run_cluster3_row_c_loop_fired_true_after_c_handoff(tmp_path: Path) -> None:
    run, _, _, _ = _run_with_results(tmp_path, "C+P", _f1_result(), _f2_result())
    assert run.rows[0].c_loop_fired is True


def test_run_cluster3_row_c_loop_source_post_p_f2_after_p_handoff(tmp_path: Path) -> None:
    run, _, _, _ = _run_with_results(tmp_path, "C+P", _f1_result(), _f2_result())
    assert run.rows[0].c_loop_source == "post_p_f2"


def test_run_cluster3_row_c_loop_fired_false_for_p_only_condition(tmp_path: Path) -> None:
    run, _, _, _ = _run_with_results(tmp_path, "P", _f1_result(), _f2_result())
    assert run.rows[0].c_loop_fired is False


def test_run_cluster3_row_p_terminal_failure_code_persists_after_c_success(tmp_path: Path) -> None:
    run, _, _, _ = _run_with_results(tmp_path, "C+P", _f1_result(), _f2_result())
    assert run.rows[0].p_terminal_failure_code == "F2_NUMERIC_LARGE"
    assert run.rows[0].failure_code is None


def test_run_cluster3_c_regression_to_f0_records_final_terminal_failure(tmp_path: Path) -> None:
    run, _, _, _ = _run_with_results(
        tmp_path,
        "C+P",
        _f2_result(),
        c_loop=CLoopRecorder(
            terminal_failure_code="F0_PARSE",
            level_reached=0,
            compile_success=False,
            functional_success=False,
        ),
    )
    assert run.rows[0].failure_code == "F0_PARSE"


def test_run_cluster3_c_regression_to_f1_records_final_terminal_failure(tmp_path: Path) -> None:
    run, _, _, _ = _run_with_results(
        tmp_path,
        "C+P",
        _f2_result(),
        c_loop=CLoopRecorder(
            terminal_failure_code="F1_COMPILE",
            level_reached=1,
            compile_success=False,
            functional_success=False,
        ),
    )
    assert run.rows[0].failure_code == "F1_COMPILE"


def test_run_cluster3_p_terminal_success_not_invalidated_by_c_regression(tmp_path: Path) -> None:
    run, _, _, _ = _run_with_results(
        tmp_path,
        "C+P",
        _f1_result(),
        _f2_result(),
        c_loop=CLoopRecorder(
            terminal_failure_code="F1_COMPILE",
            level_reached=1,
            compile_success=False,
            functional_success=False,
        ),
    )
    assert run.rows[0].p_compile_repair_succeeded is True
    assert run.rows[0].failure_code == "F1_COMPILE"


def test_run_cluster3_post_p_f3_without_compile_evidence_not_compile_repaired(tmp_path: Path) -> None:
    run, _, _, _ = _run_with_results(
        tmp_path,
        "P",
        _f1_result(),
        _result("F3_EVAL_PIPELINE", level_reached=0, compile_success=False, f3_reason="infra"),
    )
    assert run.rows[0].p_compile_repair_succeeded is False
    assert run.rows[0].p_repair_stop_reason == "p_f3_without_compile_evidence"


def test_run_cluster3_post_p_f3_with_compile_evidence_marks_compile_repaired(tmp_path: Path) -> None:
    run, _, _, _ = _run_with_results(
        tmp_path,
        "P",
        _f1_result(),
        _result("F3_EVAL_PIPELINE", level_reached=2, compile_success=True, f3_reason="infra"),
    )
    assert run.rows[0].p_compile_repair_succeeded is True
    assert run.rows[0].p_repair_stop_reason == "p_post_compile_f3_observed"


def test_run_cluster3_trace_summary_is_terminal_whole_row_summary(tmp_path: Path) -> None:
    run, _, _, _ = _run_with_results(tmp_path, "C+P", _f1_result(), _f2_result())
    row = run.rows[0]
    assert row.trace_summary.final_failure_code == row.failure_code
    assert row.trace_summary.c_loop_source == "post_p_f2"


def test_run_cluster3_terminal_source_stage_initial_sets_generation_seed_from_initial(tmp_path: Path) -> None:
    run, _, _, _ = _run_with_results(tmp_path, "P", _result(None))
    assert run.rows[0].terminal_source_stage == "initial"
    assert run.rows[0].terminal_generation_seed == 0


def test_run_cluster3_terminal_source_stage_p_attempt_sets_generation_seed_from_p_attempt(tmp_path: Path) -> None:
    run, _, _, _ = _run_with_results(tmp_path, "P", _f1_result(), _result(None))
    assert run.rows[0].terminal_source_stage == "p_attempt"
    assert run.rows[0].terminal_generation_seed == 1


def test_run_cluster3_terminal_source_stage_c_attempt_sets_generation_seed_from_c_attempt(tmp_path: Path) -> None:
    run, _, _, _ = _run_with_results(tmp_path, "C+P", _f2_result())
    assert run.rows[0].terminal_source_stage == "c_attempt"
    assert run.rows[0].terminal_generation_seed == 21


def test_run_cluster3_rejects_incomplete_c_trace_provenance(tmp_path: Path) -> None:
    class MissingGeneratedTraceCLoop(CLoopRecorder):
        def __call__(self, **kwargs: Any) -> Cluster3CLoopResult:
            result = super().__call__(**kwargs)
            return replace(result, cluster2_repair_result={"trace_summaries": []})

    with pytest.raises(ValueError, match="C repair trace count"):
        _run_with_results(tmp_path, "C+P", _f2_result(), c_loop=MissingGeneratedTraceCLoop())


def test_run_cluster3_generated_metadata_generation_seed_equals_terminal_generation_seed(tmp_path: Path) -> None:
    run, _, _, _ = _run_with_results(tmp_path, "C+P", _f2_result())
    row = run.rows[0]
    assert row.generated_metadata.generation_seed == row.terminal_generation_seed


def test_run_cluster3_p_attempt_changes_terminal_class(tmp_path: Path) -> None:
    run, _, _, _ = _run_with_results(tmp_path, "P", _f1_result(), _result(None))
    assert run.rows[0].p_repair_changed_terminal_class is True


def test_run_cluster3_writes_durable_jsonl(tmp_path: Path) -> None:
    config = _config(tmp_path, "P")
    run_cluster3(
        config,
        dependencies=RunnerDependencies(
            generation=GenerationRecorder(),
            correctness=CorrectnessRecorder(_result(None)),
        ),
    )
    assert Path(config.output).read_text(encoding="utf-8").count("\n") == 1
    assert default_content_hash_sidecar_path(config.output).exists()


def test_run_cluster3_writes_to_outputs_cluster3_only(tmp_path: Path) -> None:
    assert Cluster3RunnerConfig(condition="P", output="outputs/cluster3/test.jsonl")
    with pytest.raises(ValueError):
        Cluster3RunnerConfig(condition="P", output="outputs/cluster1/test.jsonl")
    with pytest.raises(ValueError):
        Cluster3RunnerConfig(condition="P", output="outputs/cluster2/test.jsonl")
    assert _config(tmp_path)


def test_run_cluster3_cli_parses_args(tmp_path: Path) -> None:
    config = parse_args(
        [
            "--condition",
            "C+P",
            "--output",
            str(tmp_path / "cli.jsonl"),
            "--model-revision",
            REV_A,
            "--tokenizer-revision",
            REV_B,
            "--c-repair-budget",
            "3",
            "--overwrite",
        ]
    )
    assert config.condition == "C+P"
    assert config.c_repair_budget == 3


def test_run_cluster3_cli_parses_diagnostic_seed_source(tmp_path: Path) -> None:
    config = parse_args(
        [
            "--condition",
            "G+P",
            "--scale-tier",
            "smoke",
            "--n",
            "1",
            "--dtypes",
            "fp32",
            "--diagnostic-seed-source",
            F1_DIAGNOSTIC_FIXTURE,
            "--diagnostic-expected-initial-failure",
            "F1_COMPILE",
            "--output",
            str(tmp_path / "diagnostic.jsonl"),
            "--model-revision",
            REV_A,
            "--tokenizer-revision",
            REV_B,
            "--overwrite",
        ]
    )

    assert config.condition == "G+P"
    assert config.diagnostic_seed_source == F1_DIAGNOSTIC_FIXTURE
    assert config.diagnostic_expected_initial_failure == "F1_COMPILE"
