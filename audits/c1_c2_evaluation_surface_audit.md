# C1/C2 Evaluation Surface Audit

## 1. Executive summary

Overall classification:

- Cluster 1: **C1_COMPILE_ONLY_BY_DESIGN**.
- Cluster 2: **C2_FULL_LEVEL0_LEVEL1_LEVEL2_WITH_F2_REPAIR**.
- C1/C2 asymmetry: **ASYMMETRY_ACCEPTED_COMPILE_ONLY_DESIGN** plus **ASYMMETRY_REQUIRES_REPORT_CAVEAT**.
- Template readiness: **READY_FOR_TEMPLATE_C1_COMPILE_RERUN** for a fresh template G Cluster 1 compile rerun; **ALIGNMENT_GAPS_EXIST** before a full fresh template G + template G+C diagnostic ceiling can be treated as current-pipeline paired evidence.
- Metrics: **METRICS_APPROPRIATE_FOR_CURRENT_COMPILE_AND_CORRECTNESS_SCOPE** plus **METRIC_CONCERNS_REQUIRE_CAVEATS**.

Cluster 1 evaluates generated Triton source through grammar metadata validation and a cluster-specific compile gate that includes shared Level 0 parse/signature checks plus Triton JIT/import/dummy-launch checks, then stops. It does not run shared Level 2 numerical correctness and does not record `functional_success`. This is explicit in the Cluster 1 runner boundary and docs, not an accidental omission (`cluster1/experiments/run_cluster1_modal.py:1-12`, `cluster1/validation/compile_check.py:1-5`, `docs/02_methodology_cluster1.md:21-27`).

Cluster 2 evaluates generated C/G+C rows through Level 0 parse/signature, Level 1 compile, and Level 2 numerical correctness, with repair feedback only after allowed F2 numerical failures. The correctness runner performs the gates before calling the shared Level 2 pipeline, and the repair loop terminates without feedback for pre-Level-2 failures (`cluster2/modal/correctness_runner.py:70-150`, `cluster2/feedback/repair_loop.py:366-369`, `cluster2/feedback/prompts.py:17-23`).

Fresh template G can be run through Cluster 1 at compile-parity with task-agnostic G because the current runner accepts `--grammar-variant template_upper_bound`, routes it to `cluster1/grammar/triton_kernel.gbnf`, records grammar path/SHA and provenance metadata, and uses the same C1 compile semantics (`cluster1/experiments/run_cluster1_modal.py:72-85`, `cluster1/generation/grammar_variants.py:15-31`, `cluster1/experiments/run_cluster1_modal.py:903-956`). That only answers compile and grammar-funnel parity. Functional parity requires a matching template G+C Cluster 2 diagnostic run.

The full template G+C diagnostic ceiling should not start until the pre-run registry/manifest/hash-gate/analyzer-separation work in the template plan is satisfied. Current C2 generation supports `template_upper_bound`, but replay/manifest selection still maps template controls to the legacy template artifact, so a fresh current-pipeline template G artifact must be registered and selected before paired template G+C can be interpreted as current-pipeline diagnostic evidence (`cluster2/replay/manifest.py:208-220`, `cluster2/contracts/frozen_cluster1_artifacts_manifest.json:23235-23239`, `.contracts/agentic/template_upper_bound_diagnostic_rerun_plan.md:180-186`).

## 2. Scope and method

This was a read-only audit except for this report file. I did not modify code, artifacts, analyzer outputs, docs/contracts, manifests, or grammar files. I did not invoke Modal, run generation, run experiments, or run GPU jobs.

Hub status:

- The document hub establishes the source hierarchy as code/tests, current artifacts, docs, contracts, audits, then agentic handoffs (`docs/handoff/agentic_document_hub.md:31-44`).
- The hub routes Cluster 2/G+C, replay artifacts, Cluster 1 grammar/G, artifact/provenance, analyzer/statistics, and report-scope questions to the methodology docs, artifact registry, contracts, audits, and analyzer code (`docs/handoff/agentic_document_hub.md:64-72`).
- The version registry explicitly registers the Cluster 1 methodology, Cluster 2 methodology, artifact registry, failure taxonomy/eval ladder, analysis/statistics, decision log, report outline, drift-prevention plan, and research contracts (`docs/handoff/document_version_registry.md:56-80`).
- The code-update policy confirms that code, artifact schema, analyzer, and Modal/replay changes require documentation updates, while docs-only changes must not re-record hashes or output artifacts (`docs/handoff/code_update_documentation_policy.md:40-55`, `docs/handoff/code_update_documentation_policy.md:69-70`).
- Therefore the hub routes this audit to Cluster 1 methodology docs, Cluster 2 methodology docs, failure taxonomy/eval ladder docs, analyzer/statistics docs, the artifact registry, and current research contracts. The template upper-bound rerun plan is not a primary hub table target, but it is a relevant agentic plan under the hub's source hierarchy and was inspected.

Files inspected included the required Cluster 1 runner, compile checker, validator, dataclass/logger, grammar loader/variants, grammar files, tests; shared eval levels, pipeline, schema, failure taxonomy, and factorial analyzer; Cluster 2 correctness runner, run script, repair loop, dataclass/logger, replay controls, manifest, and tests; current docs/contracts; current JSONL/JSON artifacts; and relevant audits/plans.

Required searches were run before conclusions for Level 0/1/2, compile/correctness fields, C1 compile gates, C2 correctness runner and repair loop, template grammar routing, task-agnostic grammar validity fields, provenance/scale metadata, and current artifact identifiers.

## 3. Block 1 - Cluster 1 evaluation surface

### Stages run

When a Cluster 1 generation completes, the runner generates source, optionally with grammar constraints, performs local grammar metadata validation for grammar-active rows, calls the C1 compile checker, then serializes a `GenerationResult` row. The core cell loop calls `generate_source_modal`, then `check_compiles_modal`, then converts the remote result to a C1 row (`cluster1/experiments/run_cluster1_modal.py:1003-1058`). The conversion stores generation metadata and compile outcome but no functional correctness field (`cluster1/experiments/run_cluster1_modal.py:811-900`).

Cluster 1 does invoke shared Level 0-style parse/signature validators inside its compile checker. `compile_check.py` imports `validate_signature` and `validate_source` from shared Level 0 parse (`cluster1/validation/compile_check.py:19-21`), runs source parsing before import/JIT work (`cluster1/validation/compile_check.py:195-218`), and classifies those failures as F0 parse/signature failures.

Cluster 1 does not call the shared eval pipeline for Level 1/2. Instead it uses a cluster-specific compile gate. The file header says it checks whether generated kernels compile through actual Triton JIT with dummy launches and that C1 stops at compile acceptance (`cluster1/validation/compile_check.py:1-5`). After Level 0 validation, it imports the module, resolves the kernel/launcher, and attempts dummy launches (`cluster1/validation/compile_check.py:220-265`). Success returns a `CompileResult(success=True)` (`cluster1/validation/compile_check.py:267-274`).

The C1 compile gate is effectively the code path later wrapped by shared Level 1 for C2. Shared Level 1 is a thin adapter around `cluster1.validation.compile_check.check_compiles_all_dtypes` (`shared/eval/levels/level1_compile.py:1-6`, `shared/eval/levels/level1_compile.py:36-61`). That means C1 and C2 share compile mechanics, but C1 does not invoke `run_eval_pipeline`.

Cluster 1 does not invoke shared Level 2 numerical correctness. The runner boundary states that C1 performs no correctness, profiling, repair, or derived metrics (`cluster1/experiments/run_cluster1_modal.py:1-12`). The Cluster 1 boundary tests forbid `torch.allclose`, torch testing, timing/profiling, speedups, and repair machinery in Cluster 1 (`cluster1/tests/test_cluster_boundary.py:1-6`, `cluster1/tests/test_cluster_boundary.py:37-71`, `cluster1/tests/test_cluster_boundary.py:1040-1074`). The methodology doc says Cluster 1 ends at compile/JIT launch and does not execute numerical correctness (`docs/02_methodology_cluster1.md:21-27`).

### Fields recorded

The C1 row model is `GenerationResult`. It records prompt/source/factor fields, grammar fields, generated metadata, compile outcome, failure code, compile error details, and optional launch metadata; it has no `functional_success` field (`cluster1/results/dataclass.py:57-94`). The invariant layer validates compile/failure consistency (`cluster1/results/dataclass.py:109-136`), generation metadata (`cluster1/results/dataclass.py:148-239`), paper-scale metadata (`cluster1/results/dataclass.py:241-305`), and grammar path/SHA fields (`cluster1/results/dataclass.py:373-447`). The logger writes dataclass rows as JSONL without adding functional fields (`cluster1/results/logger.py:13-16`).

The current methodology docs define C1 `compile_success` as successful parse/signature, import, launcher resolution, and at least one dummy launch for each configured dtype, and explicitly state that it does not mean numerical equivalence or speed (`docs/02_methodology_cluster1.md:161-175`). The docs list C1 schema fields as including grammar metadata and compile outcome, not `functional_success` (`docs/02_methodology_cluster1.md:177-190`).

Artifact inspection confirms the schema split. Current task-agnostic G rows have `compile_success` present but `functional_success` absent; the legacy template G rows also have `compile_success` present and `functional_success` absent. The artifact registry separately marks Cluster 1 as compile-only and current task-agnostic G as 177 rows with grammar validity split fields (`docs/05_artifacts_and_results_registry.md:38-74`).

### Design classification

Cluster 1 is **C1_COMPILE_ONLY_BY_DESIGN**. It uses shared Level 0 validators and the same underlying compile gate that C2 wraps as Level 1, but it is not a shared Level 0/1/2 evaluator. It is not Level 2-capable in its current research role, and that is a documented boundary rather than a missing feature (`docs/08_decision_log.md:63-72`, `.contracts/research/research_scope.md:67-81`).

## 4. Block 2 - Cluster 2 evaluation surface

### Stages run

For generated C/G+C rows, Cluster 2 runs a staged evaluator. The correctness runner imports shared Level 0, shared Level 1, and the shared pipeline (`cluster2/modal/correctness_runner.py:45-49`). Its generated-condition path performs source validation, signature validation, runtime import/kernel checks, Level 1 compile, and then Level 2 correctness through `run_eval_pipeline` with a `PipelineLevel2Request` (`cluster2/modal/correctness_runner.py:70-150`).

The pre-Level-2 gates return structured failures. Level 0 parse failures return F0 parse with `level_reached=0` (`cluster2/modal/correctness_runner.py:153-174`). Level 0 signature failures return F0 decorator/signature failures (`cluster2/modal/correctness_runner.py:177-205`). Level 1 compile failures return F1 with `compile_success=False` and `level_reached=1` (`cluster2/modal/correctness_runner.py:208-233`). Generated pre-Level-2 failure results mark `functional_success`, `repair_set_success`, and `eval_set_success` false and withhold feedback (`cluster2/modal/correctness_runner.py:236-274`).

Level 2 correctness is deterministic and requires both repair-set and held-out eval-set success. Level 2 builds deterministic repair/eval shapes from kernel class, dtype, base seed, and attempt, then sets `functional_success = repair_set_success and eval_set_success` (`shared/eval/levels/level2_correctness.py:139-201`). The per-output comparison uses shape checks, finite checks, and `torch.allclose` tolerances (`shared/eval/levels/level2_correctness.py:338-457`).

The shared pipeline object distinguishes the stages and records that fields above the evaluated level remain `None` rather than false (`shared/eval/pipeline.py:26-34`, `shared/eval/schema.py:41-48`). For C2 generated rows, the C2 runner performs explicit Level 0/1 gates, then uses the pipeline for Level 2 (`shared/eval/pipeline.py:95-124`, `shared/eval/pipeline.py:152-166`).

### Repair loop placement

Repair wraps generated-condition evaluation attempts. The C2 runner calls `run_repair_loop` after initial generation and correctness evaluation setup, then writes the final generated row (`cluster2/experiments/run_cluster2_modal.py:789-804`, `cluster2/experiments/run_cluster2_modal.py:676-873`). The repair loop generates/evaluates attempts, stops on success, stops when no feedback is allowed, and only builds feedback for repairable failures (`cluster2/feedback/repair_loop.py:159-181`, `cluster2/feedback/repair_loop.py:182-187`, `cluster2/feedback/repair_loop.py:248-270`).

Repair fires only after F2. The allowed feedback codes are only F2 numeric large, NaN, and shape mismatch (`cluster2/feedback/prompts.py:17-23`). The repair loop terminates without feedback if `level_reached < 2` or if the failure code is not feedback-allowed (`cluster2/feedback/repair_loop.py:366-369`). The Cluster 2 methodology doc states the same F2-only boundary (`docs/03_methodology_cluster2.md:87-102`).

### Fields recorded

Cluster 2 generated rows are `Cluster2EvalRow` records containing condition, factor fields, replay identity, prompt/source, compile_success, functional_success, repair/eval success, failure_code, correctness result, trace summary, grammar metadata, and generation metadata (`cluster2/results/dataclass.py:390-418`). The row invariants require boolean consistency and enforce that `functional_success` equals repair-set and eval-set success (`cluster2/results/dataclass.py:420-465`). Generated rows require grammar metadata for G+C and no grammar metadata for C (`cluster2/results/dataclass.py:533-560`).

C2 records `functional_success` directly from the correctness result. `compile_success` is sometimes raw and sometimes derived from the correctness evidence. The run script derives compile success from the correctness result: raw bool if present; `functional_success=True` implies compile true; F0/F1 imply compile false; F2 implies compile true; `level_reached >= 2` implies compile true; otherwise false (`cluster2/experiments/run_cluster2_modal.py:1388-1413`). The dataclass contains the same resolution policy for generated rows and legacy backfill (`cluster2/results/dataclass.py:1016-1045`, `cluster2/results/dataclass.py:1048-1113`).

Artifact inspection confirms C2 generated rows include `functional_success`, `failure_code`, generated metadata, and replay pairing. Current C rows have `functional_success=False` and F0 parse failures in 180/180 rows. Current G+C rows have `functional_success=False`, F1/F2/F3/F0 failures, `compile_success` present, grammar validity fields, and replay pair IDs.

### Design classification

Cluster 2 is **C2_FULL_LEVEL0_LEVEL1_LEVEL2_WITH_F2_REPAIR** for generated C/G+C rows. The earlier gates are explicit, not merely implied, and repair is downstream of Level 2-only failures.

## 5. Block 3 - Asymmetry and analyzer behavior

### Canonical analyzer behavior

The analyzer defines `functional_success` as the primary response and `compile_success` as a secondary diagnostic (`shared/analysis/factorial.py:60-62`). It treats Cluster 1 none/G as compile-only conditions and C2 C/G+C as generated Level-2 conditions (`shared/analysis/factorial.py:73-75`).

During normalization, Cluster 1 compile-only rows preserve `compile_success` but set `functional_success=False` because functional correctness is unproven, not measured (`shared/analysis/factorial.py:176-241`, especially `shared/analysis/factorial.py:224-235`). For C2, compile success is normalized from raw fields and failure evidence: F0/F1 are compile false, F2 is compile true, and F3 is evidence-sensitive (`shared/analysis/factorial.py:858-926`). The analyzer excludes F3 rows from compile-rate denominators while treating them as false in matched analysis absent independent compile-pass evidence (`shared/analysis/factorial.py:2114-2123`).

Docs and contracts mirror this. The analysis doc says C1 `functional_success` is assigned false as unproven/unmeasured while C1 `compile_success` is preserved (`docs/07_analysis_and_statistics.md:55-85`). The eval metrics contract says functional success is primary for C2, compile success is secondary, and C1 false should be interpreted as not measured rather than a demonstrated numeric failure (`.contracts/research/eval_metrics.md:32-69`).

### Methodological argument

The asymmetry is intentional and acceptable if reported as a surface difference. Cluster 1 rows can answer whether grammar/control improved parse/signature/JIT/dummy-launch acceptance. They cannot answer whether the generated kernels numerically match references. Cluster 2 rows can answer numerical correctness, because they pass through Level 2.

The analyzer's binary normalization can introduce false negatives in a literal sense: a C1 `compile_success=True` row might be numerically correct if Level 2 were run, but C1 did not measure that outcome. Shared `EvalResult` semantics distinguish `None` from false for fields above the evaluated level (`shared/eval/schema.py:41-48`), so reports should describe C1 functional outcomes as unmeasured/unproven rather than measured failures.

This is not a method blocker for compile-scope comparisons, but it is a report caveat and a blocker for claiming functional parity from C1-only reruns.

### Classification

The asymmetry is **ASYMMETRY_ACCEPTED_COMPILE_ONLY_DESIGN** and **ASYMMETRY_REQUIRES_REPORT_CAVEAT**. It is not **ASYMMETRY_METHOD_BLOCKER** if the analysis separates compile-only C1 evidence from C2 functional evidence and avoids interpreting C1 functional false as observed Level 2 failure.

## 6. Block 4 - Template G current-pipeline readiness

### Grammar existence and routing

`cluster1/grammar/triton_kernel.gbnf` exists and is the template upper-bound grammar. Its header states it is a task-encoded upper-bound grammar for the fixed benchmark surface and not a universal Triton grammar (`cluster1/grammar/triton_kernel.gbnf:1-13`). The task-agnostic grammar exists separately at `cluster1/grammar/triton_kernel_agnostic.gbnf` and declares itself generic/task-agnostic (`cluster1/grammar/triton_kernel_agnostic.gbnf:1-21`).

The shared grammar metadata maps `template_upper_bound` to `cluster1/grammar/triton_kernel.gbnf` and `task_agnostic` to `cluster1/grammar/triton_kernel_agnostic.gbnf` (`shared/generation_metadata.py:23-38`). Cluster 1's grammar variants use the same mapping (`cluster1/generation/grammar_variants.py:15-31`). The C1 runner accepts `--grammar-variant` choices including `template_upper_bound`, `task_agnostic`, and `both`, with the default at `template_upper_bound` (`cluster1/experiments/run_cluster1_modal.py:72-85`). Tests verify that explicit task-agnostic and template variants select the expected grammar paths (`cluster1/tests/test_run_cluster1_modal.py:53-69`, `cluster1/tests/test_run_cluster1_modal.py:129-141`).

### Metadata/provenance parity

A fresh C1 template G run would use the current C1 row model and validation path. C1 records sidecar metadata including condition, grammar variant, model and tokenizer revisions, scale tier, run config, and generation metadata schema version (`cluster1/experiments/run_cluster1_modal.py:218-250`). It validates grammar-active rows against local grammar path/SHA and local source validation (`cluster1/experiments/run_cluster1_modal.py:903-956`). C1 paper-scale validation enforces generation metadata and grammar metadata invariants (`cluster1/results/dataclass.py:241-305`, `cluster1/results/dataclass.py:373-447`).

Therefore fresh template G can be directly compared with fresh/current task-agnostic G for C1 compile semantics and grammar-funnel metrics, provided the same model revision, tokenizer revision, max_new_tokens, temperature, scale tier, Modal image/provenance, and run configuration are held constant. The old legacy template G artifact does not meet that standard: it lacks current grammar split fields, provenance, model/tokenizer metadata, scale tier, max_new_tokens, and replay identity, even though it has 180/180 compile success.

### C2 template G+C readiness

C2 supports template grammar routing for generated G+C at the generation boundary. Its config validates `grammar_variant` values (`cluster2/experiments/run_cluster2_modal.py:97-140`), the CLI accepts `--grammar-variant` defaulting to task-agnostic (`cluster2/experiments/run_cluster2_modal.py:249-280`), and generated G+C passes the selected grammar variant to generation (`cluster2/experiments/run_cluster2_modal.py:764-766`). C2 generation has grammar constants for task-agnostic and template variants and supports routing G+C to either (`cluster2/modal/generation.py:55-83`, `cluster2/modal/generation.py:261-292`, `cluster2/modal/generation.py:318-329`).

However, current replay/manifest selection still maps template controls to the legacy template artifact. The replay manifest selects task-agnostic G for task-agnostic grammar and the template selected controls otherwise (`cluster2/replay/manifest.py:208-220`). The frozen manifest's selected template controls point to `g_template_upper_bound_n20_l4`, not a new current-pipeline template artifact (`cluster2/contracts/frozen_cluster1_artifacts_manifest.json:23235-23239`). The template rerun plan explicitly requires registering new artifact IDs, updating the manifest to select the new current-pipeline template G artifact, and extending hardcoded hash gates before template G+C (`.contracts/agentic/template_upper_bound_diagnostic_rerun_plan.md:180-186`, `.contracts/agentic/template_upper_bound_diagnostic_rerun_plan.md:332-393`).

### Parity answer

Fresh template G can run through Cluster 1 at parity with task-agnostic G for compile-success and grammar-funnel metrics. It cannot be directly compared for `functional_success`, because C1 does not evaluate or record Level 2.

Fresh template G+C is required to compare functional correctness under Cluster 2. The current C2 evaluator can perform the Level 0/1/2 surface with F2 repair for template G+C, but the diagnostic is not ready to run as paired current-pipeline evidence until the new template G artifact is registered and selected instead of the legacy template controls.

Classification: **READY_FOR_TEMPLATE_C1_COMPILE_RERUN** and **ALIGNMENT_GAPS_EXIST** for the full template G+C diagnostic rerun. It is not **NOT_READY_FOR_TEMPLATE_RERUN** for C1 compile-only, but it is not yet fully **READY_FOR_TEMPLATE_C1_C2_DIAGNOSTIC_RERUN** until the manifest/registry/analyzer-separation preconditions are met.

## 7. Block 5 - Metric adequacy

### `compile_success`

In C1, `compile_success` means the generated source passed parse/signature validation, module import, kernel/launcher resolution, and dummy Triton launches for the configured dtype surface. The code path is `cluster1.validation.compile_check.check_compiles`, called from the C1 Modal runner (`cluster1/validation/compile_check.py:185-274`, `cluster1/experiments/run_cluster1_modal.py:1003-1058`). It is Level 1-style compile evidence only. It does not prove numerical correctness, speed, robust shape coverage, or code quality (`docs/02_methodology_cluster1.md:161-175`).

In C2, generated rows reach compile evidence through explicit Level 0 and Level 1 gates before Level 2. Raw `compile_success` may be present, or it may be derived from failure code, functional success, or `level_reached` (`cluster2/experiments/run_cluster2_modal.py:1388-1413`, `cluster2/results/dataclass.py:1016-1045`). F2 failures imply compile success because the row reached Level 2; F0/F1 imply compile failure.

### `functional_success`

`functional_success` is a Cluster 2 Level 2 numerical correctness metric. It requires deterministic repair-set and held-out eval-set success (`shared/eval/levels/level2_correctness.py:139-201`). It uses reference/candidate execution and output comparison with shape, finite, and `torch.allclose` checks (`shared/eval/levels/level2_correctness.py:260-457`). F3 rows represent evaluation pipeline failures rather than normal functional failures; the analyzer handles F3 separately for compile-rate denominators and matched analysis (`shared/analysis/factorial.py:2114-2123`, `docs/06_failure_taxonomy_and_eval_ladder.md:87-98`).

### Appropriateness and gaps

These metrics are appropriate for the current research question only within the documented compile and correctness scope: whether inference-time control improves LLM-generated Triton kernels in terms of grammar/compile acceptance and Level 2 numerical correctness. They are insufficient for claims about performance, speedup, robustness to unseen shapes, code quality/readability, generalization beyond the fixed kernel surface, tolerance sensitivity, resource usage, or determinism under repeated runs. The drift-prevention plan reserves performance work for a future metric contract and explicitly blocks speed claims from the current artifacts (`docs/10_cluster3_drift_prevention_plan.md:93-108`, `.contracts/research/research_scope.md:119-128`).

Missing metrics that could change conclusions include runtime performance, pass rates over broader shape distributions, repeated-run stability, memory/resource behavior, stricter or alternative numeric tolerances, and maintainability/security/code-quality measures.

Classification: **METRICS_APPROPRIATE_FOR_CURRENT_COMPILE_AND_CORRECTNESS_SCOPE** and **METRIC_CONCERNS_REQUIRE_CAVEATS**. The metric caveats do not block a template diagnostic rerun if the rerun is framed as compile/correctness only and not performance or generalization evidence.

## 8. Evaluation surface comparison matrix

| Surface | C1 none/G | C2 C/G+C | Fresh template G C1 | Fresh template G+C C2 |
|---|---|---|---|---|
| Grammar variant | none has no grammar; G current primary uses task-agnostic; legacy template is diagnostic only (`docs/02_methodology_cluster1.md:72-85`, `docs/05_artifacts_and_results_registry.md:38-74`) | C has none; G+C current primary uses task-agnostic (`docs/03_methodology_cluster2.md:110-119`) | yes, `template_upper_bound` routed to `cluster1/grammar/triton_kernel.gbnf` (`cluster1/generation/grammar_variants.py:15-31`) | yes, supported by C2 generation, but paired replay must select fresh template G rather than legacy (`cluster2/modal/generation.py:55-83`, `cluster2/replay/manifest.py:208-220`) |
| Eval Level 0 | yes inside C1 compile checker via shared parse/signature validators (`cluster1/validation/compile_check.py:19-21`, `cluster1/validation/compile_check.py:195-218`) | yes, explicit parse/signature gates (`cluster2/modal/correctness_runner.py:153-205`) | yes, same C1 compile path (`cluster1/experiments/run_cluster1_modal.py:1003-1058`) | yes, same C2 correctness runner (`cluster2/modal/correctness_runner.py:70-150`) |
| Eval Level 1 | yes as cluster-specific compile gate/dummy launch, not via shared pipeline (`cluster1/validation/compile_check.py:220-274`) | yes, explicit `check_compile_level1` gate (`cluster2/modal/correctness_runner.py:208-233`) | yes, same C1 compile semantics (`cluster1/validation/compile_check.py:185-274`) | yes, same C2 Level 1 gate (`cluster2/modal/correctness_runner.py:208-233`) |
| Eval Level 2 | no (`cluster1/experiments/run_cluster1_modal.py:1-12`, `cluster1/tests/test_cluster_boundary.py:1040-1074`) | yes for generated rows (`cluster2/modal/correctness_runner.py:70-150`, `shared/eval/levels/level2_correctness.py:139-201`) | no | yes if run through generated G+C correctness path |
| `compile_success` | yes, recorded directly (`cluster1/results/dataclass.py:57-94`) | yes for generated rows, raw or derived (`cluster2/experiments/run_cluster2_modal.py:1388-1413`) | yes, direct C1 compile result | yes, raw/derived C2 compile evidence |
| `functional_success` | no row field; analyzer normalizes to false/unproven (`cluster1/results/dataclass.py:57-94`, `shared/analysis/factorial.py:224-235`) | yes, Level 2 outcome (`cluster2/results/dataclass.py:390-465`) | no; not comparable functionally | yes, Level 2 outcome if diagnostic run completes |
| `failure_code` | yes, compile/funnel failures (`cluster1/results/dataclass.py:109-136`) | yes, F0/F1/F2/F3 (`cluster2/results/dataclass.py:420-465`) | yes, same C1 failure semantics | yes, same C2 failure taxonomy |
| `grammar_valid` | yes for current G; not applicable for none; absent in legacy template artifact (`cluster1/experiments/run_cluster1_modal.py:903-956`) | yes for G+C; not applicable for C (`cluster2/results/dataclass.py:533-560`) | yes if current runner used | yes for G+C if current runner used |
| provenance | current task-agnostic G records current metadata; older baseline/template artifacts may lack some fields (`cluster1/experiments/run_cluster1_modal.py:218-250`, `docs/05_artifacts_and_results_registry.md:121-129`) | yes, model/tokenizer/Modal/replay provenance in generated rows (`cluster2/results/dataclass.py:298-329`, `cluster2/results/dataclass.py:875-987`) | yes if fresh current pipeline is used | yes if fresh current pipeline is used and manifest/registry preconditions are met |
| `scale_tier` | current artifacts may rely on analyzer annotation; future rows should record it (`.contracts/research/scale_policy.md:22-27`, `.contracts/research/scale_policy.md:64-92`) | same; generated metadata includes scale tier in current row contract (`cluster2/experiments/run_cluster2_modal.py:97-140`) | should record current scale tier | should record current scale tier |
| pairing identity | C1 rows are source controls; task-agnostic current artifact has missing-cell coverage warning (`docs/05_artifacts_and_results_registry.md:60-74`) | yes, C pairs to none and G+C pairs to G (`cluster2/experiments/run_cluster2_modal.py:1061-1066`, `cluster2/replay/cluster1_controls.py:552-680`) | must produce a fresh current template G control artifact | yes only after C2 selects that fresh template G artifact |
| analyzer role | compile diagnostic; C1 functional normalized false/unproven (`shared/analysis/factorial.py:224-235`) | primary functional analysis plus secondary compile diagnostic (`shared/analysis/factorial.py:60-62`) | diagnostic compile ceiling vs task-agnostic G | diagnostic functional ceiling vs task-agnostic G+C, separate from primary paper analysis |

## 9. Risks and caveats

- C1 is compile-only. It cannot establish numerical correctness.
- C1 `functional_success=False` in analyzer output means false/unproven for binary analysis, not observed Level 2 failure.
- A C1 `compile_success=True` template row could be numerically correct, but that would remain unmeasured unless a C2 template G+C run evaluates it.
- Template G-only rerun is enough for compile ceiling and grammar-funnel diagnostics, but not enough for functional correctness or G+C interaction claims.
- Template G+C is required for a full diagnostic ceiling because the research question's functional side lives in C2 Level 2.
- Current template G+C readiness depends on pre-run registration/manifest/hash-gate/analyzer separation so the diagnostic uses fresh current-pipeline template G rather than the legacy 180/180 template artifact.
- Current metrics do not measure speed/performance, robustness to unseen shapes, code quality/readability, generalization, tolerance variants, resource usage, or repeated-run determinism.

## 10. Recommendation

Proceed to the template pre-run docs/schema/registry planning work before any template Modal smoke. The next step should be to make the diagnostic route explicit: register a fresh current-pipeline template G artifact ID, ensure C2 template G+C replay selects that fresh artifact, extend hash/manifest validation as needed, and keep analyzer/report outputs separated from the primary task-agnostic paper analysis.

Run template G alone only if the immediate question is compile ceiling and grammar-funnel comparability with task-agnostic G. Run template G plus template G+C if the question is whether task-encoded/template G can reach functional parity or an upper-bound diagnostic ceiling under Cluster 2. No algorithmic evaluation code change is required by this audit, but manifest/registry/analyzer-report separation work must be complete before interpreting template G+C as current-pipeline diagnostic evidence.

## 11. Appendix

### Commands run

- `git status --short`
- `nl -ba docs/handoff/agentic_document_hub.md | sed -n '1,180p'`
- `nl -ba docs/handoff/document_version_registry.md | sed -n '1,160p'`
- `nl -ba docs/handoff/code_update_documentation_policy.md | sed -n '1,160p'`
- `rg "Level 0|Level 1|Level 2|level0|level1|level2|parse|signature|compile|correctness|functional_success|compile_success" cluster1 cluster2 shared docs .contracts audits -u`
- `rg "compile_check|CompileCheck|dummy|launch|triton.jit|compile_success|validate_signature|validate_source" cluster1 shared docs audits -u`
- `rg "correctness_runner|correctness_result|functional_success|torch.allclose|Level 2|F2_|F3_EVAL_PIPELINE|EvalResult" cluster2 shared docs audits -u`
- `rg "repair_loop|feedback|F2_|F0_|F1_|terminate|repair|correctness feedback|compile feedback" cluster2 shared docs audits -u`
- `rg "template_upper_bound|template G|template-G|triton_kernel.gbnf|grammar_variant|grammar_loader|grammar_path" cluster1 cluster2 shared docs .contracts audits -u`
- `rg "task_agnostic|task-agnostic|triton_kernel_agnostic|grammar_valid|gbnf_parse_valid|semantic_valid|rejection_layer" cluster1 cluster2 shared docs .contracts audits outputs -u`
- `rg "model_revision|tokenizer_revision|max_new_tokens|temperature|modal_image_sha|scale_tier|analysis_cli_annotation|provenance" cluster1 cluster2 shared docs .contracts audits outputs -u`
- `rg "baseline_repaired_l4_n20|task_agnostic_g_aligned_pipeline_n20_l4|c_paper_n20_l4|g_plus_c_paper_n20_l4|final_g_l4_n20" README.md docs .contracts audits outputs cluster1 cluster2 -u`
- `.venv/bin/python - <<'PY' ... PY` for artifact field inspection.
- Multiple `nl -ba <file> | sed -n 'START,ENDp'` commands for line-number evidence across required files.

### Artifact field inspection summary

- `outputs/cluster1/baseline_repaired_l4_n20.jsonl`: exists, 180 valid rows, no bad JSON. `compile_success=False` for 180 rows, `functional_success` absent, `grammar_active=False`, `compile_error_type=SignatureError`, `temperature=0.2`, complete 9 cells x 20 rows.
- `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl`: exists, 177 valid rows. `grammar_variant=task_agnostic`, grammar path `cluster1/grammar/triton_kernel_agnostic.gbnf`, grammar SHA present, `gbnf_parse_valid` 105 true/72 false, `semantic_valid` 49 true/128 false, `grammar_valid` 49 true/128 false, `compile_success` 3 true/174 false, `functional_success` absent, failure codes include F0/F1 and successful rows, model/tokenizer revisions present, Modal provenance SHA present.
- `outputs/cluster2/c_paper_n20_l4.jsonl`: exists, 180 valid rows. Grammar fields absent, `functional_success=False` for 180 rows, `failure_code=F0_PARSE` for 180 rows, raw `compile_success` absent in inspected fields, generated metadata includes model/tokenizer revisions, Modal image SHA, `max_new_tokens=2048`, `temperature=0.2`, and replay pair IDs.
- `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl`: exists, 177 valid rows. `grammar_variant=task_agnostic`, grammar path/SHA present, `gbnf_parse_valid` 100 true/77 false, `semantic_valid` 52 true/125 false, `grammar_valid` 52 true/125 false, `compile_success` 4 true/173 false, `functional_success=False` for 177 rows, failure codes include F2 numeric, F1 compile/runtime, F0 parse, and F3 eval pipeline, generated metadata includes current provenance and replay pair IDs.
- `outputs/cluster1/final_g_l4_n20.jsonl`: exists, 180 valid rows. Legacy template G has `grammar_active=True` and `compile_success=True` for 180 rows, but `functional_success`, `grammar_variant`, grammar path/SHA, split grammar validity fields, model/tokenizer revisions, Modal provenance, scale tier, max_new_tokens, and replay pair IDs are absent. It is valid only as legacy diagnostic compile-only evidence.

### Required conclusion answers

1. Cluster 1 actually evaluates parse/signature plus Triton import/JIT/dummy-launch compile acceptance, and stops before Level 2.
2. Cluster 2 actually evaluates Level 0 parse/signature, Level 1 compile, and Level 2 numerical correctness, with F2-only repair.
3. The C1/C2 asymmetry is intentional and acceptable with a report caveat: C1 functional outcomes are unmeasured/unproven, not observed failures.
4. Fresh template G can be run through C1 at compile parity with task-agnostic G.
5. Fresh template G+C can be run through the C2 evaluator surface, but only after current-pipeline template G registration/manifest/hash-gate/analyzer separation preconditions are satisfied.
6. Template G-only is not enough for functional correctness; template G+C is needed for the full diagnostic ceiling.
7. `compile_success` and `functional_success` are the right metrics for the current compile/correctness scope, but not for performance or generalization claims.
8. Before any template Modal smoke, complete the pre-run diagnostic routing work so new template rows are current-pipeline, provenance-complete, separately labeled, and not confused with the legacy 180/180 template artifact.
