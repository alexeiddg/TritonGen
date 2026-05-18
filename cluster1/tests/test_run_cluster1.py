"""Tests for the Phase 7 Cluster 1 experiment runner."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import cluster1.experiments.run_cluster1 as runner
from cluster1.validation.compile_check import CompileResult


def test_parse_args_defaults(tmp_path: Path) -> None:
    output = tmp_path / "results.jsonl"

    args = runner.parse_args(
        [
            "--condition",
            "both",
            "--kernel-class",
            "all",
            "--output",
            str(output),
        ]
    )

    assert args.model_id == runner.DEFAULT_MODEL_ID
    assert args.dataset_id == runner.DEFAULT_DATASET_ID
    assert args.n == 20
    assert args.output == output
    assert args.grammar_path == runner.DEFAULT_GRAMMAR_PATH
    assert args.grammar_variant == "template_upper_bound"
    assert args.temperature == 0.2
    assert args.max_new_tokens == runner.DEFAULT_MAX_NEW_TOKENS
    assert args.max_new_tokens >= 1024


def test_grammar_variant_run_path_rejects_explicit_mismatch() -> None:
    args = SimpleNamespace(
        condition="G",
        grammar_variant="template_upper_bound",
        grammar_path=Path("cluster1/grammar/triton_kernel_agnostic.gbnf"),
    )

    with pytest.raises(ValueError, match="grammar_path must match grammar_variant"):
        runner._validate_grammar_variant_run_path(args)


def test_iter_experiment_cells_n20() -> None:
    cells = list(
        runner.iter_experiment_cells(
            ["elementwise", "reduction", "matmul"],
            condition="both",
            n=20,
        )
    )

    assert len(cells) == 360
    assert all(len(cell) == 4 for cell in cells)
    assert {cell[0].kernel_class for cell in cells} == {
        "elementwise",
        "reduction",
        "matmul",
    }
    assert {cell[1] for cell in cells} == {False, True}
    assert {cell[2] for cell in cells} == {"fp32", "fp16", "bf16"}
    assert {cell[3] for cell in cells} == set(range(20))


def test_run_one_generation_assembles_generation_result(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = runner.get_kernel_spec("elementwise")
    args = SimpleNamespace(
        model_id="fake/model",
        grammar_variant="template_upper_bound",
        max_new_tokens=128,
        temperature=0.2,
    )

    def fake_generate_source(**kwargs):
        assert kwargs["grammar_active"] is True
        assert kwargs["compiled_grammar"] == "compiled"
        assert kwargs["seed"] == 3
        return SimpleNamespace(
            source="def relu(x):\n    return x\n",
            masked_token_rate=0.4,
            generation_seed=3,
            temperature=0.2,
        )

    def fake_check_compiles_all_dtypes(source, compile_spec, shapes_by_dtype):
        assert source.startswith("def relu")
        assert compile_spec is spec.compile_spec
        assert shapes_by_dtype is spec.shapes_by_dtype
        return [
            CompileResult(True, None, None, "fp32", 5),
            CompileResult(False, "RuntimeError", "launch failed", "fp16", 2),
            CompileResult(True, None, None, "bf16", 5),
        ]

    monkeypatch.setattr(runner, "generate_source", fake_generate_source)
    monkeypatch.setattr(runner, "check_compiles_all_dtypes", fake_check_compiles_all_dtypes)

    result = runner.run_one_generation(
        spec=spec,
        dtype="fp16",
        seed=3,
        grammar_active=True,
        model=object(),
        tokenizer=object(),
        compiled_grammar="compiled",
        args=args,
    )

    assert result.model_id == "fake/model"
    assert result.grammar_active is True
    assert result.grammar_variant == "template_upper_bound"
    assert result.kernel_class == "elementwise"
    assert result.kernel_name == "relu"
    assert result.dtype == "fp16"
    assert result.compile_success is False
    assert result.compile_results_by_dtype == {
        "fp32": True,
        "fp16": False,
        "bf16": True,
    }
    assert result.compile_error_type == "RuntimeError"
    assert result.compile_error_msg == "launch failed"
    assert result.failure_code == "F1_RUNTIME"
    assert result.masked_token_rate == 0.4
    assert result.unique_solution_hash
    assert result.n_shapes_tested == 2
    assert result.generation_seed == 3


def test_main_baseline_logs_all_dtype_cells(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output = tmp_path / "baseline.jsonl"
    calls: list[tuple] = []

    monkeypatch.setattr(
        runner,
        "load_model_and_tokenizer",
        lambda model_id: calls.append(("load", model_id)) or ("model", "tokenizer"),
    )
    monkeypatch.setattr(
        runner,
        "load_compiled_grammar",
        lambda grammar_path, model_id: calls.append(("grammar", grammar_path, model_id))
        or "compiled",
    )
    monkeypatch.setattr(
        runner,
        "generate_source",
        lambda **kwargs: SimpleNamespace(
            source="def relu(x):\n    return x\n",
            masked_token_rate=0.5 if kwargs["grammar_active"] else None,
            generation_seed=kwargs["seed"],
            temperature=kwargs["temperature"],
        ),
    )
    monkeypatch.setattr(
        runner,
        "check_compiles_all_dtypes",
        lambda source, compile_spec, shapes_by_dtype: [
            CompileResult(True, None, None, "fp32", 5),
            CompileResult(True, None, None, "fp16", 5),
            CompileResult(True, None, None, "bf16", 5),
        ],
    )

    exit_code = runner.main(
        [
            "--condition",
            "baseline",
            "--kernel-class",
            "elementwise",
            "--n",
            "2",
            "--output",
            str(output),
        ]
    )

    rows = output.read_text(encoding="utf-8").splitlines()
    assert exit_code == 0
    assert len(rows) == 6
    assert calls == [("load", runner.DEFAULT_MODEL_ID)]


def test_runner_has_no_feedback_loop() -> None:
    source = Path(runner.__file__).read_text(encoding="utf-8")
    lower_source = source.lower()

    forbidden_terms = (
        "re" + "try",
        "re" + "pair",
        "feed" + "back",
        "re" + "_prompt",
    )
    for forbidden in forbidden_terms:
        assert forbidden not in lower_source

    prompt_start = source.index("prompt = build_prompt(spec, dtype)")
    generation_start = source.index("decoded = generate_source(", prompt_start)
    prompt_segment = source[prompt_start:generation_start]
    assert "compile" + "_error" not in prompt_segment
