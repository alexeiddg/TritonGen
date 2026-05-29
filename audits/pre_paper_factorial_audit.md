# TritonGen Pre-Paper Factorial Audit

Date: 2026-05-18

Repository root: `/Users/alexeidelgado/Desktop/TritonGen`

Audit target: strategic thesis alignment, factor integrity, grammar validity,
metric coherence, scale policy, run-set completeness, repair-boundary
correctness, and pre-spend readiness before additional GPU spend or
paper-scale factorial execution.

This audit is intentionally conservative. It does not implement fixes, mutate
contracts, redesign the thesis, refresh manifests, or run paper-scale jobs.
Every conclusion below is tied to repository code, contracts, manifests,
artifacts, or validation output observed during this audit.

## Table of Contents

1. [Evidence Standard](#evidence-standard)
2. [Validation Performed](#validation-performed)
3. [Executive Decision](#executive-decision)
4. [High-Priority Findings Register](#high-priority-findings-register)
5. [Block 1 - Strategic Alignment](#block-1---strategic-alignment)
6. [Block 2 - Grammar Specification](#block-2---grammar-specification)
7. [Block 3 - Metric Coherence](#block-3---metric-coherence)
8. [Block 4 - Scale and Pre-Spend](#block-4---scale-and-pre-spend)
9. [Risk Register by Class](#risk-register-by-class)
10. [Unresolved Ambiguities](#unresolved-ambiguities)
11. [Final Go/No-Go Recommendation](#final-gonogo-recommendation)

## Evidence Standard

| Label | Meaning |
|---|---|
| Verified | Directly observed in code, contracts, manifests, artifacts, or command output during this audit. |
| Inferred | Strongly supported by multiple repository facts, but not expressed as one literal statement in one source. |
| Speculative | Repository evidence is insufficient; the statement is a conditional estimate or planning judgment. |

Severity labels:

| Severity | Meaning |
|---|---|
| Critical | Can invalidate paper-scale data or make a headline claim indefensible. |
| High | Blocks honest paper-scale execution or creates serious reviewer-facing ambiguity. |
| Medium | Does not necessarily invalidate data, but must be disclosed, renamed, scoped, or cleaned before writing. |
| Low | Cleanup or supporting evidence gap that should not block bounded validation. |

Risk classes:

| Class | Scope |
|---|---|
| Methodological | Causal interpretation, factor isolation, baseline fairness, thesis alignment. |
| Engineering | Code behavior, schema consistency, runner behavior, tests. |
| Paper-writing | How claims, labels, and tables will be interpreted by reviewers. |
| Infrastructure | GPU spend, Modal/runtime gates, artifact freezing, reproducibility controls. |

## Validation Performed

Verified commands:

| Command | Result | Interpretation |
|---|---:|---|
| `git status --short` | no output | Workspace was clean at audit time. |
| `.venv/bin/python -m pytest cluster1/tests/test_grammar_acceptance.py -v` | `215 passed in 29.48s` | Local grammar fixture suite passes. The requested path `cluster1/grammar/test_grammar_acceptance.py` does not exist; the actual test file is `cluster1/tests/test_grammar_acceptance.py`. |
| `.venv/bin/python - <<'PY' ... verify_phase_minus1_g_generation_hashes() ... PY` | `VALID` | The current Phase -1 G source hash gate is valid. |
| `.venv/bin/python - <<'PY' ... validate_canonical_f2_smoke_artifacts() ... PY` | `VALID` | Canonical F2 smoke artifacts validate structurally. |
| `.venv/bin/python -m pytest shared/tests cluster2/tests -v` | `2 failed, 857 passed, 1 skipped in 214.35s` | Targeted shared/Cluster 2 suite exposes current pre-spend boundary drift. |

Targeted test failures:

| Failing test | Observed failure | Audit interpretation |
|---|---|---|
| `cluster2/tests/test_cluster2_boundary.py::test_shared_modal_files_match_phase_minus1_git_head[shared/modal_harness/smoke.py]` | Current hash `4c999a29a1e966635e186c16d211fe07a36ebd132e8ba47b150eaebab2691e30`; Phase -1 expected hash `03848df1d3196377a8bdaa363f5b7dd47f59cabcafd7f4011091ac933daa9e16`. | Verified boundary drift in a shared Modal harness file. |
| `cluster2/tests/test_cluster2_boundary.py::test_cluster1_generation_result_fields_match_phase_minus1` | Current `GenerationResult` fields include leading `failure_code`; frozen Phase -1 field list does not. | Verified schema drift relative to frozen Phase -1 boundary. |

Primary evidence anchors:

| Topic | Evidence |
|---|---|
| Thesis and factor vocabulary | `.contracts/research/research_scope.md:9-44` |
| Shared eval and failure taxonomy source of truth | `.contracts/research/research_scope.md:48-64` |
| G acceptance semantics and template upper-bound distinction | `.contracts/research/research_scope.md:77-126` |
| Scale tiers and paper n=20 rule | `.contracts/research/scale_policy.md:27-31`, `.contracts/research/scale_policy.md:171-185` |
| Cluster 2 replay contract | `.contracts/agentic/cluster2_contract.md:9-45` |
| Cluster 2 token-budget contract language | `.contracts/agentic/cluster2_contract.md:27-32`, `.contracts/agentic/cluster2_contract.md:68-75` |
| Current token-budget implementation behavior | `cluster2/experiments/run_cluster2_modal.py:1011-1013` |
| Current G/G+C grammar variant defaults | `cluster2/modal/generation.py:41-60` |
| Task-agnostic G n=20 block | `cluster2/contracts/frozen_cluster1_artifacts_manifest.json`, `cluster2/contracts/phase_minus1_manifest.json` |
| C feedback ownership | `cluster2/feedback/prompts.py`, `cluster2/feedback/repair_loop.py` |
| P status | `cluster3/README.md`, `shared/factors/registry.py` |
| Factor-cell vocabulary | `shared/factors/cells.py`, `shared/factors/registry.py` |
| Primary C2 analysis | `shared/analysis/factorial.py` |
| Metric implementations | `shared/eval/metrics/pass_at_k.py`, `shared/eval/metrics/repair.py`, `shared/eval/metrics/equal_attempts.py`, `shared/eval/metrics/coverage.py`, `shared/eval/aggregation.py` |
| Failure taxonomy | `shared/eval/failure_taxonomy.py` |

Not run:

| Activity | Reason |
|---|---|
| Full `.venv/bin/python -m pytest -v` | The targeted suite already found pre-spend boundary failures on audit-critical paths. |
| Modal paper-scale jobs | Explicitly forbidden. |
| New GPU experiments | Explicitly forbidden. |
| Contract or manifest edits | Explicitly forbidden. |

## Executive Decision

**Go/no-go: NO-GO for additional paper-scale GPU spend that would produce paper data.**

Verified blockers:

1. **Cluster 2 boundary tests fail against frozen Phase -1 invariants.** The current Phase -1 G hash gate is valid, but the broader shared/Cluster 2 boundary suite fails on `shared/modal_harness/smoke.py` hash drift and `GenerationResult` field-list drift. This is a pre-spend blocker because unresolved boundary drift can invalidate reproducibility claims.
2. **Task-agnostic G is not frozen at paper scale.** The selected task-agnostic artifact is `g_task_agnostic_n5_l4_rerun`; manifest state says paper rows are insufficient and n=20 remains pending.
3. **The full eight-cell factorial cannot be executed today.** Cluster 3 is explicitly `NOT STARTED - contract TBD`; therefore P, G+P, C+P, and G+C+P are not paper-ready.
4. **The token-budget replay contract and current runner behavior diverge.** The Cluster 2 contract describes token-budget mismatch as a hard failure, while current runner code intentionally permits fresh-generation budget migration against frozen replay manifests.
5. **Strict/template G is a composite surface-and-template upper bound.** It is useful when labeled correctly, but cannot anchor a pure grammar-only causal claim.

Verified strengths:

1. The current research scope already distinguishes strict/template upper-bound G from task-agnostic G.
2. The canonical eight-cell vocabulary exists in shared factor code.
3. Replay-control infrastructure is strong in design: none/G controls are frozen, manifest-backed, seed-paired, and preflighted.
4. C repair boundaries are clean in implementation: only F2 correctness failures trigger repair feedback.
5. Canonical F2 smoke artifacts validate and show real F2 repair-loop activation.
6. The permissive baseline is explicitly diagnostic and quantifies strict surface-contract cost without replacing the strict baseline.

Recommended gating decision:

| Work item | Recommendation |
|---|---|
| Static audit and report writing | Go. |
| Fixing/refreezing Phase -1 boundary drift | Go, but only as an explicit freeze/contract operation. |
| Completing task-agnostic G n=20 controls | Go as pre-paper gate work after boundary drift is resolved. |
| Cluster 2 C/G+C paper-scale runs | No-go until boundary tests pass and task-agnostic G n=20 is frozen. |
| Full 2^3 factorial | No-go until Cluster 3/P has a contract, implementation, smoke validation, development validation, and paper freeze. |

## High-Priority Findings Register

| ID | Finding | Status | Severity | Risk class | Evidence | Recommended action |
|---|---|---:|---|---|---|---|
| F-01 | Cluster 2 boundary suite fails against Phase -1 frozen invariants. | Verified | Critical | Engineering, Infrastructure | `cluster2/tests/test_cluster2_boundary.py` output; `shared/modal_harness/smoke.py`; `cluster1/results/dataclass.py` | Stop paper spend until drift is either reverted or explicitly re-frozen. |
| F-02 | Primary task-agnostic G lacks paper-scale n=20 frozen controls. | Verified | Critical | Methodological, Infrastructure | `cluster2/contracts/frozen_cluster1_artifacts_manifest.json`, `cluster2/contracts/phase_minus1_manifest.json` | Complete/freeze task-agnostic G n=20 before primary G/G+C paper claims. |
| F-03 | P factor is not implemented; full 2^3 factorial is unavailable. | Verified | High | Methodological | `cluster3/README.md`, `shared/factors/registry.py` | Scope near-term work to Cluster 1/2 or build Cluster 3 first. |
| F-04 | Token-budget replay contract and code behavior diverge. | Verified | High | Methodological, Engineering | `.contracts/agentic/cluster2_contract.md`; `cluster2/experiments/run_cluster2_modal.py:1011-1013` | Resolve before paper runs: either enforce hard failure or update contract with explicit rationale. |
| F-05 | Strict/template G bundles grammar with surface contract and task-family structure. | Verified | High | Methodological, Paper-writing | `cluster1/grammar/triton_kernel.gbnf`; `.contracts/research/research_scope.md` | Label as `template_upper_bound`; do not use as pure grammar evidence. |
| F-06 | Official Triton tutorial 100% acceptance is not established. | Verified | Medium | Paper-writing | `.contracts/agentic/reference/triton_corpus.md`; `cluster1/grammar/corpus/api_coverage_report.md` | Claim API allow-list coverage, not full tutorial fixture acceptance, unless a separate acceptance manifest is produced. |
| F-07 | Some docs/plans refer to broader or older factor semantics than current executable code. | Verified | Medium | Paper-writing | `.contracts/agentic/cluster2_integrated_agent_plan.md`; `cluster2/modal/generation.py`; `shared/factors/registry.py` | Declare current contracts/manifests authoritative and mark old plan text superseded. |

## Block 1 - Strategic Alignment

### Q1. Does the current factorial design still answer the thesis question?

**Conclusion: partially, but not at paper scale today.**

Verified:

| Design element | Repository state | Thesis effect |
|---|---|---|
| Eight-cell vocabulary | `shared/factors/cells.py` and `.contracts/research/research_scope.md` define none/G/C/P/G+C/G+P/C+P/G+C+P. | The intended thesis design still exists. |
| Cluster staging | `shared/factors/registry.py` scopes Cluster 1 to none/G, Cluster 2 to none/G/C/G+C, Cluster 3 to P-containing cells. | The repository intentionally stages rather than completes the factorial. |
| Strict vs task-agnostic G distinction | `.contracts/research/research_scope.md` labels template grammar as upper bound and task-agnostic G as primary route. | The design can answer nuanced grammar questions if labels are preserved. |
| Replay controls | `.contracts/agentic/cluster2_contract.md` requires none/G replay controls paired by kernel class, dtype, and base seed. | Supports causal C and G+C comparisons after controls are complete. |
| P | `cluster3/README.md` states Cluster 3 is not started and contract is TBD. | Full 2^3 thesis remains blocked. |

Inferred:

The current design can support three separate claims, but only the first two have partial executable support:

| Claim tier | Current status |
|---|---|
| Strict/template grammar upper bound on compileability | Supported by frozen Cluster 1 artifacts, with clear caveats. |
| Task-agnostic grammar and C feedback four-cell study | Methodologically aligned, but blocked by task-agnostic G n=20 and boundary drift. |
| Full G/C/P factorial | Not available until Cluster 3 exists. |

Strict vs permissive baselines:

| Baseline | Verified artifact | What it measures | Role |
|---|---|---|---|
| Strict baseline | `outputs/cluster1/baseline_repaired_l4_n20.jsonl`; 180 rows; 0/180 strict compile success. | Whether unconstrained candidates satisfy the locked generated surface and strict compile harness. | Primary strict control and replay source for none. |
| Permissive baseline | `outputs/cluster2/diagnostics/permissive_compile_baseline_n180.jsonl`; summary reports 38/180 permissive compile successes. | Whether unconstrained text contains any extractable/launchable Triton kernel under relaxed diagnostics. | Diagnostic for surface-contract cost, not primary outcome. |

Answer:

The design still answers the thesis only if the paper distinguishes strict surface control, task-agnostic grammar, correctness feedback, and future profiler/compiler repair. It does not currently answer the complete factorial thesis because task-agnostic G n=20 and P are missing.

Severity: **High** if represented as complete; **Medium** if scoped as staged Cluster 1/2 evidence.

### Q2. Does keeping the surface contract inside G preserve or weaken publishability?

**Conclusion: it preserves publishability for an "inference control package" claim and weakens pure grammar attribution.**

Verified:

| Evidence | Interpretation |
|---|---|
| `cluster1/grammar/triton_kernel.gbnf` encodes imports, helpers, family bodies, launcher signatures, output allocation, grid, bracket launch, and return shape. | Strict G bundles syntax, API, harness surface, and task-template structure. |
| `cluster1/grammar/triton_kernel_agnostic.gbnf` still requires a public launcher, typed args, output allocation, bracket launch, and return. | Task-agnostic G reduces task-template bias but keeps a harness-interface contract. |
| Strict G is 180/180 compile success, while task-agnostic n=5 rerun is 6/45 compile success. | Much of strict G lift plausibly comes from surface/template constraints. |
| Permissive baseline is 38/180 compile success. | Strict 0/180 baseline partly measures interface/surface mismatch. |

Analysis:

| Dimension | Assessment |
|---|---|
| Internal validity | Preserved for the implemented G intervention. Weakened for pure grammar claims because G includes surface contract and interface constraints. |
| Reviewer interpretation risk | High if tables say only `G`. Lower if they say `G_template_upper_bound` and `G_task_agnostic`. |
| Causal attribution risk | High for strict/template G; moderate for task-agnostic G because harness-interface rules remain. |
| Baseline fairness | Strict none vs strict G is fair for canonical generated-surface compile acceptance. It is not fair as a pure grammar-vs-no-grammar estimate unless permissive diagnostics are shown. |

Publishability:

| Claim | Defensibility |
|---|---|
| "A family-scoped grammar/surface package can force compile acceptance on a locked surface." | Defensible. |
| "Task-agnostic grammar contributes less than prior literature implies." | Pending n=20; potentially defensible if surface constraints are disclosed. |
| "Grammar alone achieves 180/180 compileability." | Not defensible without heavy qualification. |

Recommended action: keep surface contract inside G for reproducibility, but make it explicit in factor labels and methods.

### Q3. Factor-definition divergences between code and contracts/docs

| Divergence | Contract/doc definition | Code/artifact definition | Severity | Published-claim effect | Recommended action |
|---|---|---|---|---|---|
| Token-budget mismatch | `.contracts/agentic/cluster2_contract.md` says prompt/model/dtype/temperature/token-budget mismatches against frozen controls should be hard failures. | `cluster2/experiments/run_cluster2_modal.py:1011-1013` says replay token budgets are frozen provenance, not a constraint on fresh-generation budget. Tests include budget-migration behavior. | High | Affects fairness/equal-attempt interpretation if generated cells get different budget than controls. | Resolve before paper runs by enforcement or explicit contract update. |
| G+C grammar variant | Older integrated plan text discusses template upper-bound lineage. | Current `cluster2/modal/generation.py` defaults G+C to `task_agnostic` and maps template as separate upper-bound control. | Medium | Could confuse paper readers if old plan text is cited. | Treat current contract/manifests/code as authoritative; label older plan superseded. |
| P factor | Research scope includes P in final factorial. | `cluster3/README.md` says not started; registry reserves P conditions for Cluster 3. | High | Full factorial claims impossible now. | Do not claim P results until implemented and frozen. |
| Grammar acceptance | Research docs separate GBNF parse validity and semantic validation. | Code carries `gbnf_parse_valid`, `semantic_valid`, `grammar_valid`, `rejection_layer`. | Low | Mostly aligned; current schema drift around `failure_code` must be frozen. | Keep schema documented and boundary tests passing. |
| Permissive baseline | Diagnostic-only surface-cost analysis. | Artifact summary is diagnostic-only and not used as primary replay. | Low | Aligned; risk only if promoted to primary. | Keep diagnostic label in tables. |

### Q4. Which baseline should be primary: strict 0/180 or permissive 38/180?

**Primary baseline for paper claims should be the strict baseline, with the permissive baseline shown beside it as a diagnostic.**

| Baseline | What it measures | Claim it supports | Paper role |
|---|---|---|---|
| Strict baseline 0/180 | Performance of unconstrained generations under the canonical generated-surface compile harness. | "Under the locked evaluation surface, unconstrained candidates rarely satisfy the contract." | Primary control for strict compile and replay. |
| Permissive baseline 38/180 | Extractable launchable kernels under relaxed parsing/launch diagnostics. | "The strict surface contract accounts for meaningful baseline loss." | Required diagnostic context for fairness and attribution. |

The strict baseline anchors the controlled experiment because Cluster 2 replay and shared metrics depend on frozen strict artifacts. The permissive baseline must appear in the paper to prevent the misleading interpretation that unconstrained generations have zero latent Triton competence.

## Block 2 - Grammar Specification

### Q5. Classification of major task-agnostic grammar rules

Primary grammar file: `cluster1/grammar/triton_kernel_agnostic.gbnf`.

| Rule family | Example rules/surfaces | Classification | Rationale |
|---|---|---|---|
| File boundary and no prose | start symbols, code-only output | Harness-interface-derived | The evaluator expects parseable code without markdown/prose. |
| Required imports | `import torch`, `import triton`, `import triton.language as tl` | Harness-interface-derived | Imports are fixed for generated artifact reproducibility. |
| Python definitions | `def`, arguments, returns, statements | Language-derived | Python syntax. |
| Decorators | `@triton.jit`, `@triton.autotune`, `@triton.heuristics` | API-derived | Triton API surface. |
| Helper section | one or more jit helpers before launcher | Convenience-derived | Structures generation but is not required by Python/Triton generally. |
| Public launcher | typed torch/scalar args and `torch.Tensor` return | Harness-interface-derived | Needed by generated evaluation interface. |
| Output allocation | wrapper creates output tensors | Harness-interface-derived | Couples kernel code to evaluation harness expectations. |
| Grid construction | wrapper grid expression | Harness-interface-derived/API-derived | Required for bracket launch; uses Triton launch idiom. |
| Bracket launch | `kernel[grid](...)` | API-derived and harness-interface-derived | Triton launch syntax plus harness requirement for single public launcher. |
| Return output | launcher returns one tensor | Harness-interface-derived | Evaluation expects a concrete output. |
| `tl.*` allow-list | program ids, arange, load/store, dot, reductions, math, atomics, RNG, inline asm, compiler hints | API-derived | Mirrors Triton language API coverage. |
| `tl.constexpr` and dtype literals | constexpr annotations, dtype constants | API-derived | Triton compile-time API. |
| Tensor/block expressions | arithmetic, masks, offsets, pointer expressions | Language-derived/API-derived | Python expression syntax plus Triton tensor semantics. |
| Control flow | `if`, `for`, `while`, `tl.range`, `tl.static_range` | Language-derived/API-derived | Python and Triton loop APIs. |
| Indentation | explicit four-space indentation levels | Convenience-derived | Generation/parsing convenience; not a thesis-level grammar fact. |
| Fixed arity/keyword forms | restricted call shapes for APIs | Convenience-derived/API-derived | Mix of API constraints and grammar tractability. |
| Exclusions | no `triton.testing`, runtime internals, benchmarking/profiling, gluon | Harness-interface-derived and intentional restriction | Keeps generated kernels inside evaluation scope. |
| Limited arbitrary interfaces | no arbitrary multi-output/public API | Harness-interface-derived | Prevents harness ambiguity. |
| Inline asm/RNG support | `tl.inline_asm_elementwise`, random APIs | API-derived with experimental-risk note | Triton APIs, but likely less exercised by local fixtures. |

No major rule should be described as purely "arbitrary" without qualification. The arbitrary/experimental risk is mainly the combination of fixed launcher conventions, limited call forms, and less-tested API families.

### Q6. Does the task-agnostic grammar accept 100% of the official Triton tutorial corpus?

**Conclusion: not verified. A 100% tutorial acceptance claim should not be made.**

Verified:

| Evidence | Meaning |
|---|---|
| `.contracts/agentic/reference/triton_corpus.md` is a reference corpus used for API coverage and scope analysis. | It is not an acceptance manifest proving every tutorial snippet parses under the task-agnostic grammar. |
| `cluster1/grammar/corpus/api_coverage_report.md` reports 92 reference functions compared and 92 grammar functions extracted. | The grammar allow-list matches extracted API references. |
| The same report states the comparison is offline and does not use tutorial fixture acceptance as evidence. | API coverage is not equivalent to full tutorial acceptance. |
| Local grammar fixture suite passes 215 tests. | Local curated acceptance/rejection fixtures pass. |
| Existing audit `audits/task_agnostic_grammar_n5_incompatibility_audit.md` reports incompatibility between an old n=5 artifact and current grammar, including launcher-tail rejections. | Historical generated artifacts are not universal acceptance evidence. |

Rejection inventory:

| Rejection type | Verified examples | Classification | Thesis impact |
|---|---|---|---|
| Raw tutorial code using benchmarking/profiling/testing infrastructure | Scope exclusions in reference corpus docs | Intentional restriction | Low if paper claims kernel-generation scope only; high if claiming full tutorial acceptance. |
| Runtime internals, gluon, CUDA helper surfaces | Out-of-scope in reference docs | Unsupported Level 2+ or non-target feature | Low for current thesis, must be disclosed. |
| Arbitrary tutorial launch/wrapper shapes | Single-launcher/bracket-launch grammar rules | Harness artifact | Medium because it affects "task-agnostic" breadth. |
| Old generated rows missing launcher tail | Existing incompatibility audit | Harness artifact / grammar-version drift | Medium for reproducibility and artifact compatibility. |

Because no per-tutorial acceptance artifact was found, the audit cannot list every official tutorial rejection without fabricating. The defensible statement is: the task-agnostic grammar has broad API allow-list coverage and passes local acceptance fixtures, but 100% official tutorial acceptance is unproven.

### Q7. If single-launcher and bracket-launch rules were removed, what minimum harness changes would be required?

Verified current dependency:

| Current assumption | Evidence |
|---|---|
| Generated code exposes a predictable public launcher returning a tensor. | `cluster1/grammar/triton_kernel_agnostic.gbnf`, Cluster 1 result/eval shape expectations. |
| Cluster 2 replay and correctness evaluation consume frozen Cluster 1 rows with predictable metadata and callable shapes. | `cluster2/replay/*`, `cluster2/experiments/run_cluster2_modal.py`, `cluster2/modal/correctness.py`. |

Minimum required changes:

| Surface | Required change | Complexity |
|---|---|---|
| Candidate extraction | Discover one or more `@triton.jit` kernels and public Python launchers from arbitrary code. | Medium-high |
| Interface inference | Infer input tensors, scalar meta-parameters, output allocation, and return conventions. | High |
| Harness generation | Build callable adapters dynamically for one-output and possibly multi-output kernels. | High |
| Correctness fixtures | Map arbitrary interfaces onto Level 0/1/2 task specs. | High |
| Replay manifests | Store adapter decisions, inferred signatures, and extraction provenance. | Medium-high |
| Metrics | Separate "interface extraction success" from compile/correctness success. | Medium |
| Reproducibility | Freeze adapter version, AST rules, and inferred signature metadata. | High |

Estimated effort: **5-10 engineering days** for a minimal arbitrary-interface prototype for current three task families; **2-4 weeks** for a robust paper-grade adapter. Risk of breaking reproducibility: **High**, because the adapter would become a new factor-like intervention unless frozen and disclosed.

## Block 3 - Metric Coherence

### Q8. Metrics currently reported or implemented

| Metric | Implementation/docs | Research question answered | Thesis support | Recommendation |
|---|---|---|---|---|
| `compile@1` / `compile_at_1` | `shared/eval/metrics/pass_at_k.py`, Cluster 1 analysis | Does a single candidate compile under the strict harness? | Direct for Cluster 1 compile claims. | Keep. |
| `pass@1` / functional success | `shared/eval/metrics/repair.py`, `shared/analysis/factorial.py` | Does the candidate pass correctness tests? | Direct for Cluster 2. | Keep. |
| `pass_rate_within_n` / equal attempts | `shared/eval/metrics/equal_attempts.py` | What is the per-cell success rate under matched base-seed windows? | Direct for paired C2 fairness. | Keep, but label carefully. |
| `convergence_rate` | `shared/eval/metrics/repair.py` | Do generated repair loops eventually reach success? | Direct for C. | Keep. |
| `attempt_count` / repair iterations | `shared/eval/metrics/repair.py`, Cluster 2 result rows | How much repair budget is consumed? | Diagnostic for C. | Keep diagnostic. |
| `permissive_compile_rate` | `shared/eval/diagnostics/permissive_compile.py` and diagnostics artifact | How much strict baseline failure is surface-contract cost? | Diagnostic, supports fairness explanation. | Keep diagnostic only. |
| `coverage_feasible_rate` and coverage metrics | `shared/eval/metrics/coverage.py` | Does evaluation cover intended cells/tasks? | Infrastructure diagnostic. | Keep as gate/appendix. |
| failure-code rates F0/F1/F2/F3 | `shared/eval/failure_taxonomy.py`, aggregation | Where do failures occur? | Direct for factor ownership and repair boundary. | Keep. |
| compile_success in Cluster 2 | `shared/analysis/factorial.py` secondary | Do correctness-stage rows also compile? | Diagnostic only for C2. | Keep secondary. |
| fast/performance metrics (`fast@p`, latency, throughput, speedup) | Present in future docs/schema; forbidden in C2 result rows | Would P improve performance? | Future P only. | Cut from C1/C2 primary paper tables. |
| cost/GPU-time metrics | Docs/plans mention spend concerns; artifacts do not contain enough pricing/runtime data | What is efficiency/cost? | Diagnostic only if measured. | Do not report as metric unless captured. |

### Q9. Metric gaps, duplicates, and misleading risks

Metrics with no current research question:

| Metric/surface | Issue | Action |
|---|---|---|
| C2 latency/throughput/speedup fields | Forbidden in `cluster2/results/dataclass.py`; P not implemented. | Do not include in C2 paper tables. |
| Future P `fast@p` language | No Cluster 3 implementation. | Mark future only. |

Research questions with no complete metric:

| Research question | Gap | Severity |
|---|---|---|
| Does P independently repair compile/performance failures? | No Cluster 3 implementation or metric path. | High for full factorial. |
| What is dollar GPU cost per missing cell? | No reliable price/runtime artifact for all runs. | Medium; do not fabricate. |
| Does task-agnostic G accept official tutorial corpus? | No acceptance manifest. | Medium paper-writing risk. |

Duplicated or drift-prone metrics:

| Metric | Drift risk | Evidence |
|---|---|---|
| Compile success | Exists in Cluster 1 artifacts, shared eval, Cluster 2 diagnostics, and permissive diagnostics with different harness strictness. | Must label strict vs permissive vs secondary C2 compile. |
| Pass/convergence | `repair.py`, `equal_attempts.py`, and `factorial.py` each summarize success differently. | Use `shared/analysis/factorial.py` for paper tables and explain row semantics. |
| Coverage | Artifact completeness, equal-attempt base-seed coverage, and grammar API coverage use similar language. | Rename table columns to avoid conflating them. |

Metrics that risk misleading interpretation:

| Metric | Misleading interpretation | Required guardrail |
|---|---|---|
| Strict 0/180 baseline | "The model cannot write any compilable Triton." | Show permissive 38/180 diagnostic. |
| Strict G 180/180 | "Pure grammar solves compileability." | Label template upper-bound. |
| Task-agnostic n=5 compile rate | "Paper G performance." | Mark development only, not paper eligible. |
| Equal-attempt rates | "Every row has the same number of repair attempts." | Explain per-base-seed cell matching and generated-vs-replay semantics. |

### Q10. Consistency of key metrics across clusters

| Metric | Cluster 1 | Cluster 2 | Cluster 3 | Shared eval reused? | Drift assessment |
|---|---|---|---|---|---|
| `compile@1` | Primary strict compile via Cluster 1 eval/artifacts. | Secondary diagnostic in C2 analysis. | Not present. | Partially, through shared eval and analysis helpers. | Medium drift because permissive diagnostics use different semantics. |
| `pass@1` | Not primary; compile-level only. | Primary functional success in `shared/analysis/factorial.py` and repair metrics. | Not implemented. | Yes for C2. | Low within C2; absent for P. |
| `fast@p` | Not primary. | Forbidden in C2 result rows. | Future only. | No implemented P metric. | High if discussed as current. |
| `convergence_rate` | Not applicable. | `shared/eval/metrics/repair.py` over generated rows. | Not implemented. | Yes for C2. | Low for C2. |
| `permissive_compile_rate` | Diagnostic artifact derived from baseline. | Stored under `outputs/cluster2/diagnostics`. | Not applicable. | Dedicated diagnostic code. | Low if labeled diagnostic. |
| Coverage metrics | Artifact/cell coverage and grammar API coverage. | Equal-attempt/replay coverage and condition coverage. | Not implemented. | Mixed. | Medium naming risk. |

### Q11. Does F0/F1/F2/F3 taxonomy map cleanly onto repair factor ownership?

**Conclusion: yes for current C ownership; unresolved for future P interactions.**

Verified:

| Failure class | Current meaning | Current repair owner |
|---|---|---|
| F0 | Parse/extraction/surface failures | No C repair. |
| F1 | Compile/runtime/import/signature failures | No C repair in Cluster 2. Future P likely owner, but not implemented. |
| F2 | Correctness failures: numeric large, NaN, shape mismatch | C repair owner. |
| F3 | Timeout/resource/infrastructure failures | No C repair. |

Evidence:

| Boundary | Evidence |
|---|---|
| C feedback prompt allows only F2 codes | `cluster2/feedback/prompts.py` |
| Repair loop terminates non-F2 without feedback | `cluster2/feedback/repair_loop.py` |
| Targeted shared/Cluster 2 suite passes non-F2 termination tests despite two unrelated boundary failures | `cluster2/tests` result summary |
| P not implemented | `cluster3/README.md` |

Answers:

| Question | Answer |
|---|---|
| Does C ever repair F1? | Verified no in current Cluster 2 repair path. |
| Does P ever repair F2? | Verified no current P implementation exists. |
| Do any repair loops cross failure classes? | Verified no for C; future C+P behavior is unresolved. |
| Does taxonomy support clean causal claims? | Yes for C-only F2 repair claims; no complete answer for full factorial until P boundaries are implemented and tested. |

## Block 4 - Scale and Pre-Spend

### Q12. Artifact inventory

Paper tier definitions are from `.contracts/research/scale_policy.md`: smoke is never research evidence, development is not paper-table evidence, and paper requires frozen n=20 rows per cell unless a contract says otherwise.

| Artifact path | Scale tier | Sample size | Factor coverage | Frozen? | Intended use | Paper eligible? | Smoke only? | Development only? |
|---|---:|---:|---|---|---|---|---|---|
| `cluster2/contracts/frozen_cluster1_artifacts_manifest.json` | manifest | 3 selected C1 artifacts | none/G controls | yes | Freeze and replay source registry | yes as manifest | no | no |
| `cluster2/contracts/phase_minus1_manifest.json` | manifest | boundary manifest | C2 preflight | yes, but currently boundary tests fail | Phase -1 boundary gate | yes only after tests pass | no | no |
| `outputs/cluster1/baseline_repaired_l4_n20.jsonl` | paper/control | 180 | none strict baseline | yes, manifest-selected | Frozen none replay | yes | no | no |
| `outputs/cluster1/final_g_l4_n20.jsonl` | paper/control, template upper bound | 180 | strict/template G | yes, manifest-selected | Template upper-bound replay/diagnostic | yes only as template upper bound | no | no |
| `outputs/cluster1/final_none_vs_g_l4_n20.jsonl` | paper/control aggregate | 360 | none + strict/template G | derived | Combined C1 comparison | yes if labels preserved | no | no |
| `outputs/cluster1/task_agnostic_g_all_n5_l4_rerun.jsonl` | development | 45 | task-agnostic G | manifest-known, not paper-frozen | Task-agnostic development control | no | no | yes |
| `outputs/cluster1/task_agnostic_g_current_grammar_n5_l4.jsonl` | development | 45 | task-agnostic G | no | Earlier task-agnostic run | no | no | yes |
| `outputs/cluster1/smoke/metadata_smoke_task_agnostic_g_elementwise_n1.jsonl` | smoke | 3 | task-agnostic G smoke | no | Metadata smoke | no | yes | no |
| `outputs/cluster1/baseline_repaired_l4_smoke_n1.jsonl` | smoke | 3 | none | no | Baseline smoke | no | yes | no |
| `outputs/cluster1/full_baseline_n20.jsonl` | superseded/dev | 180 | none | no | Historical baseline | no unless re-declared | no | yes |
| `outputs/cluster1/full_g_n20.jsonl` | superseded/dev | 180 | G | no | Historical G | no | no | yes |
| `outputs/cluster1/full_none_vs_g_n20.jsonl` | superseded/dev | 360 | none + G | no | Historical comparison | no | no | yes |
| `outputs/cluster1/g_all_surface_hardened_n20.jsonl` | development | 180 | G surface-hardened | no | Hardening analysis | no | no | yes |
| `outputs/cluster1/g_all_surface_hardened_n5.jsonl` | development | 45 | G surface-hardened | no | Hardening analysis | no | no | yes |
| `outputs/cluster1/g_all_post_hardening_n5_l4.jsonl` | development | 45 | G post-hardening | no | Hardening analysis | no | no | yes |
| `outputs/cluster1/repaired_none_vs_g_n20.jsonl` | superseded/dev | 360 | none + G | no | Historical comparison | no | no | yes |
| `outputs/cluster2/diagnostics/permissive_compile_baseline_n180.jsonl` | diagnostic | 180 | none permissive | no as primary | Surface-cost diagnostic | appendix only | no | no |
| `outputs/cluster2/diagnostics/permissive_compile_baseline_summary.json` | diagnostic | summary | none permissive | no as primary | Reports 38/180 permissive compile successes | appendix only | no | no |
| `outputs/cluster2/smoke_none_replay_phase12.jsonl` | smoke | 1 | none replay | no | C2 replay smoke | no | yes | no |
| `outputs/cluster2/smoke_G_replay_phase12.jsonl` | smoke | 1 | G replay | no | C2 replay smoke | no | yes | no |
| `outputs/cluster2/smoke_C_phase12.jsonl` | smoke | 1 | C | no | C generation smoke | no | yes | no |
| `outputs/cluster2/smoke_GC_phase12.jsonl` | smoke | 1 | G+C | no | G+C generation smoke | no | yes | no |
| `outputs/cluster2/smoke_seed_pairing_validation.jsonl` | smoke | 3 | C | no | Seed pairing smoke | no | yes | no |
| `outputs/cluster2/smoke_seed_pairing_validation_none.jsonl` | smoke | 3 | none replay | no | Seed pairing smoke control | no | yes | no |
| `outputs/cluster2/smoke_f2_repair_relu.jsonl` | smoke | 2 | C, elementwise | canonical smoke | F2 repair activation/convergence smoke | no | yes | no |
| `outputs/cluster2/smoke_f2_repair_softmax.jsonl` | smoke | 2 | C, reduction | canonical smoke | F2 repair activation smoke | no | yes | no |
| `outputs/cluster2/smoke_f2_repair_matmul.jsonl` | smoke | 2 | C, matmul | canonical smoke | F2 repair activation smoke | no | yes | no |
| `cluster2/results/**` | mixed | varies | C2 result schemas/tests | no paper result found | Result schema and generated outputs | depends on explicit manifest | no | depends |

Completeness supplement for additional discovered artifact files under `outputs/cluster1`, `outputs/cluster2`, and `cluster2/contracts`:

| Artifact path | Scale tier | Sample size | Factor coverage | Frozen/not frozen | Intended use | Paper eligible? | Smoke only? | Development only? |
|---|---:|---:|---|---|---|---|---|---|
| `cluster2/contracts/cluster2_plan_hash.txt` | contract | n/a | Cluster 2 plan hash | frozen marker | Contract provenance | evidence only | no | no |
| `outputs/cluster1/baseline_repaired_l4_n20.jsonl.meta.json` | paper/control metadata | n/a | none strict baseline | manifest-selected | Metadata sidecar | yes with parent artifact | no | no |
| `outputs/cluster1/baseline_repaired_l4_n20_summary.md` | summary | n/a | none strict baseline | derived | Human summary | appendix only | no | no |
| `outputs/cluster1/baseline_repaired_l4_smoke_n1.jsonl.meta.json` | smoke metadata | n/a | none | not frozen | Metadata sidecar | no | yes | no |
| `outputs/cluster1/cluster1_final_summary.md` | summary | n/a | Cluster 1 final | derived | Human summary | appendix only | no | no |
| `outputs/cluster1/diagnostics/baseline_revalidation_aligned_pipeline.jsonl` | diagnostic | 180 | baseline revalidation | not paper-frozen | Diagnostic reclassification | no | no | no |
| `outputs/cluster1/diagnostics/baseline_revalidation_aligned_pipeline_parse_reclassification.jsonl` | diagnostic | 180 | baseline parse reclassification | not paper-frozen | Diagnostic reclassification | no | no | no |
| `outputs/cluster1/figures/compile_acceptance_by_kernel.png` | figure | n/a | compile acceptance | derived | Plot artifact | only if regenerated from eligible data | no | no |
| `outputs/cluster1/figures/compile_acceptance_headline.png` | figure | n/a | compile acceptance | derived | Plot artifact | only if regenerated from eligible data | no | no |
| `outputs/cluster1/figures/compile_pass_at_k.png` | figure | n/a | compile/pass metric | derived | Plot artifact | only if regenerated from eligible data | no | no |
| `outputs/cluster1/figures/diversity_by_kernel.png` | figure | n/a | diversity | derived | Plot artifact | diagnostic only | no | no |
| `outputs/cluster1/figures/failure_distribution.png` | figure | n/a | failure distribution | derived | Plot artifact | only if regenerated from eligible data | no | no |
| `outputs/cluster1/figures/masked_token_rate_by_kernel.png` | figure | n/a | decoding diagnostics | derived | Plot artifact | diagnostic only | no | no |
| `outputs/cluster1/final_g_l4_n20.jsonl.meta.json` | paper/control metadata | n/a | strict/template G | manifest-selected | Metadata sidecar | yes with parent artifact | no | no |
| `outputs/cluster1/final_none_vs_g_l4_n20_summary.md` | summary | n/a | none + strict/template G | derived | Human summary | appendix only | no | no |
| `outputs/cluster1/full_baseline_n20.jsonl.meta.json` | superseded metadata | n/a | none | not frozen | Metadata sidecar | no | no | yes |
| `outputs/cluster1/full_baseline_n20_summary.md` | superseded summary | n/a | none | not frozen | Human summary | no | no | yes |
| `outputs/cluster1/full_g_n20.jsonl.meta.json` | superseded metadata | n/a | G | not frozen | Metadata sidecar | no | no | yes |
| `outputs/cluster1/full_none_vs_g_n20_summary.md` | superseded summary | n/a | none + G | not frozen | Human summary | no | no | yes |
| `outputs/cluster1/g_all_post_hardening_n5_l4.jsonl.meta.json` | development metadata | n/a | G | not frozen | Metadata sidecar | no | no | yes |
| `outputs/cluster1/g_all_post_hardening_n5_l4_summary.md` | development summary | n/a | G | not frozen | Human summary | no | no | yes |
| `outputs/cluster1/g_all_surface_hardened_n2.jsonl` | development | 18 | G surface-hardened | not frozen | Hardening run | no | no | yes |
| `outputs/cluster1/g_all_surface_hardened_n2.jsonl.meta.json` | development metadata | n/a | G surface-hardened | not frozen | Metadata sidecar | no | no | yes |
| `outputs/cluster1/g_all_surface_hardened_n2_summary.md` | development summary | n/a | G surface-hardened | not frozen | Human summary | no | no | yes |
| `outputs/cluster1/g_all_surface_hardened_n20.jsonl.meta.json` | development metadata | n/a | G surface-hardened | not frozen | Metadata sidecar | no | no | yes |
| `outputs/cluster1/g_all_surface_hardened_n20_summary.md` | development summary | n/a | G surface-hardened | not frozen | Human summary | no | no | yes |
| `outputs/cluster1/g_all_surface_hardened_n5.jsonl.meta.json` | development metadata | n/a | G surface-hardened | not frozen | Metadata sidecar | no | no | yes |
| `outputs/cluster1/g_all_surface_hardened_n5_summary.md` | development summary | n/a | G surface-hardened | not frozen | Human summary | no | no | yes |
| `outputs/cluster1/g_elementwise_expr_hardened_n5.jsonl` | development | 15 | G elementwise | not frozen | Hardening run | no | no | yes |
| `outputs/cluster1/g_elementwise_expr_hardened_n5.jsonl.meta.json` | development metadata | n/a | G elementwise | not frozen | Metadata sidecar | no | no | yes |
| `outputs/cluster1/g_elementwise_expr_hardened_n5_summary.md` | development summary | n/a | G elementwise | not frozen | Human summary | no | no | yes |
| `outputs/cluster1/g_surface_fix_smoke_n1.jsonl` | smoke | 3 | G | not frozen | Surface-fix smoke | no | yes | no |
| `outputs/cluster1/g_surface_fix_smoke_n1.jsonl.meta.json` | smoke metadata | n/a | G | not frozen | Metadata sidecar | no | yes | no |
| `outputs/cluster1/g_surface_hardened_elementwise_n5.jsonl` | development | 15 | G elementwise | not frozen | Hardening run | no | no | yes |
| `outputs/cluster1/g_surface_hardened_elementwise_n5.jsonl.meta.json` | development metadata | n/a | G elementwise | not frozen | Metadata sidecar | no | no | yes |
| `outputs/cluster1/g_surface_hardened_elementwise_n5_summary.md` | development summary | n/a | G elementwise | not frozen | Human summary | no | no | yes |
| `outputs/cluster1/g_surface_hardened_smoke_n1.jsonl` | smoke | 3 | G | not frozen | Surface-hardened smoke | no | yes | no |
| `outputs/cluster1/g_surface_hardened_smoke_n1.jsonl.meta.json` | smoke metadata | n/a | G | not frozen | Metadata sidecar | no | yes | no |
| `outputs/cluster1/m1_small_matrix.jsonl` | development | 36 | none + G | not frozen | Small matrix development run | no | no | yes |
| `outputs/cluster1/m1_small_matrix_summary.md` | development summary | n/a | none + G | not frozen | Human summary | no | no | yes |
| `outputs/cluster1/modal_smoke_both_elementwise.jsonl` | smoke | 6 | none + G | not frozen | Modal smoke | no | yes | no |
| `outputs/cluster1/modal_smoke_g.jsonl` | smoke | 3 | G | not frozen | Modal smoke | no | yes | no |
| `outputs/cluster1/repaired_none_vs_g_n20_summary.md` | superseded summary | n/a | none + G | not frozen | Human summary | no | no | yes |
| `outputs/cluster1/smoke/metadata_smoke_task_agnostic_g_elementwise_n1.jsonl.meta.json` | smoke metadata | n/a | task-agnostic G | not frozen | Metadata sidecar | no | yes | no |
| `outputs/cluster1/task_agnostic_g_all_n5_l4.jsonl` | development | 45 | task-agnostic G | not paper-frozen | Development control | no | no | yes |
| `outputs/cluster1/task_agnostic_g_all_n5_l4.jsonl.meta.json` | development metadata | n/a | task-agnostic G | not paper-frozen | Metadata sidecar | no | no | yes |
| `outputs/cluster1/task_agnostic_g_all_n5_l4_summary.md` | development summary | n/a | task-agnostic G | not paper-frozen | Human summary | no | no | yes |
| `outputs/cluster1/task_agnostic_g_all_n5_l4_rerun.jsonl.meta.json` | development metadata | n/a | task-agnostic G | manifest-known, not paper-frozen | Metadata sidecar | no | no | yes |
| `outputs/cluster1/task_agnostic_g_all_n5_l4_rerun_summary.md` | development summary | n/a | task-agnostic G | manifest-known, not paper-frozen | Human summary | no | no | yes |
| `outputs/cluster1/task_agnostic_g_all_n5_l4_surface_once.jsonl` | development | 45 | task-agnostic G | not paper-frozen | Surface-once development run | no | no | yes |
| `outputs/cluster1/task_agnostic_g_all_n5_l4_surface_once.jsonl.meta.json` | development metadata | n/a | task-agnostic G | not paper-frozen | Metadata sidecar | no | no | yes |
| `outputs/cluster1/task_agnostic_g_all_n5_l4_surface_once_summary.md` | development summary | n/a | task-agnostic G | not paper-frozen | Human summary | no | no | yes |
| `outputs/cluster1/task_agnostic_g_current_grammar_n5_l4.jsonl.meta.json` | development metadata | n/a | task-agnostic G | not paper-frozen | Metadata sidecar | no | no | yes |
| `outputs/cluster1/task_agnostic_g_elementwise_n1_l4.jsonl` | development | 3 | task-agnostic G elementwise | not paper-frozen | Single-family dev run | no | no | yes |
| `outputs/cluster1/task_agnostic_g_elementwise_n1_l4.jsonl.meta.json` | development metadata | n/a | task-agnostic G elementwise | not paper-frozen | Metadata sidecar | no | no | yes |
| `outputs/cluster1/task_agnostic_g_elementwise_n1_l4_surfacefix.jsonl` | development | 3 | task-agnostic G elementwise | not paper-frozen | Surface-fix dev run | no | no | yes |
| `outputs/cluster1/task_agnostic_g_elementwise_n1_l4_surfacefix.jsonl.meta.json` | development metadata | n/a | task-agnostic G elementwise | not paper-frozen | Metadata sidecar | no | no | yes |
| `outputs/cluster1/task_agnostic_g_elementwise_n5_l4.jsonl` | development | 15 | task-agnostic G elementwise | not paper-frozen | Single-family dev run | no | no | yes |
| `outputs/cluster1/task_agnostic_g_elementwise_n5_l4.jsonl.meta.json` | development metadata | n/a | task-agnostic G elementwise | not paper-frozen | Metadata sidecar | no | no | yes |
| `outputs/cluster1/task_agnostic_g_elementwise_n5_l4_rerun.jsonl` | development | 15 | task-agnostic G elementwise | not paper-frozen | Single-family dev rerun | no | no | yes |
| `outputs/cluster1/task_agnostic_g_elementwise_n5_l4_rerun.jsonl.meta.json` | development metadata | n/a | task-agnostic G elementwise | not paper-frozen | Metadata sidecar | no | no | yes |
| `outputs/cluster1/task_agnostic_g_elementwise_n5_l4_rerun_summary.md` | development summary | n/a | task-agnostic G elementwise | not paper-frozen | Human summary | no | no | yes |
| `outputs/cluster1/task_agnostic_g_elementwise_n5_l4_summary.md` | development summary | n/a | task-agnostic G elementwise | not paper-frozen | Human summary | no | no | yes |
| `outputs/cluster2/c_prompt_audit_smoke.jsonl` | smoke | 3 | C | not frozen | Prompt audit smoke | no | yes | no |
| `outputs/cluster2/c_prompt_audit_smoke.jsonl.hashes.json` | smoke hash | n/a | C | not frozen | Hash sidecar | no | yes | no |
| `outputs/cluster2/smoke_C_phase12.jsonl.hashes.json` | smoke hash | n/a | C | not frozen | Hash sidecar | no | yes | no |
| `outputs/cluster2/smoke_GC_phase12.jsonl.hashes.json` | smoke hash | n/a | G+C | not frozen | Hash sidecar | no | yes | no |
| `outputs/cluster2/smoke_G_replay_phase12.jsonl.hashes.json` | smoke hash | n/a | G replay | not frozen | Hash sidecar | no | yes | no |
| `outputs/cluster2/smoke_f2_repair_matmul_local_validation.jsonl` | smoke/local validation | 2 | C | not paper-frozen | Local F2 validation | no | yes | no |
| `outputs/cluster2/smoke_f2_repair_relu_local_validation.jsonl` | smoke/local validation | 2 | C | not paper-frozen | Local F2 validation | no | yes | no |
| `outputs/cluster2/smoke_f2_repair_softmax_local_validation.jsonl` | smoke/local validation | 2 | C | not paper-frozen | Local F2 validation | no | yes | no |
| `outputs/cluster2/smoke_none_replay_phase12.jsonl.hashes.json` | smoke hash | n/a | none replay | not frozen | Hash sidecar | no | yes | no |
| `outputs/cluster2/smoke_seed_pairing_validation.jsonl.hashes.json` | smoke hash | n/a | C | not frozen | Hash sidecar | no | yes | no |
| `outputs/cluster2/smoke_seed_pairing_validation_none.jsonl.hashes.json` | smoke hash | n/a | none replay | not frozen | Hash sidecar | no | yes | no |

All discovered smoke/development JSONL files are non-paper artifacts unless selected by a frozen manifest and allowed by the scale policy. Figures and summaries inherit eligibility from the data used to generate them and should be regenerated after the final paper freeze.

### Q13. Minimum remaining paper-scale run set

Verified:

| Requirement | Current state |
|---|---|
| Paper scale | n=20 per cell in scale policy. |
| Task-agnostic G selected artifact | n=5, 45 rows. |
| Task-agnostic paper sufficiency | manifest says false. |
| Equal-attempt N=6 replay window | current n=5 lacks one seed per 9 kernel_class x dtype cells. |
| Template G | n=20 exists, but is template upper-bound/diagnostic, not primary task-agnostic G. |
| P cells | no implementation. |

Minimum missing non-P paper controls:

| Missing item | Rows/cells needed | Notes |
|---|---:|---|
| Task-agnostic G n=20 control | 135 additional rows if extending current n=5 to n=20 across 9 cells; 180 rows if rerun from scratch | Required for primary task-agnostic G and G+C replay. |
| Task-agnostic equal-attempt N=6 minimum | 9 additional rows if only satisfying N=6 replay window | Not enough for paper n=20. |
| Cluster 2 C paper generated cells | 180 base-seed cells; up to 1080 candidates/evals with repair budget 5 | Requires boundary tests and smoke gates. |
| Cluster 2 G+C paper generated cells | 180 base-seed cells; up to 1080 candidates/evals with repair budget 5 | Blocked until task-agnostic G n=20 exists. |
| Replay correctness evaluation for none/G controls | 180 none and 180 task-agnostic G replay rows at paper scale | none control exists; task-agnostic G control missing. |

P-containing cells:

| Cell | Status |
|---|---|
| P | No contract/implementation. |
| G+P | No contract/implementation. |
| C+P | No contract/implementation. |
| G+C+P | No contract/implementation. |

Cost estimate:

Dollar GPU cost cannot be verified from repository state. No complete price, runtime-per-candidate, or Modal billing artifact was found. A defensible source-count estimate is:

`C2 generated candidate upper bound = 2 generated conditions * 180 base cells * (1 initial + 5 repairs) = 2160 generated candidates/evaluations`

This excludes replay correctness evaluation and any task-agnostic G n=20 generation extension. Any dollar amount would be speculative and should not appear as an audit fact.

### Q14. Has Cluster 2 been validated end-to-end on smoke with real F2 failures and C repair activations?

**Conclusion: yes for F2-triggered repair activation; only partially for convergence.**

Verified:

| Artifact | Evidence | Interpretation |
|---|---|---|
| `outputs/cluster2/smoke_f2_repair_relu.jsonl` | two rows: first F2 numeric failure, then functional success | F2 activation and convergence demonstrated. |
| `outputs/cluster2/smoke_f2_repair_softmax.jsonl` | two rows: F2 failures, no success in one-repair smoke | F2 activation demonstrated; convergence not demonstrated. |
| `outputs/cluster2/smoke_f2_repair_matmul.jsonl` | two rows: F2 failures, no success in one-repair smoke | F2 activation demonstrated; convergence not demonstrated. |
| `validate_canonical_f2_smoke_artifacts()` | `VALID` | Canonical smoke artifacts pass structural validation. |

Minimum valid smoke before paper if model/revisions change:

| Requirement | Success criterion |
|---|---|
| Run canonical ReLU, Softmax, GEMM F2 fixtures under the intended paper model/revision/tokenizer revision. | Each fixture produces a real F2 iteration 0 and at least one C repair-loop activation. |
| Validate canonical artifact function. | Returns `VALID`. |
| Preserve fixture hashes, model IDs, revisions, modal metadata, and mtime freshness. | Preflight accepts them. |
| Demonstrate at least one convergence case. | ReLU currently satisfies this; if future model changes, repeat. |

### Q15. Code paths affecting primary paper metrics

| Code path | Factor(s) affected | Audited? | Unit-tested? | Smoke-tested? | Development-tested? | Frozen? | Pre-spend severity |
|---|---|---|---|---|---|---|---|
| `cluster1/grammar/triton_kernel.gbnf` | strict/template G | yes | via grammar tests | yes | yes | yes via manifest | High |
| `cluster1/grammar/triton_kernel_agnostic.gbnf` | task-agnostic G | yes | via grammar tests | yes | yes n=5 | hash-gated, paper n=20 missing | Critical |
| `cluster1/grammar/triton_kernel_validator.py` | G semantic validation | yes | yes | yes | yes | implicitly via hash/gates | High |
| `cluster1/generation/constrained_gen.py` | G generation | yes | yes | smoke/dev | yes | hash-gated | High |
| `cluster1/generation/constrained_decoding.py` | G decoding | yes | yes | smoke/dev | yes | hash-gated | High |
| `cluster1/generation/grammar_variants.py` | G variant semantics | yes | yes | yes | yes | hash-gated | High |
| `cluster1/experiments/run_cluster1.py` | C1 generation/eval | partial | partial | yes | yes | artifacts frozen | High |
| `cluster1/experiments/run_cluster1_modal.py` | C1 Modal execution | partial | partial | yes | yes | artifacts frozen | High |
| `cluster1/validation/compile_check.py` | compile success | yes | yes | yes | yes | indirectly | High |
| `cluster1/results/dataclass.py` | C1 schema | yes | boundary test fails field-list drift | yes | yes | Phase -1 drift | Critical |
| `shared/modal_harness/smoke.py` | Modal smoke harness | yes | boundary test fails hash drift | yes | yes | Phase -1 drift | Critical |
| `shared/eval/failure_taxonomy.py` | F0/F1/F2/F3 | yes | yes | yes | yes | shared source | High |
| `shared/eval/levels/level0_parse.py` | parse metric | partial | yes | yes | yes | shared | Medium |
| `shared/eval/levels/level1_compile.py` | compile metric | partial | yes | yes | yes | shared | Medium |
| `shared/eval/levels/level2_correctness.py` | correctness metric | yes | yes | F2 smoke | yes | shared | High |
| `shared/eval/metrics/pass_at_k.py` | compile@1 | yes | yes | n/a | yes | shared | Medium |
| `shared/eval/metrics/repair.py` | pass@1, convergence | yes | yes | F2 smoke | yes | shared | High |
| `shared/eval/metrics/equal_attempts.py` | equal-attempt rates | yes | yes | seed smoke | yes | shared | High |
| `shared/eval/metrics/coverage.py` | coverage gates | yes | yes | n/a | yes | shared | Medium |
| `shared/eval/aggregation.py` | aggregate metrics | yes | yes | n/a | yes | shared | Medium |
| `shared/analysis/factorial.py` | primary C2 paper tables | yes | yes | no paper smoke | development only | not paper-frozen | High |
| `cluster2/modal/generation.py` | C/G+C generation, hash gates | yes | yes | yes | yes | hash-gated | Critical |
| `cluster2/experiments/run_cluster2_modal.py` | C2 paper runner/preflights | yes | yes | yes | yes | not paper-run frozen | Critical |
| `cluster2/modal/correctness.py` | C2 correctness | partial | yes | F2 smoke | yes | not paper-run frozen | High |
| `cluster2/modal/correctness_runner.py` | C2 correctness execution | partial | yes | F2 smoke | yes | not paper-run frozen | High |
| `cluster2/validation/modal_correctness_check.py` | correctness validation | partial | yes | F2 smoke | yes | not paper-run frozen | High |
| `cluster2/feedback/prompts.py` | C factor feedback | yes | yes | F2 smoke | yes | not paper-run frozen | High |
| `cluster2/feedback/repair_loop.py` | C repair loop | yes | yes | F2 smoke | yes | not paper-run frozen | High |
| `cluster2/results/dataclass.py` | C2 schema | yes | yes | yes | yes | not paper-run frozen | High |
| `cluster2/replay/manifest.py` | replay controls | yes | yes | yes | yes | manifest-backed | High |
| `cluster2/replay/cluster1_controls.py` | replay row loading | yes | yes | yes | yes | manifest-backed | High |
| `shared/factors/cells.py` | factorial cell vocabulary | yes | yes | n/a | n/a | shared | Medium |
| `shared/factors/registry.py` | cluster/factor ownership | yes | yes | n/a | n/a | shared | Medium |
| `cluster3/README.md` | P status | yes | n/a | n/a | n/a | no implementation | Critical for full factorial |

### Q16. Ordered pre-paper fix list and outcome sensitivity

Ordered fix list:

| Rank | Fix/gate | Risk to paper validity | Risk of invalidating paper-scale data | Methodological severity | Implementation difficulty | Rationale |
|---:|---|---|---|---|---|---|
| 1 | Resolve Phase -1 boundary test failures for `shared/modal_harness/smoke.py` and `GenerationResult` fields. | Critical | Critical | High | Medium | Current targeted suite fails; paper data generated now would be hard to defend. |
| 2 | Resolve token-budget contract/code divergence. | High | High | High | Low-medium | Equal-attempt and replay fairness depend on stable generation budgets or explicit disclosure. |
| 3 | Freeze task-agnostic G n=20 with manifest refresh and passing gates. | Critical | Critical | Critical | Medium-high | Primary G/G+C paper path is blocked without it. |
| 4 | Re-run canonical F2 smoke if paper model/revisions differ from current validated artifacts. | High | Medium | Medium | Low-medium | Ensures C repair activation for intended paper environment. |
| 5 | Lock paper table metric definitions to `shared/analysis/factorial.py` and shared metrics. | High | Medium | High | Low | Prevents metric drift across scripts. |
| 6 | Mark strict/template G, permissive baseline, and task-agnostic G separately in methods/tables. | High | Low | High | Low | Prevents overclaiming grammar causality. |
| 7 | Decide whether near-term paper is Cluster 1/2 only or waits for Cluster 3/P. | High | High | High | High if building P | Avoids claiming incomplete factorial. |
| 8 | Add or explicitly defer official tutorial acceptance manifest. | Medium | Low | Medium | Medium | Prevents unsupported grammar-validity claims. |

Task-agnostic G n=20 outcome sensitivity:

| Task-agnostic G compile outcome | Interpretation | Narrative effect | Methodology effect |
|---:|---|---|---|
| 10% | Grammar has weak compile lift; strict/template success is mostly surface/template effect. | Strengthens "grammar contributes less" narrative if C still helps correctness. | No methodology change if predeclared and all gates pass. |
| 15% | Similar to n=5 rerun order of magnitude; modest lift. | Supports nuanced limited-grammar claim. | No methodology change. |
| 20% | Still far below template upper bound; grammar helps but is not dominant. | Narrative becomes less stark but still defensible. | No methodology change. |
| 30% | Meaningful task-agnostic grammar contribution. | Weakens "less than prior literature implies" if phrased strongly; supports "grammar helps but is insufficient." | No methodology change if factor definitions are stable; may require retuning paper framing. |

Outcomes that only change narrative:

| Outcome | Effect |
|---|---|
| Task-agnostic G lands between 10% and 30% with stable gates. | Changes strength of grammar narrative, not methodology. |
| C improves F2 convergence over both none and G controls. | Changes effect size, not design. |
| Permissive baseline remains around 38/180. | Clarifies surface-cost attribution. |

Outcomes that force methodology changes:

| Outcome | Required response |
|---|---|
| Boundary tests remain failing. | Do not run paper-scale; fix/re-freeze. |
| Task-agnostic n=20 artifacts do not satisfy equal-attempt/pairing manifests. | Do not use for primary G/G+C; repair artifact generation protocol. |
| C repairs non-F2 failures or P later repairs F2 without explicit interaction design. | Redefine factor ownership before paper. |
| Token-budget migration remains undocumented while controls and generated cells differ. | Either enforce contract or reframe fairness assumptions. |
| Cluster 3/P remains absent while paper claims 2^3 factorial. | Scope paper down or implement P. |

## Risk Register by Class

### Methodological Risks

| Risk | Severity | Status | Mitigation |
|---|---|---|---|
| Strict/template G confounds grammar with surface contract. | High | Verified | Label as upper bound; anchor primary grammar claims on task-agnostic G. |
| Task-agnostic G n=20 missing. | Critical | Verified | Complete and freeze before C2 G/G+C paper runs. |
| P absent from full factorial. | High | Verified | Do not claim full eight-cell results. |
| Token-budget contract drift affects equal-attempt fairness. | High | Verified | Resolve contract/code mismatch. |

### Engineering Risks

| Risk | Severity | Status | Mitigation |
|---|---|---|---|
| Shared/Cluster 2 tests fail. | Critical | Verified | Fix or explicitly re-freeze Phase -1 boundary. |
| Schema field-list drift around `failure_code`. | Critical | Verified | Decide whether field is contractually required and update freeze accordingly. |
| Shared Modal smoke hash drift. | Critical | Verified | Reconcile with Phase -1 manifest. |
| Multiple metric implementations can drift semantically. | Medium | Verified | Use shared analysis path for paper. |

### Paper-Writing Risks

| Risk | Severity | Status | Mitigation |
|---|---|---|---|
| Readers interpret strict G 180/180 as pure grammar. | High | Verified | Use `template_upper_bound` label. |
| Readers interpret strict 0/180 baseline as zero latent Triton ability. | Medium | Verified | Show permissive 38/180 diagnostic. |
| 100% official tutorial acceptance is assumed. | Medium | Verified as unproven | Do not claim it without manifest. |
| Smoke/development artifacts leak into paper tables. | High | Verified risk | Apply scale policy table labels. |

### Infrastructure Risks

| Risk | Severity | Status | Mitigation |
|---|---|---|---|
| GPU spend before boundary gates pass. | Critical | Verified risk | No-go until targeted suite passes. |
| Missing paper-scale task-agnostic controls. | Critical | Verified | Generate/freeze n=20 controls first. |
| Cost dollars cannot be estimated from artifacts. | Medium | Verified | Report source-count budget, not dollar claims. |
| F2 smoke freshness/model revision may expire or mismatch. | Medium | Inferred | Revalidate immediately before paper runs. |

## Unresolved Ambiguities

| Ambiguity | Status | Why it matters |
|---|---|---|
| Whether token-budget migration is an intentional methodology change or temporary engineering accommodation. | Verified unresolved | Affects replay fairness and contract compliance. |
| Whether `failure_code` should be part of the frozen Phase -1 `GenerationResult` schema. | Verified unresolved | Boundary tests currently fail. |
| Whether `shared/modal_harness/smoke.py` drift is benign instrumentation or behavior-changing. | Verified unresolved | Boundary tests currently fail. |
| Whether the paper will be scoped to Cluster 1/2 or wait for Cluster 3. | Inferred unresolved | Determines whether eight-cell factorial language is allowed. |
| Official tutorial acceptance rate for task-agnostic grammar. | Verified unmeasured | Affects grammar-validity claims. |
| Dollar GPU spend for missing cells. | Verified unmeasured | Cannot be estimated without runtime/pricing data. |

## Final Go/No-Go Recommendation

**NO-GO for additional paper-scale GPU spend that produces paper data.**

Reason:

1. The targeted shared/Cluster 2 suite currently fails on Phase -1 boundary drift.
2. Task-agnostic G n=20 controls are missing and explicitly not paper sufficient.
3. The full P-inclusive factorial is not implemented.
4. Token-budget semantics diverge between contract and code.

**GO for the following pre-paper work only:**

1. Explicitly resolve or re-freeze Phase -1 boundary drift.
2. Resolve token-budget contract/code semantics.
3. Produce and freeze task-agnostic G n=20 controls.
4. Revalidate canonical F2 smoke for the exact intended paper model/revisions.
5. Lock paper table definitions to shared metrics and separate strict/template, task-agnostic, permissive, smoke, development, and paper artifacts.

Bottom line:

Low task-agnostic grammar performance is acceptable and publishable if measured under frozen, honest conditions. The current blockers are not low performance; they are reproducibility boundary drift, incomplete paper-scale controls, and incomplete factor implementation.
