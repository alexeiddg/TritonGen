from __future__ import annotations

import ast
import hashlib
import json
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
from cluster3.results.dataclass import Cluster3EvalRow
from shared.observability import (
    ObservabilityJsonlAppendLogger,
    ObservabilitySummary,
    default_observability_hash_path,
    default_observability_summary_path,
    file_sha256,
    load_observability_events,
)


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


def _safe_modal_context() -> dict[str, object]:
    return {
        "modal_context_available": True,
        "is_remote": True,
        "function_call_id": "fc-123",
        "input_id": "in-123",
        "task_id": "task-123",
        "image_id": "image-123",
        "region": "us-east",
        "cloud_provider": "aws",
        "environment_name": "test",
        "app_name": "tritongen",
        "gpu_type": "L4",
        "gpu_count": 1,
        "cpu_cores": 2.0,
        "memory_gib": 8.0,
        "timeout_s": 300,
        "container_started_at_utc": "2026-06-03T00:00:00Z",
        "modal_context_source": "runner_config",
    }


def _safe_token_counts() -> dict[str, object]:
    return {
        "token_counts_available": True,
        "prompt_tokens": 2,
        "generated_tokens": 3,
        "total_tokens": 5,
        "token_count_source": "existing_generation_result",
        "token_count_status": "available",
    }


def _safe_cost_estimate() -> dict[str, object]:
    return {
        "cost_estimate_available": True,
        "estimated_input_cost": 0.12,
        "estimated_output_cost": 0.03,
        "estimated_total_cost": 0.15,
        "currency": "USD",
        "pricing_source": "test_fixture",
        "pricing_source_version": "2026-06-03",
        "cost_estimate_status": "estimated",
        "cost_estimate_method": "test_fixture",
    }


def _unavailable_cost_summary() -> dict[str, object]:
    return {
        "cost_estimate_available": False,
        "estimated_input_cost": None,
        "estimated_output_cost": None,
        "estimated_total_cost": None,
        "currency": None,
        "pricing_source": None,
        "pricing_source_version": None,
        "cost_estimate_status": "unavailable",
        "cost_estimate_method": "unavailable",
    }


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


class FailingObservabilityLogger:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        del args, kwargs

    def open(self) -> None:
        raise RuntimeError("observability logger unavailable")


class ScriptedObservabilityLogger:
    def __init__(
        self,
        *,
        open_exc: BaseException | None = None,
        append_exc: BaseException | None = None,
        summary_exc: BaseException | None = None,
    ) -> None:
        self.open_exc = open_exc
        self.append_exc = append_exc
        self.summary_exc = summary_exc
        self.opened = False
        self.closed = False
        self.append_calls = 0
        self.summary_calls = 0

    def open(self) -> None:
        self.opened = True
        if self.open_exc is not None:
            raise self.open_exc

    def append(self, event: Any) -> None:
        del event
        self.append_calls += 1
        if self.append_exc is not None:
            raise self.append_exc

    def write_summary(self, summary: Any) -> None:
        del summary
        self.summary_calls += 1
        if self.summary_exc is not None:
            raise self.summary_exc

    def close(self) -> None:
        self.closed = True


class SummaryInterruptingObservabilityLogger(ObservabilityJsonlAppendLogger):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.opened = False
        self.closed = False
        self.summary_calls = 0

    def open(self) -> None:
        self.opened = True
        super().open()

    def write_summary(self, summary: Any) -> Any:
        del summary
        self.summary_calls += 1
        raise KeyboardInterrupt()

    def close(self) -> None:
        self.closed = True
        super().close()


def _identity_dict(identity: Any) -> dict[str, Any]:
    if isinstance(identity, dict):
        return dict(identity)
    if hasattr(identity, "model_dump"):
        return identity.model_dump()
    return dict(identity)


def _completed_stages(event_path: Path) -> list[str]:
    return [
        event.stage
        for event in load_observability_events(event_path)
        if event.event_type == "stage_completed"
        and event.stage is not None
    ]


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


def test_runner_config_repair_history_defaults_are_legacy(tmp_path: Path) -> None:
    config = _config(tmp_path)

    assert config.repair_history_policy == "last_attempt_only_v1"
    assert config.repair_max_prompt_chars == 24000
    assert config.repair_include_latest_source is False
    assert config.repair_history_config.repair_history_policy == (
        "last_attempt_only_v1"
    )


def test_cli_accepts_explicit_agentic_repair_history_policy(
    tmp_path: Path,
) -> None:
    config = parse_args(
        [
            "--condition",
            "P",
            "--kernel-class",
            "elementwise",
            "--scale-tier",
            "smoke",
            "--n",
            "1",
            "--model-revision",
            REV_A,
            "--tokenizer-revision",
            REV_B,
            "--repair-history-policy",
            "agentic_transcript_v1",
            "--repair-max-prompt-chars",
            "12000",
            "--repair-include-latest-source",
            "--output",
            str(tmp_path / "out.jsonl"),
            "--overwrite",
        ]
    )

    assert config.repair_history_config.repair_history_policy == (
        "agentic_transcript_v1"
    )
    assert config.repair_history_config.max_prompt_chars == 12000
    assert config.repair_history_config.include_latest_source is True


def test_cli_rejects_unknown_repair_history_policy(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        parse_args(
            [
                "--condition",
                "P",
                "--kernel-class",
                "elementwise",
                "--scale-tier",
                "smoke",
                "--n",
                "1",
                "--model-revision",
                REV_A,
                "--tokenizer-revision",
                REV_B,
                "--repair-history-policy",
                "unknown_policy",
                "--output",
                str(tmp_path / "out.jsonl"),
                "--overwrite",
            ]
        )


def test_config_rejects_invalid_repair_prompt_settings(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="max_prompt_chars must be a positive int"):
        _config(tmp_path, repair_max_prompt_chars=0)
    with pytest.raises(ValueError, match="max_prompt_chars must be a positive int"):
        _config(tmp_path, repair_max_prompt_chars=True)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="include_latest_source must be a bool"):
        _config(
            tmp_path,
            repair_include_latest_source="yes",  # type: ignore[arg-type]
        )


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
        "--repair-history-policy",
        "last_attempt_only_v1",
        "--repair-max-prompt-chars",
        "24000",
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


def test_run_cluster3_agentic_p_metadata_records_rendered_prompt(
    tmp_path: Path,
) -> None:
    run, generation, _, _ = _run_with_results(
        tmp_path,
        "P",
        _f1_result(),
        _result(None),
        repair_history_policy="agentic_transcript_v1",
    )

    row = run.rows[0]
    metadata = row.generated_metadata
    assert metadata is not None
    assert row.p_history_policy == "agentic_transcript_v1"
    assert metadata.p_history_policy == "agentic_transcript_v1"
    assert metadata.p_repair_anchor_attempt_index == 0
    assert metadata.p_repair_latest_attempt_index == 0
    assert metadata.p_repair_history_attempt_count == 1
    assert metadata.p_repair_prompt_sha256 == _sha(generation.calls[1]["prompt"])
    assert metadata.p_repair_max_prompt_chars == 24000
    assert metadata.p_repair_include_latest_source is False
    assert row.p_repair_trace is not None
    assert metadata.p_repair_anchor_source_hash == row.p_repair_trace[0].source_hash
    assert metadata.p_repair_latest_source_hash == row.p_repair_trace[0].source_hash
    assert row.terminal_prompt_hash == metadata.p_repair_prompt_sha256


def test_run_cluster3_default_p_metadata_records_legacy_policy(
    tmp_path: Path,
) -> None:
    run, _, _, _ = _run_with_results(tmp_path, "P", _result(None))

    metadata = run.rows[0].generated_metadata
    assert metadata is not None
    assert run.rows[0].p_history_policy == "last_attempt_only_v1"
    assert metadata.p_history_policy == "last_attempt_only_v1"
    assert metadata.p_repair_prompt_sha256 is None
    assert metadata.p_repair_anchor_attempt_index is None


def test_run_cluster3_agentic_initial_success_records_policy_only_metadata(
    tmp_path: Path,
) -> None:
    run, generation, correctness, _ = _run_with_results(
        tmp_path,
        "P",
        _result(None),
        repair_history_policy="agentic_transcript_v1",
    )

    row = run.rows[0]
    metadata = row.generated_metadata
    assert metadata is not None
    assert row.p_repair_attempted is False
    assert row.p_history_policy == "agentic_transcript_v1"
    assert metadata.p_history_policy == "agentic_transcript_v1"
    assert metadata.p_repair_prompt_sha256 is None
    assert metadata.p_repair_history_attempt_count is None
    assert len(generation.calls) == 1
    assert len(correctness.calls) == 1


def test_run_cluster3_initial_f1_runtime_is_terminal_without_p_loop(
    tmp_path: Path,
) -> None:
    run, generation, correctness, c_loop = _run_with_results(
        tmp_path,
        "P",
        _result("F1_RUNTIME", level_reached=1, compile_success=False),
        repair_history_policy="agentic_transcript_v1",
    )

    row = run.rows[0]
    assert row.failure_code == "F1_RUNTIME"
    assert row.p_repair_attempted is False
    assert row.p_repair_stop_reason == "p_not_applicable"
    assert len(generation.calls) == 1
    assert len(correctness.calls) == 1
    assert c_loop.calls == []


def test_run_cluster3_initial_f2_is_not_p_repaired_under_p_only(
    tmp_path: Path,
) -> None:
    run, generation, correctness, c_loop = _run_with_results(
        tmp_path,
        "P",
        _f2_result(),
        repair_history_policy="agentic_transcript_v1",
    )

    row = run.rows[0]
    assert row.failure_code == "F2_NUMERIC_LARGE"
    assert row.p_repair_attempted is False
    assert len(generation.calls) == 1
    assert len(correctness.calls) == 1
    assert c_loop.calls == []


def test_run_cluster3_does_not_pass_p_transcript_to_c_loop(
    tmp_path: Path,
) -> None:
    run, _, _, c_loop = _run_with_results(
        tmp_path,
        "C+P",
        _f1_result(),
        _f2_result(),
        repair_history_policy="agentic_transcript_v1",
    )

    assert run.rows[0].p_repair_attempted is True
    assert run.rows[0].c_loop_fired is True
    assert len(c_loop.calls) == 1
    c_call = c_loop.calls[0]
    repair_history_config = c_call["repair_history_config"]
    assert repair_history_config.repair_history_policy == "agentic_transcript_v1"
    assert "p_repair_trace" not in c_call
    assert "p_repair_prompt" not in c_call
    assert c_call["seed_candidate_evaluation"]["failure_code"] == "F2_NUMERIC_LARGE"
    assert c_call["seed_candidate_prompt_hash_source"] == "p_repair_prompt"


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
    assert config.observability_mode == "off"
    assert config.observability_experiment_id is None
    assert config.observability_run_id is None
    assert config.observability_output is None


def _signed_l1a_selector_args(*extra: str, token: str | None = None) -> list[str]:
    return [
        "--condition",
        runner_mod.L1A_GRAMMAR_MODE_CP_SELECTOR,
        "--kernel-class",
        "elementwise",
        "--scale-tier",
        "smoke",
        "--n",
        "1",
        "--dtypes",
        "fp32",
        "--repair-history-policy",
        "agentic_transcript_v1",
        "--signed-l1a-authorization",
        token or runner_mod.L1A_SIGNED_AUTHORIZATION_TOKEN,
        *extra,
        "--overwrite",
    ]


def test_l1a_12cell_dry_plan_cli_parses_without_output_or_write_mode() -> None:
    config = parse_args(
        [
            "--condition",
            runner_mod.L1A_GRAMMAR_MODE_CP_SELECTOR,
            "--repair-history-policy",
            "agentic_transcript_v1",
            "--dry-plan",
        ]
    )

    assert config.condition == runner_mod.L1A_GRAMMAR_MODE_CP_SELECTOR
    assert config.dry_plan is True
    assert config.write_mode == "dry_plan"
    assert config.output == runner_mod.L1A_DRY_PLAN_PLACEHOLDER_OUTPUT
    assert config.grammar_mode_cell == "all"


def test_l1a_12cell_dry_plan_cli_selects_single_no_p_cell() -> None:
    config = parse_args(
        [
            "--condition",
            runner_mod.L1A_GRAMMAR_MODE_CP_SELECTOR,
            "--grammar-mode-cell",
            "task_agnostic__c_on__p_off",
            "--dry-plan",
        ]
    )
    payload = runner_mod.build_l1a_dry_plan_payload(config)

    assert payload["cell_count"] == 1
    cell = payload["cells"][0]
    assert cell["condition_id"] == "task_agnostic__c_on__p_off"
    assert cell["factor_cell"] == "G+C"
    assert cell["execution_role"] == "no_p_control_cell"
    assert cell["compile_feedback_active"] is False
    assert cell["output_path"].startswith(
        "outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/"
    )


def test_l1a_12cell_execution_plan_cli_parses_without_output_or_write_mode() -> None:
    config = parse_args(
        [
            "--condition",
            runner_mod.L1A_GRAMMAR_MODE_CP_SELECTOR,
            "--repair-history-policy",
            "agentic_transcript_v1",
            "--execution-plan",
        ]
    )

    assert config.condition == runner_mod.L1A_GRAMMAR_MODE_CP_SELECTOR
    assert config.execution_plan is True
    assert config.dry_plan is False
    assert config.write_mode == "execution_plan"
    assert config.output == runner_mod.L1A_EXECUTION_SELECTOR_PLACEHOLDER_OUTPUT
    assert config.grammar_mode_cell == "all"


def test_l1a_12cell_execution_plan_builds_executable_commands() -> None:
    config = parse_args(
        [
            "--condition",
            runner_mod.L1A_GRAMMAR_MODE_CP_SELECTOR,
            "--grammar-mode-cell",
            "grammar_off__c_on__p_off",
            "--repair-history-policy",
            "agentic_transcript_v1",
            "--execution-plan",
        ]
    )
    payload = runner_mod.build_l1a_execution_plan_payload(config)

    assert payload["cell_count"] == 1
    assert payload["execution_authorized"] is False
    assert payload["requires_signed_l1a_authorization"] is True
    assert payload["writes_outputs"] is False
    assert payload["writes_artifacts"] is False
    assert payload["writes_mlruns"] is False
    cell = payload["cells"][0]
    assert cell["condition_id"] == "grammar_off__c_on__p_off"
    assert cell["command_mode"] == "executable"
    assert cell["compile_feedback_active"] is False
    assert cell["execution_role"] == "no_p_control_cell"
    assert "--dry-plan" not in cell["command_selector"]
    assert "--grammar-variant" not in cell["command_selector"]
    assert "--signed-l1a-authorization" in cell["command_selector"]
    assert "--output " + cell["output_path"] in cell["command_selector"]
    assert (
        "--observability-output " + cell["observability_event_path"]
        in cell["command_selector"]
    )


def test_l1a_12cell_selector_rejects_execution_without_dry_plan(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="signed-l1a-authorization"):
        parse_args(
            [
                "--condition",
                runner_mod.L1A_GRAMMAR_MODE_CP_SELECTOR,
                "--output",
                str(tmp_path / "out.jsonl"),
                "--overwrite",
            ]
        )


def test_dry_plan_rejects_old_condition_selector() -> None:
    with pytest.raises(SystemExit):
        parse_args(["--condition", "P", "--dry-plan"])


def test_grammar_mode_cell_rejects_non_dry_plan_selector(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="grammar-mode-cell"):
        parse_args(
            [
                "--condition",
                "P",
                "--grammar-mode-cell",
                "grammar_off__c_off__p_off",
                "--output",
                str(tmp_path / "out.jsonl"),
                "--overwrite",
            ]
        )


def test_l1a_12cell_dry_plan_main_does_not_run_or_write(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    planned = runner_mod.build_l1a_launcher_dry_plan(
        repair_history_policy="agentic_transcript_v1",
        repo_root=runner_mod.REPO_ROOT,
    )
    watched_paths = {
        Path(cell.output_path) for cell in planned
    } | {
        Path(cell.content_hash_sidecar_path) for cell in planned
    } | {
        Path(cell.observability_event_path) for cell in planned
    } | {
        Path(cell.observability_summary_path) for cell in planned
    } | {
        Path(cell.observability_hash_path) for cell in planned
    } | {Path("mlruns")}
    before = {path: path.exists() for path in watched_paths}

    def fail_run(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("dry-plan must not call run_cluster3")

    monkeypatch.setattr(runner_mod, "run_cluster3", fail_run)

    payload = runner_mod.main(
        [
            "--condition",
            runner_mod.L1A_GRAMMAR_MODE_CP_SELECTOR,
            "--repair-history-policy",
            "agentic_transcript_v1",
            "--dry-plan",
        ]
    )
    printed = json.loads(capsys.readouterr().out)

    assert json.loads(json.dumps(payload, sort_keys=True)) == printed
    assert printed["cell_count"] == 12
    assert printed["writes_outputs"] is False
    assert printed["writes_artifacts"] is False
    assert printed["writes_mlruns"] is False
    assert before == {path: path.exists() for path in watched_paths}


def test_l1a_12cell_execution_plan_main_does_not_run_or_write(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    planned = runner_mod.build_l1a_launcher_executable_plan(
        repair_history_policy="agentic_transcript_v1",
        repo_root=runner_mod.REPO_ROOT,
    )
    watched_paths = {
        Path(cell.output_path) for cell in planned
    } | {
        Path(cell.content_hash_sidecar_path) for cell in planned
    } | {
        Path(cell.observability_event_path) for cell in planned
    } | {
        Path(cell.observability_summary_path) for cell in planned
    } | {
        Path(cell.observability_hash_path) for cell in planned
    } | {Path("mlruns")}
    before = {path: path.exists() for path in watched_paths}

    def fail_run(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("execution-plan must not call run_cluster3")

    monkeypatch.setattr(runner_mod, "run_cluster3", fail_run)

    payload = runner_mod.main(
        [
            "--condition",
            runner_mod.L1A_GRAMMAR_MODE_CP_SELECTOR,
            "--repair-history-policy",
            "agentic_transcript_v1",
            "--execution-plan",
        ]
    )
    printed = json.loads(capsys.readouterr().out)

    assert json.loads(json.dumps(payload, sort_keys=True)) == printed
    assert printed["cell_count"] == 12
    assert printed["execution_authorized"] is False
    assert printed["writes_outputs"] is False
    assert printed["writes_artifacts"] is False
    assert printed["writes_mlruns"] is False
    assert before == {path: path.exists() for path in watched_paths}


def test_l1a_12cell_signed_selector_passes_prelaunch_guard_without_modal(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[runner_mod.Cluster3RunnerConfig] = []

    def fake_run(config: runner_mod.Cluster3RunnerConfig) -> runner_mod.Cluster3RunResult:
        calls.append(config)
        return runner_mod.Cluster3RunResult(
            rows=(),
            route_audit=(),
            output=config.output,
            write_mode=config.write_mode,
        )

    monkeypatch.setenv("TRITONGEN_MLFLOW", "0")
    monkeypatch.setattr(runner_mod, "run_cluster3", fake_run)

    result = runner_mod.main(_signed_l1a_selector_args())
    printed = json.loads(capsys.readouterr().out)

    assert isinstance(result, runner_mod.Cluster3RunResult)
    assert len(calls) == 1
    assert calls[0].condition == runner_mod.L1A_GRAMMAR_MODE_CP_SELECTOR
    assert calls[0].signed_l1a_authorization == runner_mod.L1A_SIGNED_AUTHORIZATION_TOKEN
    assert printed["rows"] == 0
    assert printed["output"] == runner_mod.L1A_EXECUTION_SELECTOR_PLACEHOLDER_OUTPUT


def test_l1a_12cell_selector_wrong_token_fails_prelaunch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRITONGEN_MLFLOW", "0")
    config = parse_args(_signed_l1a_selector_args(token="wrong-token"))

    with pytest.raises(ValueError, match="signed-l1a-authorization"):
        runner_mod._validate_l1a_runtime_authorization(config)


def test_l1a_12cell_selector_n5_fails_prelaunch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRITONGEN_MLFLOW", "0")
    config = parse_args(
        _signed_l1a_selector_args(
            "--n",
            "5",
        )
    )

    with pytest.raises(ValueError, match="--n 1"):
        runner_mod._validate_l1a_runtime_authorization(config)


@pytest.mark.parametrize("scale_tier", ["development", "paper"])
def test_l1a_12cell_selector_non_smoke_scale_fails_prelaunch(
    monkeypatch: pytest.MonkeyPatch,
    scale_tier: str,
) -> None:
    monkeypatch.setenv("TRITONGEN_MLFLOW", "0")
    config = parse_args(_signed_l1a_selector_args("--scale-tier", scale_tier))

    with pytest.raises(ValueError, match="--scale-tier smoke"):
        runner_mod._validate_l1a_runtime_authorization(config)


def test_l1a_12cell_selector_non_elementwise_kernel_fails_prelaunch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRITONGEN_MLFLOW", "0")
    config = parse_args(_signed_l1a_selector_args("--kernel-class", "reduction"))

    with pytest.raises(ValueError, match="--kernel-class elementwise"):
        runner_mod._validate_l1a_runtime_authorization(config)


def test_l1a_12cell_selector_mlflow_enabled_fails_prelaunch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRITONGEN_MLFLOW", "1")
    config = parse_args(_signed_l1a_selector_args())

    with pytest.raises(RuntimeError, match="TRITONGEN_MLFLOW=0"):
        runner_mod._validate_l1a_runtime_authorization(config)


def test_l1a_12cell_selector_resume_fails_closed() -> None:
    args = _signed_l1a_selector_args()
    args[args.index("--overwrite")] = "--resume"

    with pytest.raises(SystemExit):
        parse_args(args)


def test_l1a_12cell_selector_existing_target_path_fails_prelaunch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRITONGEN_MLFLOW", "0")
    config = parse_args(_signed_l1a_selector_args())
    first_cell = runner_mod.build_l1a_launcher_executable_plan(
        repair_history_policy="agentic_transcript_v1",
        repo_root=runner_mod.REPO_ROOT,
        signed_authorization_placeholder=runner_mod.L1A_SIGNED_AUTHORIZATION_TOKEN,
    )[0]
    existing_target = runner_mod.REPO_ROOT / first_cell.output_path
    original_exists = runner_mod.Path.exists

    def fake_exists(path: Path) -> bool:
        if path == existing_target:
            return True
        return original_exists(path)

    monkeypatch.setattr(runner_mod.Path, "exists", fake_exists)

    with pytest.raises(FileExistsError, match="already exists"):
        runner_mod._validate_l1a_runtime_authorization(config)


def test_l1a_12cell_selector_requires_exactly_12_planned_cells(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRITONGEN_MLFLOW", "0")
    config = parse_args(_signed_l1a_selector_args())
    cells = runner_mod.build_l1a_launcher_executable_plan(
        repair_history_policy="agentic_transcript_v1",
        repo_root=runner_mod.REPO_ROOT,
        signed_authorization_placeholder=runner_mod.L1A_SIGNED_AUTHORIZATION_TOKEN,
    )
    monkeypatch.setattr(
        runner_mod,
        "build_l1a_launcher_executable_plan",
        lambda **_kwargs: cells[:11],
    )

    with pytest.raises(ValueError, match="12 planned cells"):
        runner_mod._validate_l1a_runtime_authorization(config)


def test_l1a_12cell_dry_plan_rejects_output_argument(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        parse_args(
            [
                "--condition",
                runner_mod.L1A_GRAMMAR_MODE_CP_SELECTOR,
                "--output",
                str(tmp_path / "ignored.jsonl"),
                "--dry-plan",
            ]
        )


def test_l1a_12cell_execution_plan_rejects_output_argument(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        parse_args(
            [
                "--condition",
                runner_mod.L1A_GRAMMAR_MODE_CP_SELECTOR,
                "--output",
                str(tmp_path / "ignored.jsonl"),
                "--execution-plan",
            ]
        )


def test_expand_condition_selector_all_remains_cluster3_conditions() -> None:
    assert runner_mod.expand_condition_selector("all") == runner_mod.CLUSTER3_CONDITIONS


def test_observability_cli_exposes_required_mode_choices() -> None:
    parser = runner_mod.build_arg_parser()
    action = next(
        item for item in parser._actions if "--observability-mode" in item.option_strings
    )

    assert tuple(action.choices) == ("off", "best_effort", "required")


def test_observability_cli_rejects_unknown_mode(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        parse_args(
            [
                "--condition",
                "P",
                "--output",
                str(tmp_path / "out.jsonl"),
                "--model-revision",
                REV_A,
                "--tokenizer-revision",
                REV_B,
                "--observability-mode",
                "enabled",
                "--overwrite",
            ]
        )


def test_observability_cli_parses_enabled_output(tmp_path: Path) -> None:
    event_path = tmp_path / "events.jsonl"
    config = parse_args(
        [
            "--condition",
            "P",
            "--output",
            str(tmp_path / "out.jsonl"),
            "--model-revision",
            REV_A,
            "--tokenizer-revision",
            REV_B,
            "--observability-mode",
            "required",
            "--observability-experiment-id",
            "exp-1",
            "--observability-run-id",
            "run-1",
            "--observability-output",
            str(event_path),
            "--overwrite",
        ]
    )

    assert config.observability_mode == "required"
    assert config.observability_experiment_id == "exp-1"
    assert config.observability_run_id == "run-1"
    assert config.observability_output == str(event_path)


def test_observability_enabled_modes_require_ids(tmp_path: Path) -> None:
    for mode in ("best_effort", "required"):
        with pytest.raises(ValueError, match="observability_experiment_id"):
            _config(
                tmp_path,
                observability_mode=mode,
                observability_run_id="run-1",
            )
        with pytest.raises(ValueError, match="observability_run_id"):
            _config(
                tmp_path,
                observability_mode=mode,
                observability_experiment_id="exp-1",
            )


def test_observability_off_preserves_stable_run_id_and_writes_no_sidecar(
    tmp_path: Path,
) -> None:
    event_path = tmp_path / "ignored.observability.jsonl"
    context_provider_called = False
    token_counts_provider_called = False
    cost_estimate_provider_called = False

    def context_provider() -> dict[str, object]:
        nonlocal context_provider_called
        context_provider_called = True
        return _safe_modal_context()

    def token_counts_provider(context: dict[str, object]) -> dict[str, object]:
        nonlocal token_counts_provider_called
        token_counts_provider_called = True
        return _safe_token_counts()

    def cost_estimate_provider(context: dict[str, object]) -> dict[str, object]:
        nonlocal cost_estimate_provider_called
        cost_estimate_provider_called = True
        return _safe_cost_estimate()

    base = _config(tmp_path, "P")
    explicit_off = _config(
        tmp_path,
        "P",
        observability_mode="off",
        observability_experiment_id="exp-1",
        observability_run_id="run-1",
        observability_output=str(event_path),
    )

    assert runner_mod._stable_run_id(base) == runner_mod._stable_run_id(explicit_off)
    run_cluster3(
        explicit_off,
        dependencies=RunnerDependencies(
            generation=GenerationRecorder(),
            correctness=CorrectnessRecorder(_result(None)),
            modal_context_provider=context_provider,
            token_counts_provider=token_counts_provider,
            cost_estimate_provider=cost_estimate_provider,
        ),
    )

    assert context_provider_called is False
    assert token_counts_provider_called is False
    assert cost_estimate_provider_called is False
    assert not event_path.exists()
    assert not default_observability_hash_path(event_path).exists()
    assert not default_observability_summary_path(explicit_off.output).exists()


def test_observability_required_writes_valid_sidecars_in_tmp_path(
    tmp_path: Path,
) -> None:
    event_path = tmp_path / "cluster3.events.jsonl"
    config = _config(
        tmp_path,
        "P",
        observability_mode="required",
        observability_experiment_id="cluster3-o1",
        observability_run_id="run-required",
        observability_output=str(event_path),
    )

    run_cluster3(
        config,
        dependencies=RunnerDependencies(
            generation=GenerationRecorder(),
            correctness=CorrectnessRecorder(_result(None)),
        ),
    )

    events = load_observability_events(event_path)
    event_types = [event.event_type for event in events]
    assert [event.event_sequence for event in events] == list(range(len(events)))
    assert event_types == [
        "run_started",
        "row_started",
        "stage_started",
        "stage_completed",
        "stage_started",
        "stage_completed",
        "stage_started",
        "stage_completed",
        "row_completed",
        "run_completed",
    ]
    assert {event.experiment_id for event in events} == {"cluster3-o1"}
    assert {event.run_id for event in events} == {"run-required"}
    assert events[1].row_identity.cluster == "cluster3"
    assert events[1].row_identity.condition == "P"
    assert events[8].row_identity.row_sha256 is not None
    result_lines = Path(config.output).read_text(encoding="utf-8").splitlines()
    assert events[8].row_identity.row_sha256 == _sha(result_lines[0])
    assert [events[index].stage for index in (3, 5, 7)] == [
        "generation",
        "correctness_eval",
        "row_append",
    ]
    assert events[3].duration_ns is not None
    assert events[5].duration_ns is not None
    assert events[7].duration_ns is not None
    assert events[9].duration_ns is not None
    assert {event.modal_context is not None for event in events} == {True}
    assert {
        event.modal_context.modal_context_available
        for event in events
        if event.modal_context is not None
    } == {False}
    assert {event.token_counts is not None for event in events} == {True}
    assert {
        event.token_counts.token_counts_available
        for event in events
        if event.token_counts is not None
    } == {False}
    assert {event.cost_estimate is not None for event in events} == {True}
    assert {
        event.cost_estimate.cost_estimate_available
        for event in events
        if event.cost_estimate is not None
    } == {False}

    payload = json.dumps(
        [event.model_dump(mode="json") for event in events],
        sort_keys=True,
    ).lower()
    for forbidden in (
        "prompt_text",
        "source_text",
        "full_source",
        "completion_text",
        "generated_text",
        "raw_output",
        "raw_completion",
        "raw_feedback",
        "raw_compile_log",
        "private_eval",
        "private_feedback",
        "hidden_prompt",
        "hidden_eval",
        "token_ids",
        "input_ids",
        "output_ids",
        "tokenizer_dump",
        "tokenizer_state",
        "api_key",
        "secret",
        "credential",
        "password",
        "authorization",
        "speedup",
        "throughput",
        "latency",
        "kernel_timing",
        "benchmark",
        "profiler",
        "actual_cost",
        "actual_billing",
        "invoice",
        "account_charge",
        "provider_bill",
        "modal_bill",
        "billing_api_response",
        "pricing_api_response",
        "billing_claim",
        "cost_per_success",
        "cost_per_pass",
        "pass_at_k_cost",
        "pass@k",
        "roi",
        "economic_lift",
        "benchmark_cost_conclusion",
        "lift",
        "statistical",
    ):
        assert forbidden not in payload

    summary_path = default_observability_summary_path(config.output)
    summary = ObservabilitySummary.model_validate_json(
        summary_path.read_text(encoding="utf-8")
    )
    assert summary.result_path == config.output
    assert summary.observability_event_path == str(event_path)
    assert summary.row_counts == {"total": 1}
    assert summary.event_counts == {
        "run_started": 1,
        "row_started": 1,
        "stage_started": 3,
        "stage_completed": 3,
        "row_completed": 1,
        "run_completed": 1,
    }
    assert summary.stage_durations_ns["generation"] == events[3].duration_ns
    assert summary.stage_durations_ns["correctness_eval"] == events[5].duration_ns
    assert summary.stage_durations_ns["row_append"] == events[7].duration_ns
    assert summary.token_totals == {
        "token_count_status": "unavailable",
        "events_with_token_counts": 10,
        "events_with_available_token_counts": 0,
        "prompt_tokens": 0,
        "generated_tokens": 0,
        "total_tokens": 0,
        "token_count_sources": ["unavailable"],
    }
    assert summary.estimated_cost_summary == _unavailable_cost_summary()
    assert summary.modal_context_summary == {
        "context_status": "unavailable",
        "events_with_modal_context": 10,
        "events_with_available_context": 0,
        "modal_context_sources": ["unavailable"],
    }
    assert summary.source_event_sha256 == file_sha256(event_path)
    assert default_observability_hash_path(event_path).exists()


def test_observability_stage_timing_omits_repair_stages_when_not_active(
    tmp_path: Path,
) -> None:
    event_path = tmp_path / "success-stage-timing.observability.jsonl"
    config = _config(
        tmp_path,
        "P",
        observability_mode="required",
        observability_experiment_id="cluster3-stage-timing",
        observability_run_id="run-success",
        observability_output=str(event_path),
    )

    run_cluster3(
        config,
        dependencies=RunnerDependencies(
            generation=GenerationRecorder(),
            correctness=CorrectnessRecorder(_result(None)),
        ),
    )

    assert _completed_stages(event_path) == [
        "generation",
        "correctness_eval",
        "row_append",
    ]


def test_observability_stage_timing_records_p_repair_only_when_p_path_active(
    tmp_path: Path,
) -> None:
    event_path = tmp_path / "p-repair-stage-timing.observability.jsonl"
    config = _config(
        tmp_path,
        "P",
        observability_mode="required",
        observability_experiment_id="cluster3-stage-timing",
        observability_run_id="run-p-repair",
        observability_output=str(event_path),
    )

    run_cluster3(
        config,
        dependencies=RunnerDependencies(
            generation=GenerationRecorder(),
            correctness=CorrectnessRecorder(_f1_result(), _result(None)),
        ),
    )

    assert _completed_stages(event_path) == [
        "generation",
        "correctness_eval",
        "p_repair",
        "row_append",
    ]


def test_observability_stage_timing_records_c_repair_only_when_c_path_active(
    tmp_path: Path,
) -> None:
    event_path = tmp_path / "c-repair-stage-timing.observability.jsonl"
    config = _config(
        tmp_path,
        "C+P",
        observability_mode="required",
        observability_experiment_id="cluster3-stage-timing",
        observability_run_id="run-c-repair",
        observability_output=str(event_path),
    )

    run_cluster3(
        config,
        dependencies=RunnerDependencies(
            generation=GenerationRecorder(),
            correctness=CorrectnessRecorder(_f2_result()),
            c_loop_runner=CLoopRecorder(),
        ),
    )

    assert _completed_stages(event_path) == [
        "generation",
        "correctness_eval",
        "c_repair",
        "row_append",
    ]


def test_observability_stage_timing_omits_generation_for_diagnostic_seed(
    tmp_path: Path,
) -> None:
    event_path = tmp_path / "diagnostic-seed-stage-timing.observability.jsonl"
    config = _config(
        tmp_path,
        "G+P",
        diagnostic_seed_source=F1_DIAGNOSTIC_FIXTURE,
        diagnostic_expected_initial_failure="F1_COMPILE",
        observability_mode="required",
        observability_experiment_id="cluster3-stage-timing",
        observability_run_id="run-diagnostic-seed",
        observability_output=str(event_path),
    )

    run_cluster3(
        config,
        dependencies=RunnerDependencies(
            generation=GenerationRecorder(),
            correctness=CorrectnessRecorder(_f1_result(), _result(None)),
        ),
    )

    assert _completed_stages(event_path) == [
        "correctness_eval",
        "p_repair",
        "row_append",
    ]


def test_observability_stage_timing_does_not_change_scientific_row_payload(
    tmp_path: Path,
) -> None:
    output = tmp_path / "stable-row.jsonl"
    event_path = tmp_path / "stable-row.observability.jsonl"
    base_config = _config(tmp_path, "P", output=str(output))

    run_cluster3(
        base_config,
        dependencies=RunnerDependencies(
            generation=GenerationRecorder(),
            correctness=CorrectnessRecorder(_result(None)),
        ),
    )
    row_without_observability = output.read_text(encoding="utf-8")

    config_with_observability = replace(
        base_config,
        observability_mode="required",
        observability_experiment_id="cluster3-stage-timing",
        observability_run_id="run-row-stability",
        observability_output=str(event_path),
    )
    run_cluster3(
        config_with_observability,
        dependencies=RunnerDependencies(
            generation=GenerationRecorder(),
            correctness=CorrectnessRecorder(_result(None)),
        ),
    )

    assert output.read_text(encoding="utf-8") == row_without_observability


@pytest.mark.parametrize("mode", ["best_effort", "required"])
def test_observability_enabled_modes_include_supplied_safe_modal_context(
    tmp_path: Path,
    mode: str,
) -> None:
    event_path = tmp_path / f"{mode}.observability.jsonl"
    config = _config(
        tmp_path,
        "P",
        observability_mode=mode,
        observability_experiment_id="cluster3-o2",
        observability_run_id=f"run-{mode}",
        observability_output=str(event_path),
    )

    run_cluster3(
        config,
        dependencies=RunnerDependencies(
            generation=GenerationRecorder(),
            correctness=CorrectnessRecorder(_result(None)),
            modal_context_provider=_safe_modal_context,
        ),
    )

    events = load_observability_events(event_path)
    assert len(events) == 10
    assert {
        event.modal_context.function_call_id
        for event in events
        if event.modal_context is not None
    } == {"fc-123"}
    assert {
        event.modal_context.modal_context_available
        for event in events
        if event.modal_context is not None
    } == {True}

    summary = ObservabilitySummary.model_validate_json(
        default_observability_summary_path(config.output).read_text(encoding="utf-8")
    )
    assert summary.modal_context_summary == {
        "context_status": "available",
        "events_with_modal_context": 10,
        "events_with_available_context": 10,
        "modal_context_sources": ["runner_config"],
    }


@pytest.mark.parametrize("mode", ["best_effort", "required"])
def test_observability_enabled_modes_include_supplied_safe_token_counts(
    tmp_path: Path,
    mode: str,
) -> None:
    event_path = tmp_path / f"{mode}-token-counts.observability.jsonl"
    config = _config(
        tmp_path,
        "P",
        observability_mode=mode,
        observability_experiment_id="cluster3-o3",
        observability_run_id=f"run-{mode}-token-counts",
        observability_output=str(event_path),
    )
    provider_contexts: list[dict[str, object]] = []

    def token_counts_provider(context: dict[str, object]) -> dict[str, object] | None:
        provider_contexts.append(dict(context))
        if context["event_type"] == "row_completed":
            return _safe_token_counts()
        return None

    run_cluster3(
        config,
        dependencies=RunnerDependencies(
            generation=GenerationRecorder(),
            correctness=CorrectnessRecorder(_result(None)),
            token_counts_provider=token_counts_provider,
        ),
    )

    events = load_observability_events(event_path)
    assert len(events) == 10
    assert len(provider_contexts) == 10
    assert {tuple(sorted(context)) for context in provider_contexts} == {
        ("condition", "event_sequence", "event_type", "stage", "status")
    }
    available = [
        event.token_counts
        for event in events
        if event.token_counts is not None and event.token_counts.token_counts_available
    ]
    assert len(available) == 1
    assert available[0].prompt_tokens == 2
    assert available[0].generated_tokens == 3
    assert available[0].total_tokens == 5

    summary = ObservabilitySummary.model_validate_json(
        default_observability_summary_path(config.output).read_text(encoding="utf-8")
    )
    assert summary.token_totals == {
        "token_count_status": "available",
        "events_with_token_counts": 10,
        "events_with_available_token_counts": 1,
        "prompt_tokens": 2,
        "generated_tokens": 3,
        "total_tokens": 5,
        "token_count_sources": ["existing_generation_result", "unavailable"],
    }


@pytest.mark.parametrize("mode", ["best_effort", "required"])
def test_observability_enabled_modes_include_supplied_safe_cost_estimates(
    tmp_path: Path,
    mode: str,
) -> None:
    event_path = tmp_path / f"{mode}-cost-estimates.observability.jsonl"
    config = _config(
        tmp_path,
        "P",
        observability_mode=mode,
        observability_experiment_id="cluster3-o4",
        observability_run_id=f"run-{mode}-cost-estimates",
        observability_output=str(event_path),
    )
    provider_contexts: list[dict[str, object]] = []

    def cost_estimate_provider(context: dict[str, object]) -> dict[str, object] | None:
        provider_contexts.append(dict(context))
        if context["event_type"] == "row_completed":
            return _safe_cost_estimate()
        return None

    run_cluster3(
        config,
        dependencies=RunnerDependencies(
            generation=GenerationRecorder(),
            correctness=CorrectnessRecorder(_result(None)),
            cost_estimate_provider=cost_estimate_provider,
        ),
    )

    events = load_observability_events(event_path)
    assert len(events) == 10
    assert len(provider_contexts) == 10
    assert {tuple(sorted(context)) for context in provider_contexts} == {
        ("condition", "event_sequence", "event_type", "stage", "status")
    }
    available = [
        event.cost_estimate
        for event in events
        if event.cost_estimate is not None
        and event.cost_estimate.cost_estimate_available
    ]
    assert len(available) == 1
    assert available[0].estimated_total_cost == 0.15
    assert available[0].pricing_source == "test_fixture"

    summary = ObservabilitySummary.model_validate_json(
        default_observability_summary_path(config.output).read_text(encoding="utf-8")
    )
    assert summary.estimated_cost_summary == {
        "cost_estimate_available": True,
        "estimated_input_cost": 0.12,
        "estimated_output_cost": 0.03,
        "estimated_total_cost": 0.15,
        "currency": "USD",
        "pricing_source": "test_fixture",
        "pricing_source_version": "2026-06-03",
        "cost_estimate_status": "estimated",
        "cost_estimate_method": "test_fixture",
    }


def test_observability_best_effort_invalid_token_counts_degrades_safely(
    tmp_path: Path,
) -> None:
    event_path = tmp_path / "best-effort-invalid-token-counts.observability.jsonl"
    config = _config(
        tmp_path,
        "P",
        observability_mode="best_effort",
        observability_experiment_id="cluster3-o3",
        observability_run_id="run-best-effort-invalid-token-counts",
        observability_output=str(event_path),
    )

    result = run_cluster3(
        config,
        dependencies=RunnerDependencies(
            generation=GenerationRecorder(),
            correctness=CorrectnessRecorder(_result(None)),
            token_counts_provider=lambda _context: {
                **_safe_token_counts(),
                "prompt_tokens": -1,
            },
        ),
    )

    assert len(result.rows) == 1
    assert event_path.exists()
    assert event_path.read_text(encoding="utf-8") == ""
    assert not default_observability_summary_path(config.output).exists()


def test_observability_best_effort_invalid_cost_estimate_degrades_safely(
    tmp_path: Path,
) -> None:
    event_path = tmp_path / "best-effort-invalid-cost-estimate.observability.jsonl"
    config = _config(
        tmp_path,
        "P",
        observability_mode="best_effort",
        observability_experiment_id="cluster3-o4",
        observability_run_id="run-best-effort-invalid-cost-estimate",
        observability_output=str(event_path),
    )

    result = run_cluster3(
        config,
        dependencies=RunnerDependencies(
            generation=GenerationRecorder(),
            correctness=CorrectnessRecorder(_result(None)),
            cost_estimate_provider=lambda _context: {
                **_safe_cost_estimate(),
                "estimated_input_cost": -1.0,
            },
        ),
    )

    assert len(result.rows) == 1
    assert event_path.exists()
    assert event_path.read_text(encoding="utf-8") == ""
    assert not default_observability_summary_path(config.output).exists()


def test_observability_required_invalid_token_counts_fails_before_runner_work(
    tmp_path: Path,
) -> None:
    event_path = tmp_path / "required-invalid-token-counts.observability.jsonl"
    config = _config(
        tmp_path,
        "P",
        observability_mode="required",
        observability_experiment_id="cluster3-o3",
        observability_run_id="run-required-invalid-token-counts",
        observability_output=str(event_path),
    )
    generation = GenerationRecorder()
    correctness = CorrectnessRecorder(_result(None))

    with pytest.raises(ValueError, match="prompt_tokens"):
        run_cluster3(
            config,
            dependencies=RunnerDependencies(
                generation=generation,
                correctness=correctness,
                token_counts_provider=lambda _context: {
                    **_safe_token_counts(),
                    "prompt_tokens": -1,
                },
            ),
        )

    assert generation.calls == []
    assert correctness.calls == []
    assert not Path(config.output).exists()


def test_observability_required_invalid_cost_estimate_fails_before_runner_work(
    tmp_path: Path,
) -> None:
    event_path = tmp_path / "required-invalid-cost-estimate.observability.jsonl"
    config = _config(
        tmp_path,
        "P",
        observability_mode="required",
        observability_experiment_id="cluster3-o4",
        observability_run_id="run-required-invalid-cost-estimate",
        observability_output=str(event_path),
    )
    generation = GenerationRecorder()
    correctness = CorrectnessRecorder(_result(None))

    with pytest.raises(ValueError, match="estimated_input_cost"):
        run_cluster3(
            config,
            dependencies=RunnerDependencies(
                generation=generation,
                correctness=correctness,
                cost_estimate_provider=lambda _context: {
                    **_safe_cost_estimate(),
                    "estimated_input_cost": -1.0,
                },
            ),
        )

    assert generation.calls == []
    assert correctness.calls == []
    assert not Path(config.output).exists()


def test_observability_best_effort_context_failure_degrades_safely(
    tmp_path: Path,
) -> None:
    event_path = tmp_path / "best-effort-context-failure.observability.jsonl"
    config = _config(
        tmp_path,
        "P",
        observability_mode="best_effort",
        observability_experiment_id="cluster3-o2",
        observability_run_id="run-best-effort-context-failure",
        observability_output=str(event_path),
    )

    def failing_context_provider() -> dict[str, object]:
        raise RuntimeError("context unavailable")

    result = run_cluster3(
        config,
        dependencies=RunnerDependencies(
            generation=GenerationRecorder(),
            correctness=CorrectnessRecorder(_result(None)),
            modal_context_provider=failing_context_provider,
        ),
    )

    events = load_observability_events(event_path)
    assert len(result.rows) == 1
    assert {
        event.modal_context.modal_context_available
        for event in events
        if event.modal_context is not None
    } == {False}


def test_observability_required_forbidden_modal_context_fails_before_runner_work(
    tmp_path: Path,
) -> None:
    event_path = tmp_path / "required-forbidden-context.observability.jsonl"
    config = _config(
        tmp_path,
        "P",
        observability_mode="required",
        observability_experiment_id="cluster3-o2",
        observability_run_id="run-required-forbidden-context",
        observability_output=str(event_path),
    )
    generation = GenerationRecorder()
    correctness = CorrectnessRecorder(_result(None))

    with pytest.raises(ValueError, match="non-allowlisted"):
        run_cluster3(
            config,
            dependencies=RunnerDependencies(
                generation=generation,
                correctness=correctness,
                modal_context_provider=lambda: {"MODAL_IDENTITY_TOKEN": "secret"},
            ),
        )

    assert generation.calls == []
    assert correctness.calls == []
    assert not event_path.exists()


def test_observability_required_malformed_modal_context_fails_before_runner_work(
    tmp_path: Path,
) -> None:
    event_path = tmp_path / "required-malformed-context.observability.jsonl"
    config = _config(
        tmp_path,
        "P",
        observability_mode="required",
        observability_experiment_id="cluster3-o2",
        observability_run_id="run-required-malformed-context",
        observability_output=str(event_path),
    )
    generation = GenerationRecorder()
    correctness = CorrectnessRecorder(_result(None))

    with pytest.raises(ValueError, match="unavailable Modal context"):
        run_cluster3(
            config,
            dependencies=RunnerDependencies(
                generation=generation,
                correctness=correctness,
                modal_context_provider=lambda: {
                    "modal_context_available": False,
                    "function_call_id": "fc-123",
                    "modal_context_source": "runner_config",
                },
            ),
        )

    assert generation.calls == []
    assert correctness.calls == []
    assert not event_path.exists()


def test_observability_row_sha256_uses_exact_cluster3_row_json(
    tmp_path: Path,
) -> None:
    run = run_cluster3(
        _config(tmp_path, "P"),
        dependencies=RunnerDependencies(
            generation=GenerationRecorder(),
            correctness=CorrectnessRecorder(_result(None)),
        ),
    )
    row = run.rows[0]
    assert row.generated_metadata is not None
    non_ascii_row = replace(
        row,
        generated_metadata=replace(row.generated_metadata, model_id="modelo-é"),
    )

    identity = runner_mod._observability_row_identity_from_row(non_ascii_row)
    non_exact_json = json.dumps(
        non_ascii_row.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    assert identity.row_sha256 == _sha(non_ascii_row.to_json())
    assert identity.row_sha256 != _sha(non_exact_json)


def test_observability_enabled_resume_rejected_until_resume_policy_exists(
    tmp_path: Path,
) -> None:
    for mode in ("best_effort", "required"):
        with pytest.raises(ValueError, match="observability resume"):
            _config(
                tmp_path,
                "P",
                write_mode="resume",
                observability_mode=mode,
                observability_experiment_id="exp-1",
                observability_run_id=f"run-{mode}",
            )


def test_observability_required_path_collision_fails_before_runner_work(
    tmp_path: Path,
) -> None:
    output = tmp_path / "result.jsonl"
    config = _config(
        tmp_path,
        "P",
        output=str(output),
        observability_mode="required",
        observability_experiment_id="exp-1",
        observability_run_id="run-1",
        observability_output=str(output),
    )
    generation = GenerationRecorder()
    correctness = CorrectnessRecorder(_result(None))

    with pytest.raises(ValueError, match="collides"):
        run_cluster3(
            config,
            dependencies=RunnerDependencies(
                generation=generation,
                correctness=correctness,
            ),
        )

    assert generation.calls == []
    assert correctness.calls == []
    assert not output.exists()


def test_observability_best_effort_logger_failure_preserves_runner_outcome(
    tmp_path: Path,
) -> None:
    config = _config(
        tmp_path,
        "P",
        observability_mode="best_effort",
        observability_experiment_id="exp-1",
        observability_run_id="run-1",
    )
    run = run_cluster3(
        config,
        dependencies=RunnerDependencies(
            generation=GenerationRecorder(),
            correctness=CorrectnessRecorder(_result(None)),
            observability_logger_factory=lambda *args, **kwargs: FailingObservabilityLogger(),
        ),
    )

    assert len(run.rows) == 1


def test_observability_required_logger_failure_fails_before_runner_work(
    tmp_path: Path,
) -> None:
    config = _config(
        tmp_path,
        "P",
        observability_mode="required",
        observability_experiment_id="exp-1",
        observability_run_id="run-1",
    )
    generation = GenerationRecorder()
    correctness = CorrectnessRecorder(_result(None))

    with pytest.raises(RuntimeError, match="observability logger unavailable"):
        run_cluster3(
            config,
            dependencies=RunnerDependencies(
                generation=generation,
                correctness=correctness,
                observability_logger_factory=(
                    lambda *args, **kwargs: FailingObservabilityLogger()
                ),
            ),
        )

    assert generation.calls == []
    assert correctness.calls == []


def test_observability_required_first_event_failure_closes_logger(
    tmp_path: Path,
) -> None:
    logger = ScriptedObservabilityLogger(
        append_exc=RuntimeError("observability append unavailable")
    )
    config = _config(
        tmp_path,
        "P",
        observability_mode="required",
        observability_experiment_id="exp-1",
        observability_run_id="run-1",
    )
    generation = GenerationRecorder()
    correctness = CorrectnessRecorder(_result(None))

    with pytest.raises(RuntimeError, match="observability append unavailable"):
        run_cluster3(
            config,
            dependencies=RunnerDependencies(
                generation=generation,
                correctness=correctness,
                observability_logger_factory=lambda *args, **kwargs: logger,
            ),
        )

    assert logger.opened
    assert logger.append_calls >= 1
    assert logger.closed
    assert generation.calls == []
    assert correctness.calls == []


def test_observability_best_effort_setup_interrupt_propagates(
    tmp_path: Path,
) -> None:
    logger = ScriptedObservabilityLogger(open_exc=KeyboardInterrupt())
    config = _config(
        tmp_path,
        "P",
        observability_mode="best_effort",
        observability_experiment_id="exp-1",
        observability_run_id="run-1",
    )
    generation = GenerationRecorder()
    correctness = CorrectnessRecorder(_result(None))

    with pytest.raises(KeyboardInterrupt):
        run_cluster3(
            config,
            dependencies=RunnerDependencies(
                generation=generation,
                correctness=correctness,
                observability_logger_factory=lambda *args, **kwargs: logger,
            ),
        )

    assert logger.opened
    assert generation.calls == []
    assert correctness.calls == []


def test_observability_best_effort_first_event_interrupt_propagates_and_closes(
    tmp_path: Path,
) -> None:
    logger = ScriptedObservabilityLogger(append_exc=KeyboardInterrupt())
    config = _config(
        tmp_path,
        "P",
        observability_mode="best_effort",
        observability_experiment_id="exp-1",
        observability_run_id="run-1",
    )
    generation = GenerationRecorder()
    correctness = CorrectnessRecorder(_result(None))

    with pytest.raises(KeyboardInterrupt):
        run_cluster3(
            config,
            dependencies=RunnerDependencies(
                generation=generation,
                correctness=correctness,
                observability_logger_factory=lambda *args, **kwargs: logger,
            ),
        )

    assert logger.opened
    assert logger.closed
    assert generation.calls == []
    assert correctness.calls == []


def test_observability_best_effort_summary_interrupt_propagates_and_closes(
    tmp_path: Path,
) -> None:
    loggers: list[SummaryInterruptingObservabilityLogger] = []

    def logger_factory(*args: Any, **kwargs: Any) -> SummaryInterruptingObservabilityLogger:
        logger = SummaryInterruptingObservabilityLogger(*args, **kwargs)
        loggers.append(logger)
        return logger

    config = _config(
        tmp_path,
        "P",
        observability_mode="best_effort",
        observability_experiment_id="exp-1",
        observability_run_id="run-1",
    )
    generation = GenerationRecorder()
    correctness = CorrectnessRecorder(_result(None))

    with pytest.raises(KeyboardInterrupt):
        run_cluster3(
            config,
            dependencies=RunnerDependencies(
                generation=generation,
                correctness=correctness,
                observability_logger_factory=logger_factory,
            ),
        )

    assert len(loggers) == 1
    logger = loggers[0]
    assert logger.opened
    assert logger.summary_calls == 1
    assert logger.closed
    assert len(generation.calls) == 1
    assert len(correctness.calls) == 1


def test_observability_does_not_mutate_cluster3_result_row_schema() -> None:
    fields = set(Cluster3EvalRow.__dataclass_fields__)

    assert not {
        "observability_mode",
        "observability_event_path",
        "observability_summary_path",
        "observability_run_id",
        "observability_experiment_id",
        "duration_ns",
        "token_counts",
        "estimated_cost",
    } & fields


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
