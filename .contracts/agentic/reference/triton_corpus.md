What "full Triton language corpus" should actually mean
Cluster 1 note: this reference enumerates Triton-language/API material. It does
not mean the Cluster 1 `G` control is a full Triton language grammar. Cluster 1
uses this corpus to audit the `tl.*` API allow-list while keeping the generated
module, helper, launcher, allocation, grid, bracket-launch, and return shape as
separate harness constraints.

When you scope the corpus to Triton only, here's what that means concretely so Claude Code doesn't accidentally pull in adjacent material:
In scope: triton.language module (all tl.* functions), @triton.jit decorator, @triton.autotune and triton.Config, @triton.heuristics, tl.constexpr, the public Python launcher pattern with bracket-launch syntax (kernel[grid](...)), block pointer APIs (tl.make_block_ptr, tl.advance), and the standard control flow patterns Triton supports inside kernels (if/else, for, tl.where).
Out of scope: Anything under triton.runtime beyond what the launcher needs, anything under triton._C internals, the gluon module entirely, triton.testing (that's harness code, not kernel code), TileLang's surface even if it appears in adjacent docs, and any CUDA-source helpers some Triton tutorials use for benchmarking comparisons.
The "100+ tutorial and test files" you'll pull from the Triton repo are all Triton-language files — they live under python/tutorials/ and python/test/unit/language/. Skip python/test/gluon/ if it exists, and skip anything in python/triton/experimental/ unless you have a specific reason to include an experimental feature.

---

triton
jit

Decorator for JIT-compiling a function using the Triton compiler.

autotune

Decorator for auto-tuning a triton.jit'd function.

heuristics

Decorator for specifying how the values of certain meta-parameters may be computed.

Config

An object that represents a possible kernel configuration for the auto-tuner to try.


---

triton.jit
triton.jit(fn: T)→ JITFunction[T]
triton.jit(*, version=None, repr: Callable | None = None, launch_metadata: Callable | None = None, do_not_specialize: Iterable[int | str] | None = None, do_not_specialize_on_alignment: Iterable[int | str] | None = None, debug: bool | None = None, noinline: bool | None = None)→ Callable[[T], JITFunction[T]]
Decorator for JIT-compiling a function using the Triton compiler.

Note
:
When a jit’d function is called, arguments are implicitly converted to pointers if they have a .data_ptr() method and a .dtype attribute.

Note
:
This function will be compiled and run on the GPU. It will only have access to:

python primitives,

builtins within the triton package,

arguments to this function,

other jit’d functions

Parameters
:
fn (Callable) – the function to be jit-compiled

---

triton.autotune
triton.autotune(configs, key, prune_configs_by=None, reset_to_zero=None, restore_value=None, pre_hook=None, post_hook=None, warmup=None, rep=None, use_cuda_graph=False, do_bench=None, cache_results=False)
Decorator for auto-tuning a triton.jit’d function.

@triton.autotune(configs=[
    triton.Config(kwargs={'BLOCK_SIZE': 128}, num_warps=4),
    triton.Config(kwargs={'BLOCK_SIZE': 1024}, num_warps=8),
  ],
  key=['x_size'] # the two above configs will be evaluated anytime
                 # the value of x_size changes
)
@triton.jit
def kernel(x_ptr, x_size, BLOCK_SIZE: tl.constexpr):
    ...
Note
:
When all the configurations are evaluated, the kernel will run multiple times. This means that whatever value the kernel updates will be updated multiple times. To avoid this undesired behavior, you can use the reset_to_zero argument, which resets the value of the provided tensor to zero before running any configuration.

If the environment variable TRITON_PRINT_AUTOTUNING is set to "1", Triton will print a message to stdout after autotuning each kernel, including the time spent autotuning and the best configuration.

Parameters
:
configs (list[triton.Config]) – a list of triton.Config objects

key (list[str]) – a list of argument names whose change in value will trigger the evaluation of all provided configs.

prune_configs_by –

a dict of functions that are used to prune configs, fields: ‘perf_model’: performance model used to predicate running time with different configs, returns running time ‘top_k’: number of configs to bench ‘early_config_prune’: a function used to prune configs. It should have the signature

prune_configs_by( configs: List[triton.Config], named_args: Dict[str, Any], **kwargs: Dict[str, Any]) -> List[triton.Config]: and return pruned configs. It should return at least one config.

reset_to_zero (list[str]) – a list of argument names whose value will be reset to zero before evaluating any configs.

restore_value (list[str]) – a list of argument names whose value will be restored after evaluating any configs.

pre_hook (lambda args, reset_only) – a function that will be called before the kernel is called. This overrides the default pre_hook used for ‘reset_to_zero’ and ‘restore_value’. ‘kwargs’: a dict of all arguments passed to the kernel. ‘reset_only’: a boolean indicating whether the pre_hook is called to reset the values only, without a corresponding post_hook.

post_hook (lambda args, exception) – a function that will be called after the kernel is called. This overrides the default post_hook used for ‘restore_value’. ‘kwargs’: a dict of all arguments passed to the kernel. ‘exception’: the exception raised by the kernel in case of a compilation or runtime error.

warmup (int) – warmup time (in ms) to pass to benchmarking (deprecated).

rep (int) – repetition time (in ms) to pass to benchmarking (deprecated).

do_bench (lambda fn, quantiles) – a benchmark function to measure the time of each run.

cache_results – whether to cache autotune timings to disk. Defaults to False.

“type cache_results: bool

---

triton.heuristics
triton.heuristics(values)
Decorator for specifying how the values of certain meta-parameters may be computed. This is useful for cases where auto-tuning is prohibitively expensive, or just not applicable.

# smallest power-of-two >= x_size
@triton.heuristics(values={'BLOCK_SIZE': lambda args: triton.next_power_of_2(args['x_size'])})
@triton.jit
def kernel(x_ptr, x_size, BLOCK_SIZE: tl.constexpr):
    ...
Parameters
:
values (dict[str, Callable[[dict[str, Any]], Any]]) – a dictionary of meta-parameter names and functions that compute the value of the meta-parameter. each such function takes a list of positional arguments as input.

---

triton.Config
classtriton.Config(self, kwargs, num_warps=4, num_stages=3, num_ctas=1, maxnreg=None, pre_hook=None, ir_override=None)
An object that represents a possible kernel configuration for the auto-tuner to try.

Variables
:
kwargs – a dictionary of meta-parameters to pass to the kernel as keyword arguments.

num_warps – the number of warps to use for the kernel when compiled for GPUs. For example, if num_warps=8, then each kernel instance will be automatically parallelized to cooperatively execute using 8 * 32 = 256 threads.

num_stages – the number of stages that the compiler should use when software-pipelining loops. Mostly useful for matrix multiplication workloads on SM80+ GPUs.

num_ctas – number of blocks in a block cluster. SM90+ only.

maxnreg – maximum number of registers one thread can use. Corresponds to ptx .maxnreg directive. Not supported on all platforms.

pre_hook – a function that will be called before the kernel is called. Parameters of this function are args.

ir_override – filename of a user-defined IR (*.{ttgir|llir|ptx|amdgcn}).

__init__(self, kwargs, num_warps=4, num_stages=3, num_ctas=1, maxnreg=None, pre_hook=None, ir_override=None)
Methods

__init__(self, kwargs[, num_warps, ...])

all_kwargs(self)

---

triton.language
Programming Model
tensor

Represents an N-dimensional array of values or pointers.

tensor_descriptor

A descriptor representing a tensor in global memory.

program_id

Returns the id of the current program instance along the given axis.

num_programs

Returns the number of program instances launched along the given axis.

Creation Ops
arange

Returns contiguous values within the half-open interval [start, end).

cat

Concatenate the given blocks

full

Returns a tensor filled with the scalar value for the given shape and dtype.

zeros

Returns a tensor filled with the scalar value 0 for the given shape and dtype.

zeros_like

Returns a tensor of zeros with the same shape and type as a given tensor.

cast

Casts a tensor to the given dtype.

Shape Manipulation Ops
broadcast

Tries to broadcast the two given blocks to a common compatible shape.

broadcast_to

Tries to broadcast the given tensor to a new shape.

expand_dims

Expand the shape of a tensor, by inserting new length-1 dimensions.

interleave

Interleaves the values of two tensors along their last dimension.

join

Join the given tensors in a new, minor dimension.

permute

Permutes the dimensions of a tensor.

ravel

Returns a contiguous flattened view of x.

reshape

Returns a tensor with the same number of elements as input but with the provided shape.

split

Split a tensor in two along its last dim, which must have size 2.

trans

Permutes the dimensions of a tensor.

view

Returns a tensor with the same elements as input but a different shape.

Linear Algebra Ops
dot

Returns the matrix product of two blocks.

dot_scaled

Returns the matrix product of two blocks in microscaling format.

Memory/Pointer Ops
load

Return a tensor of data whose values are loaded from memory at location defined by pointer:

store

Store a tensor of data into memory locations defined by pointer.

make_tensor_descriptor

Make a tensor descriptor object

load_tensor_descriptor

Load a block of data from a tensor descriptor.

store_tensor_descriptor

Store a block of data to a tensor descriptor.

make_block_ptr

Returns a pointer to a block in a parent tensor

advance

Advance a block pointer

Indexing Ops
flip

Flips a tensor x along the dimension dim.

where

Returns a tensor of elements from either x or y, depending on condition.

swizzle2d

Transforms the indices of a row-major size_i * size_j matrix into the indices of a column-major matrix for each group of size_g rows.

Math Ops
abs

Computes the element-wise absolute value of x.

cdiv

Computes the ceiling division of x by div

ceil

Computes the element-wise ceil of x.

clamp

Clamps the input tensor x within the range [min, max].

cos

Computes the element-wise cosine of x.

div_rn

Computes the element-wise precise division (rounding to nearest wrt the IEEE standard) of x and y.

erf

Computes the element-wise error function of x.

exp

Computes the element-wise exponential of x.

exp2

Computes the element-wise exponential (base 2) of x.

fdiv

Computes the element-wise fast division of x and y.

floor

Computes the element-wise floor of x.

fma

Computes the element-wise fused multiply-add of x, y, and z.

log

Computes the element-wise natural logarithm of x.

log2

Computes the element-wise logarithm (base 2) of x.

maximum

Computes the element-wise maximum of x and y.

minimum

Computes the element-wise minimum of x and y.

rsqrt

Computes the element-wise inverse square root of x.

sigmoid

Computes the element-wise sigmoid of x.

sin

Computes the element-wise sine of x.

softmax

Computes the element-wise softmax of x.

sqrt

Computes the element-wise fast square root of x.

sqrt_rn

Computes the element-wise precise square root (rounding to nearest wrt the IEEE standard) of x.

umulhi

Computes the element-wise most significant N bits of the 2N-bit product of x and y.

Reduction Ops
argmax

Returns the maximum index of all elements in the input tensor along the provided axis

argmin

Returns the minimum index of all elements in the input tensor along the provided axis

max

Returns the maximum of all elements in the input tensor along the provided axis

min

Returns the minimum of all elements in the input tensor along the provided axis

reduce

Applies the combine_fn to all elements in input tensors along the provided axis

sum

Returns the sum of all elements in the input tensor along the provided axis

xor_sum

Returns the xor sum of all elements in the input tensor along the provided axis

Scan/Sort Ops
associative_scan

Applies the combine_fn to each elements with a carry in input tensors along the provided axis and update the carry

cumprod

Returns the cumprod of all elements in the input tensor along the provided axis

cumsum

Returns the cumsum of all elements in the input tensor along the provided axis

histogram

computes an histogram based on input tensor with num_bins bins, the bins have a width of 1 and start at 0.

sort

topk

Returns the k largest (or smallest) elements of the input tensor along the specified dimension.

gather

Gather from a tensor along a given dimension.

Atomic Ops
atomic_add

Performs an atomic add at the memory location specified by pointer.

atomic_and

Performs an atomic logical and at the memory location specified by pointer.

atomic_cas

Performs an atomic compare-and-swap at the memory location specified by pointer.

atomic_max

Performs an atomic max at the memory location specified by pointer.

atomic_min

Performs an atomic min at the memory location specified by pointer.

atomic_or

Performs an atomic logical or at the memory location specified by pointer.

atomic_xchg

Performs an atomic exchange at the memory location specified by pointer.

atomic_xor

Performs an atomic logical xor at the memory location specified by pointer.

Random Number Generation
randint4x

Given a seed scalar and an offset block, returns four blocks of random int32.

randint

Given a seed scalar and an offset block, returns a single block of random int32.

rand

Given a seed scalar and an offset block, returns a block of random float32 in 𝑈⁡(0,1).

randn

Given a seed scalar and an offset block, returns a block of random float32 in N⁡(0,1).

Iterators
range

Iterator that counts upward forever.

static_range

Iterator that counts upward forever.

Inline Assembly
inline_asm_elementwise

Execute inline assembly over a tensor.

Compiler Hint Ops
assume

Allow compiler to assume the cond is True.

debug_barrier

Insert a barrier to synchronize all threads in a block.

max_constancy

Let the compiler know that the value first values in input are constant.

max_contiguous

Let the compiler know that the value first values in input are contiguous.

multiple_of

Let the compiler know that the values in input are all multiples of value.

Debug Ops
static_print

Print the values at compile time.

static_assert

Assert the condition at compile time.

device_print

Print the values at runtime from the device.

device_assert

Assert the condition at runtime from the device.

---
triton.language.tensor
classtriton.language.tensor(self, handle, type: dtype)
Represents an N-dimensional array of values or pointers.

tensor is the fundamental data structure in Triton programs. Most functions in triton.language operate on and return tensors.

Most of the named member functions here are duplicates of the free functions in triton.language. For example, triton.language.sqrt(x) is equivalent to x.sqrt().

tensor also defines most of the magic/dunder methods, so you can write x+y, x << 2, etc.

Constructors

__init__(self, handle, type: dtype)
Not called by user code.

Methods

__init__(self, handle, type)

Not called by user code.

abs(self[, _semantic])

Forwards to abs() free function

advance(self, offsets[, _semantic])

Forwards to advance() free function

argmax(input, axis[, tie_break_left, keep_dims])

Returns the maximum index of all elements in the input tensor along the provided axis

argmin(input, axis[, tie_break_left, keep_dims])

Returns the minimum index of all elements in the input tensor along the provided axis

associative_scan(self, axis, combine_fn[, ...])

Forwards to associative_scan() free function

atomic_add(self, val[, mask, sem, scope, ...])

Forwards to atomic_add() free function

atomic_and(self, val[, mask, sem, scope, ...])

Forwards to atomic_and() free function

atomic_cas(self, cmp, val[, sem, scope, ...])

Forwards to atomic_cas() free function

atomic_max(self, val[, mask, sem, scope, ...])

Forwards to atomic_max() free function

atomic_min(self, val[, mask, sem, scope, ...])

Forwards to atomic_min() free function

atomic_or(self, val[, mask, sem, scope, ...])

Forwards to atomic_or() free function

atomic_xchg(self, val[, mask, sem, scope, ...])

Forwards to atomic_xchg() free function

atomic_xor(self, val[, mask, sem, scope, ...])

Forwards to atomic_xor() free function

broadcast_to(self, *shape[, _semantic])

Forwards to broadcast_to() free function

cast(self, dtype[, fp_downcast_rounding, ...])

Forwards to cast() free function

cdiv(x, div)

Computes the ceiling division of x by div

ceil(self[, _semantic])

Forwards to ceil() free function

cos(self[, _semantic])

Forwards to cos() free function

cumprod(input[, axis, reverse])

Returns the cumprod of all elements in the input tensor along the provided axis

cumsum(input[, axis, reverse, dtype])

Returns the cumsum of all elements in the input tensor along the provided axis

erf(self[, _semantic])

Forwards to erf() free function

exp(self[, _semantic])

Forwards to exp() free function

exp2(self[, _semantic])

Forwards to exp2() free function

expand_dims(self, axis[, _semantic])

Forwards to expand_dims() free function

flip(x[, dim])

Flips a tensor x along the dimension dim.

floor(self[, _semantic])

Forwards to floor() free function

gather(self, index, axis[, _semantic])

Forwards to gather() free function

histogram(self, num_bins[, mask, _semantic, ...])

Forwards to histogram() free function

item(self[, _semantic, _generator])

Forwards to item() free function

log(self[, _semantic])

Forwards to log() free function

log2(self[, _semantic])

Forwards to log2() free function

logical_and(self, other[, _semantic])

logical_or(self, other[, _semantic])

max(input[, axis, return_indices, ...])

Returns the maximum of all elements in the input tensor along the provided axis

min(input[, axis, return_indices, ...])

Returns the minimum of all elements in the input tensor along the provided axis

permute(self, *dims[, _semantic])

Forwards to permute() free function

ravel(x[, can_reorder])

Returns a contiguous flattened view of x.

reduce(self, axis, combine_fn[, keep_dims, ...])

Forwards to reduce() free function

reduce_or(input, axis[, keep_dims])

Returns the reduce_or of all elements in the input tensor along the provided axis

reshape(self, *shape[, can_reorder, ...])

Forwards to reshape() free function

rsqrt(self[, _semantic])

Forwards to rsqrt() free function

sigmoid(x)

Computes the element-wise sigmoid of x.

sin(self[, _semantic])

Forwards to sin() free function

softmax(x[, dim, keep_dims, ieee_rounding])

Computes the element-wise softmax of x.

sort(self[, dim, descending])

split(self[, _semantic, _generator])

Forwards to split() free function

sqrt(self[, _semantic])

Forwards to sqrt() free function

sqrt_rn(self[, _semantic])

Forwards to sqrt_rn() free function

store(self, value[, mask, boundary_check, ...])

Forwards to store() free function

sum(input[, axis, keep_dims, dtype])

Returns the sum of all elements in the input tensor along the provided axis

to(self, dtype[, fp_downcast_rounding, ...])

Alias for tensor.cast().

trans(self, *dims[, _semantic])

Forwards to trans() free function

view(self, *shape[, _semantic])

Forwards to view() free function

xor_sum(input[, axis, keep_dims])

Returns the xor sum of all elements in the input tensor along the provided axis

Attributes

T

Transposes a 2D tensor.

type

---

triton.language.tensor_descriptor
classtriton.language.tensor_descriptor(self, handle, shape: List[tensor], strides: List[tensor], block_type: block_type)
A descriptor representing a tensor in global memory.

__init__(self, handle, shape: List[tensor], strides: List[tensor], block_type: block_type)
Not called by user code.

Methods

__init__(self, handle, shape, strides, ...)

Not called by user code.

atomic_add(self, offsets, value[, _semantic])

atomic_and(self, offsets, value[, _semantic])

atomic_max(self, offsets, value[, _semantic])

atomic_min(self, offsets, value[, _semantic])

atomic_or(self, offsets, value[, _semantic])

atomic_xor(self, offsets, value[, _semantic])

gather(self, *args[, _semantic])

Gather multiple descriptors worth of data

load(self, offsets[, _semantic])

Load a block from the descriptor starting at the given element offsets.

scatter(self, value, *args[, _semantic])

Scatter multiple descriptors worth of data

store(self, offsets, value[, _semantic])

Store a block from the descriptor starting at the given element offsets.

Attributes

block_shape

block_type

dtype

type

---

triton.language.program_id
triton.language.program_id(axis, _semantic=None)
Returns the id of the current program instance along the given axis.

Parameters
:
axis (int) – The axis of the 3D launch grid. Must be 0, 1 or 2.

---

Triton.language.num_programs
triton.language.num_programs(axis, _semantic=None)
Returns the number of program instances launched along the given axis.

Parameters
:
axis (int) – The axis of the 3D launch grid. Must be 0, 1 or 2.

---

triton.language.arange
triton.language.arange(start, end, _semantic=None)
Returns contiguous values within the half-open interval [start, end). end - start must be less than or equal to TRITON_MAX_TENSOR_NUMEL = 1048576

Parameters
:
start (int32) – Start of the interval. Must be a power of two.

end (int32) – End of the interval. Must be a power of two greater than start.

---

triton.language.cat
triton.language.cat(input, other, can_reorder=False, dim=0, _semantic=None)
Concatenate the given blocks

Parameters
:
input (Tensor) – The first input tensor.

other (Tensor) – The second input tensor.

can_reorder (bool) – Compiler hint. If true, the compiler is allowed to reorder elements while concatenating inputs. Only use if the order does not matter (e.g., result is only used in reduction ops).

dim (int) – The dimension to concatenate along (used when can_reorder is False).

---

triton.language.full
triton.language.full(shape, value, dtype, _semantic=None)
Returns a tensor filled with the scalar value for the given shape and dtype.

Parameters
:
shape (tuple of ints) – Shape of the new array, e.g., (8, 16) or (8, )

value (scalar) – A scalar value to fill the array with

dtype (tl.dtype) – Data type of the new array, e.g., tl.float16

---

triton.language.zeros
triton.language.zeros(shape, dtype)
Returns a tensor filled with the scalar value 0 for the given shape and dtype.

Parameters
:
shape (tuple of ints) – Shape of the new array, e.g., (8, 16) or (8, )

dtype (DType) – Data-type of the new array, e.g., tl.float16

---

triton.language.zeros_like
triton.language.zeros_like(input)
Returns a tensor of zeros with the same shape and type as a given tensor.

Parameters
:
input (Tensor) – input tensor

---

triton.language.cast
triton.language.cast(input, dtype: dtype, fp_downcast_rounding: str | None = None, bitcast: bool = False, _semantic=None)
Casts a tensor to the given dtype.

Parameters
:
dtype (tl.dtype) – The target data type.

fp_downcast_rounding (str, optional) – The rounding mode for downcasting floating-point values. This parameter is only used when self is a floating-point tensor and dtype is a floating-point type with a smaller bitwidth. Supported values are "rtne" (round to nearest, ties to even) and "rtz" (round towards zero).

bitcast (bool, optional) – If true, the tensor is bitcasted to the given dtype, instead of being numerically casted.

This function can also be called as a member function on tensor, as x.cast(...) instead of cast(x, ...).

---

riton.language.broadcast
triton.language.broadcast(input, other, _semantic=None)
Tries to broadcast the two given blocks to a common compatible shape.

Parameters
:
input (Block) – The first input tensor.

other (Block) – The second input tensor.

---

triton.language.broadcast_to
triton.language.broadcast_to(input, *shape, _semantic=None)
Tries to broadcast the given tensor to a new shape.

Parameters
:
input (Block) – The input tensor.

shape – The desired shape.

shape can be passed as a tuple or as individual parameters:

# These are equivalent
broadcast_to(x, (32, 32))
broadcast_to(x, 32, 32)
This function can also be called as a member function on tensor, as x.broadcast_to(...) instead of broadcast_to(x, ...).

---

triton.language.expand_dims
triton.language.expand_dims(input, axis, _semantic=None)
Expand the shape of a tensor, by inserting new length-1 dimensions.

Axis indices are with respect to the resulting tensor, so result.shape[axis] will be 1 for each axis.

Parameters
:
input (tl.tensor) – The input tensor.

axis (int | Sequence[int]) – The indices to add new axes

This function can also be called as a member function on tensor, as x.expand_dims(...) instead of expand_dims(x, ...).

---

triton.language.interleave
triton.language.interleave(a, b)
Interleaves the values of two tensors along their last dimension. The two tensors must have the same shape. Equivalent to tl.join(a, b).reshape(a.shape[:-1] + [2 * a.shape[-1]])

Parameters
:
a (Tensor) – The first input tensor.

b (Tensor) – The second input tensor.

---

triton.language.join
triton.language.join(a, b, _semantic=None)
Join the given tensors in a new, minor dimension.

For example, given two tensors of shape (4,8), produces a new tensor of shape (4,8,2). Given two scalars, returns a tensor of shape (2).

The two inputs are broadcasted to be the same shape.

If you want to join more than two elements, you can use multiple calls to this function. This reflects the constraint in Triton that tensors must have power-of-two sizes.

join is the inverse of split.

Parameters
:
a (Tensor) – The first input tensor.

b (Tensor) – The second input tensor.

---

triton.language.permute
triton.language.permute(input, *dims, _semantic=None)
Permutes the dimensions of a tensor.

Parameters
:
input (Block) – The input tensor.

dims – The desired ordering of dimensions. For example, (2, 1, 0) reverses the order dims in a 3D tensor.

dims can be passed as a tuple or as individual parameters:

# These are equivalent
permute(x, (2, 1, 0))
permute(x, 2, 1, 0)
trans() is equivalent to this function, except when dims is empty, it tries to swap the last two axes.

This function can also be called as a member function on tensor, as x.permute(...) instead of permute(x, ...).

---

riton.language.ravel
triton.language.ravel(x, can_reorder=False)
Returns a contiguous flattened view of x.

Parameters
:
x (Block) – the input tensor

This function can also be called as a member function on tensor, as x.ravel(...) instead of ravel(x, ...).

---

triton.language.reshape
triton.language.reshape(input, *shape, can_reorder=False, _semantic=None, _generator=None)
Returns a tensor with the same number of elements as input but with the provided shape.

Parameters
:
input (Block) – The input tensor.

shape – The new shape.

shape can be passed as a tuple or as individual parameters:

# These are equivalent
reshape(x, (32, 32))
reshape(x, 32, 32)
This function can also be called as a member function on tensor, as x.reshape(...) instead of reshape(x, ...).

---

triton.language.split
triton.language.split(a, _semantic=None, _generator=None)→ tuple[tensor, tensor]
Split a tensor in two along its last dim, which must have size 2.

For example, given a tensor of shape (4,8,2), produces two tensors of shape (4,8). Given a tensor of shape (2), returns two scalars.

If you want to split into more than two pieces, you can use multiple calls to this function (probably plus calling reshape). This reflects the constraint in Triton that tensors must have power-of-two sizes.

split is the inverse of join.

Parameters
:
a (Tensor) – The tensor to split.

This function can also be called as a member function on tensor, as x.split() instead of split(x).

---

triton.language.trans
triton.language.trans(input: tensor, *dims, _semantic=None)
Permutes the dimensions of a tensor.

If the parameter dims is not specified, the function defaults to swapping the last two axes, thereby performing an (optionally batched) 2D transpose.

Parameters
:
input – The input tensor.

dims – The desired ordering of dimensions. For example, (2, 1, 0) reverses the order dims in a 3D tensor.

dims can be passed as a tuple or as individual parameters:

# These are equivalent
trans(x, (2, 1, 0))
trans(x, 2, 1, 0)
permute() is equivalent to this function, except it doesn’t have the special case when no permutation is specified.

This function can also be called as a member function on tensor, as x.trans(...) instead of trans(x, ...).

---

triton.language.view
triton.language.view(input, *shape, _semantic=None)
Returns a tensor with the same elements as input but a different shape. The order of the elements may not be preserved.

Parameters
:
input (Block) – The input tensor.

shape – The desired shape.

shape can be passed as a tuple or as individual parameters:

# These are equivalent
view(x, (32, 32))
view(x, 32, 32)
This function can also be called as a member function on tensor, as x.view(...) instead of view(x, ...).

---

triton.language.dot
triton.language.dot(input, other, acc=None, input_precision=None, allow_tf32=None, max_num_imprecise_acc=None, out_dtype=triton.language.float32, _semantic=None)
Returns the matrix product of two blocks.

The two blocks must both be two-dimensional or three-dimensional and have compatible inner dimensions. For three-dimensional blocks, tl.dot performs the batched matrix product, where the first dimension of each block represents the batch dimension.

Warning

When using TF32 precision, the float32 inputs may be truncated to TF32 format (19-bit floating point) without rounding which may bias the result. For best results, you must round to TF32 explicitly, or load the data using TensorDescriptor with round_f32_to_tf32=True.

Parameters
:
input (2D or 3D tensor of scalar-type in {int8, float8_e5m2, float16, bfloat16, float32}) – The first tensor to be multiplied.

other (2D or 3D tensor of scalar-type in {int8, float8_e5m2, float16, bfloat16, float32}) – The second tensor to be multiplied.

acc (2D or 3D tensor of scalar-type in {float16, float32, int32}) – The accumulator tensor. If not None, the result is added to this tensor.

input_precision (string. Available options for nvidia: "tf32", "tf32x3", "ieee". Default: "tf32". Available options for amd: "ieee", (CDNA3 only) "tf32".) – How to exercise the Tensor Cores for f32 x f32. If the device does not have Tensor Cores or the inputs are not of dtype f32, this option is ignored. For devices that do have tensor cores, the default precision is tf32.

allow_tf32 – Deprecated. If true, input_precision is set to “tf32”. Only one of input_precision and allow_tf32 can be specified (i.e. at least one must be None).

---

triton.language.dot_scaled
triton.language.dot_scaled(lhs, lhs_scale, lhs_format, rhs, rhs_scale, rhs_format, acc=None, fast_math=False, lhs_k_pack=True, rhs_k_pack=True, out_dtype=triton.language.float32, _semantic=None)
Returns the matrix product of two blocks in microscaling format.

lhs and rhs use microscaling formats described here: https://www.opencompute.org/documents/ocp-microscaling-formats-mx-v1-0-spec-final-pdf

Software emulation enables targeting hardware architectures without native microscaling operation support. Right now for such case, microscaled lhs/rhs are upcasted to bf16 element type beforehand for dot computation, with one exception: for AMD CDNA3 specifically, if one of the inputs is of fp16 element type, the other input is also upcasted to fp16 element type instead. This behavior is experimental and may be subject to change in the future.

Parameters
:
lhs (2D tensor representing fp4, fp8 or bf16 elements. Fp4 elements are packed into uint8 inputs with the first element in lower bits. Fp8 are stored as uint8 or the corresponding fp8 type.) – The first tensor to be multiplied.

lhs_scale (e8m0 type represented as an uint8 tensor, or None.) – Scale factor for lhs tensor. Shape should be [M, K//group_size] when lhs is [M, K], where group_size is 32 if scales type are e8m0.

lhs_format (str) – format of the lhs tensor. Available formats: {e2m1, e4m3, e5m2, bf16, fp16}.

rhs (2D tensor representing fp4, fp8 or bf16 elements. Fp4 elements are packed into uint8 inputs with the first element in lower bits. Fp8 are stored as uint8 or the corresponding fp8 type.) – The second tensor to be multiplied.

rhs_scale (e8m0 type represented as an uint8 tensor, or None.) – Scale factor for rhs tensor. Shape should be [N, K//group_size] where rhs is [K, N]. Important: Do NOT transpose rhs_scale

rhs_format (str) – format of the rhs tensor. Available formats: {e2m1, e4m3, e5m2, bf16, fp16}.

acc – The accumulator tensor. If not None, the result is added to this tensor.

lhs_k_pack (bool, optional) – If false, the lhs tensor is packed into uint8 along M dimension.

rhs_k_pack (bool, optional) – If false, the rhs tensor is packed into uint8 along N dimension.

---

triton.language.load
triton.language.load(pointer, mask=None, other=None, boundary_check=(), padding_option='', cache_modifier='', eviction_policy='', volatile=False, _semantic=None)
Return a tensor of data whose values are loaded from memory at location defined by pointer:

If pointer is a single element pointer, a scalar is be loaded. In this case:

mask and other must also be scalars,

other is implicitly typecast to pointer.dtype.element_ty, and

boundary_check and padding_option must be empty.

If pointer is an N-dimensional tensor of pointers, an N-dimensional tensor is loaded. In this case:

mask and other are implicitly broadcast to pointer.shape,

other is implicitly typecast to pointer.dtype.element_ty, and

boundary_check and padding_option must be empty.

If pointer is a block pointer defined by make_block_ptr, a tensor is loaded. In this case:

mask and other must be None, and

boundary_check and padding_option can be specified to control the behavior of out-of-bound access.

Parameters
:
pointer (triton.PointerType, or block of dtype=triton.PointerType) – Pointer to the data to be loaded

mask (Block of triton.int1, optional) – if mask[idx] is false, do not load the data at address pointer[idx] (must be None with block pointers)

other (Block, optional) – if mask[idx] is false, return other[idx]. If other is None, the masked-out value is undefined.

boundary_check (tuple of ints, optional) – tuple of integers, indicating the dimensions which should do the boundary check

padding_option – should be one of {“”, “zero”, “nan”}, the padding value to use while out of bounds. “” means an undefined value.

cache_modifier (str, optional, should be one of {“”, “.ca”, “.cg”, “.cv”}, where “.ca” stands for cache at all levels, “.cg” stands for cache at global level (cache in L2 and below, not L1), and “.cv” means don’t cache and fetch again. see cache operator for more details.) – changes cache option in NVIDIA PTX

eviction_policy (str, optional) – changes eviction policy in NVIDIA PTX

volatile (bool, optional) – changes volatile option in NVIDIA PTX

---

triton.language.store
triton.language.store(pointer, value, mask=None, boundary_check=(), cache_modifier='', eviction_policy='', _semantic=None)
Store a tensor of data into memory locations defined by pointer.

If pointer is a single element pointer, a scalar is stored. In this case:

mask must also be scalar, and

boundary_check and padding_option must be empty.

If pointer is an N-dimensional tensor of pointers, an N-dimensional block is stored. In this case:

mask is implicitly broadcast to pointer.shape, and

boundary_check must be empty.

If pointer is a block pointer defined by make_block_ptr, a block of data is stored. In this case:

mask must be None, and

boundary_check can be specified to control the behavior of out-of-bound access.

value is implicitly broadcast to pointer.shape and typecast to pointer.dtype.element_ty.

Parameters
:
pointer (triton.PointerType, or block of dtype=triton.PointerType) – The memory location where the elements of value are stored

value (Block) – The tensor of elements to be stored

mask (Block of triton.int1, optional) – If mask[idx] is false, do not store value[idx] at pointer[idx]

boundary_check (tuple of ints, optional) – tuple of integers, indicating the dimensions which should do the boundary check

cache_modifier (str, optional, should be one of {“”, “.wb”, “.cg”, “.cs”, “.wt”}, where “.wb” stands for cache write-back all coherent levels, “.cg” stands for cache global, “.cs” stands for cache streaming, “.wt” stands for cache write-through, see cache operator for more details.) – changes cache option in NVIDIA PTX

eviction_policy (str, optional, should be one of {"", "evict_first", "evict_last"}) – changes eviction policy in NVIDIA PTX

This function can also be called as a member function on tensor, as x.store(...) instead of store(x, ...).

---

triton.language.make_tensor_descriptor
triton.language.make_tensor_descriptor(base: tensor, shape: List[tensor], strides: List[tensor], block_shape: List[constexpr], padding_option='zero', _semantic=None)→ tensor_descriptor
Make a tensor descriptor object

Parameters
:
base – the base pointer of the tensor, must be 16-byte aligned

shape – A list of non-negative integers representing the tensor shape

strides – A list of tensor strides. Leading dimensions must be multiples of 16-byte strides and the last dimension must be contiguous.

block_shape – The shape of block to be loaded/stored from global memory

Notes
On NVIDIA GPUs with TMA support, this will result in a TMA descriptor object and loads and stores from the descriptor will be backed by the TMA hardware.

Currently only 2-5 dimensional tensors are supported.

Example
@triton.jit
def inplace_abs(in_out_ptr, M, N, M_BLOCK: tl.constexpr, N_BLOCK: tl.constexpr):
    desc = tl.make_tensor_descriptor(
        in_out_ptr,
        shape=[M, N],
        strides=[N, 1],
        block_shape=[M_BLOCK, N_BLOCK],
    )

    moffset = tl.program_id(0) * M_BLOCK
    noffset = tl.program_id(1) * N_BLOCK

    value = desc.load([moffset, noffset])
    desc.store([moffset, noffset], tl.abs(value))

# TMA descriptors require a global memory allocation
def alloc_fn(size: int, alignment: int, stream: Optional[int]):
    return torch.empty(size, device="cuda", dtype=torch.int8)

triton.set_allocator(alloc_fn)

M, N = 256, 256
x = torch.randn(M, N, device="cuda")
M_BLOCK, N_BLOCK = 32, 32
grid = (M / M_BLOCK, N / N_BLOCK)
inplace_abs[grid](x, M, N, M_BLOCK, N_BLOCK)

---

triton.language.load_tensor_descriptor
triton.language.load_tensor_descriptor(desc: tensor_descriptor_base, offsets: Sequence[constexpr | tensor], _semantic=None)→ tensor
Load a block of data from a tensor descriptor.

---

triton.language.store_tensor_descriptor
triton.language.store_tensor_descriptor(desc: tensor_descriptor_base, offsets: Sequence[constexpr | tensor], value: tensor, _semantic=None)→ tensor
Store a block of data to a tensor descriptor.

---

triton.language.make_block_ptr
triton.language.make_block_ptr(base: tensor, shape, strides, offsets, block_shape, order, _semantic=None)
Returns a pointer to a block in a parent tensor

Parameters
:
base – The base pointer to the parent tensor

shape – The shape of the parent tensor

strides – The strides of the parent tensor

offsets – The offsets to the block

block_shape – The shape of the block

order – The order of the original data format

---

triton.language.advance
triton.language.advance(base, offsets, _semantic=None)
Advance a block pointer

Parameters
:
base – the block pointer to advance

offsets – the offsets to advance, a tuple by dimension

This function can also be called as a member function on tensor, as x.advance(...) instead of advance(x, ...).

---

triton.language.flip
triton.language.flip(x, dim=None)
Flips a tensor x along the dimension dim.

Parameters
:
x (Block) – the first input tensor

dim (int) – the dimension to flip along

This function can also be called as a member function on tensor, as x.flip(...) instead of flip(x, ...).

---

triton.language.where
triton.language.where(condition, x, y, _semantic=None)
Returns a tensor of elements from either x or y, depending on condition.

Note that x and y are always evaluated regardless of the value of condition.

If you want to avoid unintended memory operations, use the mask arguments in triton.load and triton.store instead.

The shape of x and y are both broadcast to the shape of condition. x and y must have the same data type.

Parameters
:
condition (Block of triton.bool) – When True (nonzero), yield x, otherwise yield y.

x – values selected at indices where condition is True.

y – values selected at indices where condition is False.

---

triton.language.swizzle2d
triton.language.swizzle2d(i, j, size_i, size_j, size_g)
Transforms the indices of a row-major size_i * size_j matrix into the indices of a column-major matrix for each group of size_g rows.

For example, for size_i = size_j = 4 and size_g = 2, it will transform

[[0 , 1 , 2 , 3 ],
 [4 , 5 , 6 , 7 ],
 [8 , 9 , 10, 11],
 [12, 13, 14, 15]]
into

[[0, 2,  4 , 6 ],
 [1, 3,  5 , 7 ],
 [8, 10, 12, 14],
 [9, 11, 13, 15]]

---

triton.language.abs
triton.language.abs(x, _semantic=None)
Computes the element-wise absolute value of x.

Parameters
:
x (Block) – the input values

This function can also be called as a member function on tensor, as x.abs() instead of abs(x).

---

triton.language.cdiv
triton.language.cdiv(x, div)
Computes the ceiling division of x by div

Parameters
:
x (Block) – the input number

div (Block) – the divisor

This function can also be called as a member function on tensor, as x.cdiv(...) instead of cdiv(x, ...).

---

triton.language.ceil
triton.language.ceil(x, _semantic=None)
Computes the element-wise ceil of x.

Parameters
:
x (Block) – the input values

---

triton.language.clamp
triton.language.clamp(x, min, max, propagate_nan: constexpr = <PROPAGATE_NAN.NONE: 0>, _semantic=None)
Clamps the input tensor x within the range [min, max]. Behavior when min > max is undefined.

Parameters
:
x (Block) – the input tensor

min (Block) – the lower bound for clamping

max (Block) – the upper bound for clamping

propagate_nan (tl.PropagateNan) – whether to propagate NaN values. Applies only to the x tensor. If either min or max is NaN, the result is undefined.

See also

tl.PropagateNan

---

triton.language.cos
triton.language.cos(x, _semantic=None)
Computes the element-wise cosine of x.

Parameters
:
x (Block) – the input values

---

triton.language.div_rn
triton.language.div_rn(x, y, _semantic=None)
Computes the element-wise precise division (rounding to nearest wrt the IEEE standard) of x and y.

Parameters
:
x (Block) – the input values

y (Block) – the input values

---

triton.language.erf
triton.language.erf(x, _semantic=None)
Computes the element-wise error function of x.

Parameters
:
x (Block) – the input values

---

triton.language.exp
triton.language.exp(x, _semantic=None)
Computes the element-wise exponential of x.

Parameters
:
x (Block) – the input values

---

triton.language.exp2
triton.language.exp2(x, _semantic=None)
Computes the element-wise exponential (base 2) of x.

Parameters
:
x (Block) – the input values

---

triton.language.fdiv
triton.language.fdiv(x, y, ieee_rounding=False, _semantic=None)
Computes the element-wise fast division of x and y.

Parameters
:
x (Block) – the input values

y (Block) – the input values

---

triton.language.floor
triton.language.floor(x, _semantic=None)
Computes the element-wise floor of x.

Parameters
:
x (Block) – the input values

---

triton.language.fma
triton.language.fma(x, y, z, _semantic=None)
Computes the element-wise fused multiply-add of x, y, and z.

Parameters
:
x (Block) – the input values

y (Block) – the input values

z (Block) – the input values

---

triton.language.log
triton.language.log(x, _semantic=None)
Computes the element-wise natural logarithm of x.

Parameters
:
x (Block) – the input values

---

triton.language.log2
triton.language.log2(x, _semantic=None)
Computes the element-wise logarithm (base 2) of x.

Parameters
:
x (Block) – the input values

---

triton.language.maximum
triton.language.maximum(x, y, propagate_nan: constexpr = <PROPAGATE_NAN.NONE: 0>, _semantic=None)
Computes the element-wise maximum of x and y.

Parameters
:
x (Block) – the first input tensor

y (Block) – the second input tensor

propagate_nan (tl.PropagateNan) – whether to propagate NaN values.

See also

tl.PropagateNan

---

triton.language.minimum
triton.language.minimum(x, y, propagate_nan: constexpr = <PROPAGATE_NAN.NONE: 0>, _semantic=None)
Computes the element-wise minimum of x and y.

Parameters
:
x (Block) – the first input tensor

y (Block) – the second input tensor

propagate_nan (tl.PropagateNan) – whether to propagate NaN values.

See also

tl.PropagateNan

---

triton.language.rsqrt
triton.language.rsqrt(x, _semantic=None)
Computes the element-wise inverse square root of x.

Parameters
:
x (Block) – the input values

---

riton.language.sigmoid
triton.language.sigmoid(x)
Computes the element-wise sigmoid of x.

Parameters
:
x (Block) – the input values

This function can also be called as a member function on tensor, as x.sigmoid(...) instead of sigmoid(x, ...).

---

triton.language.sin
triton.language.sin(x, _semantic=None)
Computes the element-wise sine of x.

Parameters
:
x (Block) – the input values

---

triton.language.softmax
triton.language.softmax(x, dim=None, keep_dims=False, ieee_rounding=False)
Computes the element-wise softmax of x.

Parameters
:
x (Block) – the input values

This function can also be called as a member function on tensor, as x.softmax(...) instead of softmax(x, ...).

---

triton.language.sqrt
triton.language.sqrt(x, _semantic=None)
Computes the element-wise fast square root of x.

Parameters
:
x (Block) – the input values

---

triton.language.sqrt_rn
triton.language.sqrt_rn(x, _semantic=None)
Computes the element-wise precise square root (rounding to nearest wrt the IEEE standard) of x.

Parameters
:
x (Block) – the input values

---

triton.language.umulhi
triton.language.umulhi(x, y, _semantic=None)
Computes the element-wise most significant N bits of the 2N-bit product of x and y.

Parameters
:
x (Block) – the input values

y (Block) – the input values

---

triton.language.argmax
triton.language.argmax(input, axis, tie_break_left=True, keep_dims=False)
Returns the maximum index of all elements in the input tensor along the provided axis

The reduction operation should be associative and commutative.

Parameters
:
input (Tensor) – the input values

axis (int) – the dimension along which the reduction should be done. If None, reduce all dimensions

keep_dims (bool) – if true, keep the reduced dimensions with length 1

tie_break_left (bool) – if true, in case of a tie (i.e., multiple elements have the same maximum index value), return the left-most index for values that aren’t NaN

This function can also be called as a member function on tensor, as x.argmax(...) instead of argmax(x, ...).

---

triton.language.argmin
triton.language.argmin(input, axis, tie_break_left=True, keep_dims=False)
Returns the minimum index of all elements in the input tensor along the provided axis

The reduction operation should be associative and commutative.

Parameters
:
input (Tensor) – the input values

axis (int) – the dimension along which the reduction should be done. If None, reduce all dimensions

keep_dims (bool) – if true, keep the reduced dimensions with length 1

tie_break_left (bool) – if true, in case of a tie (i.e., multiple elements have the same minimum index value), return the left-most index for values that aren’t NaN

This function can also be called as a member function on tensor, as x.argmin(...) instead of argmin(x, ...).

---

triton.language.max
triton.language.max(input, axis=None, return_indices=False, return_indices_tie_break_left=True, keep_dims=False)
Returns the maximum of all elements in the input tensor along the provided axis

The reduction operation should be associative and commutative.

Parameters
:
input (Tensor) – the input values

axis (int) – the dimension along which the reduction should be done. If None, reduce all dimensions

keep_dims (bool) – if true, keep the reduced dimensions with length 1

return_indices (bool) – if true, return index corresponding to the maximum value

return_indices_tie_break_left (bool) – if true, in case of a tie (i.e., multiple elements have the same maximum value), return the left-most index for values that aren’t NaN

This function can also be called as a member function on tensor, as x.max(...) instead of max(x, ...).

---

riton.language.min
triton.language.min(input, axis=None, return_indices=False, return_indices_tie_break_left=True, keep_dims=False)
Returns the minimum of all elements in the input tensor along the provided axis

The reduction operation should be associative and commutative.

Parameters
:
input (Tensor) – the input values

axis (int) – the dimension along which the reduction should be done. If None, reduce all dimensions

keep_dims (bool) – if true, keep the reduced dimensions with length 1

return_indices (bool) – if true, return index corresponding to the minimum value

return_indices_tie_break_left (bool) – if true, in case of a tie (i.e., multiple elements have the same minimum value), return the left-most index for values that aren’t NaN

This function can also be called as a member function on tensor, as x.min(...) instead of min(x, ...).

---

triton.language.reduce
triton.language.reduce(input, axis, combine_fn, keep_dims=False, _semantic=None, _generator=None)
Applies the combine_fn to all elements in input tensors along the provided axis

Parameters
:
input (Tensor) – the input tensor, or tuple of tensors

axis (int | None) – the dimension along which the reduction should be done. If None, reduce all dimensions

combine_fn (Callable) – a function to combine two groups of scalar tensors (must be marked with @triton.jit)

keep_dims (bool) – if true, keep the reduced dimensions with length 1

This function can also be called as a member function on tensor, as x.reduce(...) instead of reduce(x, ...).

---

riton.language.sum
triton.language.sum(input, axis=None, keep_dims=False, dtype: constexpr = None)
Returns the sum of all elements in the input tensor along the provided axis

The reduction operation should be associative and commutative.

Parameters
:
input (Tensor) – the input values

axis (int) – the dimension along which the reduction should be done. If None, reduce all dimensions

keep_dims (bool) – if true, keep the reduced dimensions with length 1

dtype (tl.dtype) – the desired data type of the returned tensor. If specified, the input tensor is casted to dtype before the operation is performed. This is useful for preventing data overflows. If not specified, integer and bool dtypes are upcasted to tl.int32 and float dtypes are upcasted to at least tl.float32.

This function can also be called as a member function on tensor, as x.sum(...) instead of sum(x, ...).

---

triton.language.xor_sum
triton.language.xor_sum(input, axis=None, keep_dims=False)
Returns the xor sum of all elements in the input tensor along the provided axis

The reduction operation should be associative and commutative.

Parameters
:
input (Tensor) – the input values

axis (int) – the dimension along which the reduction should be done. If None, reduce all dimensions

keep_dims (bool) – if true, keep the reduced dimensions with length 1

This function can also be called as a member function on tensor, as x.xor_sum(...) instead of xor_sum(x, ...).

---

triton.language.associative_scan
triton.language.associative_scan(input, axis, combine_fn, reverse=False, _semantic=None, _generator=None)
Applies the combine_fn to each elements with a carry in input tensors along the provided axis and update the carry

Parameters
:
input (Tensor) – the input tensor, or tuple of tensors

axis (int) – the dimension along which the reduction should be done

combine_fn (Callable) – a function to combine two groups of scalar tensors (must be marked with @triton.jit)

reverse (bool) – whether to apply the associative scan in the reverse direction along axis

This function can also be called as a member function on tensor, as x.associative_scan(...) instead of associative_scan(x, ...).

---

triton.language.cumprod
triton.language.cumprod(input, axis=0, reverse=False)
Returns the cumprod of all elements in the input tensor along the provided axis

Parameters
:
input (Tensor) – the input values

axis (int) – the dimension along which the scan should be done

reverse (bool) – if true, the scan is performed in the reverse direction

This function can also be called as a member function on tensor, as x.cumprod(...) instead of cumprod(x, ...).

---

triton.language.cumsum
triton.language.cumsum(input, axis=0, reverse=False, dtype: constexpr = None)
Returns the cumsum of all elements in the input tensor along the provided axis

Parameters
:
input (Tensor) – the input values

axis (int) – the dimension along which the scan should be done

reverse (bool) – if true, the scan is performed in the reverse direction

dtype (tl.dtype) – the desired data type of the returned tensor. If specified, the input tensor is casted to dtype before the operation is performed. If not specified, small integer types (< 32 bits) are upcasted to prevent overflow. Note that tl.bfloat16 inputs are automatically promoted to tl.float32.

This function can also be called as a member function on tensor, as x.cumsum(...) instead of cumsum(x, ...).

---

triton.language.histogram
triton.language.histogram(input, num_bins, mask=None, _semantic=None, _generator=None)
computes an histogram based on input tensor with num_bins bins, the bins have a width of 1 and start at 0.

Parameters
:
input (Tensor) – the input tensor

num_bins (int) – number of histogram bins

mask (Block of triton.int1, optional) – if mask[idx] is false, exclude input[idx] from histogram

This function can also be called as a member function on tensor, as x.histogram(...) instead of histogram(x, ...).

---

triton.language.sort
triton.language.sort(x, dim: constexpr = None, descending: constexpr = constexpr[0])

---

triton.language.topk
triton.language.topk(x, k: constexpr, dim: constexpr = None, descending: constexpr = True)
Returns the k largest (or smallest) elements of the input tensor along the specified dimension.

The elements are returned in sorted order (largest first).

Parameters
:
x (Tensor) – The input tensor.

k (int) – The number of top elements to return. Must be a power of two.

dim (int, optional) – The dimension along which to find the top k elements. If None, uses the last dimension. Currently only the last dimension is supported.

descending (bool, optional) – If set to True, returns k largest elements. If set to False, returns k smallest elements.

Returns
:
A tensor containing the k largest elements along the specified dimension.

Return type
:
Tensor

Example:

# Get top 4 elements from a 1D tensor
x = tl.arange(0, 16)
top4 = tl.topk(x, 4)  # Returns [15, 14, 13, 12]

---

triton.language.gather
triton.language.gather(src, index, axis, _semantic=None)
Gather from a tensor along a given dimension.

Parameters
:
src (Tensor) – the source tensor

index (Tensor) – the index tensor

axis (int) – the dimension to gather along

This function can also be called as a member function on tensor, as x.gather(...) instead of gather(x, ...).

---

triton.language.atomic_add
triton.language.atomic_add(pointer, val, mask=None, sem=None, scope=None, _semantic=None)
Performs an atomic add at the memory location specified by pointer.

Return the data stored at pointer before the atomic operation.

Parameters
:
pointer (Block of dtype=triton.PointerDType) – The memory locations to operate on

val (Block of dtype=pointer.dtype.element_ty) – The values with which to perform the atomic operation

sem (str, optional) – Specifies the memory semantics for the operation. Acceptable values are “acquire”, “release”, “acq_rel” (stands for “ACQUIRE_RELEASE”), and “relaxed”. If not provided, the function defaults to using “acq_rel” semantics.

scope (str, optional) – Defines the scope of threads that observe the synchronizing effect of the atomic operation. Acceptable values are “gpu” (default), “cta” (cooperative thread array, thread block), or “sys” (stands for “SYSTEM”). The default value is “gpu”.

This function can also be called as a member function on tensor, as x.atomic_add(...) instead of atomic_add(x, ...).

---

triton.language.atomic_and
triton.language.atomic_and(pointer, val, mask=None, sem=None, scope=None, _semantic=None)
Performs an atomic logical and at the memory location specified by pointer.

Return the data stored at pointer before the atomic operation.

Parameters
:
pointer (Block of dtype=triton.PointerDType) – The memory locations to operate on

val (Block of dtype=pointer.dtype.element_ty) – The values with which to perform the atomic operation

sem (str, optional) – Specifies the memory semantics for the operation. Acceptable values are “acquire”, “release”, “acq_rel” (stands for “ACQUIRE_RELEASE”), and “relaxed”. If not provided, the function defaults to using “acq_rel” semantics.

scope (str, optional) – Defines the scope of threads that observe the synchronizing effect of the atomic operation. Acceptable values are “gpu” (default), “cta” (cooperative thread array, thread block), or “sys” (stands for “SYSTEM”). The default value is “gpu”.

This function can also be called as a member function on tensor, as x.atomic_and(...) instead of atomic_and(x, ...).

---

triton.language.atomic_cas
triton.language.atomic_cas(pointer, cmp, val, sem=None, scope=None, _semantic=None)
Performs an atomic compare-and-swap at the memory location specified by pointer.

Return the data stored at pointer before the atomic operation.

Parameters
:
pointer (Block of dtype=triton.PointerDType) – The memory locations to operate on

cmp (Block of dtype=pointer.dtype.element_ty) – The values expected to be found in the atomic object

val (Block of dtype=pointer.dtype.element_ty) – The values with which to perform the atomic operation

sem (str, optional) – Specifies the memory semantics for the operation. Acceptable values are “acquire”, “release”, “acq_rel” (stands for “ACQUIRE_RELEASE”), and “relaxed”. If not provided, the function defaults to using “acq_rel” semantics.

scope (str, optional) – Defines the scope of threads that observe the synchronizing effect of the atomic operation. Acceptable values are “gpu” (default), “cta” (cooperative thread array, thread block), or “sys” (stands for “SYSTEM”). The default value is “gpu”.

This function can also be called as a member function on tensor, as x.atomic_cas(...) instead of atomic_cas(x, ...).

---

triton.language.atomic_max
triton.language.atomic_max(pointer, val, mask=None, sem=None, scope=None, _semantic=None)
Performs an atomic max at the memory location specified by pointer.

Return the data stored at pointer before the atomic operation.

Parameters
:
pointer (Block of dtype=triton.PointerDType) – The memory locations to operate on

val (Block of dtype=pointer.dtype.element_ty) – The values with which to perform the atomic operation

sem (str, optional) – Specifies the memory semantics for the operation. Acceptable values are “acquire”, “release”, “acq_rel” (stands for “ACQUIRE_RELEASE”), and “relaxed”. If not provided, the function defaults to using “acq_rel” semantics.

scope (str, optional) – Defines the scope of threads that observe the synchronizing effect of the atomic operation. Acceptable values are “gpu” (default), “cta” (cooperative thread array, thread block), or “sys” (stands for “SYSTEM”). The default value is “gpu”.

This function can also be called as a member function on tensor, as x.atomic_max(...) instead of atomic_max(x, ...).

---

riton.language.atomic_min
triton.language.atomic_min(pointer, val, mask=None, sem=None, scope=None, _semantic=None)
Performs an atomic min at the memory location specified by pointer.

Return the data stored at pointer before the atomic operation.

Parameters
:
pointer (Block of dtype=triton.PointerDType) – The memory locations to operate on

val (Block of dtype=pointer.dtype.element_ty) – The values with which to perform the atomic operation

sem (str, optional) – Specifies the memory semantics for the operation. Acceptable values are “acquire”, “release”, “acq_rel” (stands for “ACQUIRE_RELEASE”), and “relaxed”. If not provided, the function defaults to using “acq_rel” semantics.

scope (str, optional) – Defines the scope of threads that observe the synchronizing effect of the atomic operation. Acceptable values are “gpu” (default), “cta” (cooperative thread array, thread block), or “sys” (stands for “SYSTEM”). The default value is “gpu”.

This function can also be called as a member function on tensor, as x.atomic_min(...) instead of atomic_min(x, ...).

---

triton.language.atomic_or
triton.language.atomic_or(pointer, val, mask=None, sem=None, scope=None, _semantic=None)
Performs an atomic logical or at the memory location specified by pointer.

Return the data stored at pointer before the atomic operation.

Parameters
:
pointer (Block of dtype=triton.PointerDType) – The memory locations to operate on

val (Block of dtype=pointer.dtype.element_ty) – The values with which to perform the atomic operation

sem (str, optional) – Specifies the memory semantics for the operation. Acceptable values are “acquire”, “release”, “acq_rel” (stands for “ACQUIRE_RELEASE”), and “relaxed”. If not provided, the function defaults to using “acq_rel” semantics.

scope (str, optional) – Defines the scope of threads that observe the synchronizing effect of the atomic operation. Acceptable values are “gpu” (default), “cta” (cooperative thread array, thread block), or “sys” (stands for “SYSTEM”). The default value is “gpu”.

This function can also be called as a member function on tensor, as x.atomic_or(...) instead of atomic_or(x, ...).

---

triton.language.atomic_xchg
triton.language.atomic_xchg(pointer, val, mask=None, sem=None, scope=None, _semantic=None)
Performs an atomic exchange at the memory location specified by pointer.

Return the data stored at pointer before the atomic operation.

Parameters
:
pointer (Block of dtype=triton.PointerDType) – The memory locations to operate on

val (Block of dtype=pointer.dtype.element_ty) – The values with which to perform the atomic operation

sem (str, optional) – Specifies the memory semantics for the operation. Acceptable values are “acquire”, “release”, “acq_rel” (stands for “ACQUIRE_RELEASE”), and “relaxed”. If not provided, the function defaults to using “acq_rel” semantics.

scope (str, optional) – Defines the scope of threads that observe the synchronizing effect of the atomic operation. Acceptable values are “gpu” (default), “cta” (cooperative thread array, thread block), or “sys” (stands for “SYSTEM”). The default value is “gpu”.

This function can also be called as a member function on tensor, as x.atomic_xchg(...) instead of atomic_xchg(x, ...).

---

triton.language.atomic_xor
triton.language.atomic_xor(pointer, val, mask=None, sem=None, scope=None, _semantic=None)
Performs an atomic logical xor at the memory location specified by pointer.

Return the data stored at pointer before the atomic operation.

Parameters
:
pointer (Block of dtype=triton.PointerDType) – The memory locations to operate on

val (Block of dtype=pointer.dtype.element_ty) – The values with which to perform the atomic operation

sem (str, optional) – Specifies the memory semantics for the operation. Acceptable values are “acquire”, “release”, “acq_rel” (stands for “ACQUIRE_RELEASE”), and “relaxed”. If not provided, the function defaults to using “acq_rel” semantics.

scope (str, optional) – Defines the scope of threads that observe the synchronizing effect of the atomic operation. Acceptable values are “gpu” (default), “cta” (cooperative thread array, thread block), or “sys” (stands for “SYSTEM”). The default value is “gpu”.

This function can also be called as a member function on tensor, as x.atomic_xor(...) instead of atomic_xor(x, ...).

---

triton.language.randint
triton.language.randint(seed, offset, n_rounds: constexpr = constexpr[10])
Given a seed scalar and an offset block, returns a single block of random int32.

Parameters
:
seed – The seed for generating random numbers.

offsets – The offsets to generate random numbers for.

----


triton.language.randint4x
triton.language.randint4x(seed, offset, n_rounds: constexpr = constexpr[10])
Given a seed scalar and an offset block, returns four blocks of random int32.

This is the maximally efficient entry point to Triton’s Philox pseudo-random number generator.

Parameters
:
seed – The seed for generating random numbers.

offsets – The offsets to generate random numbers for.

---

triton.language.rand
triton.language.rand(seed, offset, n_rounds: constexpr = constexpr[10])
Given a seed scalar and an offset block, returns a block of random float32 in 𝑈⁡(0,1).

Parameters
:
seed – The seed for generating random numbers.

offsets – The offsets to generate random numbers for.

---

triton.language.randn
triton.language.randn(seed, offset, n_rounds: constexpr = constexpr[10])
Given a seed scalar and an offset block, returns a block of random float32 in N⁡(0,1).

Parameters
:
seed – The seed for generating random numbers.

offsets – The offsets to generate random numbers for.

---

triton.language.range
classtriton.language.range(self, arg1, arg2=None, step=None, num_stages=None, loop_unroll_factor=None, disallow_acc_multi_buffer=False, flatten=False, warp_specialize=False, disable_licm=False)
Iterator that counts upward forever.

@triton.jit
def kernel(...):
    for i in tl.range(10, num_stages=3):
        ...
Note
:
This is a special iterator used to implement similar semantics to Python’s range in the context of triton.jit functions. In addition, it allows user to pass extra attributes to the compiler.

Parameters
:
arg1 – the start value.

arg2 – the end value.

step – the step value.

num_stages –

pipeline the loop into this many stages (so there are num_stages iterations of the loop in flight at once).

Note this is subtly different than passing num_stages as a kernel argument. The kernel argument only pipelines loads that feed into dot operations, while this attribute tries to pipeline most (though not all) loads in this loop.

loop_unroll_factor – Tells the Triton IR level loop unroller how many times to unroll a for loop that this range is used with. Less than 2 for this value implies no unrolling.

disallow_acc_multi_buffer – If true, prevent the accumulator of the dot operation in the loop to be multi-buffered, if applicable.

flatten – automatically flatten the loop nest starting at this loop to create a single flattened loop. The compiler will try to pipeline the flattened loop which can avoid stage stalling.

warp_specialize – Enable automatic warp specialization on the loop. The compiler will attempt to partition memory, MMA, and vector operations in the loop into separate async partitions. This will increase the total number of warps required by the kernel.

disable_licm –

Tells the compiler it shouldn’t hoist loop invariant code outside the loop. This is often useful to avoid creating long liveranges within a loop.

Note that warp specialization is only supported on Blackwell GPUs and only works on simple matmul loops. Support for arbitrary loops will be expanded over time.

__init__(self, arg1, arg2=None, step=None, num_stages=None, loop_unroll_factor=None, disallow_acc_multi_buffer=False, flatten=False, warp_specialize=False, disable_licm=False)
Methods

__init__(self, arg1[, arg2, step, ...])

Attributes

type

----

triton.language.static_range
classtriton.language.static_range(self, arg1, arg2=None, step=None)
Iterator that counts upward forever.

@triton.jit
def kernel(...):
    for i in tl.static_range(10):
        ...
Note
:
This is a special iterator used to implement similar semantics to Python’s range in the context of triton.jit functions. In addition, it also guides the compiler to unroll the loop aggressively.

Parameters
:
arg1 – the start value.

arg2 – the end value.

step – the step value.

__init__(self, arg1, arg2=None, step=None)
Methods

__init__(self, arg1[, arg2, step])

Attributes

type

---

triton.language.inline_asm_elementwise
triton.language.inline_asm_elementwise(asm: str, constraints: str, args: Sequence, dtype: dtype | Sequence[dtype], is_pure: bool, pack: int, _semantic=None)
Execute inline assembly over a tensor. Essentially, this is map where the function is inline assembly.

The input tensors args are implicitly broadcasted to the same shape.

dtype can be a tuple of types, in which case the output is a tuple of tensors.

Each invocation of the inline asm processes pack elements at a time. Exactly which set of inputs a block receives is unspecified. Input elements of size less than 4 bytes are packed into 4-byte registers.

This op does not support empty dtype – the inline asm must return at least one tensor, even if you don’t need it. You can work around this by returning a dummy tensor of arbitrary type; it shouldn’t cost you anything if you don’t use it.

Example using PTX assembly:

@triton.jit
def kernel(A, B, C, D, BLOCK: tl.constexpr):
    a = tl.load(A + tl.arange(0, BLOCK)) # uint8 tensor
    b = tl.load(B + tl.arange(0, BLOCK)) # float32 tensor

    # For each (a,b) in zip(a,b), perform the following:
    # - Let ai be `a` converted to int32.
    # - Let af be `a` converted to float.
    # - Let m be the max of ai and b.
    # - Return ai and mi.
    # Do the above 4 elements at a time.
    (c, d) = tl.inline_asm_elementwise(
        asm="""
        {
            // Unpack `a` into `ai`.
            .reg .b8 tmp<4>;
            mov.b32 {tmp0, tmp1, tmp2, tmp3}, $8;
            cvt.u32.u8 $0, tmp0;
            cvt.u32.u8 $1, tmp1;
            cvt.u32.u8 $2, tmp2;
            cvt.u32.u8 $3, tmp3;
        }
        // Convert `ai` to float.
        cvt.rn.f32.s32 $4, $0;
        cvt.rn.f32.s32 $5, $1;
        cvt.rn.f32.s32 $6, $2;
        cvt.rn.f32.s32 $7, $3;
        // Take max of `ai` and `b`.
        max.f32 $4, $4, $9;
        max.f32 $5, $5, $10;
        max.f32 $6, $6, $11;
        max.f32 $7, $7, $12;
        """,
        constraints=(
            # 8 output registers, namely
            #   $0=ai0, $1=ai1, $2=ai2, $3=ai3,
            #   $4=m0,  $5=m1,  $6=m2,  $7=m3.
            "=r,=r,=r,=r,=r,=r,=r,=r,"
            # 5 input registers, namely
            #   $8=ai,
            #   $9=b0, $10=b1, $11=b2, $12=b3.
            # The four elements from `a` are all packed into one register.
            "r,r,r,r,r"),
        args=[a, b],
        dtype=(tl.int32, tl.float32),
        is_pure=True,
        pack=4,
    )
    tl.store(C + tl.arange(0, BLOCK), c)
    tl.store(D + tl.arange(0, BLOCK), d)
Parameters
:
asm – assembly to run. Must match target’s assembly format.

constraints – asm constraints in LLVM format

args – the input tensors, whose values are passed to the asm block

dtype – the element type(s) of the returned tensor(s)

is_pure – if true, the compiler assumes the asm block has no side-effects

pack – the number of elements to be processed by one instance of inline assembly

Returns
:
one tensor or a tuple of tensors of the given dtypes

---

triton.language.assume
triton.language.assume(cond, _semantic=None)
Allow compiler to assume the cond is True.

---


triton.language.debug_barrier
triton.language.debug_barrier(_semantic=None)
Insert a barrier to synchronize all threads in a block.

---

triton.language.max_constancy
triton.language.max_constancy(input, values, _semantic=None)
Let the compiler know that the value first values in input are constant.

e.g. if values is [4], then each group of 4 values in input should all be equal, for example [0, 0, 0, 0, 1, 1, 1, 1].

---

triton.language.max_contiguous
triton.language.max_contiguous(input, values, _semantic=None)
Let the compiler know that the value first values in input are contiguous.

---

triton.language.multiple_of
triton.language.multiple_of(input, values, _semantic=None)
Let the compiler know that the values in input are all multiples of value.

---

triton.language.static_print
triton.language.static_print(*values, sep: str = ' ', end: str = '\n', file=None, flush=False, _semantic=None)
Print the values at compile time. The parameters are the same as the builtin print.

NOTE: Calling the Python builtin print is not the same as calling this, it instead maps to device_print, which has special requirements for the arguments.

tl.static_print(f"BLOCK_SIZE={BLOCK_SIZE}")

---

triton.language.static_assert
triton.language.static_assert(cond, msg='', _semantic=None)
Assert the condition at compile time. Does not require that the TRITON_DEBUG environment variable is set.

tl.static_assert(BLOCK_SIZE == 1024)

---

triton.language.device_print
triton.language.device_print(prefix, *args, hex=False, _semantic=None)
Print the values at runtime from the device. String formatting does not work for runtime values, so you should provide the values you want to print as arguments. The first value must be a string, all following values must be scalars or tensors.

Calling the Python builtin print is the same as calling this function, and the requirements for the arguments will match this function (not the normal requirements for print).

tl.device_print("pid", pid)
print("pid", pid)
On CUDA, printfs are streamed through a buffer of limited size (on one host, we measured the default as 6912 KiB, but this may not be consistent across GPUs and CUDA versions). If you notice some printfs are being dropped, you can increase the buffer size by calling

triton.runtime.driver.active.utils.set_printf_fifo_size(size_bytes)
CUDA may raise an error if you try to change this value after running a kernel that uses printfs. The value set here may only affect the current device (so if you have multiple GPUs, you’d need to call it multiple times).

Parameters
:
prefix – a prefix to print before the values. This is required to be a string literal.

args – the values to print. They can be any tensor or scalar.

hex – print all values as hex instead of decimal

---

triton.language.device_assert
triton.language.device_assert(cond, msg='', mask=None, _semantic=None)
Assert the condition at runtime from the device. Requires that the environment variable TRITON_DEBUG is set to a value besides 0 in order for this to have any effect.

Using the Python assert statement is the same as calling this function, except that the second argument must be provided and must be a string, e.g. assert pid == 0, "pid != 0". The environment variable must be set for this assert statement to have any effect.

tl.device_assert(pid == 0)
assert pid == 0, f"pid != 0"
Parameters
:
cond – the condition to assert. This is required to be a boolean tensor.

msg – the message to print if the assertion fails. This is required to be a string literal.

---

triton.testing
Benchmark

This class is used by the perf_report function to generate line plots with a concise API.

do_bench

Benchmark the runtime of the provided function.

do_bench_cudagraph

Benchmark the runtime of the provided function.

perf_report

Mark a function for benchmarking.

assert_close

Asserts that two inputs are close within a certain tolerance.

---

triton.testing.Benchmark
classtriton.testing.Benchmark(self, x_names: List[str], x_vals: List[Any], line_arg: str, line_vals: List[Any], line_names: List[str], plot_name: str, args: Dict[str, Any], xlabel: str = '', ylabel: str = '', x_log: bool = False, y_log: bool = False, styles=None)
This class is used by the perf_report function to generate line plots with a concise API.

__init__(self, x_names: List[str], x_vals: List[Any], line_arg: str, line_vals: List[Any], line_names: List[str], plot_name: str, args: Dict[str, Any], xlabel: str = '', ylabel: str = '', x_log: bool = False, y_log: bool = False, styles=None)
Constructor. x_vals can be a list of scalars or a list of tuples/lists. If x_vals is a list of scalars and there are multiple x_names, all arguments will have the same value. If x_vals is a list of tuples/lists, each element should have the same length as x_names.

Parameters
:
x_names (List[str]) – Name of the arguments that should appear on the x axis of the plot.

x_vals (List[Any]) – List of values to use for the arguments in x_names.

line_arg (str) – Argument name for which different values correspond to different lines in the plot.

line_vals (List[Any]) – List of values to use for the arguments in line_arg.

line_names (List[str]) – Label names for the different lines.

plot_name (str) – Name of the plot.

args (Dict[str, Any]) – Dictionary of keyword arguments to remain fixed throughout the benchmark.

xlabel (str, optional) – Label for the x axis of the plot.

ylabel (str, optional) – Label for the y axis of the plot.

x_log (bool, optional) – Whether the x axis should be log scale.

y_log (bool, optional) – Whether the y axis should be log scale.

styles (list[tuple[str, str]]) – A list of tuples, where each tuple contains two elements: a color and a linestyle.

Methods

__init__(self, x_names, x_vals, line_arg, ...)

Constructor.

---

triton.testing.do_bench
triton.testing.do_bench(fn, warmup=25, rep=100, grad_to_none=None, quantiles=None, return_mode='mean')
Benchmark the runtime of the provided function. By default, return the median runtime of fn along with the 20-th and 80-th performance percentile.

Parameters
:
fn (Callable) – Function to benchmark

warmup (int) – Warmup time (in ms)

rep (int) – Repetition time (in ms)

grad_to_none (torch.tensor, optional) – Reset the gradient of the provided tensor to None

quantiles (list[float], optional) – Performance percentile to return in addition to the median.

return_mode (str) – The statistical measure to return. Options are “min”, “max”, “mean”, “median”, or “all”. Default is “mean”.

---

triton.testing.do_bench_cudagraph
triton.testing.do_bench_cudagraph(fn, rep=20, grad_to_none=None, quantiles=None, return_mode='mean')
Benchmark the runtime of the provided function.

Parameters
:
fn (Callable) – Function to benchmark

rep (int) – Repetition time (in ms)

grad_to_none (torch.tensor, optional) – Reset the gradient of the provided tensor to None

return_mode (str) – The statistical measure to return. Options are “min”, “max”, “mean”, “median”, or “all”. Default is “mean”.

---

triton.testing.perf_report
triton.testing.perf_report(benchmarks)
Mark a function for benchmarking. The benchmark can then be executed by using the .run method on the return value.

Parameters
:
benchmarks (List of Benchmark) – Benchmarking configurations.

---

triton.testing.assert_close
triton.testing.assert_close(x, y, atol=None, rtol=None, err_msg='')
Asserts that two inputs are close within a certain tolerance.

Parameters
:
x (scala, list, numpy.ndarray, or torch.Tensor) – The first input.

y (scala, list, numpy.ndarray, or torch.Tensor) – The second input.

atol (float, optional) – The absolute tolerance. Default value is 1e-2.

rtol (float, optional) – The relative tolerance. Default value is 0.

err_msg (str) – The error message to use if the assertion fails.

---
Triton Semantics
Triton mostly follows the semantics of NumPy with minor exceptions. In this document, we go over some of the array computing features supported in Triton, and we cover the exceptions where Triton’s semantics deviate from that NumPy.

Type Promotion
Type Promotion occurs when tensors of different data types are used in an operation. For binary operations associated to dunder methods and the ternary function tl.where on its last two arguments, Triton automatically converts the input tensors to a common data type following a hierarchy of kinds (sets of dtypes): {bool} < {integral dypes} < {floating point dtypes}.

The algorithm is as follows:

Kind If one tensor is of a dtype of a higher kind, the other tensor is promoted to this dtype: (int32, bfloat16) -> bfloat16

Width If both tensors are of dtypes of the same kind, and one of them is of a higher width, the other one is promoted to this dtype: (float32, float16) -> float32

Prefer float16 If both tensors are of the same width and signedness but different dtypes (float16 and bfloat16 or different fp8 types), they are both promoted to float16. (float16, bfloat16) -> float16

Prefer unsigned Otherwise (same width, different signedness), they are promoted to the unsigned dtype: (int32, uint32) -> uint32

The rules are a bit different when they involve a scalar. By scalar here we mean a numeric literal, a variable marked with tl.constexpr or a combination of these. These are represented by NumPy scalars and have types bool, int and float.

When an operation involves a tensor and a scalar:

If the scalar is of a kind lower or equal to the tensor, it will not participate in the promotion: (uint8, int) -> uint8

If the scalar is of a higher kind, we choose the lowest dtype in which it fits among int32 < uint32 < int64 < uint64 for ints and float32 < float64 for floats. Then, both the tensor and the scalar are promoted to this dtype: (int16, 4.0) -> float32

Broadcasting
Broadcasting allows operations on tensors of different shapes by automatically expanding their shapes to a compatible size without copying the data. This follows the following rules:

If one of the tensor shapes is shorter, pad it on the left with ones until both tensors have the same number of dimensions: ((3, 4), (5, 3, 4)) -> ((1, 3, 4), (5, 3, 4))

Two dimensions are compatible if they are equal, or if one of them is 1. A dimension of 1 will be expanded to match the dimension of the other tensor. ((1, 3, 4), (5, 3, 4)) -> ((5, 3, 4), (5, 3, 4))

Differences with NumPy
C rounding in integer division Operators in Triton follow C semantics rather than Python semantics for efficiency. As such, int // int implements rounding towards zero as in C for integers of mixed signs, rather than rounding towards minus infinity as in Python. For the same reason, the modulus operator int % int (which is defined as a % b = a - b * (a // b)) also follows C semantics rather than Python semantics.

Perhaps confusingly, integer division and modulus follow Python semantics for computations where all the inputs are scalars.

---

Debugging Triton
This tutorial provides guidance for debugging Triton programs. It is mostly documented for Triton users. Developers interested in exploring Triton’s backend, including MLIR code transformation and LLVM code generation, can refer to this section to explore debugging options.

For compiler-level instrumentation of floating-point computations, see Floating-Point Sanitizer (FpSan).

Using Triton’s Debugging Operations
Triton includes four debugging operators that allow users to check and inspect tensor values:

static_print and static_assert are intended for compile-time debugging.

device_print and device_assert are used for runtime debugging.

device_assert executes only when TRITON_DEBUG is set to 1. Other debugging operators execute regardless of the value of TRITON_DEBUG.

Using the Interpreter
The interpreter is a straightforward and helpful tool for debugging Triton programs. It allows Triton users to run Triton programs on the CPU and inspect the intermediate results of each operation. To enable the interpreter mode, set the environment variable TRITON_INTERPRET to 1. This setting causes all Triton kernels to bypass compilation and be simulated by the interpreter using numpy equivalents of Triton operations. The interpreter processes each Triton program instance sequentially, executing operations one at a time.

There are three primary ways to use the interpreter:

Print the intermediate results of each operation using the Python print function. To inspect an entire tensor, use print(tensor). To examine individual tensor values at idx, use print(tensor.handle.data[idx]).

Attach pdb for step-by-step debugging of the Triton program:

TRITON_INTERPRET=1 pdb main.py
b main.py:<line number>
r
Import the pdb package and set breakpoints in the Triton program:

import triton
import triton.language as tl
import pdb

@triton.jit
def kernel(x_ptr, y_ptr, BLOCK_SIZE: tl.constexpr):
  pdb.set_trace()
  offs = tl.arange(0, BLOCK_SIZE)
  x = tl.load(x_ptr + offs)
  tl.store(y_ptr + offs, x)
Limitations
The interpreter has several known limitations:

It does not support operations on bfloat16 numeric types. To perform operations on bfloat16 tensors, use tl.cast(tensor) to convert the tensor to float32.

It does not support indirect memory access patterns such as:

ptr = tl.load(ptr)
x = tl.load(ptr)
Using Third-party Tools
For debugging on NVIDIA GPUs, compute-sanitizer is an effective tool for checking data races and memory access issues. To use it, prepend compute-sanitizer to your command to run the Triton program.

For debugging on AMD GPUs, you may want to try the LLVM AddressSanitizer for ROCm.

For detailed visualization of memory access in Triton programs, consider using the triton-viz tool, which is agnostic to the underlying GPUs.

---

Floating-Point Sanitizer (FpSan)
FpSan is a compiler instrumentation mode that rewrites selected floating-point Triton IR operations into deterministic “payload algebra” over integer bit-patterns. Its goal is not to approximate IEEE floating-point arithmetic. Instead, it preserves selected algebraic structure so that kernels that are symbolically equivalent under the sanitized semantics continue to agree, while wrong rewrites, wrong operands, wrong dataflow, or missing synchronization tend to perturb the result.

This makes FpSan primarily a kernel-checking tool. It is especially useful when you care more about whether a kernel preserves the intended symbolic computation than about its exact IEEE result on a particular input.

At a high level, FpSan:

maps floating-point bit-patterns into an integer payload domain

replaces supported floating-point ops with integer-domain rewrites chosen to preserve selected identities exactly

maps the resulting payload back into a floating-point bit-pattern so the rest of the pipeline can continue

Enabling FpSan
Enable FpSan before the compile or run you want to instrument.

From Python:

import triton

triton.knobs.compilation.instrumentation_mode = "fpsan"
# compile and run kernels here
triton.knobs.compilation.instrumentation_mode = ""
From the shell:

TRITON_INSTRUMENTATION_MODE=fpsan python your_script.py
Notes:

FpSan is a compiler feature, so it does not apply in interpreter mode.

On AMD, the backend currently enables FpSan only for gfx942, gfx950, and gfx1250.

How to Use It
The most effective way to use FpSan is to compare two kernels, or two versions of one kernel, under the same FpSan mode. Typical uses include:

comparing an optimized kernel against a simple reference kernel

comparing a fused kernel against an unfused composition

comparing two schedule variants that should be mathematically equivalent

checking that accumulator selection, predication, or TMEM pipelines preserve the intended payload flow

FpSan results should only be compared against other FpSan results, not against ordinary floating-point outputs.

Payload Model
For each floating-point width w, FpSan defines a bijection between floating-point bit-patterns and a w-bit integer payload; arithmetic wraps modulo 2^w.

Conceptually:

embed(x) maps a float bit-pattern to an integer payload

unembed(u) maps an integer payload back to a float bit-pattern

sanitized float ops are implemented as unembed(F(embed(...)))

The embedding is deliberately chosen so that a few important constants are stable:

embed(+0.0) = 0

embed(+1.0) = 1

embed(-1.0) = all-ones

Those fixed points are the reason identities such as x + 0 = x and x * 1 = x behave naturally under FpSan.

What FpSan Preserves
FpSan preserves exact identities in the payload algebra selected by each rewrite. The most important ones are:

ring identities for add, subtract, multiply, FMA, and dot-like accumulation

selected exponential identities for exp and exp2 (see below for details)

trigonometric identities for sin and cos

payload equality through casts, loads, stores, and copies

deterministic op-distinguishing tags for unary functions that do not yet have a richer algebraic model

This is what makes FpSan valuable for kernel checks: if two kernels should be the same symbolic computation under the preserved properties, they should produce the same payloads. This holds assuming a (generally believed) conjecture in transcendental number theory, Schanuel’s conjecture. One of the authors of FpSan has a [blog post](https://cp4space.hatsya.com/2026/05/03/schanuels-conjecture-and-the-semantics-of-fpsan/) explaining the theory behind FpSan from a mathematical perspective.

What FpSan Does Not Preserve
FpSan is not an IEEE simulator.

In particular, do not rely on it for:

real floating-point ordering, rounding, NaN propagation, infinities, subnormals, or exceptions

real transcendental semantics for log, sqrt, erf, floor, ceil, rsqrt, and similar tagged unary ops

expected floating-point bit patterns (i.e. for kernels that bitcast between floats and integers)

When a property matters for your check, the right question is: “is this property preserved by the payload rewrite for this specific op family?”

Common Arithmetic Ops
Add, Sub, Mul
Supported operations:

x + y

x - y

x * y

Rewrite:

add, subtract, or multiply the embedded payloads, then unembed the result

Exact preserved properties:

x + 0 = x

x - 0 = x

x - x = 0

x * 1 = x

associativity and commutativity of add and mul

distributivity of mul over add

Important caveat:

This is ring arithmetic modulo 2^w, not IEEE arithmetic.

Min and Max
Supported operations:

tl.minimum(x, y)

tl.maximum(x, y)

min(x, y) and max(x, y) in Triton code

Rewrite:

signed integer min or max on payloads

Exact preserved properties:

idempotence: min(x, x) = x and max(x, x) = x

commutativity

associativity

Important caveats:

The order is the signed integer order of payloads, not IEEE float order.

NaN handling, and the exact signed-zero contract, are not modeled.

Division
Supported operation:

x / y

Rewrite:

x / y becomes embed(x) * inv(embed(y)), then unembed

Here inv is:

the true modular inverse for odd payloads

a parity-preserving involution for even payloads

Exact preserved properties:

x / 1 = x

1 / (1 / x) = x

for odd payloads, the usual modular inverse laws hold

Important caveats:

x / x = 1 is not guaranteed for all payloads.

Division by zero does not produce IEEE infinities or traps.

This rewrite is chosen for algebraic checking, not numeric realism.

Remainder
Supported operation:

x % y

Rewrite:

signed integer remainder on payloads after forcing the denominator odd with den | 1

Exact preserved properties:

same inputs produce the same sanitized remainder payload

Important caveats:

Real floating-point remainder semantics are not modeled.

Zero denominators are intentionally mapped to a safe odd payload instead of trapping.

FMA
Supported operation:

tl.fma(a, b, c)

Rewrite:

a * b + c in payload arithmetic

Exact preserved properties:

exact agreement with the sanitized expansion mul followed by add

fma(a, b, c) = a*b + c in the payload ring

Important caveat:

There is no special fused-rounding behavior.

Unary Math Ops
exp2
Supported operation:

tl.exp2(x)

Rewrite:

modular exponentiation by a fixed odd generator in payload space

Exact preserved properties:

exp2(x + y) = exp2(x) * exp2(y)

exp2(0) = 1

exp2(-x) = 1.0 / exp2(x)

exp
Supported operation:

tl.exp(x)

Rewrite:

exp(x) is implemented as exp2(x * rcp_log2) in payload space

Exact preserved properties:

exp uses the same payload-space construction as exp2 after scaling the input by a fixed internal payload constant

sin and cos
Supported operations:

tl.sin(x)

tl.cos(x)

Rewrite:

a deterministic payload-space rewrite chosen to preserve the identities below

Exact preserved properties:

sin(x + y) = sin(x) * cos(y) + cos(x) * sin(y)

sin(x - y) = sin(x) * cos(y) - cos(x) * sin(y)

cos(x + y) = cos(x) * cos(y) - sin(x) * sin(y)

cos(x - y) = cos(x) * cos(y) + sin(x) * sin(y)

cos(x)^2 + sin(x)^2 = 1

Important caveat:

These are not IEEE trig values; they are payload functions chosen to preserve the angle identities above.

Tagged Unary Ops
Supported operations:

tl.log(x)

tl.log2(x)

tl.sqrt(x)

tl.rsqrt(x)

tl.erf(x)

tl.floor(x)

tl.ceil(x)

precise square root variants

Rewrite:

an invertible payload tag: multiply by an odd constant, xor with an op-specific hash, then multiply again

Exact preserved properties:

payload equality is preserved for the same op: if x == y in payload space, then op(x) == op(y)

different supported unary ops get different tags

Important caveats:

These rewrites intentionally do not preserve real mathematical identities such as sqrt(x)^2 = x or log(x*y) = log(x) + log(y).

Casts and Format Conversions
Float-to-Float Conversions
Supported operations:

converting a tensor between floating-point types with x.to(dtype)

implicit float widening and narrowing conversions

Rewrite:

signed integer extension or truncation in payload space, followed by unembed

Exact preserved properties:

0, +1, and -1 remain stable across the conversion

sign-extension behavior in the payload domain

truncation drops high payload bits

an upcast followed by a downcast is the identity

Important caveat:

This preserves payload structure, not IEEE conversion semantics.

Conversions between fp types of the same width do not model any loss of precision or range, so for example under fpsan fn(a.to(tl.float16)).to(tl.bfloat16) == fn(a) (for any bfloat16 a).

Packed fp4 conversion
Rewrite:

unpack low and high nibbles from the source byte tensor

reshape and reorder them

interpret each unpacked nibble directly as a payload in the destination float width

Exact preserved properties:

deterministic unpacking of packed fp4 storage

exact preservation of the unpacked nibble payloads

Important caveat:

This is not real fp4 numeric decoding.

The same raw-payload interpretation is reused by scaled-dot paths for e2m1.

Pure Extern Elementwise Ops
Supported operation:

tl.extern_elementwise when all of the following hold:

the op is pure

the result type is float-like

there is at least one operand

every operand is numeric

Rewrite:

rotate each operand payload by its argument index

sum the rotated payloads

xor the result with a stable hash of the symbol name

unembed

Exact preserved properties:

deterministic dependence on all operands and on operand order

deterministic distinction between different external symbols

mixed float and integer operands are supported; float operands are embedded, integer operands are used directly after signed casting to the result width

Important caveat:

This is a structural tag, not a numeric model of the external function.

Gluon MMA and Tensor Memory
Supported Gluon operations include:

mma_v2

warpgroup_mma and warpgroup_mma_wait

tcgen05_mma and tcgen05_mma_scaled

tcgen05_copy and tcgen05_commit

allocate_tensor_memory

tensor-memory descriptor methods such as load, load_min, load_max, store, slice, index, and _reinterpret

AMD mfma, mfma_scaled, wmma, wmma_scaled, and scaled_upcast

Rewrite:

perform multiply-add accumulation in payload space

preserve payload bits across tensor-memory loads, stores, copies, and views

keep accumulator-selection and predication behavior structurally visible

Exact preserved properties:

exact matrix-multiply algebra over the payload ring

exact agreement with sanitized scalar multiply-add expansion

accumulation with the provided accumulator is preserved as payload addition

tensor-memory operations preserve payload flow across the pipeline

Important caveats:

Scaled MMA preserves the sanitizer’s payload treatment of low-precision operands and scales, not exact hardware-format numeric decoding.

Tensor-memory operations preserve payload dataflow; they do not make FpSan a substitute for race or synchronization checking.

Currently fpsan is supported on all NVIDIA hardware, as well as AMD gfx942, gfx950, and gfx1250.

Practical Guidance for Checks
FpSan is a good fit when you want to check:

that two kernels implement the same preserved algebra

that a fused kernel keeps the intended dataflow

that predication or accumulator-selection logic is wired correctly

that a tensor-memory or warp-specialized pipeline preserves payload flow

FpSan is a poor fit when you want to check:

IEEE edge cases

real transcendental accuracy

NaN or infinity behavior

hardware-format decode semantics for low-precision formats

In short, rely on FpSan for structure-preserving kernel validation, and rely on ordinary numerical tests for IEEE behavior.

---

Cluster 1 grammar/surface audit - May 15, 2026

Purpose

This audit separates Triton API coverage from Cluster 1 harness structure. The
task-agnostic `G` surface is a generated-module contract plus `tl.*` allow-list,
not the full Triton language grammar.

Structural harness constraints

- The task-agnostic generated module allows one to three `@triton.jit` helpers.
  This cap is pragmatic and evaluation-set dependent. It is not a Triton
  language property.
- The module must expose exactly one typed public launcher returning
  `torch.Tensor`.
- The launcher must allocate output, bind a `grid`, launch one helper with
  bracket syntax, and return the allocated output.
- Raw official snippets that define a JIT kernel and then launch it at module
  scope are valid Triton patterns but violate the Cluster 1 harness interface.
  Classify those rejections as `HARNESS_CONTRACT_RESTRICTION`.

API allow-list validation

The current task-agnostic allow-list covers the official `triton.language` API
families represented above:

- programming model: `program_id`, `num_programs`;
- creation: `arange`, `cat`, `full`, `zeros`, `zeros_like`, `cast`;
- shape manipulation: `broadcast`, `broadcast_to`, `expand_dims`,
  `interleave`, `join`, `permute`, `ravel`, `reshape`, `split`, `trans`,
  `view`;
- linear algebra: `dot`, `dot_scaled`;
- memory/pointer and descriptor APIs: `load`, `store`,
  `make_tensor_descriptor`, `load_tensor_descriptor`,
  `store_tensor_descriptor`, `make_block_ptr`, `advance`, plus descriptor
  method calls used by the corpus fixtures;
- indexing: `flip`, `where`, `swizzle2d`;
- math and activation: `abs`, `cdiv`, `ceil`, `clamp`, `cos`, `div_rn`, `erf`,
  `exp`, `exp2`, `fdiv`, `floor`, `fma`, `log`, `log2`, `maximum`, `minimum`,
  `rsqrt`, `sigmoid`, `sin`, `softmax`, `sqrt`, `sqrt_rn`, `umulhi`;
- reductions: `argmax`, `argmin`, `max`, `min`, `reduce`, `sum`, `xor_sum`;
- scan/sort: `associative_scan`, `cumprod`, `cumsum`, `histogram`, `sort`,
  `topk`, `gather`;
- atomics: `atomic_add`, `atomic_and`, `atomic_cas`, `atomic_max`,
  `atomic_min`, `atomic_or`, `atomic_xchg`, `atomic_xor`;
- RNG: `randint4x`, `randint`, `rand`, `randn`;
- iterators: `tl.range`, `tl.static_range`;
- inline assembly: `tl.inline_asm_elementwise`;
- compiler hints and debug ops: `assume`, `debug_barrier`, `max_constancy`,
  `max_contiguous`, `multiple_of`, `static_print`, `static_assert`,
  `device_print`, `device_assert`.

The corpus and current official Triton language reference do not list `tl.tanh`.
Do not add `tl.tanh` unless an official Triton API reference or tutorial corpus
revision introduces it.

Validation result

The local validator accepted all corpus-derived Cluster 1 task-agnostic
fixtures used for this audit:

- `corpus_primitives`
- `block_pointer_copy`
- `advanced_block_pointer_alias`
- `reduce_combiner`
- `tuple_reduce_combiner`
- `tuple_associative_scan_combiner`
- `tensor_descriptor_methods`
- `tensor_descriptor_padding_option`
- `heuristic_scale`
- `generic_autotune_config`
- `positional_axis_reduction`
- `static_range_output_store`
- `generic_reduction_control_flow`
- `generic_nested_loop_tile_control`
- `multiline_nested_tl_expressions`
- `comments_and_multiline_calls`

No corpus-validated `tl.*` allow-list gap was found. No grammar behavior change
is justified by this audit.

Classification rules for future audits

- `GRAMMAR_BUG`: an in-scope official `tl.*` API name or call shape from this
  corpus is missing from the allow-list.
- `HARNESS_CONTRACT_RESTRICTION`: valid Triton code is rejected because it lacks
  the single typed launcher, output allocation, grid binding, bracket launch, or
  returned allocated output required by Cluster 1.
- `LEGITIMATE_SCOPE_EXCLUSION`: valid Triton/API material is deliberately out
  of Cluster 1's generated-code surface.
- `UNSUPPORTED_LEVEL2_FEATURE`: the example requires multi-stage fused or
  Level 2+ structure beyond the current Level 1-style harness.
