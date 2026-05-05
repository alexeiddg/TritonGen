from cluster1.data.kernels.spec import KernelSpec
from cluster1.data.kernels.elementwise_relu import RELU_SPEC
from cluster1.data.kernels.reduction_softmax import SOFTMAX_SPEC
from cluster1.data.kernels.matmul_tiled_gemm import GEMM_SPEC

KERNEL_SPECS: dict[str, KernelSpec] = {
    "elementwise": RELU_SPEC,
    "reduction": SOFTMAX_SPEC,
    "matmul": GEMM_SPEC,
}


def get_kernel_spec(kernel_class: str) -> KernelSpec:
    if kernel_class not in KERNEL_SPECS:
        raise KeyError(
            f"Unknown kernel_class {kernel_class!r}. "
            f"Must be one of: {list(KERNEL_SPECS.keys())}"
        )
    return KERNEL_SPECS[kernel_class]
