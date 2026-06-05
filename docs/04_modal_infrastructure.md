# Modal Infrastructure And Provenance

## 1. Purpose

This document defines Modal's role in the preliminary Cluster 1 + Cluster 2 handoff. Modal is not incidental tooling in this project. It is part of the execution and reproducibility architecture used to run GPU-backed generation, compile validation, and correctness evaluation while preserving row-level provenance.

This document is documentation only. It does not define new experiments, authorize new Modal runs, change artifact status, or replace the artifact registry at `docs/05_artifacts_and_results_registry.md`.

## 2. Plain-Language Overview

Model generation and Triton evaluation need GPUs. A local machine may not provide repeatable, available, or scalable GPU access for multi-hour runs over many kernels, dtypes, and seeds. Modal provides remote GPU execution while keeping orchestration and artifact control in the repository.

Remote execution must be tracked carefully. The generated row is not just source code and a success flag; it also depends on the model revision, tokenizer revision, package versions, grammar file, image definition, GPU route, seed identity, and runner code. Those fields make it possible to audit what produced a row and to detect drift.

## 3. Why Modal Was Introduced

Modal was introduced to support:

- remote GPU model generation;
- remote GPU compile validation for generated Triton kernels;
- remote correctness evaluation for Cluster 2 rows;
- smoke, development, and paper-scale runs through the same runner surfaces;
- isolation of GPU-heavy work from the local machine;
- durable JSONL outputs for long-running jobs;
- row-level provenance for model, tokenizer, image, grammar, package, and seed identity.

Modal supports reproducibility only when the repository records enough provenance to reconstruct or audit the run. Modal execution by itself is not proof that a result is reproducible.

## 3.1 External API Baseline Generation

External API baselines can also be generated through Modal when the model is
served by a provider API instead of loaded on a Modal GPU. The OpenAI GPT path
uses a lightweight Modal image and a Modal Secret for `OPENAI_API_KEY`; it does
not request a GPU for generation.

Setup:

```bash
modal secret create openai-api-key OPENAI_API_KEY=<token>
export TRITONGEN_MODAL_OPENAI_SECRET=openai-api-key
```

Smoke command:

```bash
modal run -m run_external_modal --models openai --n-seeds 1 --openai-model gpt-5.1
```

The runner writes `outputs/external/openai_baseline_n20.jsonl` with the same row
shape as the Claude/Gemini external baseline files. Compile evaluation can then
run through:

```bash
modal run -m eval_external_modal --model openai
```

These external API rows are experimental baseline artifacts until explicitly
registered in `docs/05_artifacts_and_results_registry.md`.

OpenAI rows additionally preserve provider metadata such as `provider_api`,
`provider_model_id`, `provider_model_snapshot`, `response_id`, `request_id`,
`cached_input_tokens`, `reasoning_tokens`, `response_sha256`, and
`source_sha256` where available. These fields account for Responses API
differences from the Claude/Gemini SDK response objects while preserving the
shared evaluator-facing fields (`source`, `model_name`, `usage`,
`compile_success`, and `failure_code`).

## 4. Modal's Role By Cluster

| Cluster/condition | Modal role | Current artifacts |
|---|---|---|
| Cluster 1 / G | Remote generation and compile validation through the shared Modal generation/compile harness | `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` |
| Cluster 2 / C | Remote generation, correctness evaluation, and F2-only repair orchestration | `outputs/cluster2/c_paper_n20_l4.jsonl` |
| Cluster 2 / G+C | Remote task-agnostic grammar-guided generation, correctness evaluation, and F2-only repair orchestration | `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` |
| Replay none/G | Frozen artifact consumption by Cluster 2; replay controls are not regenerated | `outputs/cluster1/baseline_repaired_l4_n20.jsonl`; `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` |

Cluster 3 and the `P` factor are deferred. This document does not define `P` Modal behavior.

## 5. Scale Tiers And Run Gates

The current code and audits use scale tiers to separate smoke, development, and paper/preliminary runs:

| Tier | Meaning | Current status |
|---|---|---|
| smoke | Minimal path, commonly n=1 or equivalent | Useful for plumbing and schema checks; not report-scale evidence |
| development | Small iteration scale, commonly n=5 or similar | Legacy unless explicitly promoted |
| paper/preliminary | Current report-scale row target, n=20 per kernel/dtype cell | Current authoritative artifacts are registered in `docs/05_artifacts_and_results_registry.md` |

No paper-scale run should occur without smoke, development, and audit gates appropriate to the active runner. Old n=5 artifacts are legacy unless explicitly promoted. Current authoritative artifacts are the four registered 2^2 artifacts, not older smoke or development outputs.

Command snippets in audits are historical evidence. Before any future run, the active CLI must be verified against current code. This document does not recommend or authorize a new Modal run.

## 6. Provenance Fields

Provenance fields may appear as top-level fields in flat Cluster 1 rows or under nested `generated_metadata` in current Cluster 2 rows. `docs/07_analysis_and_statistics.md` owns analyzer normalization across schema differences.

| Field | Meaning |
|---|---|
| `model_id` | Hugging Face model identifier used for generation |
| `model_revision` | Immutable model revision used or observed for generation |
| `tokenizer_revision` | Immutable tokenizer revision used or observed for generation |
| `transformers_version` | Runtime Transformers package version |
| `tokenizers_version` | Runtime Tokenizers package version |
| `xgrammar_version` | Runtime XGrammar package version where grammar guidance is active |
| `grammar_sha` | SHA-256 of the grammar file used for grammar-guided rows |
| `grammar_path` | Grammar path used by G/G+C rows |
| `grammar_variant` | Grammar variant, currently `task_agnostic` for primary G/G+C artifacts |
| `modal_image_sha` | Stable Modal image identifier or stable fallback identifier |
| `modal_image_provenance_sha256` | Deterministic digest over image provenance components |
| `modal_image_provenance_components` | Structured fallback evidence: image source hash, package pins, runtime image env, Python/runtime versions, and GPU route extras |
| `max_new_tokens` | Generation token budget where recorded |
| `condition` | Experimental condition represented by the row |
| `kernel_class` | Locked kernel archetype |
| `dtype` | Data type cell |
| seed/sample fields | Experimental identity fields such as `base_seed`, `generation_seed`, `sample_index`, `attempt_index`, and `replay_pair_id` |

Missing or unknown provenance is a caveat. It must not be silently ignored or reinterpreted as harmless.

## 7. Current Provenance Caveats

Direct artifact inspection in Phase 6 verified:

| Condition | Provenance status | Caveat |
|---|---|---|
| none | 180 rows; no nested `generated_metadata`; model_id present; model/tokenizer/package/image/grammar provenance fields are null or absent | Legacy baseline schema/provenance limitation |
| G | 177 rows; model/tokenizer revisions, package versions, grammar SHA/path/variant, fallback Modal image provenance, and schema version are present | `modal_image_sha=unknown` on 177/177 rows, although `modal_image_provenance_sha256` is present |
| C | 180 rows; nested `generated_metadata` present on 180/180; model/tokenizer revisions, package versions, Modal image ID, fallback image digest/components, and replay pair IDs are present | Grammar-free; no grammar metadata by design |
| G+C | 177 rows; nested `generated_metadata` present on 177/177; model/tokenizer revisions, package versions, Modal image ID, grammar SHA/path/variant, and replay pair IDs are present | 177/180 coverage and five `F3_EVAL_PIPELINE` rows |

The current analyzer output at `outputs/analysis/factorial_2x2_preliminary.json` is valid JSON and has `metadata.reportable=true` under explicit scale-tier annotation. It remains a preliminary covered 2^2 output, not a full 2^3/P result.

`modal_image_provenance_sha256` can provide useful fallback evidence when `modal_image_sha` is unknown or not available, but the fallback digest should be described as fallback provenance. It should not be overstated as equivalent to a verified runtime Modal object ID unless the row records a stable `im-...` identifier.

## 8. Grammar And Hash Provenance

Task-agnostic grammar rows record a grammar SHA. The primary G and G+C artifacts use:

- grammar variant: `task_agnostic`;
- grammar path: `cluster1/grammar/triton_kernel_agnostic.gbnf`;
- current grammar SHA: `7896a1befca10f68ab6aa4521681fa2577eba6fb669e87daf622c15691a22e32`.

Template `G` remains diagnostic/reference material only. It must not be used as the primary G or G+C condition.

Hash gates and manifests prevent silent drift in frozen controls and generated-condition code paths. Current hash-related anchors include `shared/eval/content_hashes.py`, `cluster2/contracts/frozen_cluster1_artifacts_manifest.json`, `cluster2/contracts/phase_minus1_manifest.json`, and G+C routing/hash checks in `cluster2/modal/generation.py`.

Historical hash findings were resolved through targeted audits, but the current citation-grade state is the docs layer plus the artifact registry. Do not re-record hashes casually, and do not update frozen artifact identities as part of documentation.

## 9. Durable Row Writing

Long Modal runs can fail mid-run. Cluster 2 therefore writes completed logical rows durably as newline-delimited JSON.

`cluster2/results/logger.py` implements `Cluster2JsonlAppendLogger`. It opens the output in overwrite or resume mode, writes a content-hash sidecar, appends one canonical `Cluster2EvalRow` at a time, flushes the file, and fsyncs after each appended row. `cluster2/experiments/run_cluster2_modal.py` records rows through this logger after preflight checks and after paper-scale generated metadata validation.

This matters because G+C historically encountered a correctness-payload crash during a paper-scale run. Durable row writing preserved completed work and made the failure auditable. The current authoritative G+C artifact is the completed 177-row file at `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl`, not an older failed partial run.

Partial outputs remain historical evidence unless explicitly promoted. A strict full-run consumer must still validate expected row counts and caveats.

## 10. Malformed Correctness Payload Handling

A correctness payload without `correctness_result` previously caused the G+C runner to crash. Current `cluster2/experiments/run_cluster2_modal.py` defensively converts missing or non-dict correctness payloads into canonical terminal result rows with:

- `functional_success=False`;
- `repair_set_success=False`;
- `eval_set_success=False`;
- `compile_success=False`;
- `failure_code="F3_EVAL_PIPELINE"`;
- a public malformed-payload summary.

This behavior supports auditability and lets the run continue. It does not make those rows functional successes or official final results. Current G+C has five `F3_EVAL_PIPELINE` rows, and `docs/06_failure_taxonomy_and_eval_ladder.md` plus `docs/07_analysis_and_statistics.md` define their methodology and analyzer caveats.

## 11. Boundary And Hash Gates

Some shared/Modal files are guarded by Phase -1 or frozen-boundary hash checks. The purpose is to block GPU spend or report-facing interpretation when the execution surface has drifted unexpectedly.

Relevant surfaces include:

- `shared/modal_harness/`;
- `cluster2/modal/`;
- `cluster2/contracts/phase_minus1_manifest.json`;
- `cluster2/contracts/frozen_cluster1_artifacts_manifest.json`;
- `shared/eval/content_hashes.py`;
- tests such as `cluster2/tests/test_cluster2_boundary.py`, `cluster2/tests/test_modal_generation_c2.py`, and `shared/tests/test_content_hashes.py`.

Hash mismatches should be diagnosed as behavior changes, accepted boundary updates, stale manifest entries, or true blockers. Accepted hash changes must be documented. Hashes should not be re-recorded as part of a documentation phase.

## 12. Current Authoritative Run Artifacts

Artifact identity and row counts are owned by `docs/05_artifacts_and_results_registry.md`:

- none: `outputs/cluster1/baseline_repaired_l4_n20.jsonl`, 180 rows;
- G: `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl`, 177 rows;
- C: `outputs/cluster2/c_paper_n20_l4.jsonl`, 180 rows;
- G+C: `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl`, 177 rows;
- analyzer: `outputs/analysis/factorial_2x2_preliminary.json`, valid JSON, 714 loaded rows, `metadata.reportable=true` via `analysis_cli_annotation`.

This page explains Modal/provenance context. It does not duplicate the full registry.

## 13. What This Document Does Not Claim

- Modal execution does not by itself prove reproducibility.
- No new Modal run is authorized by this document.
- No full final-paper statistical result is claimed beyond the verified, caveated 2^2 analyzer output.
- No timing, profiling, speedup, or performance result is claimed.
- No full 2^3 result is claimed.
- No Cluster 3 or `P` result is claimed.
- No missing or unknown provenance field is treated as harmless.
- No failed or partial run is treated as a current authoritative artifact unless it is explicitly registered.

## 14. Traceability

| Infrastructure claim | Code path | Test/audit path | Artifact evidence | Caveat |
|---|---|---|---|---|
| Shared Modal app/image/generation/compile surfaces exist | `shared/modal_harness/app.py`; `shared/modal_harness/images.py`; `shared/modal_harness/generation.py`; `shared/modal_harness/compile.py`; `cluster1/generation/modal_generate.py`; `cluster1/experiments/run_cluster1_modal.py` | `shared/tests/test_modal_harness_local_imports.py`; `shared/tests/test_modal_harness_schemas.py`; `shared/tests/test_modal_harness_compile.py`; `cluster1/tests/test_run_cluster1_modal.py` | G artifact and Cluster 1 run metadata fields | Cluster 1 is compile-only and does not run Level 2 |
| Cluster 2 uses isolated C2 generation/correctness Modal surfaces | `cluster2/modal/generation.py`; `cluster2/modal/correctness.py`; `cluster2/experiments/run_cluster2_modal.py` | `cluster2/tests/test_modal_generation_c2.py`; `cluster2/tests/test_modal_schemas.py`; `cluster2/tests/test_modal_correctness_check.py`; `cluster2/tests/test_run_cluster2_modal.py` | C and G+C artifacts | C/G+C are current; Cluster 3/P is deferred |
| Cluster 2 GPU policy uses L4 for C2 generation/evaluation | `cluster2/constants.py`; `cluster2/experiments/run_cluster2_modal.py`; `cluster2/modal/generation.py`; `cluster2/modal/correctness_runner.py` | `cluster2/tests/test_run_cluster2_modal.py`; `cluster2/tests/test_cluster2_boundary.py`; C/G+C run reports | C and G+C generated metadata and run audits | C1 shared default generation GPU remains separate from explicit C2 L4 policy |
| Provenance fields are recorded and validated | `shared/generation_metadata.py`; `cluster1/generation/provenance.py`; `shared/modal_harness/schemas.py`; `cluster2/modal/schemas.py`; `cluster1/results/dataclass.py`; `cluster2/results/dataclass.py` | `cluster1/tests/test_generation_provenance.py`; `shared/tests/test_generation_metadata_constants.py`; `cluster2/tests/test_results_logger.py`; `audits/modal_image_sha_provenance_fix_report.md` | G, C, and G+C artifacts | none baseline has legacy provenance gaps; G has `modal_image_sha=unknown` |
| Durable C2 row writing exists | `cluster2/results/logger.py`; `cluster2/experiments/run_cluster2_modal.py` | `cluster2/tests/test_results_logger.py`; `cluster2/tests/test_run_cluster2_modal.py`; `audits/c2_durable_result_writing_fix_report.md` | C and G+C JSONL artifacts plus sidecars | Durability still depends on underlying filesystem behavior; partial outputs need strict caveats |
| Malformed correctness payloads become F3 failures | `cluster2/experiments/run_cluster2_modal.py`; `shared/eval/failure_taxonomy.py`; `cluster2/feedback/trace.py` | `cluster2/tests/test_run_cluster2_modal.py`; `shared/tests/test_failure_taxonomy.py`; `audits/g_plus_c_correctness_payload_failure_fix_report.md`; `audits/cluster2_g_plus_c_paper_n20_l4_run_report.md` | G+C has five `F3_EVAL_PIPELINE` rows | F3 rows are not functional successes and remain visible analyzer caveats |
| Boundary/hash gates protect Modal and replay surfaces | `shared/eval/content_hashes.py`; `cluster2/modal/generation.py`; `cluster2/contracts/phase_minus1_manifest.json`; `cluster2/contracts/frozen_cluster1_artifacts_manifest.json` | `shared/tests/test_content_hashes.py`; `cluster2/tests/test_cluster2_boundary.py`; `cluster2/tests/test_modal_generation_c2.py`; `audits/shared_modal_smoke_boundary_hash_resolution_report.md`; `audits/g_plus_c_hash_gate_and_metadata_fix_report.md` | Frozen none/G controls and C/G+C sidecars | Do not update hashes casually or during documentation-only phases |
| Artifact registry owns current artifact identity | `docs/05_artifacts_and_results_registry.md` | `audits/repository_documentation_methodology_readiness_audit.md` | all four JSONL artifacts and analyzer JSON | Registry caveats must travel with any report-facing claim |

## 15. TODOs For Later Phases

- Phase 7 will extract a decision log into `docs/08_decision_log.md`.
- Phase 8 will align README and formal contracts after the citation-grade docs stabilize.
- Phase 9 will create the preliminary report outline.
- Phase 10 will translate Modal lessons into Cluster 3 drift-prevention guardrails.
- Before final report prose uses statistical results, verify the cited analyzer JSON still has `metadata.reportable=true` and preserve all visible caveats.
