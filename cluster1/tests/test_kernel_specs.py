"""Tests for KernelBench-backed kernel specs (Phase 6, Task 6.8)."""

import pytest

from cluster1.data.kernels import KERNEL_SPECS, get_kernel_spec
from cluster1.data.kernels.spec import KernelSpec
from cluster1.data.prompts.prompt_contract import build_prompt


class TestKernelSpecsPresent:
    def test_all_kernel_classes_present(self):
        assert set(KERNEL_SPECS.keys()) == {"elementwise", "reduction", "matmul"}

    @pytest.mark.parametrize("kernel_class", ["elementwise", "reduction", "matmul"])
    def test_spec_is_kernelspec(self, kernel_class: str):
        spec = get_kernel_spec(kernel_class)
        assert isinstance(spec, KernelSpec)

    @pytest.mark.parametrize("kernel_class", ["elementwise", "reduction", "matmul"])
    def test_three_dtype_keys(self, kernel_class: str):
        spec = get_kernel_spec(kernel_class)
        assert set(spec.shapes_by_dtype.keys()) == {"fp32", "fp16", "bf16"}

    @pytest.mark.parametrize("kernel_class", ["elementwise", "reduction", "matmul"])
    def test_at_least_five_shapes_per_dtype(self, kernel_class: str):
        spec = get_kernel_spec(kernel_class)
        for dtype_key, shapes in spec.shapes_by_dtype.items():
            assert len(shapes) >= 5, (
                f"{kernel_class}/{dtype_key} has only {len(shapes)} shapes, need >=5"
            )

    @pytest.mark.parametrize("kernel_class", ["elementwise", "reduction", "matmul"])
    def test_dataset_id_is_kernelbench(self, kernel_class: str):
        spec = get_kernel_spec(kernel_class)
        assert spec.dataset_id == "ScalingIntelligence/KernelBench"

    @pytest.mark.parametrize("kernel_class", ["elementwise", "reduction", "matmul"])
    def test_dataset_problem_id_is_positive_int(self, kernel_class: str):
        spec = get_kernel_spec(kernel_class)
        assert isinstance(spec.dataset_problem_id, int)
        assert spec.dataset_problem_id > 0

    @pytest.mark.parametrize("kernel_class", ["elementwise", "reduction", "matmul"])
    def test_build_prompt_contains_signature(self, kernel_class: str):
        spec = get_kernel_spec(kernel_class)
        prompt = build_prompt(spec, "fp32")
        sig_str = str(spec.reference_signature)
        assert sig_str in prompt, (
            f"Prompt for {kernel_class} does not contain signature: {sig_str}"
        )

    @pytest.mark.parametrize("kernel_class", ["elementwise", "reduction", "matmul"])
    def test_reference_code_not_empty(self, kernel_class: str):
        spec = get_kernel_spec(kernel_class)
        assert len(spec.reference_code) > 50

    def test_get_kernel_spec_raises_on_unknown(self):
        with pytest.raises(KeyError):
            get_kernel_spec("unknown_class")


class TestVerifiedProblemIds:
    """Verify the problem IDs match KernelBench Level 1 expectations."""

    def test_relu_is_problem_19(self):
        assert get_kernel_spec("elementwise").dataset_problem_id == 19

    def test_softmax_is_problem_23(self):
        assert get_kernel_spec("reduction").dataset_problem_id == 23

    def test_matmul_is_problem_1(self):
        assert get_kernel_spec("matmul").dataset_problem_id == 1
