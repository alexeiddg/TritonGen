# Cross-Cluster Pipeline Compatibility Audit

Date: 2026-05-18
Scope: read-only audit of Cluster 1 none, Cluster 1 G/template diagnostic, Cluster 1 task-agnostic G, Cluster 2 C, and Cluster 2 G+C comparability.

## 1. Executive summary

Recommendation: **BLOCKED_PENDING_INVESTIGATION**.

Direct comparison of existing rows in one factorial/subset analysis is not currently established. The locked KernelSpecs, reference code route, tolerance table, shared compile adapter, task-agnostic grammar file, and paired seed contract are largely aligned. The blockers are elsewhere:

- Existing Cluster 1 n=20 artifacts are legacy row schemas: no `condition`, `schema_version`, `grammar_path`, `grammar_sha`, `grammar_valid`, `stop_reason`, `model_revision`, `tokenizer_revision`, or canonical `failure_code` in the JSONL rows.
- The frozen template G diagnostic is not task-agnostic G. It routes to `template_upper_bound`, while the primary G+C path defaults to `task_agnostic`.
- Cluster 2 remote correctness currently runs Level 2 correctness directly over CUDA, and its loader maps syntax/import/launcher failures through Level 2 runtime failure behavior rather than the Cluster 1 Level 0/Level 1 compile taxonomy.
- Local revalidation of the baseline through current strict compile/eval is unsafe under the task rules because Cluster 1 dummy-launch compile uses CUDA tensors and C2 remote correctness uses CUDA/Modal. Existing diagnostic artifacts are useful evidence, but this audit did not rerun those GPU-backed paths.

Question classifications: **7 COMPATIBLE**, **7 INCOMPATIBLE_REQUIRES_FIX**, **4 UNKNOWN_REQUIRES_INVESTIGATION**, **0 NOT_APPLICABLE**.

Baseline regeneration does not appear automatically required from available evidence, but **baseline regeneration vs revalidation remains unresolved** because the required current GPU-backed revalidation could not be safely rerun locally. Existing diagnostic `outputs/cluster1/diagnostics/baseline_revalidation_aligned_pipeline_parse_reclassification.jsonl` reports 180/180 compile-success agreement and 0 cross-category label drift after parse reclassification, but it is an existing artifact, not a fresh run from this audit.

n=20 remains blocked for primary C/G+C paper-scale spend. The manifest explicitly marks task-agnostic G as development-only n=5 and insufficient for paper-scale primary G+C.

## 2. Artifact inventory

| artifact path | exists | rows | condition evidence | grammar variant evidence | schema version | legacy/current | notes |
|---|---:|---:|---|---|---|---|---|
| `outputs/cluster1/baseline_repaired_l4_n20.jsonl` | yes | 180 | row `condition` absent; `grammar_active=False`; manifest condition `none` | none | absent | legacy | SHA256 `1f3e004b25564f347b2fb293216d2a9589ac7aaa60728cabd1d20e40af4f4cc3`; ast parse valid rows: 0/180; compile_success true: 0/180 |
| `outputs/cluster1/final_g_l4_n20.jsonl` | yes | 180 | row `condition` absent; `grammar_active=True`; manifest condition `G` | row variant absent; manifest expected `template_upper_bound` | absent | legacy diagnostic | SHA256 `51af551433ae5180eac85cf877409a8d73b0e53fba07b40699d42024757a3d18`; not primary task-agnostic G |
| `outputs/cluster1/task_agnostic_g_all_n5_l4_rerun.jsonl` | yes | 45 | row `condition` absent; `grammar_active=True` | `task_agnostic` | absent | legacy/dev | SHA256 `0efb88886ec0abca432835e66309e232155bce55f562de385d13d8f506e55d56`; 5 rows per kernel/dtype only |
| `outputs/cluster1/task_agnostic_g_current_grammar_n5_l4.jsonl` | yes | 45 | row `condition` absent; `grammar_active=True` | `task_agnostic` | absent | legacy/dev | SHA256 `38c310329e80626c1788ab09674bc6b7a89ca3f88c280c5d87eee1c2d9d08744`; still lacks current grammar metadata row fields |
| `outputs/cluster2/smoke_none_replay_phase12.jsonl` | yes | 1 | `none` | nested replay metadata only | absent in row | smoke/current C2 row shape | replay row contains `replay_metadata` with frozen artifact/source/row hashes |
| `outputs/cluster2/smoke_G_replay_phase12.jsonl` | yes | 1 | `G` | nested replay metadata only | absent in row | smoke/current C2 row shape | replay metadata records both template and task-agnostic frozen G hashes |
| `outputs/cluster2/smoke_C_phase12.jsonl` | yes | 1 | `C` | none | absent in row | smoke/current C2 eval row | generated metadata contains `generation_seed` and code hashes but no flattened model/grammar fields |
| `outputs/cluster2/smoke_GC_phase12.jsonl` | yes | 1 | `G+C` | top-level absent; generated metadata lacks grammar path in this smoke | absent in row | smoke/current C2 eval row | generated metadata contains code hashes and seed only |
| `outputs/cluster2/c_prompt_audit_smoke.jsonl` | yes | 3 | `C` | generated metadata has `grammar_variant=None` | absent in row | smoke/current C2 eval row | 3 rows, C only |

Artifact/schema inspection command evidence: `.venv/bin/python` JSONL inspection reported the row counts and key sets above. File hashes were computed with `.venv/bin/python` and `hashlib.sha256`.

## 3. Block 1 - KernelSpec consistency

### Question 1 - KernelSpec sources of truth

Classification: **COMPATIBLE**.

| archetype | KernelBench problem ID | problem name | reference code SHA256 | Cluster 1 prompt source | Cluster 1 validator source | Cluster 2 eval source |
|---|---:|---|---|---|---|---|
| ReLU / elementwise | 19 | `relu` | `310b0b47a42165c8e471a2671690f64228427ee40a7bbe4d45263466fea3789d` | `cluster1/data/kernels/elementwise_relu.py:61` `RELU_SPEC` | `cluster1/data/kernels/elementwise_relu.py:55` `_RELU_COMPILE_SPEC` | `shared/eval/reference_runner.py:218` `_get_locked_spec`; `shared/eval/correctness_shapes.py:58` metadata |
| Softmax / reduction | 23 | `softmax` | `fe50b14fdf7bf9b5ca24ec8a25f03ce1a3fcf5b61b89aef4ab63da83f9f26819` | `cluster1/data/kernels/reduction_softmax.py:61` `SOFTMAX_SPEC` | `cluster1/data/kernels/reduction_softmax.py:55` `_SOFTMAX_COMPILE_SPEC` | same `shared/eval/reference_runner.py:218` route |
| GEMM / matmul | 1 | `gemm` | `256e40cbdeeb9208412e25dc57e8b8738645d8aa2b285b4d8f0e1f5272d2a874` | `cluster1/data/kernels/matmul_tiled_gemm.py:64` `GEMM_SPEC` | `cluster1/data/kernels/matmul_tiled_gemm.py:58` `_MATMUL_COMPILE_SPEC` | same `shared/eval/reference_runner.py:218` route |

Evidence:

- `cluster1/data/kernels/__init__.py:6-10` maps `elementwise`, `reduction`, `matmul` to `RELU_SPEC`, `SOFTMAX_SPEC`, `GEMM_SPEC`.
- `shared/eval/reference_runner.py:57-60` loads the locked spec and checks the spec name against C2 metadata.
- `shared/eval/reference_runner.py:218-225` calls `cluster1.data.kernels.get_kernel_spec`.
- `shared/eval/correctness_shapes.py:58-80` records matching C2 problem IDs and names.
- Current source file hashes: `elementwise_relu.py` `c20819748d5397e85e7809614dbb7164b3a40736a42c699f2d71cb67eceaa517`; `reduction_softmax.py` `b08017dcf771da195a5f14ae6a3650cc2d6b2345fe29d3814e37c47e907b08b6`; `matmul_tiled_gemm.py` `e7cba41e90a065b1f70b8fe0cf8acbb8e89f2a1c2747bed88a31895c19f975e5`.

Smallest fix if incompatible: none.

### Question 2 - Shape schedules

Classification: **INCOMPATIBLE_REQUIRES_FIX**.

Cluster 1 compile/dummy-launch schedules come from `KernelSpec.shapes_by_dtype`, which calls `shared/eval/correctness_shapes.py:get_compile_shapes` at lines `238-246`. The schedules are the same for fp32/fp16/bf16:

- elementwise compile: `(32,)`, `(100,)`, `(1024,)`, `(3, 257)`, `(5, 129)`
- reduction compile: `(16, 64)`, `(33, 100)`, `(128, 1001)`, `(16384, 1)`, `(1, 16384)`
- matmul compile: `(24, 24, 24)`, `(48, 48, 48)`, `(128, 128, 64)`, `(100, 100, 100)`, `(16384, 1, 1)`

Cluster 2 correctness schedules come from `shared/eval/correctness_shapes.py:195-235` and include repair/eval split anchors plus deterministic generated shapes. The anchor split is defined at `shared/eval/correctness_shapes.py:87-112`. Example: elementwise repair starts `(1,), (32,), (100,), (1024,), (3, 257)` and eval starts `(2,), (33,), (257,), (4096,), (5, 129)`, with default `DEFAULT_SHAPES_PER_SPLIT=6` at line `30`.

The schedules are not identical: Cluster 1 compile uses 5 compile probes; Cluster 2 correctness uses 6 repair plus 6 eval shapes by default. The mismatch affects direct comparability if original Cluster 1 `compile_success` rows are analyzed beside Cluster 2 `functional_success` rows. It does not block comparability if Cluster 1 controls are replayed through the same Cluster 2 correctness path before analysis.

Smallest fix: do not compare original C1 compile-only outcomes against C2 correctness outcomes. Materialize/reuse C2 replay rows for C1 none and C1 G under the same correctness path, and label original C1 JSONLs as provenance only. Files: analysis/aggregation code and result manifests, not KernelSpec files. Expected test: aggregation rejects mixing legacy C1 compile-only rows with C2 correctness rows.

### Question 3 - PyTorch reference used by C2 correctness

Classification: **COMPATIBLE**.

Evidence:

- `shared/eval/reference_runner.py:45-55` defines `run_reference`.
- `shared/eval/reference_runner.py:57` calls `_get_locked_spec(kernel_class)`.
- `shared/eval/reference_runner.py:72-76` loads `KernelSpec.reference_code`, instantiates `Model`, and calls `model.forward`.
- `shared/eval/reference_runner.py:191-215` executes only `spec.reference_code` in an isolated module.
- The same source strings are defined in `cluster1/data/kernels/elementwise_relu.py:18-38`, `cluster1/data/kernels/reduction_softmax.py:18-38`, and `cluster1/data/kernels/matmul_tiled_gemm.py:18-38`.

Same dataset row: yes for IDs 19, 23, 1. Same function: yes, `Model.forward`. Same source hash: yes, the reference code SHA256 values in Question 1 are taken from `KernelSpec.reference_code` consumed by both Cluster 1 and Cluster 2.

Smallest fix if incompatible: none.

### Question 4 - Tolerance tables

Classification: **COMPATIBLE**.

Runtime tolerance table:

- Source: `shared/eval/tolerances.py:15-96` `TOLERANCE_TABLE`
- Loader: `shared/eval/tolerances.py:105-114` `get_tolerances`
- Caller: `shared/eval/levels/level2_correctness.py:167-170`

Mappings:

- elementwise: fp32 `1e-5/1e-5`, fp16 `1e-3/1e-3`, bf16 `1e-3/1e-3`
- reduction: fp32 `1e-4/1e-4`, fp16 `1e-2/1e-2`, bf16 `1e-2/1e-2`
- matmul: fp32 `1e-3/1e-3`, fp16 `5e-2/5e-2`, bf16 `5e-2/5e-2`

No fallback tolerance is used: `get_tolerances` indexes `TOLERANCE_TABLE[kernel_class]` and `class_table[dtype_key]`, so unknown classes/dtypes raise `KeyError`. File hash: `shared/eval/tolerances.py` `c661831f9f4b66dd055ffc9e04138056daca598d4f55ae19a95393a6091afd07`.

Smallest fix if incompatible: none.

## 4. Block 2 - Eval pipeline alignment

### Question 5 - Cluster 1 compile validator vs Cluster 2 compile validator

Classification: **COMPATIBLE** for Level 1 compile gate.

Evidence:

- Cluster 1 strict compile path: `cluster1/validation/compile_check.py:183-292`, especially `check_compiles` and `check_compiles_all_dtypes`.
- Cluster 2 Level 1 adapter: `shared/eval/levels/level1_compile.py:36-61` `check_compile_level1`.
- `shared/eval/levels/level1_compile.py:45-51` lazily imports and delegates to `cluster1.validation.compile_check.check_compiles_all_dtypes`.

Therefore Level 1 compile is not a parallel reimplementation; it wraps the Cluster 1 implementation. The adapter normalizes the result into `Level1CompileResult` at `shared/eval/levels/level1_compile.py:64-100`.

Smallest fix if incompatible: none for Level 1. Separate issue: actual C2 remote correctness does not currently call this Level 1 gate before Level 2; see Questions 6-8.

### Question 6 - Signature contract enforcement

Classification: **INCOMPATIBLE_REQUIRES_FIX**.

Cluster 1:

- `cluster1/validation/compile_check.py:193-216` runs `check_parse` and `check_signature`.
- `cluster1/validation/compile_check.py:232-242` also loads the module and compares `inspect.signature` against `CompileSpec.reference_signature`.
- `shared/eval/levels/level0_parse.py:21-55` enforces top-level launcher name, expected parameter names, and presence of a `@triton.jit` helper.

Cluster 2 Level 1 compile adapter:

- If `shared.eval.levels.level1_compile.check_compile_level1` is called, it delegates to the same C1 compile path.

Actual Cluster 2 remote correctness:

- `cluster2/modal/correctness_runner.py:67-89` calls `run_eval_pipeline` with only a `PipelineLevel2Request`.
- `shared/eval/pipeline.py:198-207` labels Level 0 and Level 1 as `deferred_phase1` unless separate code calls them.
- `cluster2/modal/correctness_runner.py:330-348` `_GeneratedSourceCandidateRunner` loads the source and only checks that the launcher attribute exists and is callable.
- Syntax/import/launcher failures are caught inside Level 2 as `F1_RUNTIME` at `shared/eval/levels/level2_correctness.py:313-322`, not as `F0_PARSE` or `F0_BAD_SIGNATURE`.

Expected params and launcher names align when Level 1 is used, but actual C2 correctness does not enforce the same Level 0/Level 1 contract before correctness. This can silently classify the same bad source differently.

Smallest fix: add an explicit Level 0 + Level 1 preflight to C2 remote correctness before Level 2, and map parse/signature failures to the shared `F0_*` taxonomy. Files: `cluster2/modal/correctness_runner.py`, possibly `shared/eval/pipeline.py`. Expected test: one syntax-error row returns `F0_PARSE` in both C1 and C2; one wrong launcher signature returns `F0_BAD_SIGNATURE` in both.

### Question 7 - One frozen-none valid Python source through C1 and C2

Classification: **UNKNOWN_REQUIRES_INVESTIGATION**.

Evidence gathered:

- Static artifact scan with `.venv/bin/python` found `outputs/cluster1/baseline_repaired_l4_n20.jsonl` has `valid_python=0`, `invalid_python=180`, `compile_success_true=0`.
- Therefore no frozen-none baseline row exists that satisfies the requested prerequisite "parses as valid Python".
- The current Cluster 1 strict eval path requires CUDA dummy-launch compile: `cluster1/data/kernels/elementwise_relu.py:44`, `reduction_softmax.py:44`, and `matmul_tiled_gemm.py:45-46` construct tensors on `device="cuda"`; `cluster1/validation/compile_check.py:246-250` launches the candidate.
- The current C2 remote correctness path uses CUDA: `cluster2/modal/correctness_runner.py:53` sets `C2_CORRECTNESS_DEVICE = "cuda"` and line `87` passes it to Level 2.

Missing evidence: a safe local run of one eligible frozen-none source through current C1 strict eval and C2 Level 0 + Level 1. It is missing because the artifact has no parse-valid row and the strict paths require CUDA/Modal work forbidden by this audit.

Command that would be needed for full GPU-backed diagnostic, not run:

```bash
modal run -m cluster1.diagnostics.revalidate_baseline_aligned_pipeline --input outputs/cluster1/baseline_repaired_l4_n20.jsonl --output outputs/cluster1/diagnostics/<new-output>.jsonl
```

Smallest fix: first decide whether this question should use a G row instead of frozen none, or generate a synthetic fixture for Level 0/Level 1 parity tests. Do not use original frozen-none rows for this specific parse-valid smoke because none qualify.

### Question 8 - Failure taxonomy

Classification: **INCOMPATIBLE_REQUIRES_FIX**.

Shared taxonomy exists:

- `shared/eval/failure_taxonomy.py:8-24` defines canonical codes.
- `shared/eval/failure_taxonomy.py:41-55` maps legacy compile errors.
- `shared/eval/failure_taxonomy.py:58-111` `classify_failure` is used by Cluster 2 replay at `cluster2/replay/cluster1_controls.py:637-648`.

Drift paths:

- Cluster 1 compile has `_classify_error` in `cluster1/validation/compile_check.py:299-310`, then maps via `canonical_failure_code_from_compile_error`.
- Actual C2 Level 2 catches candidate-runner exceptions and labels them `F1_RUNTIME` at `shared/eval/levels/level2_correctness.py:313-322`, even for syntax/import failures that C1 Level 0 would classify as `F0_PARSE`.
- Existing C2 smoke row evidence: `outputs/cluster2/smoke_C_phase12.jsonl` first row has `failure_code="F1_RUNTIME"` with trace summary containing "syntax error in generated source".
- Existing baseline diagnostic evidence: `outputs/cluster1/diagnostics/baseline_revalidation_aligned_pipeline_parse_reclassification.jsonl` reports 180 rows, 0 entrypoint disagreements, 0 compile-success drift after parse reclassification, but that is an artifact-specific aligned diagnostic, not proof that C2 remote correctness taxonomy is aligned.

Smallest fix: route C2 correctness through the shared Level 0 and Level 1 checks before Level 2, and require `RemoteCorrectnessResult.failure_code` to preserve those codes. Files: `cluster2/modal/correctness_runner.py`, `shared/eval/pipeline.py`, tests under `cluster2/tests/test_modal_correctness_check.py`.

## 5. Block 3 - Generation pipeline alignment

### Question 9 - Generation parameters

Classification: **INCOMPATIBLE_REQUIRES_FIX**.

Cluster 1 current code:

- Adapter: `cluster1/generation/modal_generate.py:21-87`
- Request schema: `shared/modal_harness/schemas.py:46-63`
- Decoding implementation: `cluster1/generation/constrained_gen.py:48-52` uses `max_new_tokens`, `temperature`, `do_sample=True`; no explicit `top_p`.
- Current default token budget: `cluster1/constants.py:6-7` `DEFAULT_MAX_NEW_TOKENS = 1536`.
- Remote generation default GPU: `shared/modal_harness/generation.py:27` `DEFAULT_GENERATION_GPU = "L40S"`.

Cluster 1 frozen artifacts:

- Rows record `model_id`, `temperature`, `generation_seed`, but not `max_new_tokens`, `model_revision`, or `tokenizer_revision`.
- Manifest seed schedule records frozen `max_new_tokens=512`, `model_revision="unavailable_in_frozen_cluster1_artifact"`, and `tokenizer_revision="unavailable_in_frozen_cluster1_artifact"`.

Cluster 2 C/G+C current code:

- Runner defaults: `cluster2/experiments/run_cluster2_modal.py:70-78`, `238-264`.
- C2 default token budget: `cluster2/constants.py:36-37` `DEFAULT_MAX_NEW_TOKENS = 1536`.
- C2 generation GPU: `cluster2/constants.py:39` and `cluster2/modal/generation.py:83`, L4 only.
- C2 generated conditions require immutable model/tokenizer revisions: `cluster2/experiments/run_cluster2_modal.py:119-129` and `cluster2/modal/schemas.py:185-191`.
- Decoding for unconstrained C: `cluster2/modal/generation.py:944-948` uses `max_new_tokens`, `temperature`, `do_sample=True`; no explicit `top_p`.
- Decoding for G+C reuses `cluster1.generation.constrained_gen.generate_source` at `cluster2/modal/generation.py:380-397`.

Drift:

- Frozen C1 artifacts used `max_new_tokens=512`; current C1/C2 code defaults to 1536.
- Frozen C1 artifacts lack immutable model/tokenizer revisions; C2 generated runs require them.
- C1 historical generation GPU was L40S; C2 generated runs are L4.
- No explicit `top_p` is recorded in code or artifacts, so it falls through to model/generation defaults and is not provenance-controlled.

Smallest fix: for paper-scale comparison, record and enforce model revision, tokenizer revision, token budget, GPU, and decoding config for all conditions. Either replay C1 only as frozen provenance with explicit sidecar fields, or regenerate all conditions under a single current generation contract. Files: `cluster2/contracts/frozen_cluster1_artifacts_manifest.json`, C1/C2 result schemas, generation runners.

### Question 10 - Prompt templates

Classification: **COMPATIBLE** for base prompt, with intended C-condition repair prompt differences.

Evidence:

- Base prompt template and builder are in `cluster1/data/prompts/prompt_contract.py:13-38` and `92-108`.
- Cluster 1 specs store `prompt_template=PROMPT_TEMPLATE` in each KernelSpec.
- Cluster 2 runner builds base prompts through the same function at `cluster2/experiments/run_cluster2_modal.py:1112-1116`.
- Cluster 2 validates prompt SHA against replay schedule before generation at `cluster2/experiments/run_cluster2_modal.py:983-1029`.

Repair prompt differences:

- C2 generated conditions run `run_repair_loop` at `cluster2/experiments/run_cluster2_modal.py:735-742`.
- Repair prompt construction is in `cluster2/feedback/prompts.py:190-250`, adding sections such as Base task, Previous source, Failure code, Feedback, Public details, and Instruction.
- These differences are the intended C intervention, not hidden prompt drift. They must be analyzed as repair attempts, not as prompt-identical one-shot rows.

Smallest fix if incompatible: none for base prompt. Analysis must stratify attempt 0 vs repair attempts or explicitly model repair attempts.

### Question 11 - Grammar path resolution and hashes

Classification: **COMPATIBLE** for current task-agnostic routing.

Evidence:

- Shared mapping: `shared/generation_metadata.py:27-30` maps `task_agnostic` to `cluster1/grammar/triton_kernel_agnostic.gbnf`.
- Cluster 1 mapping copies shared paths in `cluster1/generation/grammar_variants.py:13-20`; `grammar_path_for_variant` is at lines `23-31`.
- Cluster 1 request schema enforces grammar path mapping at `shared/modal_harness/schemas.py:87-96`.
- C2 G+C default is `task_agnostic` at `cluster2/modal/generation.py:57-68`, and `generation_routing_for_condition` returns that path at `cluster2/modal/generation.py:278-290`.
- Runtime resolution for both paths handles repo/package paths: `shared/modal_harness/generation.py:217-230` and `cluster2/modal/generation.py:978-991`.

Hashes:

- `cluster1/grammar/triton_kernel_agnostic.gbnf`: `7896a1befca10f68ab6aa4521681fa2577eba6fb669e87daf622c15691a22e32`
- `cluster1/grammar/triton_kernel.gbnf`: `0f875b88ea80d7bc9573793f2cfb81bd75523af5ef5c0416466bc07d3eaf9b82`

Duplicated routing tables exist (`shared/generation_metadata.py`, `cluster1/generation/grammar_variants.py`, `cluster2/modal/generation.py`), but current code derives from the shared mapping at import time. The risk is future drift, not current byte drift.

Smallest fix if incompatible: add a unit test asserting C1 and C2 grammar route mappings equal `shared.generation_metadata.GRAMMAR_PATHS_BY_VARIANT` and file SHA values.

### Question 12 - Seed semantics

Classification: **COMPATIBLE**.

Evidence:

- Frozen replay manifest declares pair key fields and seed invariants. `cluster2/contracts/frozen_cluster1_artifacts_manifest.json` SHA256 is `e68846cd957c90723974673729ab6907a0c144c695c6cd06e6c5cb06ab4f0657`.
- `cluster2/replay/manifest.py:253-308` returns manifest-authoritative seed schedules and requires dense zero-based base seeds.
- C2 generated condition pairing: `cluster2/experiments/run_cluster2_modal.py:966-970` maps C to none and G+C to G.
- Attempt 0 seed rule: `cluster2/experiments/run_cluster2_modal.py:974-980` returns `pairing_entry.generation_seed` for attempt 0.
- Repair seed rule: `cluster2/feedback/repair_loop.py:286-291` defines `seed_for_attempt(base_seed, attempt_index) = base_seed * 10 + attempt_index`.
- Aggregation validates attempt 0 generated seed equals replay seed at `shared/eval/aggregation.py:671-672`.

Result:

- C paired with frozen none reuses the frozen generation seed for attempt 0.
- G+C paired with frozen G reuses the frozen generation seed for attempt 0.
- Repair attempts derive new seeds deterministically by `base_seed * 10 + attempt_index`.

Smallest fix if incompatible: none.

## 6. Block 4 - Metadata schema alignment

### Question 13 - Row field comparison

Classification: **INCOMPATIBLE_REQUIRES_FIX**.

Key field presence:

| field | C1 none n20 | C1 template G n20 | C1 task-agnostic G n5 | C2 smoke C/G+C |
|---|---|---|---|---|
| `condition` | missing | missing | missing | present |
| `grammar_active` | present | present | present | not top-level; inferred/nested only |
| `grammar_variant` | missing | missing | present | nested/generated only, often absent in smoke rows |
| `grammar_path` | missing | missing | missing | nested generated payload path only; absent in eval smoke top-level |
| `grammar_sha` | missing | missing | missing | nested generated payload only; absent in eval smoke top-level |
| `grammar_valid`, `gbnf_parse_valid`, `semantic_valid`, `rejection_layer`, `stop_reason` | missing | missing | missing | nested generated payload only; absent in eval smoke top-level |
| `model_id` | present | present | present | replay/generated metadata nested, not top-level |
| `model_revision`, `tokenizer_revision` | missing | missing | missing | required for generated requests; nested where payload preserves them |
| `kernel_id` | missing | missing | missing | missing |
| `kernel_class`, `dtype` | present | present | present | present |
| `seed`/`base_seed`/`generation_seed` | `generation_seed` only | `generation_seed` only | `generation_seed` only | `base_seed`, nested generation/replay seed metadata |
| `compile_success` | present | present | present | absent |
| `functional_success` | absent | absent | absent | present |

Evidence: `.venv/bin/python` key-set inspection of the four C1 artifacts and seven C2 smoke artifacts. Example first-row summaries show C1 rows have no `condition`, no revision fields, and no grammar validation fields; C2 smoke rows have `functional_success` but no `compile_success`.

Smallest fix: introduce a normalized analysis table schema that expands nested C2 metadata and maps C1 replay controls through C2 eval rows. Reject legacy C1 JSONL rows as direct analysis inputs unless converted with explicit provenance and current eval fields.

### Question 14 - Per-row grammar metadata expectations

Classification: **INCOMPATIBLE_REQUIRES_FIX**.

Current metadata expectation for grammar-active rows includes `grammar_active`, `grammar_variant`, `grammar_path`, `grammar_sha`, and `grammar_valid`.

Evidence:

- C1 current schema invariant: `cluster1/results/dataclass.py:166-187` requires grammar-active current-schema rows to include `grammar_variant`, `grammar_sha`, `grammar_path`, `gbnf_parse_valid`, `semantic_valid`, and `grammar_valid`.
- Shared required paper-scale grammar fields: `shared/generation_metadata.py:96-103`.
- Existing C1 artifacts:
  - `baseline_repaired_l4_n20.jsonl`: `grammar_active=False`, no grammar fields expected.
  - `final_g_l4_n20.jsonl`: `grammar_active=True`, but row `grammar_variant`, `grammar_path`, `grammar_sha`, `grammar_valid` are absent.
  - `task_agnostic_g_all_n5_l4_rerun.jsonl`: `grammar_active=True`, `grammar_variant=task_agnostic`, but `grammar_path`, `grammar_sha`, `grammar_valid` absent.
  - `task_agnostic_g_current_grammar_n5_l4.jsonl`: same gap.

Which artifacts satisfy current expectations: none of the grammar-active C1 JSONLs satisfy current row-level grammar metadata expectations. The frozen none baseline is not grammar-active, but it is still legacy for model/eval metadata.

Smallest fix: exclude legacy grammar-active C1 JSONLs from current-grammar analysis, or produce a non-mutating metadata sidecar/conversion layer that records grammar path/hash/validation provenance per row without rewriting the frozen artifacts.

### Question 15 - Sidecar `.meta.json` and hash sidecars

Classification: **INCOMPATIBLE_REQUIRES_FIX**.

C1 sidecars:

- `outputs/cluster1/baseline_repaired_l4_n20.jsonl.meta.json` keys: `condition`, `expected_rows`, `finished_at_utc`, `git_commit`, `infrastructure_failures`, `kernel_class`, `model_id`, `n`, `output_path`, `run_config`, `seed_schedule`, `started_at_utc`, `status`, `written_rows`. SHA256 `ce14490c915515305c7a9e9c310f8e79c3c5f192eea55a9f6a77f5623759d551`.
- `outputs/cluster1/final_g_l4_n20.jsonl.meta.json` same shape. SHA256 `9248134ebd45f3e6ba614a8897ce4e7431f5ce3b00e1b0829cb668a00b8ce83b`.
- Task-agnostic C1 sidecars add `grammar_variant` but not row-level grammar SHA/path/validity or model/tokenizer revisions.

C2 sidecars:

- `outputs/cluster2/smoke_C_phase12.jsonl.hashes.json`, `outputs/cluster2/smoke_GC_phase12.jsonl.hashes.json`, and `outputs/cluster2/c_prompt_audit_smoke.jsonl.hashes.json` contain `schema_version`, `eval_pipeline_hashes`, `generated_condition_hashes`, `replay_control_hashes`, `external_pins`, and `optional_diagnostics`.
- `cluster2/results/logger.py:95-130` builds these sidecars and `cluster2/results/logger.py:133-168` collects condition-specific hashes.
- `cluster2/replay/cluster1_controls.py:606-633` records frozen artifact ID/path/SHA and row/source SHA in replay candidates.
- `cluster2/contracts/frozen_cluster1_artifacts_manifest.json` records frozen paths and SHAs for C1 none, template G, and task-agnostic G n=5.

Mismatch:

- C1 sidecars are run summaries; C2 sidecars are content-hash manifests. Schemas are not consistent.
- C2 does record frozen C1 artifact paths/SHAs through the manifest and replay metadata.
- Frozen C1 sidecars do not record immutable model/tokenizer revisions; manifest fills them as `unavailable_in_frozen_cluster1_artifact`.

Smallest fix: define one cross-cluster provenance sidecar schema for analysis inputs. Include `git_commit`, `model_id`, `model_revision`, `tokenizer_revision`, `modal_generation_gpu`, `max_new_tokens`, `scale_tier`, `kernel_ids/classes`, `seed_schedule`, frozen artifact paths/SHAs, grammar SHA/path/variant, and eval hash class.

## 7. Block 5 - Baseline-specific compatibility

### Question 16 - Re-evaluate all 180 baseline rows through current C1 strict eval

Classification: **UNKNOWN_REQUIRES_INVESTIGATION**.

This audit did not rerun strict C1 eval because the required path launches CUDA/Triton work:

- C1 dummy args allocate CUDA tensors in the kernel specs.
- `cluster1/validation/compile_check.py:246-250` launches the generated kernel over each shape.

Existing evidence:

- `outputs/cluster1/diagnostics/baseline_revalidation_aligned_pipeline.jsonl`: 180 rows, 0 compile-success drift, 0 C1/C2 entrypoint disagreement, 180 cross-category label drifts before parse reclassification.
- `outputs/cluster1/diagnostics/baseline_revalidation_aligned_pipeline_parse_reclassification.jsonl`: 180 rows, 0 compile-success drift, 0 C1/C2 entrypoint disagreement, 0 cross-category label drift; SHA256 `ef0150058d67bc8bc6e0ce5de57eed173bcc6fc0b31c74657d86dfd1f5957e97`.

Missing evidence: a fresh, current strict C1 revalidation run from this audit. The command would require Modal/GPU and an output write, both forbidden here.

Command needed, not run:

```bash
modal run -m cluster1.diagnostics.revalidate_baseline_aligned_pipeline --input outputs/cluster1/baseline_repaired_l4_n20.jsonl --output outputs/cluster1/diagnostics/<new-output>.jsonl
```

Does this block paper-scale spend: yes, unless the existing diagnostic artifact is formally accepted as the current revalidation gate and tied to current eval hashes.

### Question 17 - Run 180 baseline rows through current C2 eval path Level 0 + Level 1 only

Classification: **UNKNOWN_REQUIRES_INVESTIGATION**.

Missing evidence:

- No safe local Level 1 run was performed because `shared/eval/levels/level1_compile.py:45-51` delegates to the C1 compile path and therefore to CUDA dummy launches.
- Actual C2 remote correctness does not run Level 0 + Level 1 only; it runs Level 2 correctness on CUDA through `cluster2/modal/correctness_runner.py:67-89`.

Existing diagnostic evidence from `outputs/cluster1/diagnostics/baseline_revalidation_aligned_pipeline_parse_reclassification.jsonl` shows C1 and shared C2 Level 1 entrypoint agreement for 180 rows, but it was not rerun here and lacks a content-hash sidecar for this audit.

Command needed, not run:

```bash
modal run -m cluster1.diagnostics.revalidate_baseline_aligned_pipeline --input outputs/cluster1/baseline_repaired_l4_n20.jsonl --output outputs/cluster1/diagnostics/<new-output>.jsonl
```

Smallest fix: create a non-mutating C2 Level 0/Level 1 diagnostic that writes a hash sidecar, or accept the existing parse-reclassification diagnostic as the gate by recording its evaluator source hashes.

### Question 18 - Baseline regeneration vs revalidation

Classification: **UNKNOWN_REQUIRES_INVESTIGATION**.

Evidence that original generation would differ today:

- Frozen manifest records C1 frozen `max_new_tokens=512`; current C1/C2 defaults are 1536.
- Frozen C1 rows do not contain immutable `model_revision` or `tokenizer_revision`; C2 generated paths require immutable revisions.
- Historical C1 generation GPU is L40S (`shared/modal_harness/generation.py:27` and `phase_minus1_manifest.json`), while C2 generated paths are L4.
- Prompt builder source is shared and current file hash is `104d00f4820bdcf8c685a5873adbdeca2d1fa97b93b3fd1b0ec53469b18d94db`, but frozen rows only carry prompt SHA in manifest sidecars, not row fields.
- Seed schedule for frozen artifacts is explicit and paired.

Interpretation:

- Regenerating the baseline would not reproduce the frozen baseline unless model/tokenizer revision, token budget, GPU, and prompt are pinned to the original conditions.
- Existing diagnostics suggest revalidation may be sufficient for compile-gate comparability, but this audit cannot close the question for paper-scale analysis because Questions 16 and 17 were not rerun safely and C2 correctness taxonomy/gate alignment still has known drift.

Smallest fix: prefer revalidation over regeneration if the goal is to preserve frozen controls, but first run/accept a hash-pinned current revalidation gate and convert C1 controls into C2 replay rows for the analysis table.

## 8. Compatibility matrix

| item | C1 none | C1 G/template diagnostic | C1 task-agnostic G | C2 C | C2 G+C | status | evidence |
|---|---|---|---|---|---|---|---|
| KernelSpec IDs | 19/23/1 via C1 specs | same | same | C2 metadata 19/23/1 | same | COMPATIBLE | `cluster1/data/kernels/*.py`; `shared/eval/correctness_shapes.py:58-80` |
| reference code | C1 `KernelSpec.reference_code` | same | same | `reference_runner` loads C1 specs | same | COMPATIBLE | `shared/eval/reference_runner.py:57-76` |
| shape schedules | compile-only 5 probes | compile-only 5 probes | compile-only 5 probes | correctness 6+6 split | correctness 6+6 split | INCOMPATIBLE | `correctness_shapes.py:87-137`, `238-246` |
| tolerances | not used by original compile rows | not used by original compile rows | not used by original compile rows | shared table | shared table | COMPATIBLE for C2 correctness; not comparable to C1 compile-only | `shared/eval/tolerances.py:15-114` |
| compile gate | C1 strict compile | C1 strict compile | C1 strict compile | shared Level 1 available, but remote correctness bypasses | same | INCOMPATIBLE for actual C2 correctness | `compile_check.py:183-292`; `correctness_runner.py:67-89` |
| signature gate | Level 0 + import signature | same | same | Level 1 available; actual correctness only launcher getattr | same | INCOMPATIBLE | `level0_parse.py:21-55`; `correctness_runner.py:330-348` |
| failure taxonomy | legacy compile labels in rows | legacy compile labels in rows | legacy compile labels in rows | Level 2 runtime can label syntax as F1 | same | INCOMPATIBLE | `failure_taxonomy.py`; C2 smoke syntax as F1_RUNTIME |
| prompt | shared base prompt | shared base prompt | shared base prompt | shared base plus repair feedback after attempt 0 | same, with G | COMPATIBLE if attempt/repair is modeled | `prompt_contract.py`; `run_cluster2_modal.py:1112-1116` |
| model/tokenizer | model_id only; revisions absent | same | same | revisions required | revisions required | INCOMPATIBLE | C1 artifact keys; `cluster2/modal/schemas.py:185-191` |
| generation parameters | frozen token budget 512 in manifest | same | same | current default 1536 | current default 1536 | INCOMPATIBLE | `cluster2/constants.py:36-37`; manifest seed schedules |
| grammar path/hash | none | template, row hash absent | task-agnostic, row hash absent | none | task-agnostic current hash | INCOMPATIBLE for existing artifacts; route compatible | `shared/generation_metadata.py:27-30`; artifact keys |
| seed semantics | generation_seed 0..n-1 | same | same n=5 | paired attempt 0; repairs derived | paired attempt 0; repairs derived | COMPATIBLE | `run_cluster2_modal.py:974-980`; `repair_loop.py:286-291` |
| metadata schema | legacy C1 | legacy C1 | legacy C1 | C2 eval row/nested metadata | C2 eval row/nested metadata | INCOMPATIBLE | artifact key inspection |
| sidecars | run summary | run summary | run summary | content-hash sidecars | content-hash sidecars | INCOMPATIBLE | C1 `.meta.json`; C2 `.hashes.json` |
| baseline revalidation | not rerun; existing diagnostic | not baseline | not baseline | not rerun | not rerun | UNKNOWN | existing diagnostics plus GPU blocker |

## 9. Fix list

1. **Do not mix legacy C1 compile-only rows with C2 correctness rows.**
   - Files to modify: analysis ingestion/aggregation code; possibly `shared/analysis/factorial.py`.
   - Smallest fix: require C1 controls to enter analysis only as C2 replay rows or through a normalized converted schema with eval provenance.
   - Expected test: attempting to load `outputs/cluster1/*.jsonl` directly into cross-cluster analysis fails with a schema/provenance error.
   - Risk: medium; affects analysis inputs but not generation.

2. **Add C2 Level 0/Level 1 preflight before Level 2 correctness.**
   - Files: `cluster2/modal/correctness_runner.py`, `shared/eval/pipeline.py`, tests under `cluster2/tests/`.
   - Smallest fix: call shared `check_parse`, `check_signature`, and `check_compile_level1` before Level 2; return `F0_*`/`F1_*` without running correctness when those gates fail.
   - Expected test: same malformed source has the same canonical failure code under C1 strict and C2 remote correctness.
   - Risk: high; changes result taxonomy and may change previously logged C2 smoke outcomes.

3. **Normalize metadata schema for analysis rows.**
   - Files: C1/C2 result adapters, analysis ingestion, manifest schema.
   - Smallest fix: create a read-only normalized analysis table builder that expands nested C2 metadata and rejects missing critical fields.
   - Expected test: required fields `condition`, `base_seed`, `model_revision`, `tokenizer_revision`, `grammar_path`, `grammar_sha`, `functional_success`, and provenance hashes are present or explicitly `UNKNOWN` with exclusion flags.
   - Risk: medium.

4. **Resolve generation parameter drift.**
   - Files: manifests, C1/C2 generation configs, analysis provenance checks.
   - Smallest fix: enforce token budget, model revision, tokenizer revision, temperature, `top_p` policy, and GPU provenance before paper-scale runs.
   - Expected test: C2 runner refuses paper-scale generation if paired replay provenance lacks required comparable fields or if the analysis mode has not declared them intentionally unequal.
   - Risk: medium.

5. **Separate template G diagnostic from task-agnostic primary G.**
   - Files: replay manifest and analysis selectors.
   - Smallest fix: require `grammar_variant=task_agnostic` for primary G+C; keep `template_upper_bound` behind an explicit diagnostic flag.
   - Expected test: paper-scale G+C with task-agnostic variant fails until n=20 task-agnostic G replay coverage exists.
   - Risk: low.

## 10. Unknowns list

1. **Question 7: no parse-valid frozen none row and local strict eval is unsafe.**
   - Missing evidence: one eligible frozen-none row evaluated through C1 strict and C2 Level 0 + Level 1.
   - Why missing: 0/180 frozen none rows parse as valid Python; strict compile/eval requires CUDA/Modal.
   - Blocks n=20: yes for claiming current C1/C2 strict eval parity from local evidence.
   - Resolution: use a G row or synthetic fixture for parse-valid parity, and run GPU-backed parity only via an approved non-mutating diagnostic.

2. **Question 16: current full baseline C1 strict revalidation was not rerun.**
   - Missing evidence: fresh 180-row current strict revalidation with current source hashes.
   - Why missing: forbidden GPU/Modal/output-writing path.
   - Blocks n=20: yes unless existing diagnostic is accepted and hash-pinned.
   - Resolution: run `modal run -m cluster1.diagnostics.revalidate_baseline_aligned_pipeline ...` outside this audit, or record acceptance of the existing parse-reclassification diagnostic with evaluator hashes.

3. **Question 17: current C2 Level 0 + Level 1-only baseline run was not rerun.**
   - Missing evidence: fresh 180-row C2 Level 0/Level 1 parity artifact.
   - Why missing: Level 1 delegates to CUDA compile; actual C2 correctness does not expose Level 0/Level 1-only mode.
   - Blocks n=20: yes.
   - Resolution: add a non-mutating C2 Level 0/Level 1 diagnostic command with hash sidecar, then run it on approved GPU infrastructure.

4. **Question 18: baseline regeneration vs revalidation remains unresolved.**
   - Missing evidence: accepted current revalidation gate and analysis decision on legacy generation provenance.
   - Why missing: model/tokenizer revisions are absent in frozen rows and strict eval was not rerun here.
   - Blocks n=20: yes.
   - Resolution: prefer frozen baseline revalidation, but only after Questions 16-17 are closed and metadata normalization prevents hidden drift.

## 11. Final recommendation

**BLOCKED_PENDING_INVESTIGATION**.

Rationale: Several core definitions are aligned, but direct paper-scale comparison is not yet defensible. Critical unknowns remain for current baseline revalidation and C1/C2 eval parity under the strict compile/eval gates, and known incompatibilities remain in actual C2 correctness taxonomy, metadata schema, token-budget/model-revision provenance, and task-agnostic G paper coverage.

Do not run n=20 C/G+C paper-scale spend until:

1. C2 correctness aligns Level 0/Level 1/Level 2 taxonomy with C1 or the analysis explicitly uses only C2 replay/eval rows for all conditions.
2. Task-agnostic G has paper-scale n=20 replay coverage if primary G+C is task-agnostic.
3. Baseline revalidation is rerun or the existing parse-reclassification diagnostic is formally hash-pinned as current evidence.
4. A normalized analysis schema rejects legacy rows with missing model/grammar/eval provenance.
