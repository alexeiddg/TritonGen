# Scale Policy

**Status:** authoritative scale vocabulary for development and preliminary reporting  
**Last aligned:** 2026-05-21  
**Applies to:** all clusters, shared eval, Modal harness runs, analysis outputs

## Purpose

This project intentionally uses different experimental scales at different
engineering maturity levels. That is normal for ML systems work. The important
rule is that every run must say which scale produced it, and analysis must not
mix development-scale data with paper-scale claims.

The canonical tiers are:

```text
smoke
development
paper
```

Every future run config, row schema, JSONL sidecar, aggregate summary, registry
entry, and artifact filename should record `scale_tier` using one of those
values. The current registered 2^2 artifacts predate row-level scale-tier
serialization; they are handled through explicit analyzer annotation recorded in
analyzer metadata, not by rewriting raw JSONL.

## Scale Tiers

| Tier | Purpose | Kernel set | Conditions | Samples | Model | Claim status |
| --- | --- | --- | --- | --- | --- | --- |
| `smoke` | Prove the code path runs end to end without crashing | 1 kernel | 1 condition | `n=1` | fast development model, currently `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ` | Infrastructure pass/fail only |
| `development` | Iterate on prompts, grammar variants, repair templates, feedback parsing, and harness behavior | 3 kernels, one per class | Active conditions under development | `n=3..5` | fast development model, currently `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ` | Directional indicators only |
| `paper` | Produce reported or report-candidate results | Current preliminary artifacts use the locked three-class KernelBench subset; future final paper runs may expand after new contracts | Current preliminary 2^2 cells; future full factorial only after P is defined | `n=20` per sample cell target | recorded per artifact | Report-facing only when registered and not blocked by caveats |

A sample cell is the unit that receives `n` samples. At minimum it is
`(kernel_id, condition)`. If dtype, grammar variant, prompt version, or model is
varied within a run, those fields are part of the sample-cell identity too. For
the current Cluster 1 artifacts, dtype is part of the effective cell identity.

## Promotion Rules

Runs must move through the tiers in order:

```text
smoke -> development -> paper
```

Do not run paper scale until development-scale runs are stable enough that
their outcomes are directional rather than random infrastructure noise. A
development-scale repair loop is not stable if repair iterations, failure
classes, or pass rates swing sharply between adjacent runs with the same code
and seed schedule.

Promotion requirements:

- `smoke` passes before enabling parallelism or more conditions;
- `development` produces stable directional findings before paper scale;
- prompts, grammars, feedback templates, seed schedule, kernel set, and eval
  gates are frozen before a paper-scale run starts;
- no prompt, grammar, harness, or eval change is made after a paper-scale run
  starts unless the run is invalidated and restarted under a new `run_id`.

## Current Preliminary N20 Artifacts

The current preliminary handoff has registered n=20 artifacts in
`docs/05_artifacts_and_results_registry.md`:

| Condition | Artifact | Rows | Intended rows | Current status |
| --- | --- | ---: | ---: | --- |
| `none` | `outputs/cluster1/baseline_repaired_l4_n20.jsonl` | 180 | 180 | authoritative control with legacy schema/provenance caveats |
| `G` | `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` | 177 | 180 | authoritative task-agnostic G artifact with coverage caveat |
| `C` | `outputs/cluster2/c_paper_n20_l4.jsonl` | 180 | 180 | authoritative C artifact; compile success normalized from failure code |
| `G+C` | `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` | 177 | 180 | authoritative G+C artifact with coverage and F3 caveats |

Current G and G+C coverage is 177/180, not complete 180/180 coverage. Missing
rows are `matmul/fp32` seed 5 and `matmul/bf16` seeds 0 and 18. Old n=5
artifacts are development/legacy evidence unless explicitly promoted into the
artifact registry.

The analyzer output at `outputs/analysis/factorial_2x2_preliminary.json` is
valid JSON, loads 714 rows, and records `metadata.reportable=true`,
`metadata.scale_tiers=["paper"]`,
`metadata.raw_scale_tiers_before_annotation=["unspecified"]`,
`metadata.scale_tier_source="analysis_cli_annotation"`, and
`metadata.requested_scale_tier="paper"`. The raw none/G/C/G+C JSONL artifacts
were not rewritten; the paper scale label is attached at analysis time for this
legacy/current artifact set.

Current C/G+C artifacts record `max_new_tokens=2048` according to the artifact
registry and Phase 0/7 evidence. Older `1536` token-budget references are
historical unless a future code/config review re-promotes them for a new run.

## Phase 4 Evidence And Grammar Hash Sequencing

Baseline revalidation is diagnostic comparison, not regeneration. The frozen
none baseline artifact must not be rewritten. The accepted post-fix Phase 4
evidence path is
`outputs/cluster1/diagnostics/baseline_revalidation_aligned_pipeline_parse_reclassification.jsonl`.
It must show all 180 frozen rows evaluated under the aligned C1 and C2
entrypoints, zero compile-success drift, and zero entrypoint disagreement.

Real baseline revalidation requires a Modal GPU environment because Triton dummy
compile is CUDA-dependent. L4 is the preferred evidence class because the
original baseline used L4; A10 is the only acceptable documented fallback. T4 or
lower and local-only mocked evidence are insufficient to close the baseline
comparability gate.

The Cluster 1 grammar hash gate is sequenced after passing Phase 4 evidence and
before Phase 5. The hash gate is not resolved by evaluation alignment itself.
Re-recording or reconciling grammar provenance before baseline revalidation is
complete is not acceptable, because the baseline evidence is what establishes
that the current aligned pipeline is stable enough to trust the provenance
update.

## Artifact Naming

Future artifact names should make the scale obvious without opening the file.
Use this convention for new outputs:

```text
{cluster}_{scale_tier}_{condition_set}_k{kernel_count}_n{sample_count}_{model_alias}_{run_id}.jsonl
```

Examples:

```text
cluster2_smoke_C_k1_n1_qwen7b_20260511.jsonl
cluster2_development_C-GC_k3_n5_qwen7b_20260511.jsonl
cluster3_development_P-GP-CP-GCP_k3_n5_qwen7b_20260511.jsonl
factorial_paper_all8_k9_n20_qwen32b_20260601.jsonl
```

Existing registered artifacts such as
`outputs/cluster1/baseline_repaired_l4_n20.jsonl`,
`outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl`,
`outputs/cluster2/c_paper_n20_l4.jsonl`, and
`outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` remain the current authoritative
2^2 artifacts. Template-G, n=5, smoke, failed, and partial artifacts are
historical or diagnostic unless promoted into the registry with row counts,
schema, provenance, and caveats.

The old template artifact `outputs/cluster1/final_g_l4_n20.jsonl` is registered
only as legacy diagnostic/reference material. Its 180/180 legacy compile result
does not make it current paper-scale primary G; it remains current-excluded
unless a new template G lineage and matching template G+C lineage are rerun
under the current metadata policy and analyzed separately as non-primary
diagnostics.

## Required Run Metadata

Every run should record:

- `scale_tier`;
- `run_id`;
- `cluster`;
- `condition_set`;
- `kernel_count`;
- `kernel_ids`;
- `kernel_classes`;
- `sample_size`;
- `sample_cell_keys`;
- `model_id`;
- `model_alias`;
- `temperature`;
- `max_new_tokens`;
- `seed_schedule`;
- `dtypes`;
- `grammar_variant` when G is enabled;
- per-row G metadata for current G/G+C rows:
  `grammar_sha`, `grammar_path`, `gbnf_parse_valid`, `semantic_valid`,
  `grammar_valid`, `rejection_layer`, and `stop_reason`;
- per-row runtime/model provenance:
  `xgrammar_version`, `transformers_version`, `tokenizers_version`,
  `model_revision`, `tokenizer_revision`, and `modal_image_sha` or
  `modal_image_provenance_sha256`;
- `repair_budget`;
- `max_eval_level`;
- `modal_generation_gpu`;
- `modal_eval_gpu`;
- `git_hash`;
- `artifact_path`;
- `frozen_for_paper` boolean.

For paper-scale runs, also record the final prompt version, grammar version,
feedback-template version, eval-suite version, and whether a secondary model
replication was run. Future paper-scale current-grammar rows must pass the
generation metadata gate and must serialize `scale_tier`. Legacy/current rows
with missing scale-tier fields or `unknown` provenance remain readable only
under explicit registry and analyzer caveats; they must not be silently promoted
by default.

## Analysis Rules

Smoke-scale data is never analyzed as research evidence. It is a pass/fail
infrastructure check.

Development-scale data may be plotted or summarized for engineering decisions,
but every artifact and figure must label it as development scale. It must not
appear in paper result tables.

Paper-scale or preliminary-scale data supports report-facing claims only when
registered and not blocked by reportability caveats. Paper tables must be
generated from a manifest or registry entry that lists the exact artifacts,
kernel IDs, model IDs, seed schedule, and git hash where available.

Aggregators must reject mixed-scale analysis by default. A mixed-scale report
may exist only as an explicitly labeled diagnostic report.

Analyzer scale-tier handling:

- Current legacy/current 2^2 artifacts may use explicit analyzer annotation
  because raw rows lack `scale_tier`, provided the analyzer records
  `scale_tier_source`, `requested_scale_tier`, and
  `raw_scale_tiers_before_annotation`.
- CLI annotation may fill missing legacy row tiers only when the registry,
  manifest, or analysis policy authorizes that exact artifact set.
- Future artifacts, including Cluster 3/P rows, must persist `scale_tier` in
  rows and registry entries; CLI annotation is not the normal path for future
  paper-scale rows.
- In short, future rows must include `scale_tier`, and registry entries must
  include `scale_tier`.
- Analyzer reportability must reject conflicts between explicit raw row
  `scale_tier`, registry/manifest scale tier, and invocation annotation.

## Cluster 1 Template-Grammar Reference Control

The current template Cluster 1 grammar was developed against the three-kernel
KernelBench subset: ReLU, Softmax, and GEMM. That is why it is useful as a
template G diagnostic/reference upper-bound control. It measures what happens
when the grammar is allowed to encode the selected task families.

Default paper-scale policy:

- keep the current template grammar frozen as `template_upper_bound` reference;
- report it only as reference/diagnostic on the original three-kernel subset
  unless a new contract says otherwise;
- keep old template artifacts such as `outputs/cluster1/final_g_l4_n20.jsonl`
  outside the current primary analyzer unless explicitly rerun under current
  metadata and paired with matching template G+C diagnostic evidence;
- do not expand the diagnostic/reference template grammar merely to cover the larger paper-scale
  kernel set;
- use the task-agnostic Triton grammar for the primary task-agnostic G condition
  on the larger paper-scale kernel set.

If the diagnostic/reference template grammar is expanded to encode 6-9 paper-scale kernels, the run
must be labeled as a new task-aware template upper bound, not as general
task-agnostic G enforcement for Triton generation. Expanding the diagnostic/reference template grammar strengthens
the task-encoding control; it does not become the primary task-agnostic G
condition.

## Cluster Sequencing

Cluster 2 should be built first at smoke scale:

```text
one kernel, condition C, n=1, development model
```

Once the C loop runs end to end, promote it to development scale:

```text
three kernels, active C conditions, n=3..5, development model
```

Cluster 3 should follow the same pattern:

```text
one kernel, condition P, n=1 -> three kernels, active P conditions, n=3..5
```

Cluster 3/P is deferred. Do not schedule or report P-containing paper-scale
runs until P semantics, failure boundaries, artifact schema, analyzer behavior,
and registry rules are defined.

## Preliminary Method Sentence

The preliminary handoff methodology should include a sentence like:

> The current preliminary registered artifacts cover the 2^2 subset over none,
> G, C, and G+C at an n=20 target over the locked elementwise, reduction, and
> matmul archetypes. The task-agnostic G and G+C artifacts are 177/180 and the
> analyzer output is reportable for the covered 2^2 scope through explicit
> paper-scale analysis annotation, with raw rows still recorded as missing
> row-level `scale_tier` before annotation.

This preserves the separation reviewers need: development scale is preserved
for reproducibility, while current report-facing claims must cite the registry
and carry row-count and reportability caveats.
