"""Offline grammar acceptance and rejection tests."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from cluster1.data.prompts.prompt_contract import (
    ELEMENTWISE_AUTOTUNE_CONFIGS,
    MATMUL_AUTOTUNE_CONFIGS,
    REDUCTION_AUTOTUNE_CONFIGS,
    _format_autotune_configs,
)
from cluster1.grammar.acceptance_fixtures import (
    BAD_KERNELS,
    GOOD_KERNELS,
    TASK_AGNOSTIC_BAD_KERNELS,
    TASK_AGNOSTIC_COMPILE_CATCHABLE_KERNELS,
    TASK_AGNOSTIC_COMPILE_CATCHABLE_REJECTION_REASONS,
    TASK_AGNOSTIC_GENERATED_N5_DISAGREEMENT_REASONS,
    TASK_AGNOSTIC_GOOD_KERNELS,
    TASK_AGNOSTIC_SURFACE_REJECTION_REASONS,
)
from cluster1.grammar.triton_kernel_validator import (
    DEFAULT_GBNF_PATH,
    TASK_AGNOSTIC_GBNF_PATH,
    _collect_gbnf_productions,
    _compile_lark_parser,
    _semantic_accepts,
    accepts_source,
    validate_grammar_file,
)


def test_validator_compiles_actual_gbnf() -> None:
    report = validate_grammar_file()
    assert report.lark_compiles, "\n".join(report.errors)
    assert report.n_accept_cases >= 5
    assert report.n_reject_cases >= 10


def test_task_agnostic_validator_compiles_actual_gbnf() -> None:
    report = validate_grammar_file(TASK_AGNOSTIC_GBNF_PATH)
    assert report.lark_compiles, "\n".join(report.errors)
    assert report.n_accept_cases == len(TASK_AGNOSTIC_GOOD_KERNELS)
    assert report.n_reject_cases == len(TASK_AGNOSTIC_BAD_KERNELS)


def test_validator_rejects_malformed_gbnf_text(tmp_path) -> None:
    malformed = DEFAULT_GBNF_PATH.read_text(encoding="utf-8").replace(
        'tl-load-call ::= "tl.load(" kernel-expr ")"',
        'tl-load-call ::= "tl.load(" kernel-expr ")" | (',
    )
    grammar_path = tmp_path / "triton_kernel.gbnf"
    grammar_path.write_text(malformed, encoding="utf-8")

    report = validate_grammar_file(grammar_path)

    assert not report.lark_compiles
    assert report.errors


def test_acceptance_uses_actual_gbnf_behavior(tmp_path) -> None:
    tightened = DEFAULT_GBNF_PATH.read_text(encoding="utf-8").replace(
        'relu-where-call ::= "tl.where(x > "',
        'relu-where-call ::= "tl.not_where(x > "',
        1,
    )
    grammar_path = tmp_path / "triton_kernel.gbnf"
    grammar_path.write_text(tightened, encoding="utf-8")

    assert not accepts_source(GOOD_KERNELS["relu"], grammar_path)


@pytest.mark.parametrize("name", ["relu", "softmax", "matmul"])
def test_template_grammar_still_accepts_current_golden_fixtures(name: str) -> None:
    assert accepts_source(GOOD_KERNELS[name], DEFAULT_GBNF_PATH)


@pytest.mark.parametrize("name", ["relu", "softmax", "matmul"])
def test_task_agnostic_grammar_accepts_current_golden_fixtures(name: str) -> None:
    assert accepts_source(GOOD_KERNELS[name], TASK_AGNOSTIC_GBNF_PATH)


@pytest.mark.parametrize("name", TASK_AGNOSTIC_GOOD_KERNELS)
def test_task_agnostic_grammar_accepts_non_benchmark_fixtures(
    name: str,
) -> None:
    source = TASK_AGNOSTIC_GOOD_KERNELS[name]

    assert name not in {"relu", "softmax", "matmul"}
    assert accepts_source(source, TASK_AGNOSTIC_GBNF_PATH)


@pytest.mark.parametrize("name", TASK_AGNOSTIC_GOOD_KERNELS)
def test_template_grammar_is_not_required_to_accept_non_benchmark_fixtures(
    name: str,
) -> None:
    source = TASK_AGNOSTIC_GOOD_KERNELS[name]

    assert not accepts_source(source, DEFAULT_GBNF_PATH), name


@pytest.mark.parametrize("name", TASK_AGNOSTIC_BAD_KERNELS)
def test_task_agnostic_grammar_rejects_invalid_surface_fixtures(
    name: str,
) -> None:
    source = TASK_AGNOSTIC_BAD_KERNELS[name]

    assert not accepts_source(source, TASK_AGNOSTIC_GBNF_PATH), name


def test_task_agnostic_rejection_audit_metadata_covers_fixture_groups() -> None:
    assert set(TASK_AGNOSTIC_BAD_KERNELS) == set(
        TASK_AGNOSTIC_SURFACE_REJECTION_REASONS
    )
    assert set(TASK_AGNOSTIC_COMPILE_CATCHABLE_KERNELS) == set(
        TASK_AGNOSTIC_COMPILE_CATCHABLE_REJECTION_REASONS
    )
    assert all(
        reason.startswith("KEEP_SURFACE_CHECK:")
        for reason in TASK_AGNOSTIC_SURFACE_REJECTION_REASONS.values()
    )
    assert all(
        reason.startswith("DELETE_OR_RELAX_COMPILE_CATCHABLE:")
        for reason in TASK_AGNOSTIC_COMPILE_CATCHABLE_REJECTION_REASONS.values()
    )
    assert all(
        reason.startswith(("KEEP_SURFACE_CHECK:", "DELETE_OR_RELAX_COMPILE_CATCHABLE:"))
        for reason in TASK_AGNOSTIC_GENERATED_N5_DISAGREEMENT_REASONS.values()
    )


@pytest.mark.parametrize("name", TASK_AGNOSTIC_COMPILE_CATCHABLE_KERNELS)
def test_task_agnostic_accepts_compile_catchable_semantic_fixtures(
    name: str,
) -> None:
    source = TASK_AGNOSTIC_COMPILE_CATCHABLE_KERNELS[name]
    parser = _compile_lark_parser(TASK_AGNOSTIC_GBNF_PATH.read_text(encoding="utf-8"))

    parser.parse(source)
    assert accepts_source(source, TASK_AGNOSTIC_GBNF_PATH), name


@pytest.mark.parametrize(
    "name,source",
    [
        *TASK_AGNOSTIC_BAD_KERNELS.items(),
        *TASK_AGNOSTIC_COMPILE_CATCHABLE_KERNELS.items(),
    ],
)
def test_task_agnostic_parser_validator_disagreement_policy(
    name: str,
    source: str,
) -> None:
    parser = _compile_lark_parser(TASK_AGNOSTIC_GBNF_PATH.read_text(encoding="utf-8"))
    try:
        parser.parse(source)
        parser_accepts = True
    except Exception:
        parser_accepts = False

    accepted = accepts_source(source, TASK_AGNOSTIC_GBNF_PATH)
    assert (
        not parser_accepts
        or accepted
        or name in TASK_AGNOSTIC_SURFACE_REJECTION_REASONS
    ), name


@pytest.mark.parametrize(
    "name",
    [
        "generated_n1_fp16_assert_div_assignment",
        "generated_n1_bf16_assert_div_assignment",
        "generated_surfacefix_fp16_assert_assignment",
        "generated_surfacefix_bf16_assert_assignment",
    ],
)
def test_task_agnostic_parser_rejects_invalid_assert_assignment_surface(
    name: str,
) -> None:
    source = TASK_AGNOSTIC_BAD_KERNELS[name]
    parser = _compile_lark_parser(TASK_AGNOSTIC_GBNF_PATH.read_text(encoding="utf-8"))

    with pytest.raises(Exception):
        parser.parse(source)
    assert not accepts_source(source, TASK_AGNOSTIC_GBNF_PATH)


def test_task_agnostic_accepts_valid_native_assert_statement() -> None:
    source = TASK_AGNOSTIC_GOOD_KERNELS["native_assert_statement"]
    parser = _compile_lark_parser(TASK_AGNOSTIC_GBNF_PATH.read_text(encoding="utf-8"))

    parser.parse(source)
    assert accepts_source(source, TASK_AGNOSTIC_GBNF_PATH)


def test_task_agnostic_generated_n5_disagreement_policy() -> None:
    artifact = (
        Path(__file__).parents[2]
        / "outputs"
        / "cluster1"
        / "task_agnostic_g_elementwise_n5_l4.jsonl"
    )
    rows = {
        (row["dtype"], row["generation_seed"]): row
        for row in (
            json.loads(line)
            for line in artifact.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }
    parser = _compile_lark_parser(TASK_AGNOSTIC_GBNF_PATH.read_text(encoding="utf-8"))
    expected_kept_rejections = {
        key
        for key, reason in TASK_AGNOSTIC_GENERATED_N5_DISAGREEMENT_REASONS.items()
        if reason.startswith("KEEP_SURFACE_CHECK:")
    }
    expected_relaxed_accepts = {
        key
        for key, reason in TASK_AGNOSTIC_GENERATED_N5_DISAGREEMENT_REASONS.items()
        if reason.startswith("DELETE_OR_RELAX_COMPILE_CATCHABLE:")
    }

    assert set(TASK_AGNOSTIC_GENERATED_N5_DISAGREEMENT_REASONS) <= set(rows)

    parser_or_semantic_rejections: set[tuple[str, int]] = set()
    parser_rejections: set[tuple[str, int]] = set()
    for key, row in rows.items():
        source = row["source"]
        try:
            parser.parse(source)
        except Exception:
            parser_rejections.add(key)
            parser_or_semantic_rejections.add(key)
            continue
        if not accepts_source(source, TASK_AGNOSTIC_GBNF_PATH):
            parser_or_semantic_rejections.add(key)

    assert parser_or_semantic_rejections == expected_kept_rejections
    assert parser_rejections <= expected_kept_rejections
    for key in expected_relaxed_accepts:
        assert accepts_source(rows[key]["source"], TASK_AGNOSTIC_GBNF_PATH), key


def test_task_agnostic_rejects_undefined_block_size_meta_reference() -> None:
    assert not accepts_source(
        TASK_AGNOSTIC_BAD_KERNELS["undefined_block_size_meta_reference"],
        TASK_AGNOSTIC_GBNF_PATH,
    )


def test_task_agnostic_accepts_defined_block_size_meta_reference() -> None:
    assert accepts_source(
        TASK_AGNOSTIC_GOOD_KERNELS["vector_add"],
        TASK_AGNOSTIC_GBNF_PATH,
    )


def test_task_agnostic_accepts_keyword_meta_binding() -> None:
    assert accepts_source(
        TASK_AGNOSTIC_GOOD_KERNELS["keyword_meta_binding"],
        TASK_AGNOSTIC_GBNF_PATH,
    )


@pytest.mark.parametrize(
    "name",
    [
        "generic_launcher_name",
        "positional_axis_reduction",
        "generic_reduction_control_flow",
        "generic_nested_loop_tile_control",
        "multiline_nested_tl_expressions",
        "two_helper_kernels_generic",
        "reduce_combiner",
        "corpus_primitives",
        "scalar_wrapper_param_torch_dtype",
    ],
)
def test_task_agnostic_accepts_generic_language_surface_forms(name: str) -> None:
    source = TASK_AGNOSTIC_GOOD_KERNELS[name]
    parser = _compile_lark_parser(TASK_AGNOSTIC_GBNF_PATH.read_text(encoding="utf-8"))

    ast.parse(source)
    parser.parse(source)
    assert accepts_source(source, TASK_AGNOSTIC_GBNF_PATH), name


@pytest.mark.parametrize(
    "name",
    [
        "malformed_ifdevice_type",
        "broken_string_or_operations",
        "unclosed_parens",
        "missing_matrix_launcher",
        "repeated_helper_only_module",
        "truncated_public_wrapper_signature",
        "eof_inside_string",
        "eof_inside_parens",
        "top_level_solution_comment_drift",
        "malformed_wrapper_augassign_assert",
        "malformed_bracket_launch_assignment",
    ],
)
def test_task_agnostic_rejects_observed_surface_regression_fixtures(
    name: str,
) -> None:
    source = TASK_AGNOSTIC_BAD_KERNELS[name]
    parser = _compile_lark_parser(TASK_AGNOSTIC_GBNF_PATH.read_text(encoding="utf-8"))

    with pytest.raises(Exception):
        parser.parse(source)
    assert not accepts_source(source, TASK_AGNOSTIC_GBNF_PATH), name


def test_task_agnostic_remains_non_relu_template() -> None:
    source = TASK_AGNOSTIC_GOOD_KERNELS["non_template_body_shape"]

    assert "tl.where(x > 0" not in source
    assert accepts_source(source, TASK_AGNOSTIC_GBNF_PATH)


@pytest.mark.parametrize(
    "name",
    [
        "generated_n1_fp32_undefined_block_size",
        "generated_n1_fp16_assert_div_assignment",
        "generated_n1_bf16_assert_div_assignment",
        "generated_surfacefix_fp16_assert_assignment",
        "generated_surfacefix_bf16_assert_assignment",
    ],
)
def test_task_agnostic_generated_n1_failure_variants_rejected_locally(
    name: str,
) -> None:
    assert not accepts_source(TASK_AGNOSTIC_BAD_KERNELS[name], TASK_AGNOSTIC_GBNF_PATH)


def test_prompt_contract_autotune_configs_are_accepted_by_grammar() -> None:
    configs = _format_autotune_configs([ELEMENTWISE_AUTOTUNE_CONFIGS[0]])
    source = f"""\
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs={configs},
    key=["n_elements"],
)
@triton.jit
def _relu_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    out = tl.where(x > 0.0, x, 0.0)
    tl.store(out_ptr + offsets, out, mask=mask)

def relu(x: torch.Tensor) -> torch.Tensor:
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 64
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    _relu_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
"""

    assert accepts_source(source)


def test_prompt_contract_renders_python_config_calls() -> None:
    elementwise = _format_autotune_configs([ELEMENTWISE_AUTOTUNE_CONFIGS[0]])
    matmul = _format_autotune_configs([MATMUL_AUTOTUNE_CONFIGS[0]])

    assert (
        'triton.Config({"BLOCK_SIZE": 64}, num_warps=2, num_stages=3)'
        in elementwise
    )
    assert "triton.Config({BLOCK_SIZE=64" not in elementwise
    assert (
        'triton.Config({"BLOCK_M": 32, "BLOCK_N": 32, "BLOCK_K": 32}, '
        "num_warps=4, num_stages=2)"
        in matmul
    )
    assert "triton.Config({BLOCK_M=32" not in matmul


def test_all_prompt_contract_autotune_entries_are_accepted_by_grammar() -> None:
    parser = _compile_lark_parser(DEFAULT_GBNF_PATH.read_text(encoding="utf-8"))
    prompt_configs = (
        ELEMENTWISE_AUTOTUNE_CONFIGS + REDUCTION_AUTOTUNE_CONFIGS + MATMUL_AUTOTUNE_CONFIGS
    )

    for config in prompt_configs:
        config_list = _format_autotune_configs([config])
        source = f"""\
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs={config_list},
    key=["n_elements"],
)
@triton.jit
def _relu_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    out = tl.where(x > 0.0, x, 0.0)
    tl.store(out_ptr + offsets, out, mask=mask)

def relu(x: torch.Tensor) -> torch.Tensor:
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 64
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    _relu_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
"""

        parser.parse(source)


@pytest.mark.parametrize(
    "bad_config",
    [
        'triton.Config({"BLOCK_M": 256, "BLOCK_N": 256, "BLOCK_K": 256}, num_warps=16, num_stages=5)',
        'triton.Config({"BLOCK_SIZE": 64}, num_warps=16, num_stages=5)',
        'triton.Config({"BLOCK_SIZE": 512}, num_warps=4, num_stages=3)',
    ],
)
def test_actual_gbnf_rejects_autotune_configs_outside_prompt_contract(
    bad_config: str,
) -> None:
    parser = _compile_lark_parser(DEFAULT_GBNF_PATH.read_text(encoding="utf-8"))
    source = f"""\
import torch
import triton
import triton.language as tl

@triton.autotune(configs=[{bad_config}], key=["n_elements"])
@triton.jit
def _relu_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    out = tl.where(x > 0.0, x, 0.0)
    tl.store(out_ptr + offsets, out, mask=mask)

def relu(x: torch.Tensor) -> torch.Tensor:
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 64
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    _relu_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
"""

    with pytest.raises(Exception):
        parser.parse(source)


@pytest.mark.parametrize(
    "source",
    [
        GOOD_KERNELS["relu"].replace(
            "_relu_kernel[grid](x, out, n_elements, BLOCK_SIZE)",
            "_relu_kernel[grid](BLOCK_SIZE=BLOCK_SIZE, x)",
        ),
        GOOD_KERNELS["relu"].replace(
            "grid = (triton.cdiv(n_elements, BLOCK_SIZE),)",
            "grid = [x=1]",
        ),
    ],
)
def test_actual_gbnf_rejects_python_invalid_wrapper_syntax(source: str) -> None:
    parser = _compile_lark_parser(DEFAULT_GBNF_PATH.read_text(encoding="utf-8"))

    with pytest.raises(Exception):
        parser.parse(source)


@pytest.mark.parametrize(
    "bad_name",
    [
        "missing_output_allocation",
        "launch_uses_input_not_output",
        "relu_missing_launch_tail",
        "relu_wrong_launch_tail",
        "softmax_missing_launch_tail",
        "matmul_missing_launch_tail",
        "return_input_after_allocation",
        "unused_output_allocation",
        "reassigned_output_after_allocation",
        "torch_empty_tensor_shape",
        "torch_empty_missing_device_dtype",
        "torch_empty_like_invalid_empty_source",
        "relu_helper_missing_args",
        "relu_helper_missing_constexpr",
        "relu_helper_wrong_output_name",
        "softmax_helper_missing_args",
        "softmax_helper_missing_constexpr",
        "matmul_helper_missing_args",
        "matmul_helper_wrong_ptr_name",
        "grid_float_division",
        "grid_matmul_operator",
    ],
)
def test_actual_gbnf_rejects_validator_mismatch_wrapper_forms(bad_name: str) -> None:
    parser = _compile_lark_parser(DEFAULT_GBNF_PATH.read_text(encoding="utf-8"))

    with pytest.raises(Exception):
        parser.parse(BAD_KERNELS[bad_name])


@pytest.mark.parametrize(
    "good_name",
    [
        "relu_block_size_64",
        "relu_wrapper_blank_lines",
        "relu_where_out_assignment",
        "softmax_block_size_256",
        "matmul_k_from_b_shape",
    ],
)
def test_scope_hardening_preserves_family_level_wrapper_variation(
    good_name: str,
) -> None:
    parser = _compile_lark_parser(DEFAULT_GBNF_PATH.read_text(encoding="utf-8"))
    source = GOOD_KERNELS[good_name]

    parser.parse(source)
    assert accepts_source(source)


@pytest.mark.parametrize(
    "good_name",
    [
        "relu",
        "relu_where_out_assignment",
    ],
)
def test_relu_elementwise_positive_expressions_are_accepted(good_name: str) -> None:
    parser = _compile_lark_parser(DEFAULT_GBNF_PATH.read_text(encoding="utf-8"))
    source = GOOD_KERNELS[good_name]

    parser.parse(source)
    assert accepts_source(source)


@pytest.mark.parametrize(
    "bad_name",
    [
        "relu_tl_max_scalar_axis",
        "relu_tl_max_x_axis",
        "relu_tl_sum_x_axis",
        "relu_tl_dot_x_x",
        "relu_tl_atomic_add",
        "relu_tl_exp_x",
        "relu_tl_log_x",
        "relu_tl_sqrt_x",
        "relu_arbitrary_tl_call",
    ],
)
def test_relu_rejects_non_relu_tl_compute_calls(
    bad_name: str,
) -> None:
    parser = _compile_lark_parser(DEFAULT_GBNF_PATH.read_text(encoding="utf-8"))

    with pytest.raises(Exception):
        parser.parse(BAD_KERNELS[bad_name])
    assert not accepts_source(BAD_KERNELS[bad_name])


def test_task_agnostic_launch_wrapper_shape_remains_task_agnostic() -> None:
    productions = _collect_gbnf_productions(
        TASK_AGNOSTIC_GBNF_PATH.read_text(encoding="utf-8")
    )

    assert "softmax-launch-wrapper" not in productions
    assert "softmax-kernel-body" not in productions
    assert "def softmax" not in "\n".join(productions.values())
    assert "_softmax_kernel" not in "\n".join(productions.values())

    launch_surface = "\n".join(
        productions[name]
        for name in [
            "module",
            "agnostic-module",
            "jit-helper-section",
            "launch-wrapper",
            "wrapper-body",
            "bracket-launch-stmt",
            "wrapper-return-stmt",
        ]
    )
    assert "tl.max" not in launch_surface
    assert "tl.sum" not in launch_surface
    assert "tl.exp" not in launch_surface
    assert "row" not in launch_surface
    assert "axis" not in launch_surface


@pytest.mark.parametrize(
    "bad_name",
    [
        "relu_bare_x_compute",
        "relu_x_plus_one_compute",
        "relu_x_times_x_compute",
        "relu_scalar_zero_compute",
        "relu_boolean_compute",
    ],
)
def test_relu_rejects_non_relu_atom_and_arithmetic_compute(
    bad_name: str,
) -> None:
    parser = _compile_lark_parser(DEFAULT_GBNF_PATH.read_text(encoding="utf-8"))

    with pytest.raises(Exception):
        parser.parse(BAD_KERNELS[bad_name])
    assert not accepts_source(BAD_KERNELS[bad_name])


@pytest.mark.parametrize(
    "name,required_calls",
    [
        ("softmax", ("tl.max", "tl.sum")),
        ("matmul", ("tl.dot",)),
    ],
)
def test_softmax_and_gemm_family_ops_remain_accepted(
    name: str,
    required_calls: tuple[str, ...],
) -> None:
    parser = _compile_lark_parser(DEFAULT_GBNF_PATH.read_text(encoding="utf-8"))
    source = GOOD_KERNELS[name]

    for call in required_calls:
        assert call in source
    parser.parse(source)
    assert accepts_source(source)


@pytest.mark.parametrize(
    "bad_name",
    [
        "softmax_duplicate_mask_keyword",
        "softmax_uses_undefined_n_rows_in_kernel",
        "softmax_python_min_subscript",
        "softmax_pointer_slice_assignment",
        "softmax_negative_tensor_index_mask",
        "softmax_missing_store",
        "matmul_program_id_tuple_subscript",
        "matmul_missing_store",
    ],
)
def test_observed_softmax_gemm_compile_failures_rejected_locally(
    bad_name: str,
) -> None:
    parser = _compile_lark_parser(DEFAULT_GBNF_PATH.read_text(encoding="utf-8"))

    with pytest.raises(Exception):
        parser.parse(BAD_KERNELS[bad_name])
    assert not accepts_source(BAD_KERNELS[bad_name])


@pytest.mark.parametrize(
    "bad_name,case",
    [
        ("relu_missing_dimension_extraction", "missing dimension extraction"),
        ("relu_wrong_dimension_binding_type", "wrong variable binding type"),
        ("relu_undefined_grid_variable", "undefined grid variable"),
        ("relu_arbitrary_wrapper_expression", "arbitrary wrapper expression"),
        ("relu_invalid_prelude_ordering", "invalid wrapper prelude ordering"),
        ("relu_missing_return", "missing return"),
        ("relu_wrong_launch_argument_ordering", "wrong launch argument ordering"),
        ("softmax_missing_shape_extraction", "missing softmax shape extraction"),
        ("softmax_wrong_shape_binding_type", "wrong softmax binding type"),
        ("softmax_invalid_prelude_ordering", "invalid softmax prelude ordering"),
        ("matmul_missing_dimension_extraction", "missing GEMM dimension extraction"),
        ("matmul_wrong_dimension_binding_type", "wrong GEMM binding type"),
        ("matmul_invalid_grid_construction", "noncanonical GEMM grid construction"),
    ],
)
def test_scope_hardened_wrapper_parser_rejects_noncanonical_forms(
    bad_name: str,
    case: str,
) -> None:
    parser = _compile_lark_parser(DEFAULT_GBNF_PATH.read_text(encoding="utf-8"))

    with pytest.raises(Exception):
        parser.parse(BAD_KERNELS[bad_name])
    assert not accepts_source(BAD_KERNELS[bad_name]), case


@pytest.mark.parametrize(
    "name,source",
    [
        *[(name, GOOD_KERNELS[name]) for name in [
            "relu_block_size_64",
            "relu_wrapper_blank_lines",
            "relu_where_out_assignment",
            "softmax_block_size_256",
            "matmul_k_from_b_shape",
        ]],
        *[(name, BAD_KERNELS[name]) for name in [
            "relu_missing_dimension_extraction",
            "relu_wrong_dimension_binding_type",
            "relu_undefined_grid_variable",
            "relu_arbitrary_wrapper_expression",
            "relu_invalid_prelude_ordering",
            "relu_missing_return",
            "relu_wrong_launch_argument_ordering",
            "softmax_missing_shape_extraction",
            "softmax_wrong_shape_binding_type",
            "softmax_invalid_prelude_ordering",
            "matmul_missing_dimension_extraction",
            "matmul_wrong_dimension_binding_type",
            "matmul_invalid_grid_construction",
            "relu_tl_max_scalar_axis",
            "relu_tl_max_x_axis",
            "relu_tl_sum_x_axis",
            "relu_tl_dot_x_x",
            "relu_tl_atomic_add",
            "relu_tl_exp_x",
            "relu_tl_log_x",
            "relu_tl_sqrt_x",
            "relu_bare_x_compute",
            "relu_x_plus_one_compute",
            "relu_x_times_x_compute",
            "relu_scalar_zero_compute",
            "relu_boolean_compute",
            "relu_arbitrary_tl_call",
            "softmax_duplicate_mask_keyword",
            "softmax_uses_undefined_n_rows_in_kernel",
            "softmax_python_min_subscript",
            "softmax_pointer_slice_assignment",
            "softmax_negative_tensor_index_mask",
            "softmax_missing_store",
            "matmul_program_id_tuple_subscript",
            "matmul_missing_store",
        ]],
    ],
)
def test_parser_and_semantic_validator_agree_on_scope_hardening_fixtures(
    name: str,
    source: str,
) -> None:
    parser = _compile_lark_parser(DEFAULT_GBNF_PATH.read_text(encoding="utf-8"))
    try:
        parser.parse(source)
        parser_accepts = True
    except Exception:
        parser_accepts = False

    assert parser_accepts == accepts_source(source), name


@pytest.mark.parametrize(
    "bad_name",
    [
        "relu_missing_launch_tail",
        "relu_wrong_launch_tail",
        "softmax_missing_launch_tail",
        "matmul_missing_launch_tail",
    ],
)
def test_semantic_validator_rejects_bad_launch_args(bad_name: str) -> None:
    assert not _semantic_accepts(ast.parse(BAD_KERNELS[bad_name]))


@pytest.mark.parametrize(
    "bad_name",
    [
        "relu_helper_missing_args",
        "relu_helper_missing_constexpr",
        "relu_helper_wrong_output_name",
        "softmax_helper_missing_args",
        "softmax_helper_missing_constexpr",
        "matmul_helper_missing_args",
        "matmul_helper_wrong_ptr_name",
    ],
)
def test_semantic_validator_rejects_bad_helper_signatures(bad_name: str) -> None:
    assert not _semantic_accepts(ast.parse(BAD_KERNELS[bad_name]))


@pytest.mark.parametrize(
    "name,source",
    [
        ("relu", GOOD_KERNELS["relu"]),
        ("softmax", GOOD_KERNELS["softmax"]),
        ("matmul", GOOD_KERNELS["matmul"]),
    ],
)
def test_actual_gbnf_rejects_incomplete_canonical_module_boundaries(
    name: str,
    source: str,
) -> None:
    incomplete_prefixes = {
        "imports_only": source.split("@triton.jit", maxsplit=1)[0],
        "helper_only": source.split(f"\ndef {name}", maxsplit=1)[0] + "\n",
        "before_return": source.rsplit("    return ", maxsplit=1)[0] + "\n",
    }

    for boundary, prefix in incomplete_prefixes.items():
        assert not accepts_source(prefix), boundary


@pytest.mark.parametrize("name,source", GOOD_KERNELS.items())
def test_good_kernels_are_accepted(name: str, source: str) -> None:
    assert accepts_source(source), f"GOOD_KERNELS[{name!r}] was rejected"


@pytest.mark.parametrize("name,source", BAD_KERNELS.items())
def test_bad_kernels_are_rejected(name: str, source: str) -> None:
    assert not accepts_source(source), f"BAD_KERNELS[{name!r}] was accepted"
