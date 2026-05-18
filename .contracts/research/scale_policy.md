# Scale Policy

**Status:** authoritative scale vocabulary for development and reporting  
**Date:** 2026-05-11  
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

Every run config, JSONL sidecar, aggregate summary, and artifact filename should
record `scale_tier` using one of those values.

## Scale Tiers

| Tier | Purpose | Kernel set | Conditions | Samples | Model | Claim status |
| --- | --- | --- | --- | --- | --- | --- |
| `smoke` | Prove the code path runs end to end without crashing | 1 kernel | 1 condition | `n=1` | fast development model, currently `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ` | Infrastructure pass/fail only |
| `development` | Iterate on prompts, grammar variants, repair templates, feedback parsing, and harness behavior | 3 kernels, one per class | Active conditions under development | `n=3..5` | fast development model, currently `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ` | Directional indicators only |
| `paper` | Produce the reported results | Target 6-9 KernelBench problems balanced across elementwise, reduction, and matmul | Full factorial where applicable | `n=20` per sample cell | at least one larger model, currently planned as `Qwen/Qwen2.5-Coder-32B-Instruct` or `deepseek-ai/DeepSeek-Coder-V2-Instruct` | Reportable paper evidence |

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

Existing Cluster 1 artifacts such as
`outputs/cluster1/baseline_repaired_l4_n20.jsonl` and
`outputs/cluster1/final_g_l4_n20.jsonl` remain valid frozen artifacts. Future
analysis should attach explicit `scale_tier`, `kernel_count`, `model_id`, and
`grammar_variant` metadata to them before they are combined with other runs.

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
replication was run. Paper-scale current-grammar rows must pass the generation
metadata gate; legacy rows with `unknown`/missing provenance remain readable but
are not reportable paper-scale evidence.

## Analysis Rules

Smoke-scale data is never analyzed as research evidence. It is a pass/fail
infrastructure check.

Development-scale data may be plotted or summarized for engineering decisions,
but every artifact and figure must label it as development scale. It must not
appear in paper result tables.

Paper-scale data is the only data that supports final reported claims. Paper
tables must be generated from a manifest that lists the exact paper-scale
artifacts, kernel IDs, model IDs, seed schedule, and git hash.

Aggregators must reject mixed-scale analysis by default. A mixed-scale report
may exist only as an explicitly labeled diagnostic report.

## Cluster 1 Template-Grammar Reference Control

The current template Cluster 1 grammar was developed against the three-kernel
KernelBench subset: ReLU, Softmax, and GEMM. That is why it is useful as a
template G diagnostic/reference upper-bound control. It measures what happens
when the grammar is allowed to encode the selected task families.

Default paper-scale policy:

- keep the current template grammar frozen as `template_upper_bound` reference;
- report it only as reference/diagnostic on the original three-kernel subset
  unless a new contract says otherwise;
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

Only after Cluster 2 and Cluster 3 both reach stable development scale should
the project schedule a paper-scale factorial run.

## Paper Method Sentence

The paper methodology should include a sentence like:

> The reported results were generated at a fixed evaluation scale of n=20
> samples per cell across 6-9 KernelBench problems balanced across elementwise,
> reduction, and matmul classes, using model X at temperature Y with seed
> schedule Z. Pipeline development used a smaller subset and is not included in
> the reported results.

This is the clean separation reviewers need: development scale is preserved for
reproducibility, but only paper scale supports the paper claims.
