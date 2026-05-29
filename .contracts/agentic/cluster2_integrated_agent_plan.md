# Cluster 2 Integrated Plan - v5

**Status:** authoritative phased execution plan for Cluster 2 + shared eval suite + isolated Cluster 2 Modal surfaces
**Date:** 2026-05-12
**Audience:** the single implementer working Cluster 2 from start to finish
**Sequencing model:** linear, commit-sized phases. No parallel multi-agent work graph.
**GPU policy:** Cluster 2 always passes `L4` explicitly on every new Cluster 2 Modal generation or eval call. The shared `DEFAULT_GENERATION_GPU` constant stays `"L40S"` and Cluster 1 defaults are not changed.
**Cluster 1 invariant:** Cluster 1 generation, grammar-constrained generation `G`, prompt rendering, Modal generation, result schema, analyzers, `KERNEL_SPECS` iteration, and default GPU behavior are frozen. Phase -1 records fingerprints and manifests only.
**Cluster 1 contract sources:** `.contracts/agentic/cluster1_contract.md` and `.contracts/agentic/cluster1_plan.md`.
**Tracked reproducibility surface:** because `.contracts/agentic/` and `outputs/` are gitignored, Phase -1 writes committed manifests under `cluster2/contracts/`.

---

## 0. Object of Study and Thesis Scope

This plan is a **controlled study of inference-time control mechanisms for Triton kernel generation**. It is not a general Triton benchmark framework, not a universal KernelBench coverage project, and not an attempt at population-level generalization.

### Foundational claim

> Given a fixed prompt X, model M, and matched generation attempts, an inference-time control mechanism improves Triton kernel convergence relative to unconstrained generation.

Kernel correctness is an **outcome metric**, not the object of study.

### Experimental scope

The three locked KernelBench Level 1 problems from Cluster 1 remain the **primary experimental substrate**. They are framed as **representative kernel archetypes**, not as exhaustive benchmark coverage:

| Archetype | KernelBench problem | Why included |
|---|---|---|
| Pointwise | ReLU (level 1, problem 19) | Simplest indexing, masks, block-size handling |
| Reduction | Softmax (level 1, problem 23) | Row-wise reduction, numerically sensitive |
| Tiled matmul | GEMM (level 1, problem 1) | Multi-axis grids, `tl.dot`, shared-memory tile constraints |

The defended thesis claim is intentionally narrow. The primary defended comparison is `C` vs the frozen `none` replay control. `G+C` vs the frozen `G` replay control is a pre-registered secondary comparison.

> **Under fixed prompts and matched generation attempts, correctness-feedback control (`C`) improves convergence on three representative Triton kernel archetypes (ReLU/pointwise, Softmax/reduction, GEMM/tiled-matmul, drawn from KernelBench Level 1) relative to unconstrained generation.**

If frozen Cluster 1 replay artifacts do not contain resolved model/tokenizer revisions, the claim must say fixed `model_id`, not fixed resolved revision. Revision pinning may be claimed for replay controls only when those revisions are actually present in the frozen artifacts.

Held-out kernels are deferred out of the Cluster 2 implementation-critical path. Any future held-out check requires a separate contract amendment or explicitly optional post-Cluster-2 plan.

### Experimental design

- **Experimental unit:** `(archetype, dtype, seed)`.
- **Conditions:** `{none, G, C, G+C}`.
- **Replay controls:** `none` and `G` are analytical controls loaded from frozen Cluster 1 JSONL artifacts. They are not regenerated.
- **New generation conditions:** only `C` and `G+C` may invoke new model generation.
- **Primary causal outcome:**

  ```text
  Lift_C = convergence_rate(C, attempts=N) - pass_rate_within_N_attempts(frozen none replay control)
  ```

  measured per `(archetype, dtype, base_seed)` cell, aggregated over cells with 95% bootstrap CI.

- **Secondary outcome:** `G+C` convergence compared with frozen `G` replay control under the same equal-attempts mapping rule.
- **Gating / feasibility outcome:** infrastructure coverage. Reported alongside lift to contextualize, never substituted for it.

### Equal-attempts definition

Equal-attempts means each condition is evaluated against the same maximum number of candidate sources per cell. For replay controls (`none`, `G`), candidates come from frozen Cluster 1 artifacts. For generated conditions (`C`, `G+C`), candidates come from new Cluster 2 generation/repair trajectories.

Equal-attempts is not token-matched, wall-time-matched, or GPU-cost-matched.

Across compared conditions:
- Same prompt template (`cluster1.data.prompts.prompt_contract.build_prompt`).
- Same model identity and tokenizer identity, with resolved revisions recorded when available.
- Same dtype handling.
- Same maximum candidate-source count per cell (`repair_budget=5` means `N=6` candidate sources).
- The **only** treatment difference is the control mechanism.

Repair feedback **may guide correction** but **may not redefine the underlying task**. The base prompt is included verbatim in every repair iteration.

---

## 1. Locked Resolutions

### 1.1 Condition Routing

| Condition | Generation source | Allowed to invoke model generation? | Uses Cluster 1 G internals? | Notes |
|---|---|---:|---:|---|
| `none` | frozen Cluster 1 baseline JSONL | No | No | Replay-only control |
| `G` | frozen Cluster 1 grammar-active JSONL | No | Already reflected in frozen artifacts | Replay-only control |
| `C` | Cluster 2 repair loop | Yes | No | New C-only trajectory |
| `G+C` | Cluster 2 repair loop using frozen/unchanged G machinery | Yes | Yes, but unchanged | New trajectory; G code path must remain byte-identical |

**Replay control:** A control condition whose source candidates are loaded from frozen Cluster 1 JSONL artifacts instead of generated again.

The runner owns routing for `{none, G, C, G+C}`. C2 remote generation owns only `{C, G+C}`. Conditions `none` and `G` must never instantiate a C2 generation request and must never call a model generation function during Cluster 2 runs.

### 1.2 Cluster 1 G Is Frozen

Cluster 1 G is frozen. Cluster 2 must not modify:
- grammar files,
- grammar loader,
- constrained decoding,
- hardware checker,
- prompt contract,
- KernelBench locked prompt rendering,
- `RemoteGenerator.generate_one`,
- Cluster 1 model-loading defaults,
- Cluster 1 Modal generation schema,
- Cluster 1 result schema,
- Cluster 1 experiment runner behavior.

`G+C` may use G only through an adapter that calls the existing frozen G path or reproduces its behavior under byte-hash gates. No G redevelopment is allowed. No new Cluster 1 inference, Modal generation work, retraining, or revalidation is allowed except Phase -1 freeze/fingerprint verification.

### 1.3 C2 Modal Isolation

Cluster 2 Modal surfaces live under `cluster2/modal/`:
- `cluster2/modal/schemas.py`
- `cluster2/modal/generation.py`
- `cluster2/modal/correctness.py`
- `cluster2/modal/correctness_runner.py`

This layout is chosen over adding C2 classes to `shared/modal_harness/` because Cluster 2 has different schemas, revision pinning, routing, feedback, and replay-control semantics. Keeping these modules under `cluster2/modal/` makes ownership obvious and keeps Cluster 1 Modal entry points frozen.

Existing Cluster 1 Modal files remain untouched. Files not to edit:
- `shared/modal_harness/generation.py`
- `shared/modal_harness/schemas.py`
- `shared/modal_harness/smoke.py`

If shared helpers are needed, create new helper modules rather than modifying Cluster 1 entry points. C2 may reuse shared image builders, app objects, volumes, secrets, or environment helpers only if:
- Cluster 1 image manifests remain unchanged,
- Cluster 1 source-content hashes remain unchanged,
- Cluster 1 tests and fingerprint gates pass.

Cluster 2 interoperability with Modal/GCP/shared infrastructure occurs through stable artifacts and schemas, not by mutating Cluster 1 Modal classes.

Interoperability surfaces:
- JSONL outputs,
- source strings,
- eval request/result schemas,
- content-hash manifests,
- object storage paths,
- runner CLI contracts,
- artifact paths.

### 1.4 Other Locked Decisions

| Concern | Locked decision |
|---|---|
| Experimental substrate | Three locked KernelBench Level 1 archetypes: ReLU, Softmax, GEMM. |
| Held-out role | Deferred. No held-out Phase 16 in the implementation-critical path. No held-out specs under `cluster1/`. |
| Coverage role | Gating / feasibility metric, not primary scientific outcome. |
| Token statistics | Not collected. Token-matched controls and token-cost analysis are out of scope. |
| Statistical estimator | `pass@1_initial` may use unbiased pass@k for iteration-0 only. `convergence_rate` and `pass_rate_within_N_attempts` are Bernoulli per cell, reported with 95% bootstrap CI over cells. |
| Convergence definition | A generated condition converges if any candidate source at iteration `i in {0..5}` reaches `functional_success=True`. A replay control passes if any replayed frozen source among the mapped `N` candidates reaches `functional_success=True` under the C2 evaluator. |
| Shape-pattern alphabet | `{ND, RxC, MNK}` for the locked three only. No universal shape abstraction expansion. Shape metadata is C2-side, not added to Cluster 1 specs. |
| Repair vs eval shape sets | Procedural generator returns disjoint `repair_shape_set` and `eval_shape_set`. Convergence requires passing both at the same candidate. |
| Private-eval feedback content | If repair shapes pass but eval shapes fail, feedback says only: "The previous attempt passed initial correctness shapes but failed Level 2. Produce a corrected complete Triton Python module." |
| Numeric determinism | Correctness calls disable TF32 and set deterministic torch/cuDNN flags. |
| Reference execution | KernelBench `KernelSpec.reference_code` loaded into isolated module; `Model()` instantiated; `Model.forward(*inputs)` under `torch.no_grad()`. `get_inputs()` is not called. |
| Memory caps | `MAX_DIM = 16384`, `MAX_ELEMENTS = 2**24`. |
| Cluster 1 default GPU | `DEFAULT_GENERATION_GPU = "L40S"` stays unchanged. |
| Cluster 2 GPUs | New C2 generation and C2 evaluation pass `L4` explicitly. Replay controls call only C2 evaluation. |
| `G+C` grammar variant | `grammar_variant="template_upper_bound"` only. `task_agnostic` deferred. |
| Modal isolation | Subprocess only. No Sandbox option. |
| Repair budget | `repair_budget = 5`; iteration 0 plus 5 repairs means `N=6` candidate sources. |
| Seed schedule | For generated conditions, attempt `i` uses generation seed `base_seed * 10 + i`. Replay controls map frozen rows by seed or generation index to the same attempt indexes; they do not regenerate missing indexes. |
| Model/tokenizer revision pinning | C2 generation requests carry `model_revision` and `tokenizer_revision`. Frozen C1 rows record `model_revision` and `tokenizer_revision` if available. Missing C1 revisions are recorded explicitly in the Phase -1 manifest. |
| Level 1 feedback content | error_type + lineno when available + first 200 chars of error_msg. No LLVM/C++/PTX backtraces. |
| AST sanitizer | Allowlist-only, default-deny. Alias/direct-import/getattr bypass handling is required. |
| Generated-code surface scan | Folded into the AST sanitizer module. |
| Aggregator | Compares invariant eval hashes across all evaluated rows. Compares generation hashes only within comparable generation-source classes. Checks frozen Cluster 1 hashes against Phase -1 manifest. |
| Paper scale | The main runner supports `--scale-tier paper --n 20`; no separate paper runner. |
| CLI write mode | `--overwrite` and hash-checked `--resume` only. No `--append`. |
| Performance scope | No profiler, timing, speedup, fast@, or performance sidecar fields. |

---

## 2. Current Repo State and New Surface Plan

Already present and reusable without changing Cluster 1 behavior:
- `shared/eval/{schema, constants, tolerances, failure_taxonomy, diversity}.py`
- `shared/eval/levels/{level0_parse, level1_compile}.py`
- `shared/eval/metrics/pass_at_k.py`
- `shared/eval/adapter_cluster1.py`
- `shared/modal_harness/{app, images, volumes, secrets, runtime, errors, compile, compile_runner}.py`
- `cluster1/data/kernels/{elementwise_relu, reduction_softmax, matmul_tiled_gemm}.py`
- `cluster1/data/prompts/prompt_contract.py`
- `cluster2/` package skeleton

New implementation surfaces:
- `cluster2/contracts/phase_minus1_manifest.json`
- `cluster2/contracts/cluster2_plan_hash.txt`
- `cluster2/contracts/frozen_cluster1_artifacts_manifest.json`
- `shared/eval/content_hashes.py`
- `shared/eval/run_config.py`, `shared/eval/pipeline.py`
- `shared/eval/correctness_shapes.py`, `shared/eval/reference_runner.py`
- `shared/eval/levels/level0_ast_sanitizer.py`, `shared/eval/levels/level2_correctness.py`
- `shared/eval/aggregation.py`
- `shared/eval/metrics/{repair, coverage, equal_attempts}.py`
- `shared/eval/reporting/{tables, coverage_table}.py`
- `cluster2/modal/{schemas, generation, correctness, correctness_runner}.py`
- `cluster2/generation/modal_generate_c2.py`
- `cluster2/replay/cluster1_controls.py`
- `cluster2/validation/modal_correctness_check.py`
- `cluster2/feedback/{trace, prompts, repair_loop}.py`
- `cluster2/results/{dataclass, logger}.py`
- `cluster2/experiments/run_cluster2_modal.py`
- focused `cluster2/tests/*` and `shared/tests/*`

Cluster 1 source files are not implementation write surfaces. If an unforeseen need to edit Cluster 1 appears, stop and request a contract amendment.

---

## 3. Replay-Control Mapping Rules

Frozen none and G rows are mapped into Cluster 2 control cells from Phase -1 manifests.

Required mapping fields per frozen row:
- `kernel_class`
- `dtype`
- `grammar_active`
- `seed` or `generation_index`
- `attempt_index`
- `source`
- `unique_solution_hash`
- `model_id`
- `model_revision`, if available
- `tokenizer_revision`, if available
- Cluster 1 artifact path
- Cluster 1 row SHA256 or source SHA256

Mapping rule:

For each Cluster 2 cell `(kernel_class, dtype, condition)`, replay exactly `N` frozen source candidates from the corresponding Cluster 1 artifact:
- condition `none` uses `grammar_active=False`
- condition `G` uses `grammar_active=True`

`N = repair_budget + 1` for the compared generated conditions. The default paper value is `N=6`.

Frozen rows are selected deterministically by `(kernel_class, dtype, grammar_active, seed/generation_index)` and mapped to `attempt_index in [0, N-1]`. If the frozen artifact already stores compatible seeds, use them. If it stores only row order, Phase -1 assigns stable generation indexes and records the mapping in `cluster2/contracts/frozen_cluster1_artifacts_manifest.json`.

If fewer than `N` valid frozen candidates exist for a cell, mark the cell:

```text
coverage_failure_missing_frozen_control
```

Do not regenerate.

Replay controls are evaluated by the current C2 Level 0/1/2 evaluator. Their generation hash comes from the frozen Cluster 1 artifact/source hash. Their eval hash comes from the current C2 eval pipeline hash.

---

## 4. Operational Definitions

- **Generated row:** a candidate row whose source came from new C2 model generation (`C` or `G+C`).
- **Replay control row:** a candidate row whose source came from frozen C1 artifacts (`none` or `G`).
- **Covered cell:** a `(kernel, dtype, base_seed, condition)` cell for which the locked spec exists, the C2 shape metadata is supported, repair/eval shape sets can be generated, reference execution succeeds, and the evaluator attempts the candidate source(s).
- **Coverage failure:** a pre-candidate inability to evaluate the cell, including `coverage_failure_missing_frozen_control`.
- **Infrastructure failure:** Modal, GPU, image, serialization, schema, filesystem, timeout, or harness failure not attributable to generated source quality.
- **Candidate failure:** parse, signature, sanitizer, compile, runtime, output-shape, NaN/Inf, or numeric mismatch failure.
- **Eval success:** one candidate source has `functional_success=True`, meaning it passes both repair and eval shape sets under pinned tolerance rules.
- **Repair success / convergence:** a generated condition reaches eval success at any attempt before budget exhaustion.
- **Replay pass-within-N:** a replay control has at least one mapped frozen candidate pass within the `N` replayed candidates.
- **Dtype/device/random input seed:** dtype comes from config; correctness runs on L4; input factories derive deterministic seeds from `(kernel_name, dtype, shape, base_seed, attempt_index, split)`.

---

## 5. Phase-by-Phase Execution

Each phase is one commit. Linear; do not start phase N+1 until phase N's DoD is green.

### Phase -1 - Freeze + Pre-registration + Tracked Manifests

**Goal:** before Cluster 2 implementation, freeze Cluster 1 and record enough committed metadata to reproduce replay controls and detect drift. No Cluster 1 code is edited.

**Owner write set:**
- git tags: `cluster1-freeze-2026-05-12`, `cluster2-preregistration-2026-05-12`
- `cluster2/contracts/phase_minus1_manifest.json`
- `cluster2/contracts/cluster2_plan_hash.txt`
- `cluster2/contracts/frozen_cluster1_artifacts_manifest.json`
- optional untracked operational logs under `outputs/cluster1/` and `outputs/cluster2/`

**Tasks:**

1. Record the current git commit, dirty status, and freeze tag.
2. Compute and commit the SHA256 of this v5 plan in `cluster2/contracts/cluster2_plan_hash.txt`.
3. Record hashes of `.contracts/agentic/cluster1_contract.md` and `.contracts/agentic/cluster1_plan.md` in `phase_minus1_manifest.json`.
4. Identify frozen Cluster 1 JSONL artifacts for:
   - baseline `none` (`grammar_active=False`)
   - grammar-active `G` (`grammar_active=True`)
5. Compute artifact SHA256s, row SHA256s or source SHA256s, row counts, condition counts, dtypes, kernel classes, seeds/generation indexes, and replay mappings.
6. Record model/tokenizer resolved revisions if available in the frozen artifacts. If unavailable, record `unavailable_in_frozen_cluster1_artifact`; comparisons may proceed only with this limitation disclosed.
7. Record:
   - prompt hashes for locked specs and dtypes,
   - `GenerationResult` field list hash,
   - `KERNEL_SPECS` keys/order,
   - `--kernel-class all` expansion row count,
   - `RemoteGenerator.generate_one` source hash,
   - Cluster 1 model-loading source hash,
   - `DEFAULT_GENERATION_GPU`,
   - Cluster 1 Modal image/source manifests,
   - Cluster 1 analyzer replay result over frozen artifacts.
8. Pre-register the statistical analysis plan inside `phase_minus1_manifest.json`:
   - primary comparison: `C` vs frozen `none` replay control,
   - secondary comparison: `G+C` vs frozen `G` replay control,
   - estimator: per-cell Bernoulli with 10000 bootstrap resamples over cells,
   - alpha = 0.05, two-sided,
   - no multiple comparison correction because only one primary comparison,
   - paper sample size: `n=20`, dtypes `(fp32, fp16, bf16)`.
9. If frozen controls are missing or invalid, mark Phase -1 failed. Do not regenerate none/G unless the user explicitly invalidates the freeze and approves a contract amendment.

**Required pre-Phase-0 gates:**
- Cluster 1 unit suite green.
- Cluster 1 boundary scanner green.
- Existing Cluster 1 JSONL analyzer reads frozen artifacts.
- `GenerationResult` unchanged.
- Prompt rendering unchanged.
- `KERNEL_SPECS` keys/order unchanged.
- `--kernel-class all` behavior unchanged.
- `DEFAULT_GENERATION_GPU == "L40S"`.
- `RemoteGenerator.generate_one` hash captured.
- Existing Modal image/source manifest captured.
- Frozen control artifacts have enough rows for planned paper `N=6` replay per `(kernel_class, dtype, condition)` cell, or the missing cells are explicitly pre-registered as `coverage_failure_missing_frozen_control`.

**DoD:** tracked manifests exist, freeze/pre-registration tags are created, all gates above are logged pass/fail, and failures block Phase 0.

---

### Phase 0 - Cluster 2 Contract + Content Hashes + C2 Shape Metadata

**Goal:** publish the Cluster 2 contract, add the content-hash module, and define C2-side shape metadata for the locked three. No Cluster 1 files are edited.

**Owner write set:**
- `.contracts/agentic/cluster2_contract.md`
- `cluster2/contracts/phase_minus1_manifest.json` updates only if Phase -1 manifest format needs a non-semantic correction
- `shared/eval/content_hashes.py`
- `shared/eval/correctness_shapes.py`
- `cluster2/README.md`
- `shared/tests/test_content_hashes.py`
- `shared/tests/test_correctness_shapes_metadata.py`

**Locked decisions:**
- Shape metadata is a C2-side mapping keyed by the three locked Cluster 1 specs:
  - ReLU: `shape_arity=1`, `shape_pattern="ND"`
  - Softmax: `shape_arity=2`, `shape_pattern="RxC"`
  - GEMM: `shape_arity=3`, `shape_pattern="MNK"`
- No `KernelSpec` fields are added.
- No `HELD_OUT_KERNEL_SPECS` registry is added.
- `shared/modal_harness/generation.py`, `shared/modal_harness/schemas.py`, and `shared/modal_harness/smoke.py` remain untouched.

**Content-hash API:**

```python
def module_content_sha256(module_path: str) -> str: ...
def function_source_sha256(fn: Callable) -> str: ...
def file_sha256(path: str | Path) -> str: ...
def collect_eval_pipeline_hashes() -> dict[str, str]: ...
def collect_c2_generation_hashes(condition: str) -> dict[str, str]: ...
def collect_cluster1_frozen_generation_hashes(condition: str, manifest_path: str) -> dict[str, str]: ...
def collect_external_pins() -> dict[str, str]: ...
def collect_modal_source_manifest(paths: list[str]) -> dict[str, str]: ...
```

Modal image/source manifests must include source-content hashes, not only serialized image build instructions.

**DoD:** tests pass; Phase -1 manifest still validates; Cluster 1 fingerprint gates remain green.

---

### Phase 1 - `RunConfig` + `run_eval_pipeline` Skeleton

**Owner write set:** `shared/eval/run_config.py`, `shared/eval/pipeline.py`, `shared/eval/__init__.py`, `shared/tests/test_eval_run_config.py`, `shared/tests/test_eval_pipeline.py`.

`RunConfig` includes:

```python
condition: Literal["none", "G", "C", "G+C"]
source_class: Literal["generated_row", "replay_control_row"]
generation_mode: Literal[
    "replay_control",
    "new_c2_generation",
    "new_c2_generation_with_G_adapter",
]
scale_tier: Literal["smoke", "development", "paper"]
repair_budget: int
equal_attempts_n: int
enable_ast_sanitizer: bool
dtypes: tuple[str, ...]
model_id: str
model_revision: str
tokenizer_revision: str
modal_generation_gpu: str | None
modal_eval_gpu: str
```

Routing invariants:
- `none` and `G`: `source_class="replay_control_row"`, `generation_mode="replay_control"`, `modal_generation_gpu is None`.
- `C`: `source_class="generated_row"`, `generation_mode="new_c2_generation"`.
- `G+C`: `source_class="generated_row"`, `generation_mode="new_c2_generation_with_G_adapter"`.
- `equal_attempts_n = repair_budget + 1`.

**DoD:** tests pass; Phase -1 fingerprint gates remain green.

---

### Phase 2 - Procedural Correctness Shapes + Reference Wrapper

**Owner write set:** `shared/eval/correctness_shapes.py`, `shared/eval/reference_runner.py`, `shared/tests/test_correctness_shapes.py`, `shared/tests/test_reference_runner.py`.

Implement split repair/eval shape sets for `{ND, RxC, MNK}`, input factories, memory caps, and isolated KernelBench reference execution. No broad KernelBench generalization is added.

**DoD:** tests pass; Phase -1 fingerprint gates remain green.

---

### Phase 3 - AST Sanitizer + Folded Surface Scan

**Owner write set:** `shared/eval/levels/level0_ast_sanitizer.py`, `shared/eval/levels/__init__.py`, `shared/eval/failure_taxonomy.py`, `shared/tests/test_eval_level0_ast_sanitizer.py`, `shared/tests/test_failure_taxonomy.py`.

Implement allowlist-only launcher checks, alias handling, direct symbol import handling, `getattr` bypass rejection, and folded generated-code surface scan. Add `F0_SURFACE_VIOLATION`.

No profiler/timing/speedup surfaces are added.

**DoD:** positive fixtures pass, negative fixtures reject with line numbers, runtime stays below 50 ms for fixtures, and Phase -1 fingerprint gates remain green.

---

### Phase 4 - Level 2 Correctness + Pipeline Wiring

**Owner write set:** `shared/eval/levels/level2_correctness.py`, `shared/eval/pipeline.py`, `shared/tests/test_eval_level2_correctness.py`, `shared/tests/test_eval_pipeline_with_level2.py`.

Level 2 uses both repair and eval shape sets. `functional_success=True` requires both. Feedback may include repair-set shape/diff data only. Eval-set failures after repair-set success use the generic Level 2 failure message.

**DoD:** tests pass; private eval values never appear in feedback; Phase -1 fingerprint gates remain green.

---

### Phase 5 - C2 Modal Schemas

**Owner write set:** `cluster2/modal/schemas.py`, `cluster2/tests/test_modal_schemas.py`.

Define:
- `EvalIdentity`
- `RemoteC2GenerationRequest`
- `RemoteC2GenerationResult`
- `RemoteCorrectnessRequest`
- `RemoteCorrectnessResult`

`RemoteC2GenerationRequest` accepts only `C` and `G+C`; it rejects `none`, `G`, and all `P` modes. Cluster 1 schemas are untouched.

Expected sidecar generation modes:

```json
{"none": {"generation_mode": "replay_control"}}
{"G": {"generation_mode": "replay_control"}}
{"C": {"generation_mode": "new_c2_generation"}}
{"G+C": {"generation_mode": "new_c2_generation_with_G_adapter"}}
```

**DoD:** tests pass; imports are cheap; Phase -1 fingerprint gates remain green.

---

### Phase 6 - C2 Remote Correctness Modal Function

**Owner write set:** `cluster2/modal/correctness.py`, `cluster2/modal/correctness_runner.py`, `cluster2/validation/modal_correctness_check.py`, `cluster2/tests/test_modal_correctness_check.py`.

Remote correctness uses shared image/app helpers without modifying shared Cluster 1 Modal entry points. The Modal function runs on L4, spawns a subprocess, sets determinism flags, runs Level 2, and returns eval-pipeline hashes plus external pins.

No `shared/modal_harness/smoke.py` edits are allowed. Smoke commands call C2 modules directly.

**DoD:** tests pass; smoke commands documented; Phase -1 fingerprint gates remain green.

---

### Phase 7 - C2 Modal Generation Isolated from Cluster 1

**Owner write set:** `cluster2/modal/generation.py`, `cluster2/generation/modal_generate_c2.py`, `cluster2/tests/test_modal_generation_c2.py`.

Implement C2 generation in `cluster2/modal/generation.py`. Do not add `generate_one_c2` to `shared/modal_harness/generation.py`.

Rules:
- `C` uses C2 generation with `grammar_active=False`.
- `G+C` uses C2 generation with `grammar_active=True`, `grammar_variant="template_upper_bound"`, and the frozen G grammar/loader/constrained-decoding behavior under byte-hash gates.
- C2 model/tokenizer loading uses explicit `model_revision` and `tokenizer_revision`.
- `G+C` must compile/load grammar using the tokenizer path/revision actually used by the C2 generation path. Do not modify the Cluster 1 grammar loader to achieve this; the C2 adapter must supply the correct tokenizer identity while the frozen loader remains byte-identical.
- Cluster 1 `RemoteGenerator.generate_one`, `load_model`, schemas, and defaults are not modified.
- Phase -1 hashes for G grammar assets and relevant generation helpers must match before any `G+C` generation call.

**Tests:**
- `test_c2_generation_request_rejects_none_and_g`
- `test_c2_generation_passes_l4_explicitly`
- `test_c2_generation_passes_model_and_tokenizer_revisions`
- `test_g_plus_c_uses_template_upper_bound`
- `test_remote_generator_generate_one_hash_matches_phase_minus_1`
- `test_shared_modal_generation_file_untouched`
- `test_shared_modal_schemas_file_untouched`

**DoD:** tests pass; no existing Cluster 1 Modal file changed; Phase -1 fingerprint gates remain green.

---

### Phase 8 - Feedback Prompts + Trace Summaries

**Owner write set:** `cluster2/feedback/trace.py`, `cluster2/feedback/prompts.py`, `cluster2/tests/test_feedback_prompts.py`, `cluster2/tests/test_feedback_trace.py`.

Feedback is deterministic per failure code. Eval-set shape values and diff values never appear in prompts. Forbidden terms include `speedup`, `fast@`, `nsight`, `ncu`, `nvml`, `compute-sanitizer`, `profil`, `benchmark`, `RL`, `GRPO`, `TRL`, `LLVM`, `PTX`, `C++ traceback`, `eval_shape_set`, `hidden`, `private`, `edge cases`, and `extra shapes`.

No token sidecar is added.

**DoD:** tests pass; Phase -1 fingerprint gates remain green.

---

### Phase 9 - Repair Loop

**Owner write set:** `cluster2/feedback/repair_loop.py`, `cluster2/tests/test_repair_loop.py`.

Sequential orchestration only. Iteration 0 plus up to 5 repairs. Stop on first `functional_success=True`. Generation seed for generated attempt `i` is `base_seed * 10 + i`.

The repair loop is used only for `C` and `G+C`.

**DoD:** tests pass without Modal/torch/triton; Phase -1 fingerprint gates remain green.

---

### Phase 10 - Result Builder + Logger + Content Hash Sidecars

**Owner write set:** `cluster2/results/dataclass.py`, `cluster2/results/logger.py`, `cluster2/tests/test_results_logger.py`.

Primary JSONL rows include:
- condition,
- source_class (`generated_row` or `replay_control_row`),
- generation_mode,
- attempt_index,
- cell identity,
- source hash,
- eval result,
- compact trace summary for generated repair conditions.

Content hash sidecars separate:
- invariant eval-pipeline hashes,
- C2 generation hashes for generated rows,
- frozen Cluster 1 generation hashes for replay controls,
- external pins.

Full trace sidecars and private per-shape eval diff sidecars are optional diagnostics and are not implementation blockers. No token sidecar is added. Cluster 1 `GenerationResult` and Cluster 1 JSONL schemas are unchanged.

C2 JSONL rows must contain no timing, profiling, speedup, or performance fields.

`--append` is not supported. Logger supports new output writes and hash-checked resume only.

**DoD:** tests pass; Phase -1 fingerprint gates remain green.

---

### Phase 11 - Cluster 2 Runner CLI + Replay-Control Adapter

**Owner write set:** `cluster2/experiments/run_cluster2_modal.py`, `cluster2/replay/cluster1_controls.py`, `cluster2/tests/test_run_cluster2_modal.py`, `cluster2/tests/test_replay_controls.py`.

**Goal:** one runner owns all four conditions while routing generation correctly.

**CLI:**

```bash
modal run -m cluster2.experiments.run_cluster2_modal \
  --condition C|G+C|none|G|both|all \
  --kernel-class elementwise|reduction|matmul|all \
  --scale-tier smoke|development|paper \
  --n 1..20 \
  --frozen-cluster1-manifest cluster2/contracts/frozen_cluster1_artifacts_manifest.json \
  --model-id Qwen/Qwen2.5-Coder-7B-Instruct-AWQ \
  --model-revision <sha> \
  --tokenizer-revision <sha> \
  --grammar-variant template_upper_bound \
  --dtypes fp32[,fp16,bf16] \
  --temperature 0.2 \
  --max-new-tokens 1024 \
  --repair-budget 5 \
  --modal-generation-gpu L4 \
  --modal-eval-gpu L4 \
  --output outputs/cluster2/<name>.jsonl \
  --overwrite|--resume
```

For replay-only `none` and `G`, `--modal-generation-gpu`, `--temperature`, `--max-new-tokens`, and revision flags are accepted only for run metadata/comparison validation; no generation call may occur.

**Per-condition behavior:**
- `C`: generate/evaluate/repair through the C2 repair loop.
- `G+C`: generate/evaluate/repair through the C2 repair loop with frozen G adapter.
- `none`: load frozen `grammar_active=False` rows, convert them into `Cluster2EvalRow`-compatible replay candidates, and evaluate through C2 Level 0/1/2.
- `G`: load frozen `grammar_active=True` rows, convert them into replay candidates, and evaluate through C2 Level 0/1/2.

**No-regeneration gate:**
During Cluster 2 runs, conditions `none` and `G` must not call any model generation function. Enforce by:
- explicit runner routing,
- mock/spying tests,
- log assertion that no Modal generation call was made for `none` or `G`,
- required sidecar field `"generation_mode": "replay_control"` for `none` and `G`.

If fewer than `N` valid frozen candidates exist for a replay cell, emit `coverage_failure_missing_frozen_control` and do not regenerate.

**Tests:**
- `test_runner_routes_none_to_replay_adapter`
- `test_runner_routes_g_to_replay_adapter`
- `test_runner_never_calls_generation_for_none`
- `test_runner_never_calls_generation_for_g`
- `test_runner_routes_c_to_c2_generation`
- `test_runner_routes_gc_to_c2_generation_with_g_adapter`
- `test_replay_adapter_maps_exactly_n_candidates`
- `test_replay_adapter_marks_missing_rows_coverage_failure`
- `test_runner_records_generation_mode_sidecar`
- `test_runner_resume_rejects_hash_mismatch`
- `test_runner_uses_l4_explicitly_for_c2_modal_calls`

**DoD:** tests pass; `python -c "import cluster2.experiments.run_cluster2_modal"` loads cheaply; Phase -1 fingerprint gates remain green.

---

### Phase 12 - Modal Smoke Sequence

**Goal:** verify integrated C2 paths. No new code.

Smoke requirements:
- C2 schemas import from `cluster2.modal.schemas`.
- C2 correctness smoke calls `cluster2.modal.correctness`.
- C2 generation smoke calls `cluster2.modal.generation` for `C` and `G+C`.
- Replay smoke runs `none` and `G` through the main runner using `--frozen-cluster1-manifest`.
- Modal dashboard shows L4 for C2 generation/eval calls.
- Logs assert zero model-generation calls for replay controls.

**DoD:** smoke commands pass; replay controls evaluate frozen sources only; Phase -1 fingerprint gates remain green.

---

### Phase 13 - Aggregation + Coverage + Convergence Metrics

**Owner write set:** `shared/eval/aggregation.py`, `shared/eval/metrics/{repair, coverage, equal_attempts}.py`, `shared/eval/reporting/{tables, coverage_table}.py`, `shared/tests/test_aggregation.py`.

Aggregation understands two source classes:

```text
generated_row
replay_control_row
```

For replay controls:
- generation hash comes from frozen Cluster 1 artifact/source hash,
- eval hash comes from the current C2 eval pipeline hash.

For generated `C` and `G+C` rows:
- generation hash comes from the C2 generation pipeline hash,
- eval hash comes from the current C2 eval pipeline hash.

Aggregation compares:
- eval hashes across all compared rows,
- generation hashes only within comparable generation-source classes,
- frozen Cluster 1 hashes against the Phase -1 manifest.

Do not reject replay controls simply because their generation hash differs from C2 generated rows.

Metrics:
- `compute_pass_at_1_initial(rows)` only for iteration-0 results.
- `compute_convergence_rate(rows)` per cell for generated conditions.
- `compute_pass_rate_within_n(rows)` per cell for replay controls.
- `compute_lift_with_bootstrap_ci(rows_treatment, rows_control)` with bootstrap over cells.
- `compute_coverage(coverage_status_records)`.

**DoD:** tests pass; Phase -1 fingerprint gates remain green.

---

### Phase 14 - Boundary Tests + Import Discipline

**Owner write set:** `cluster2/tests/test_cluster2_boundary.py`, `shared/tests/test_eval_imports.py`.

Required checks:
- no profiler/timing/speedup strings in Cluster 2,
- no heavy imports at Cluster 2 module top,
- `RemoteGenerator.generate_one` hash matches Phase -1,
- shared Modal generation/schema/smoke file hashes match Phase -1,
- Cluster 1 request schemas still reject non-Cluster-1 modes,
- `DEFAULT_GENERATION_GPU == "L40S"`,
- replay conditions never invoke C2 generation in spy tests,
- C2 runner passes `L4` explicitly for new C2 Modal calls.

**DoD:** tests pass; Phase -1 fingerprint gates remain green.

---

### Phase 15 - Development Scale on Locked Three

**Goal:** development-scale Cluster 2 on the three locked archetypes.

**Behavior:**
- `C` and `G+C` are generated/evaluated.
- `none` and `G` are replayed/evaluated.
- Report convergence lift against replay controls.

Example commands:

```bash
modal run -m cluster2.experiments.run_cluster2_modal \
  --condition C --kernel-class all --scale-tier development --n 3 \
  --dtypes fp32 --model-id Qwen/Qwen2.5-Coder-7B-Instruct-AWQ \
  --model-revision <sha> --tokenizer-revision <sha> \
  --modal-generation-gpu L4 --modal-eval-gpu L4 \
  --frozen-cluster1-manifest cluster2/contracts/frozen_cluster1_artifacts_manifest.json \
  --output outputs/cluster2/cluster2_development_C_k3_n3_qwen7b_20260512.jsonl

modal run -m cluster2.experiments.run_cluster2_modal \
  --condition G+C --kernel-class all --scale-tier development --n 3 \
  --dtypes fp32 --grammar-variant template_upper_bound \
  --model-id Qwen/Qwen2.5-Coder-7B-Instruct-AWQ \
  --model-revision <sha> --tokenizer-revision <sha> \
  --modal-generation-gpu L4 --modal-eval-gpu L4 \
  --frozen-cluster1-manifest cluster2/contracts/frozen_cluster1_artifacts_manifest.json \
  --output outputs/cluster2/cluster2_development_GC_k3_n3_qwen7b_20260512.jsonl

modal run -m cluster2.experiments.run_cluster2_modal \
  --condition none --kernel-class all --scale-tier development --n 3 \
  --dtypes fp32 --modal-eval-gpu L4 \
  --frozen-cluster1-manifest cluster2/contracts/frozen_cluster1_artifacts_manifest.json \
  --output outputs/cluster2/cluster2_development_none_replay_k3_n3_qwen7b_20260512.jsonl

modal run -m cluster2.experiments.run_cluster2_modal \
  --condition G --kernel-class all --scale-tier development --n 3 \
  --dtypes fp32 --modal-eval-gpu L4 \
  --frozen-cluster1-manifest cluster2/contracts/frozen_cluster1_artifacts_manifest.json \
  --output outputs/cluster2/cluster2_development_G_replay_k3_n3_qwen7b_20260512.jsonl
```

**DoD:** development commands complete; no generation calls for `none`/`G`; summary reports lift + CI + coverage context; Phase -1 fingerprint gates remain green.

---

### Phase 15P - Paper-Scale Locked-Three Run (`n=20`)

**Goal:** produce paper-scale evidence for the locked thesis claim using the main runner.

**Behavior:**
- `C` and `G+C` use new generation/repair.
- `none` and `G` use frozen replay controls.
- If frozen controls lack enough rows for `n=20`, fail with `coverage_failure_missing_frozen_control`.
- Do not regenerate `none` or `G`.

Command shape:

```bash
modal run -m cluster2.experiments.run_cluster2_modal \
  --condition all --kernel-class all --scale-tier paper --n 20 \
  --dtypes fp32,fp16,bf16 \
  --model-id Qwen/Qwen2.5-Coder-7B-Instruct-AWQ \
  --model-revision <sha> --tokenizer-revision <sha> \
  --grammar-variant template_upper_bound \
  --modal-generation-gpu L4 --modal-eval-gpu L4 \
  --frozen-cluster1-manifest cluster2/contracts/frozen_cluster1_artifacts_manifest.json \
  --output outputs/cluster2/paper_20260512/cluster2_paper_locked_three.jsonl \
  --overwrite
```

**Tests:**
- `test_main_runner_supports_paper_scale_n20`
- `test_paper_scale_requires_locked_kernel_set`
- `test_paper_scale_fails_missing_frozen_controls_without_regeneration`
- `test_paper_scale_expected_rows_for_locked_three_dtypes_n20`

**DoD:** paper-scale outputs exist; aggregation summary reports primary `C` vs frozen `none` replay-control lift with 95% CI; secondary `G+C` vs frozen `G` replay-control comparison is labeled secondary; Phase -1 fingerprint gates and hash-class gates pass.

---

### Phase 16 - Deferred Held-Out Extension

Held-out generalization and held-out specs under `cluster1/` are deferred. They are not part of Cluster 2 implementation, DoD, paper-scale evidence, or Phase -1 pre-registration.

Any future held-out work requires a separate contract amendment and must not be reported as part of the Cluster 2 thesis claim.

---

## 6. Stop Conditions

Pause and request a contract amendment if any work requires:

- regenerating `none` or `G` controls,
- calling any model generation function for `none` or `G`,
- modifying any existing Cluster 1 generation, grammar, prompt, schema, result, runner, or Modal source file,
- editing `RemoteGenerator.generate_one` or Cluster 1 model-loading defaults,
- adding `generate_one_c2` to `shared/modal_harness/generation.py`,
- adding C2 schemas to `shared/modal_harness/schemas.py`,
- editing `shared/modal_harness/smoke.py`,
- changing `DEFAULT_GENERATION_GPU`,
- adding held-out specs under `cluster1/`,
- broadening the thesis claim beyond the three locked archetypes,
- adding broad KernelBench generalization, a K=30 random sample, Cluster 3 infrastructure, token-matched controls, profiler/timing/speedup fields, or universal shape abstraction expansion,
- comparing rows with mismatched invariant eval hashes or external pins,
- rejecting replay controls solely because their generation hashes differ from C2 generated rows.

---

## 7. Definition of Done - Cluster 2 Complete

Cluster 2 is complete when:

1. Phase -1 tracked manifests under `cluster2/contracts/` exist and record the v5 plan hash, Cluster 1 contract/plan hashes, frozen C1 artifact hashes, row counts, replay mapping, prompt hashes, `GenerationResult` hash, `KERNEL_SPECS` keys/order, `RemoteGenerator.generate_one` hash, `DEFAULT_GENERATION_GPU`, model/tokenizer revisions if available, and Cluster 1 Modal image/source manifests.
2. Phases 0-15P are merged. Phase 16 remains deferred.
3. `pytest shared/tests cluster1/tests cluster2/tests -v` is green throughout.
4. C2 Modal generation is isolated under `cluster2/modal/`; existing Cluster 1 Modal files are unchanged.
5. `C` and `G+C` invoke new generation on L4; `none` and `G` are replay-only and invoke no generation.
6. Development scale reports convergence lift against replay controls.
7. Paper scale uses the main runner with `--scale-tier paper --n 20`; no separate paper runner exists.
8. Aggregation compares eval hashes globally, generation hashes only within comparable generation-source classes, and frozen C1 hashes against Phase -1 manifests.
9. `RemoteGenerator.generate_one` remains byte-identical to Phase -1.
10. The defended claim is exactly:

    > Under fixed prompts, fixed model identity, and matched generation attempts (`C` budget 6 vs 6 frozen `none` replay candidates), correctness-feedback control `C` improved Level 2 convergence rate by **`Z` pp** (95% bootstrap CI [`a`, `b`] over cells) on three representative Triton kernel archetypes (ReLU/pointwise, Softmax/reduction, GEMM/tiled-matmul) drawn from KernelBench Level 1. Equal-attempts matches candidate-source count, not token cost, wall time, or GPU cost. If frozen replay controls contain resolved model/tokenizer revisions, those revisions are reported; otherwise, unavailable replay-control revisions are disclosed and not claimed as pinned.

No Cluster 3 performance infrastructure, timing/profiling, speedup machinery, token-matched controls, or held-out generalization claim is part of Cluster 2 DoD.

---

## 8. Phase Index

| Phase | Deliverable |
|---|---|
| -1 | Freeze + tracked manifests + frozen replay mapping |
| 0 | Contract + content hashes + C2-side shape metadata |
| 1 | `RunConfig` + gated eval pipeline |
| 2 | Procedural shapes + reference wrapper |
| 3 | AST sanitizer + folded surface scan |
| 4 | Level 2 correctness |
| 5 | C2 Modal schemas under `cluster2/modal/` |
| 6 | C2 remote correctness |
| 7 | C2 remote generation under `cluster2/modal/` |
| 8 | Feedback prompts + trace summaries |
| 9 | Repair loop |
| 10 | Result builder + logger + content hash sidecars |
| 11 | Main runner + replay-control adapter |
| 12 | Modal smoke sequence |
| 13 | Aggregation + coverage + convergence metrics |
| 14 | Boundary tests + import discipline |
| 15 | Development scale on locked three |
| 15P | Paper-scale locked-three run with main runner |
| 16 | Deferred held-out extension, not implementation-critical |

---

## 9. Drift-Detection Contract

At the end of every phase touching `shared/`, `cluster2/modal/`, or any Cluster 1-adjacent import path:

1. Recompute Phase -1 source hashes for:
   - `RemoteGenerator.generate_one`,
   - Cluster 1 model-loading defaults,
   - Cluster 1 grammar files,
   - Cluster 1 prompt contract,
   - shared Modal generation/schema/smoke files.
2. Recompute Cluster 1 Modal image/source manifests.
3. Recompute frozen artifact hashes for replay controls.
4. Compare against `cluster2/contracts/phase_minus1_manifest.json` and `cluster2/contracts/frozen_cluster1_artifacts_manifest.json`.

Any mismatch blocks the phase unless a contract amendment explicitly invalidates and replaces the freeze. Mismatches never authorize automatic `none` or `G` regeneration.

---

## 10. What v5 Changes vs v4

| v4 issue | v5 resolution |
|---|---|
| `none` and `G` equal-attempt controls required fresh generation | Replaced with replay controls from frozen C1 artifacts. |
| `generate_one_c2` added beside `generate_one` | Removed. C2 generation lives under `cluster2/modal/generation.py`. |
| C2 schemas added to shared Modal schemas | Removed. C2 schemas live under `cluster2/modal/schemas.py`. |
| `shared/modal_harness/smoke.py` edited for fingerprints/smoke | Removed. Phase -1 uses tracked manifests; C2 smoke calls C2 modules directly. |
| `.contracts/agentic/` and `outputs/` ignored but treated as reproducible state | Fixed with tracked manifests under `cluster2/contracts/`. |
| Held-out Phase 16 and held-out specs touched `cluster1/` | Deferred out of implementation-critical path. No held-out `cluster1/` specs. |
| Separate paper runner | Removed. Main runner supports `--scale-tier paper --n 20`. |
| `--append` output mode | Removed. Only `--overwrite` and hash-checked `--resume`. |
| Modal image digest could miss source drift | Source-content manifests are required. |
| Hash comparison risked rejecting valid replay controls | Aggregation compares generation hashes only within comparable source classes. |

---

## 11. Honest Limits

- The thesis claim is defended on three representative archetypes, not on KernelBench Level 1 generally and not on Triton kernels generally.
- Replay controls inherit the frozen Cluster 1 artifact quality and metadata. If model/tokenizer revisions are unavailable in frozen artifacts, that limitation is disclosed rather than repaired by regeneration.
- Equal-attempts matches candidate-source count, not token cost, wall-time compute, or GPU cost.
- LLM generation is not bit-reproducible beyond recorded model/tokenizer revisions, prompt, temperature, seed, and environment pins. The plan avoids unnecessary regeneration by replaying Cluster 1 controls.
- Future held-out or generalization work requires a separate scope decision.
