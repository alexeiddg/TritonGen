# Cluster 2 Methodology

## 1. Purpose

Cluster 2 is the implementation layer for the `C` and `G+C` conditions in the preliminary 2^2 technical handoff.

`C` means correctness-feedback repair. It introduces a bounded repair loop that may use numerical correctness feedback after a candidate has reached the correctness stage and failed there.

`G+C` means the Cluster 1 task-agnostic grammar condition plus the Cluster 2 correctness-feedback repair loop. It is not a separate cluster and it is not the template grammar condition.

Cluster 2 exists to test whether correctness feedback improves generated Triton kernels beyond the no-control baseline and beyond grammar-only generation.

## 2. Plain-language explanation

A Triton kernel can compile and still compute the wrong answer. Compilation mostly says the generated source can be parsed, compiled, and launched under the configured harness. It does not prove that the output tensor matches the reference implementation.

Numerical correctness needs a separate check. Cluster 2 adds that check and, only for the right kind of failure, gives the model a concise correction signal before trying again.

The feedback loop must be restricted. If the loop were allowed to repair parse, signature, or compile failures, then the `C` factor would stop meaning "correctness feedback" and would become a broader debugging assistant. Cluster 2 therefore only sends feedback for Level 2 numerical/correctness failures.

Replay controls are used so the `none` and `G` comparison rows remain frozen. Cluster 2 generates only the `C` and `G+C` conditions while comparing them against seed-aligned Cluster 1 control artifacts.

## 3. Experimental role in the 2^2 preliminary design

| Report condition | Uses G? | Uses C? | Source artifact |
|---|---:|---:|---|
| none | no | no | `outputs/cluster1/baseline_repaired_l4_n20.jsonl` |
| G | yes | no | `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` |
| C | no | yes | `outputs/cluster2/c_paper_n20_l4.jsonl` |
| G+C | yes | yes | `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` |

The current report scope is 2^2 only: `none`, `G`, `C`, and `G+C`.

The full 2^3 design, the `P` factor, and Cluster 3 are deferred.

## 4. Condition definitions

`none` is the frozen Cluster 1 baseline replay control. It uses no grammar and no correctness repair.

`G` is the frozen Cluster 1 task-agnostic grammar control. It uses grammar-guided decoding plus semantic post-validation and no correctness repair.

`C` is a generated Cluster 2 condition. It uses no grammar and may use correctness-feedback repair only after an F2 numerical/correctness failure.

`G+C` is a generated Cluster 2 condition. It combines task-agnostic `G` with the `C` repair loop. It is not a new cluster, not a template-grammar condition, and not a separate factor beyond the composition of `G` and `C`.

## 5. Replay-control design

Cluster 2 treats `none` and `G` as frozen controls and does not regenerate them. `C` is paired against `none`; `G+C` is paired against `G`.

Primary paths:

| Role | Path |
|---|---|
| none replay control | `outputs/cluster1/baseline_repaired_l4_n20.jsonl` |
| G replay control | `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` |
| Frozen control manifest | `cluster2/contracts/frozen_cluster1_artifacts_manifest.json` |
| C generated artifact | `outputs/cluster2/c_paper_n20_l4.jsonl` |
| G+C generated artifact | `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` |

The matched unit is the kernel/dtype/seed identity. Current code and audits use tuple matching over fields such as `kernel_class`, `kernel_id` or `kernel_name`, `dtype`, and normalized `base_seed`. Generated Cluster 2 rows also carry replay provenance such as `replay_pair_id` in nested metadata where supported.

The current G and G+C coverage is 177/180, not 180/180. The missing rows are:

| Kernel class | Dtype | Seed |
|---|---|---:|
| matmul | fp32 | 5 |
| matmul | bf16 | 0 |
| matmul | bf16 | 18 |

These missing rows must be handled explicitly in paired analysis. The current policy is to skip the missing covered-row identities, not impute them.

## 6. Level 0 / Level 1 / Level 2 evaluation ladder

Cluster 2 uses an ordered evaluation ladder:

| Level | Meaning | Failure family |
|---|---|---|
| Level 0 | Parse, signature, and surface validity | F0 |
| Level 1 | Compile/runtime launch gate | F1 |
| Level 2 | Numerical correctness | F2 |
| Infrastructure/pipeline | Malformed or infrastructure evaluation failure | F3 |

Generated `C` and `G+C` candidates pass through the ladder in order. Level 2 only runs after earlier gates have passed. Malformed correctness payloads or evaluation-infrastructure failures are represented by `F3_EVAL_PIPELINE` rather than crashing the whole run.

Relevant paths include `shared/eval/levels/level0_parse.py`, `shared/eval/levels/level1_compile.py`, `shared/eval/levels/level2_correctness.py`, and `shared/eval/failure_taxonomy.py`.

## 7. C repair policy

The `C` repair loop fires only when Level 2 evaluation ran and produced an allowed F2 numerical/correctness failure.

F0 failures terminate immediately. F1 failures terminate immediately. F0 and F1 rows do not receive feedback prompts. This boundary keeps correctness feedback from becoming parse, signature, or compile repair.

The implementation anchors are:

| Path | Role |
|---|---|
| `cluster2/feedback/prompts.py` | Defines allowed F2 feedback codes and builds correctness-only feedback. |
| `cluster2/feedback/repair_loop.py` | Enforces generated-condition repair and terminates below Level 2 or outside allowed F2 codes. |
| `cluster2/feedback/trace.py` | Records compact public trace summaries. |
| `cluster2/experiments/run_cluster2_modal.py` | Routes generated rows, records terminal attempts, and writes durable output rows. |

Relevant tests include `cluster2/tests/test_feedback_prompts.py`, `cluster2/tests/test_repair_loop.py`, and `cluster2/tests/test_generated_eval_ladder.py`.

## 8. Feedback content boundary

Correctness feedback should contain only numerical/correctness information. It must not expose compile-error-shaped language, signature-repair hints, Triton API repair hints for F0/F1 rows, private eval-set details, token details, timing information, or profiling information.

`cluster2/feedback/prompts.py` sanitizes public feedback text and rejects non-F2 failure codes for feedback construction. `cluster2/feedback/repair_loop.py` passes empty compile/signature/sanitizer context into the default feedback path. Serialized repair traces provide evidence for this boundary without turning F0/F1 failures into feedback-driven attempts.

## 9. G+C routing

`G+C` uses:

- `grammar_active=True`
- `grammar_variant=task_agnostic`
- grammar path `cluster1/grammar/triton_kernel_agnostic.gbnf`

The routing is implemented in `cluster2/modal/generation.py` and validated in `cluster2/modal/schemas.py`. `template_upper_bound` is diagnostic/reference material and must not be used for report-scale `G+C`.

## 10. Durable result writing

Cluster 2 writes completed logical rows durably during long runs. `cluster2/results/logger.py` appends one canonical JSON object per completed row, flushes it, and fsyncs it before the runner proceeds. `cluster2/experiments/run_cluster2_modal.py` records rows through that logger after preflight checks.

This matters because a previous G+C correctness-payload crash produced partial completed work. Durable row writing preserved completed rows and allowed the failure mode to be audited. The current authoritative G+C artifact is the completed 177-row artifact at `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl`, not an older failed partial run.

## 11. Malformed correctness payload / F3_EVAL_PIPELINE

Malformed correctness payloads are recorded as canonical failure rows instead of crashing the entire run. The runner synthesizes an `F3_EVAL_PIPELINE` row when it cannot recover a valid correctness payload.

Current artifact evidence shows five `F3_EVAL_PIPELINE` rows in `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl`.

Current analyzer policy treats these rows as infrastructure/evaluation-pipeline failures. They remain denominator failures and are not reportable successes. Full analyzer semantics are owned by Phase 5, but this caveat must stay visible in Cluster 2 methodology.

## 12. Result schema and metadata

Cluster 2 rows may use nested `generated_metadata`. Important row fields include:

- `condition`
- `source_class`
- `generation_mode`
- `attempt_index`
- `kernel_class`
- `kernel_name` or equivalent kernel identity
- `dtype`
- `base_seed`
- `generation_seed`
- `failure_code`
- `functional_success`
- `repair_set_success`
- `eval_set_success`
- `repair_trace`
- `generated_metadata`

Required generated metadata includes model and tokenizer revisions, Modal image provenance, package versions, and replay pairing fields. `G+C` rows also require grammar metadata such as `grammar_active`, `grammar_variant`, `grammar_path`, `grammar_sha`, `gbnf_parse_valid`, `semantic_valid`, and `grammar_valid`.

`C` rows are grammar-free. The current C artifact does not carry raw top-level `compile_success`; analyzer normalization derives compile-success semantics from failure-code policy. `functional_success` is the primary correctness outcome for Cluster 2.

## 13. Current authoritative artifacts

Artifact identities and row counts are owned by `docs/05_artifacts_and_results_registry.md`.

| Role | Path | Rows | Status |
|---|---|---:|---|
| none replay control | `outputs/cluster1/baseline_repaired_l4_n20.jsonl` | 180 | authoritative control |
| G replay control | `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` | 177 | authoritative with coverage caveat |
| C generated condition | `outputs/cluster2/c_paper_n20_l4.jsonl` | 180 | authoritative |
| G+C generated condition | `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` | 177 | authoritative with coverage and F3 caveats |
| 2^2 analyzer output | `outputs/analysis/factorial_2x2_preliminary.json` | 714 loaded rows | valid JSON, `metadata.reportable=true` via `analysis_cli_annotation` |

The analyzer output is reportable for the covered 2^2 scope, but it must not be described as full 2^3/P evidence or as free of coverage, F3, model-fit, and provenance caveats.

## 14. Analyzer relationship

Cluster 2 supplies the `C` and `G+C` rows used by the preliminary analyzer. `functional_success` is the primary Cluster 2 outcome. `compile_success` is a secondary structural metric.

The analyzer must normalize C rows that lack raw top-level `compile_success`. It must also preserve the current `F3_EVAL_PIPELINE` policy for G+C rows. Current evidence says the analyzer output exists, loads 714 rows, and is reportable under explicit scale-tier annotation.

Phase 5 and `docs/07_analysis_and_statistics.md` will own the full statistical details, including failure taxonomy, compile-success normalization, pairing semantics, and reportability.

## 15. Tests and traceability

| Claim | Code path | Test path | Artifact path | Caveat |
|---|---|---|---|---|
| C feedback is restricted to allowed F2 failures | `cluster2/feedback/prompts.py`; `cluster2/feedback/repair_loop.py` | `cluster2/tests/test_feedback_prompts.py`; `cluster2/tests/test_repair_loop.py`; `cluster2/tests/test_generated_eval_ladder.py` | `outputs/cluster2/c_paper_n20_l4.jsonl`; `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` | Current C artifact has all F0_PARSE rows; current G+C has four F2 rows. |
| F0/F1 terminate without feedback | `cluster2/feedback/repair_loop.py`; `shared/eval/levels/level0_parse.py`; `shared/eval/levels/level1_compile.py` | `cluster2/tests/test_repair_loop.py`; `cluster2/tests/test_generated_eval_ladder.py` | C and G+C artifacts | F0/F1 rows are terminal failures, not repaired rows. |
| G+C uses task-agnostic grammar | `cluster2/modal/generation.py`; `cluster2/modal/schemas.py` | `cluster2/tests/test_modal_generation_c2.py`; `cluster2/tests/test_run_cluster2_modal.py` | `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` | Template grammar is diagnostic/reference only. |
| Replay controls are frozen | `cluster2/replay/manifest.py`; `cluster2/replay/cluster1_controls.py`; `cluster2/experiments/run_cluster2_modal.py` | `cluster2/tests/test_run_cluster2_modal.py` | none/G control artifacts; `cluster2/contracts/frozen_cluster1_artifacts_manifest.json` | G replay coverage is 177/180. |
| C artifact has 180 rows | `cluster2/results/dataclass.py`; `cluster2/results/logger.py` | `cluster2/tests/test_results_logger.py`; `cluster2/tests/test_run_cluster2_modal.py` | `outputs/cluster2/c_paper_n20_l4.jsonl` | C lacks raw top-level `compile_success`; analyzer normalization is required. |
| G+C artifact has 177 rows | `cluster2/replay/manifest.py`; `cluster2/results/dataclass.py` | `cluster2/tests/test_modal_generation_c2.py`; `cluster2/tests/test_run_cluster2_modal.py` | `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` | Missing three matmul rows. |
| Durable row writing exists | `cluster2/results/logger.py`; `cluster2/experiments/run_cluster2_modal.py` | `cluster2/tests/test_results_logger.py`; `cluster2/tests/test_run_cluster2_modal.py` | C and G+C artifacts | Older partial runs remain historical evidence only. |
| Malformed correctness payloads become F3 rows | `cluster2/experiments/run_cluster2_modal.py`; `shared/eval/failure_taxonomy.py`; `cluster2/feedback/trace.py` | `cluster2/tests/test_run_cluster2_modal.py`; `shared/tests/test_failure_taxonomy.py`; `shared/tests/test_factorial_analysis.py` | `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` | Five current G+C rows are `F3_EVAL_PIPELINE`. |

## 16. Known caveats

- `G+C` is 177/180, not 180/180.
- Missing G/G+C rows are matmul/fp32 seed 5, matmul/bf16 seed 0, and matmul/bf16 seed 18.
- `outputs/analysis/factorial_2x2_preliminary.json` exists and has `metadata.reportable=true` under explicit scale-tier annotation.
- `G+C` has five `F3_EVAL_PIPELINE` rows.
- `C` lacks raw top-level `compile_success` and requires analyzer normalization.
- Cluster 3 and the `P` factor are deferred.
- Old smoke, n=5, failed, and partial runs are historical evidence unless explicitly promoted.

## 17. What this document does not claim

- No full 2^3 factorial result.
- No Cluster 3 or `P` result.
- No timing, profiling, speedup, or performance result.
- No claim that `C` provides feedback for parse, signature, or compile failures.
- No claim that `G+C` uses template grammar.
- No claim of complete 180/180 `G+C` coverage.
- No claim that the reportable analyzer output removes 177/180, F3, P-deferred, or provenance caveats.

## 18. Open TODOs for later phases

- Phase 5 will define the full failure taxonomy and analyzer semantics in `docs/06_failure_taxonomy_and_eval_ladder.md` and `docs/07_analysis_and_statistics.md`.
- Phase 6 will document Modal infrastructure and provenance.
- Phase 8 will align README and formal contracts after citation-grade docs are stable.
- Phase 9 will outline the preliminary technical report.
